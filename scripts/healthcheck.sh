#!/bin/bash

# Health check script for Certbot DNSExit
# Exit codes: 0=healthy, 1=unhealthy

set -e

# Configuration
CERT_DIR="/etc/letsencrypt/live"
LOG_FILE="/var/log/letsencrypt/certbot.log"
MAX_CERT_AGE_HOURS="${HEALTH_CHECK_CERT_AGE_HOURS:-1080}"  # 45 days default
API_TIMEOUT="${HEALTH_CHECK_API_TIMEOUT:-10}"
STRICT_MODE="${HEALTH_CHECK_STRICT_MODE:-false}"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] HEALTH: $*" >&2
}

# Level 1: Basic filesystem check
check_filesystem() {
    log "Checking filesystem..."

    # Check if certificate directory exists
    if [ ! -d "$CERT_DIR" ]; then
        log "ERROR: Certificate directory $CERT_DIR does not exist"
        return 1
    fi

    # Check if log file exists and is writable
    if [ ! -f "$LOG_FILE" ] || [ ! -w "$LOG_FILE" ]; then
        log "ERROR: Log file $LOG_FILE is not accessible"
        return 1
    fi

    log "Filesystem check passed"
    return 0
}

# Level 2: Certificate validity check
check_certificates() {
    log "Checking certificate validity..."

    local cert_found=false
    local cert_errors=0

    # Find domains with certificates
    while IFS= read -r -d '' cert; do
        cert_found=true
        domain=$(basename "$(dirname "$cert")")

        # Get certificate expiration date
        if ! expiry_date=$(openssl x509 -in "$cert" -noout -enddate 2>/dev/null | cut -d= -f2); then
            log "ERROR: Cannot read certificate $cert"
            ((cert_errors++))
            continue
        fi

        # Convert to seconds since epoch (cross-platform)
        if command -v gdate >/dev/null 2>&1; then
            # macOS
            expiry_seconds=$(gdate -d "$expiry_date" +%s 2>/dev/null)
        else
            # Linux
            expiry_seconds=$(date -d "$expiry_date" +%s 2>/dev/null)
        fi

        if [ -z "$expiry_seconds" ] || [ "$expiry_seconds" = "0" ]; then
            log "ERROR: Cannot parse expiry date for $domain: $expiry_date"
            ((cert_errors++))
            continue
        fi

        current_seconds=$(date +%s)
        age_hours=$(( (expiry_seconds - current_seconds) / 3600 ))

        if [ $age_hours -lt 0 ]; then
            log "ERROR: Certificate for $domain has expired (${age_hours}h ago)"
            ((cert_errors++))
        elif [ $age_hours -lt 24 ]; then
            log "WARNING: Certificate for $domain expires in ${age_hours}h"
            if [ "$STRICT_MODE" = "true" ]; then
                ((cert_errors++))
            fi
        else
            log "Certificate for $domain is valid (${age_hours}h remaining)"
        fi
    done < <(find "$CERT_DIR" -name "fullchain.pem" -print0 2>/dev/null)

    if [ "$cert_found" = "false" ]; then
        log "WARNING: No certificates found - this may be normal for initial setup"
        return 0  # Not critical for health
    fi

    if [ $cert_errors -gt 0 ]; then
        log "Certificate check failed: $cert_errors errors found"
        return 1
    fi

    log "Certificate check passed"
    return 0
}

# Level 3: API connectivity check (disabled - not required for certificate renewal)
check_api_connectivity() {
    log "API connectivity check skipped (not required for certificate renewal)"
    return 0
}

# Level 4: Process health check
check_process_health() {
    log "Checking process health..."

    local process_errors=0

    # Check if certbot process is running (in daemon mode)
    if pgrep -f "certbot" >/dev/null 2>&1; then
        log "Certbot process is running"
    else
        # In one-time mode, this might be normal
        if [ "${RENEWAL_INTERVAL:-86400}" = "0" ]; then
            log "One-time mode detected, no certbot process expected"
        else
            log "WARNING: No certbot process found in daemon mode"
            if [ "$STRICT_MODE" = "true" ]; then
                ((process_errors++))
            fi
        fi
    fi

    # Check recent log activity (last 30 minutes)
    if [ -f "$LOG_FILE" ]; then
        # Use find to check if log file was modified recently
        if find "$LOG_FILE" -mmin -30 >/dev/null 2>&1; then
            log "Recent log activity detected"
        else
            log "WARNING: No recent log activity (last 30 minutes)"
            if [ "$STRICT_MODE" = "true" ]; then
                ((process_errors++))
            fi
        fi
    fi

    if [ $process_errors -gt 0 ]; then
        log "Process health check failed: $process_errors errors"
        return 1
    fi

    log "Process health check passed"
    return 0
}

# Export metrics for monitoring systems (optional)
export_metrics() {
    if [ -n "$HEALTH_METRICS_FILE" ]; then
        mkdir -p "$(dirname "$HEALTH_METRICS_FILE")"
        echo "# Certbot DNSExit Health Metrics" > "$HEALTH_METRICS_FILE"
        echo "certbot_health_last_check $(date +%s)" >> "$HEALTH_METRICS_FILE"
        echo "certbot_health_status 1" >> "$HEALTH_METRICS_FILE"
        log "Metrics exported to $HEALTH_METRICS_FILE"
    fi
}

# Main health check execution
main() {
    local failed_checks=()
    local start_time=$(date +%s)

    log "Starting health check..."

    # Execute checks (continue on failure to collect all issues)
    set +e

    if ! check_filesystem; then
        failed_checks+=("filesystem")
    fi

    if ! check_certificates; then
        failed_checks+=("certificates")
    fi

    if ! check_api_connectivity; then
        failed_checks+=("api_connectivity")
    fi

    if ! check_process_health; then
        failed_checks+=("process_health")
    fi

    set -e

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    # Export metrics if requested
    export_metrics

    # Report results
    if [ ${#failed_checks[@]} -eq 0 ]; then
        log "All health checks passed ✅ (took ${duration}s)"
        exit 0
    else
        log "Health check failed ❌ - Failed checks: ${failed_checks[*]} (took ${duration}s)"
        exit 1
    fi
}

main "$@"