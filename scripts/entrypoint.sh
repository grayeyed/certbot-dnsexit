#!/bin/bash

# DNS Exit Certbot Entrypoint Script (Adapted from Cloudflare version)
# https://github.com/serversideup/docker-certbot-dns-cloudflare
# This script orchestrates the certificate generation/renewal process

default_uid=1000  # Default UID/GID of the 'certbot' user created in the Dockerfile
default_gid=1000  # This ensures is_default_privileges() works correctly with the Dockerfile's default
default_unprivileged_user=certbot
default_unprivileged_group=certbot

# Configuration
CERTBOT_DIR="${CERTBOT_DIR:-/etc/letsencrypt}"
WORK_DIR="${WORK_DIR:-/var/lib/letsencrypt}"

# Handle LOG_FILE logic: if not set by user, don't log to file
if [ "${LOG_FILE:-NOT_SET}" = "NOT_SET" ]; then
    LOG_FILE="/var/log/letsencrypt/certbot.log"
    LOG_FILE_SET_BY_USER=false
else
    LOG_FILE_SET_BY_USER=true
fi

# Set LOG_LEVEL environment variable for Python scripts (preserve existing value or default to INFO)
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

################################################################################
# Functions
################################################################################

log() {
    message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"

    # If LOG_FILE not set by user, output only to stdout
    if [ "$LOG_FILE_SET_BY_USER" = "true" ]; then
        echo "$message" | tee -a "$LOG_FILE"
    else
        echo "$message"
    fi
}

cleanup() {
    log "Shutdown requested, exiting gracefully..."
    exit 0
}

debug_print() {
    if [ "$LOG_LEVEL" = "DEBUG" ]; then
        echo "$1"
    fi
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

configure_uid_and_gid() {
    debug_print "Preparing environment for $PUID:$PGID..."

    # Handle existing user with the same UID
    if id -u "${PUID}" >/dev/null 2>&1; then
        old_user=$(id -nu "${PUID}")
        debug_print "UID ${PUID} already exists for user ${old_user}. Moving to a new UID."
        usermod -u "999${PUID}" "${old_user}"
    fi

    # Handle existing group with the same GID
    if getent group "${PGID}" >/dev/null 2>&1; then
        old_group=$(getent group "${PGID}" | cut -d: -f1)
        debug_print "GID ${PGID} already exists for group ${old_group}. Moving to a new GID."
        groupmod -g "999${PGID}" "${old_group}"
    fi

    # Change UID and GID of  run_as user and group
    usermod -u "${PUID}" "${default_unprivileged_user}" 2>&1 >/dev/null || log "Error changing user ID."
    groupmod -g "${PGID}" "${default_unprivileged_user}" 2>&1 >/dev/null || log "Error changing group ID."

    # Ensure the correct permissions are set for all required directories
    chown -R "${default_unprivileged_user}:${default_unprivileged_group}" \
        "$CERTBOT_DIR" \
        "$WORK_DIR" \
        "$(dirname "$LOG_FILE")"
}

configure_windows_file_permissions() {
    # Permissions must be created after volumes have been mounted; otherwise, windows file system permissions will override
    # the permissions set within the container.
    mkdir -p "$CERTBOT_DIR/accounts" "$(dirname "$LOG_FILE")" "$WORK_DIR"
    chmod 755 "$CERTBOT_DIR" "$WORK_DIR"
    chmod 700 "$CERTBOT_DIR/accounts" "$(dirname "$LOG_FILE")"
}

# Workaround https://github.com/microsoft/wsl/issues/12250 by replacing symlinks with direct copies of the files they
# reference.
replace_symlinks() {
    target_dir="$1"

    # Iterate over all items in the directory
    for item in "$target_dir"/*; do
        if [ -L "$item" ]; then
            # If the item is a symlink
            target=$(readlink -f "$item")
            if [ -e "$target" ]; then
                log "Replacing symlink $item with a copy of $target"
                cp -r "$target" "$item"
            else
                log "Warning: target $target of symlink $item does not exist"
            fi
        elif [ -d "$item" ]; then
            # If the item is a directory, process it recursively
            replace_symlinks "$item"
        fi
    done
}

is_default_privileges() {
    [ "${PUID:-$default_uid}" = "$default_uid" ] && [ "${PGID:-$default_gid}" = "$default_gid" ]
}

run_certbot() {
    # Ensure the log directory is set to 700
    chmod 700 "$(dirname "$LOG_FILE")"
    chown "${PUID}:${PGID}" "$(dirname "$LOG_FILE")"

    if is_default_privileges; then
        certbot_cmd="certbot"
    else
        certbot_cmd="su-exec ${default_unprivileged_user} certbot"
    fi

    debug_print "Running certbot with command: $certbot_cmd"

    # Get domains from environment variable
    DOMAINS_LIST="$DOMAINS"

    # Get extra arguments for certbot certonly from environment
    CERTBOT_EXTRA_ARGS="$CERTBOT_CERTONLY_EXTRA_ARGS"

    if [ -z "$DOMAINS_LIST" ]; then
        error_exit "No domains specified in configuration"
    fi

    # Convert comma-separated domains to certbot format (simplified)
    CERTBOT_DOMAINS=""
    for domain in $(echo "$DOMAINS_LIST" | tr ',' '\n'); do
        domain=$(echo "$domain" | xargs)  # trim whitespace
        CERTBOT_DOMAINS="$CERTBOT_DOMAINS -d $domain"
    done

    # Parse extra arguments safely
    if [ -n "$CERTBOT_EXTRA_ARGS" ]; then
        IFS=' ' read -ra EXTRA_ARGS <<< "$CERTBOT_EXTRA_ARGS"
    else
        EXTRA_ARGS=()
    fi

    $certbot_cmd certonly \
        --manual \
        --manual-auth-hook /app/src/auth_hook.py \
        --manual-cleanup-hook /app/src/cleanup_hook.py \
        --preferred-challenges dns \
        $VERBOSE_FLAGS \
        $CERTBOT_DOMAINS \
        --email "$LETSENCRYPT_EMAIL" \
        --agree-tos \
        --non-interactive \
        "${EXTRA_ARGS[@]}"

    exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log "Error: certbot command failed with exit code $exit_code"
        return $exit_code  # Return error code instead of exiting
    fi

    if [ "$REPLACE_SYMLINKS" = "true" ]; then
        replace_symlinks "$CERTBOT_DIR/live"
    fi

    return 0
}

validate_environment_variables() {
    # Load DNSEXIT_API_KEY from Docker secret if available
    if [ -f "/run/secrets/dnsexit_api_key" ]; then
        export DNSEXIT_API_KEY=$(cat "/run/secrets/dnsexit_api_key" | tr -d '\n')
        log "Loaded DNSEXIT_API_KEY from Docker secret"
    fi

    # Validate required environment variables
    for var in DNSEXIT_API_KEY LETSENCRYPT_EMAIL; do
        if [ -z "$(eval echo \$$var)" ]; then
            error_exit "$var environment variable is not set"
        fi
    done
}

# Set certbot verbosity based on LOG_LEVEL
case "$LOG_LEVEL" in
    QUIET)
        VERBOSE_FLAGS=""
        log "Running in quiet mode - minimal output"
        ;;
    DEBUG)
        VERBOSE_FLAGS="-vvv"
        log "Setting Certbot verbosity to $VERBOSE_FLAGS (LOG_LEVEL: $LOG_LEVEL)"
        ;;
    INFO)
        VERBOSE_FLAGS="-vv"
        log "Setting Certbot verbosity to $VERBOSE_FLAGS (LOG_LEVEL: $LOG_LEVEL)"
        ;;
    WARNING|ERROR)
        VERBOSE_FLAGS="-v"
        log "Setting Certbot verbosity to $VERBOSE_FLAGS (LOG_LEVEL: $LOG_LEVEL)"
        ;;
    *)
        VERBOSE_FLAGS=""
        log "LOG_LEVEL $LOG_LEVEL not recognized for Certbot verbosity, using default (no extra verbosity)"
        ;;
esac

################################################################################
# Main
################################################################################

# Initialize variables early
DOMAINS_LIST="$DOMAINS"
RENEWAL_INTERVAL="${RENEWAL_INTERVAL:-86400}"
CERTBOT_EXTRA_ARGS="$CERTBOT_CERTONLY_EXTRA_ARGS"

trap cleanup TERM INT

validate_environment_variables

if ! is_default_privileges; then
    configure_uid_and_gid
fi

if [ "$REPLACE_SYMLINKS" = "true" ]; then
    configure_windows_file_permissions
fi

cat <<"EOF"
      .-.
     (o o)  Hello!
     |=-|=  I'm Certbot,
    /     \  ready to
   /       \ encrypt your
  /         \ world!
  '---------'
EOF

log "🚀 Let's Get Encrypted! 🚀"
log "🌐 Domain(s): $DOMAINS_LIST"
log "📧 Email: $LETSENCRYPT_EMAIL"
log "⏰ DNS Propagation Wait: ${DNS_PROPAGATION_WAIT:-300} seconds"
log "🔧 Extra Certbot Args: ${CERTBOT_EXTRA_ARGS:-none}"
log "Let's Encrypt, shall we?"
log "-----------------------------------------------------------"


# Check if a command was passed to the container
if [ $# -gt 0 ]; then
    if is_default_privileges; then
        exec "$@"
    else
        exec su-exec "${default_unprivileged_user}" "$@"
    fi
else
    # Run certbot initially to get the certificates
    run_certbot

    # If RENEWAL_INTERVAL is set to 0, do not attempt to renew certificates and exit immediately
    if [ "$RENEWAL_INTERVAL" = "0" ]; then
        log "Let's Encrypt Renewals are disabled because RENEWAL_INTERVAL=0. Running once and exiting..."
        cleanup
    fi

    # Infinite loop to keep the container running and periodically check for renewals
    while true; do
        # POSIX-compliant way to show next run time
        current_timestamp=$(date +%s)
        next_timestamp=$((current_timestamp + RENEWAL_INTERVAL))
        next_run=$(date -r "$next_timestamp" '+%Y-%m-%d %H:%M:%S %z' 2>/dev/null || date '+%Y-%m-%d %H:%M:%S %z')
        log "Next certificate renewal check will be at ${next_run}"

        # Store PID of sleep process and wait for it
        sleep "$RENEWAL_INTERVAL" &
        sleep_pid=$!
        wait $sleep_pid
        wait_status=$?

        # Check if we received a signal (more portable check)
        case $wait_status in
        0) : ;; # Normal exit
        *) cleanup ;;
        esac

        if ! run_certbot; then
            log "Error: Certificate renewal failed. Will retry in $RENEWAL_INTERVAL seconds."
        fi
    done
fi
