# DNS Exit Certbot - Detailed Usage Guide

This comprehensive guide provides detailed operational instructions and advanced scenarios for the Certbot DNSExit application. Start with [README.md](README.md) for project overview and basic setup.

## Table of Contents

- [Configuration](#configuration)
- [Advanced Certbot Arguments](#advanced-certbot-arguments)
- [Automation](#automation)
- [Troubleshooting](#troubleshooting)
- [Development](#development)
- [Security Operations](#security-operations)

## Detailed Setup Instructions

```bash
# Build the Docker image
docker build -t certbot-dnsexit .

# Or use docker compose
docker compose build
```

### 2. Configuration

#### Option A: Using Environment Variables (Recommended)
Create a `.env` file:
```bash
# Required
LETSENCRYPT_EMAIL=your-email@example.com

# Optional
DOMAINS=example.com,*.example.com
LOG_LEVEL=INFO
RENEWAL_INTERVAL=86400
CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal
```

**Note:** `DNSEXIT_API_KEY` is now loaded automatically from Docker secrets when using docker compose.

#### Option B: Using Environment Variables (Alternative)
All configuration can be done via environment variables in your `.env` file:
```bash
# Required
LETSENCRYPT_EMAIL=your-email@example.com

# Optional
DOMAINS=example.com,*.example.com
DNS_PROPAGATION_WAIT=60
DNS_PROPAGATION_ADDRESS=ns11.dnsexit.com
DNS_FINALIZATION_WAIT=5
LOG_LEVEL=INFO
RENEWAL_INTERVAL=86400
CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal
```

### 3. Run the Container

#### Using Docker Compose (Recommended)
```bash
# Create directories for persistent storage
mkdir -p ./certs ./config

# Copy environment template
cp .env.example .env
# Edit .env with your values

# Run certificate generation
docker compose up

# For initial testing with debug output
docker compose run --rm certbot LOG_LEVEL=DEBUG
```

#### Using Docker Directly
```bash
# Create directories
mkdir -p ./certs ./config

# Run certificate generation
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your-email@example.com \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit

# For initial testing with debug output
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your-email@example.com \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

## Environment Variables Reference

Complete list of configuration parameters with **priority order** (environment variables override defaults):

### Required Variables (Must be set)
| Variable | Description | Example | Notes |
|----------|-------------|---------|-------|
| `DNSEXIT_API_KEY` | DNSExit API key for DNS management | `abc123def456` | Auto-loaded from Docker secrets |
| `LETSENCRYPT_EMAIL` | Email for Let's Encrypt registration | `admin@example.com` | Required |

### Optional Variables (Override defaults)
| Variable | Description | Default | Priority |
|----------|-------------|---------|----------|
| `DOMAINS` | Comma-separated domains | From environment | High |
| `LOG_LEVEL` | Logging verbosity level (QUIET, DEBUG, INFO, WARNING, ERROR, CRITICAL). QUIET shows only errors. Also controls Certbot verbosity: DEBUG->-vvv, INFO->-vv, WARNING/ERROR->-v | `INFO` | High |
| `RENEWAL_INTERVAL` | Renewal check interval in seconds. Set to 0 to run once and exit. | `86400` (1 day) | High |
| `CERTBOT_CERTONLY_EXTRA_ARGS` | Additional arguments for `certbot certonly` command as a single string. | (none) | High |
| `DNS_PROPAGATION_WAIT` | DNS propagation wait time in seconds | `300` | High |
| `DNS_PROPAGATION_ADDRESS` | DNS server for propagation checks | `ns12.dnsexit.com` | High |
| `DNS_FINALIZATION_WAIT` | Additional wait after DNS propagation | `5` | High |
| `PUID` | User ID the container runs as. Default: 0 (root). For security, run as a non-root user (e.g., 1000). | `0` | High |
| `PGID` | Group ID the container runs as. Default: 0 (root). For security, run as a non-root group (e.g., 1000). | `0` | High |

### Configuration Validation

#### Check Current Configuration
```bash
# View effective configuration
docker run --rm \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=test@example.com \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit \
  /app/scripts/entrypoint.sh --dry-run # Note: --dry-run is a conceptual test, not a direct script arg
```

#### Test Configuration Priority
```bash
# Test environment variable override
export DOMAINS="override.com,test.com"
docker compose run --rm certbot
# Will use override.com domains
```

## Directory Structure

```
certs/
├── live/           # Symlinks to latest certificates
├── archive/        # All certificate versions
├── renewal/        # Renewal configuration files
└── accounts/       # Let's Encrypt account info

.env.example       # Environment variables template
```

## Certificate Locations

After successful generation, certificates are stored in:
- `certs/live/[domain]/fullchain.pem` - Full certificate chain
- `certs/live/[domain]/privkey.pem` - Private key
- `certs/live/[domain]/cert.pem` - Certificate only
- `certs/live/[domain]/chain.pem` - Intermediate certificates

## Testing

### 1. Test with Debug Logging
Always test with debug mode first to validate configuration:
```bash
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your-email@example.com \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

### 2. Check Logs
```bash
# View logs
docker compose logs certbot

# Or check log file (if LOG_FILE is set)
cat /var/log/letsencrypt/certbot.log
```

### 3. Verify Certificate
```bash
# Check certificate details
openssl x509 -in certs/live/example.com/fullchain.pem -text -noout

# Check expiration
openssl x509 -enddate -noout -in certs/live/example.com/fullchain.pem
```

## Advanced Configuration

### Health Check Configuration

The application includes comprehensive Docker health checking capabilities with configurable parameters:

```bash
# Environment variables for health checks (future feature)
HEALTH_CHECK_CERT_AGE_HOURS=1080    # Maximum certificate age before health check fails (7 days)
HEALTH_CHECK_STRICT_MODE=false     # Fail health check on warnings (true) or only on errors (false)
HEALTH_METRICS_FILE="/tmp/health_metrics.prom"  # Optional Prometheus metrics export
```

#### Health Check Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `HEALTH_CHECK_CERT_AGE_HOURS` | Max certificate age before failure | `168` (7 days) | `24` |
| `HEALTH_CHECK_API_TIMEOUT` | API connectivity timeout | `10` | `5` |
| `HEALTH_CHECK_STRICT_MODE` | Fail on warnings vs errors only | `false` | `true` |
| `HEALTH_METRICS_FILE` | Path to export Prometheus metrics | (none) | `/tmp/metrics.prom` |

### Tuning Parameters

```bash
# Performance tuning via environment variables
MAX_RETRIES=5
DELAY_BETWEEN_ATTEMPTS=300
DNS_PROPAGATION_WAIT=60
LOG_LEVEL=INFO
LOG_RETAIN_DAYS=30
CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal --rsa-key-size 4096
```

## Logging Configuration

The application provides comprehensive logging capabilities with support for multiple log levels and structured output. By default, logs are written to console (stdout) for Docker log aggregation. File logging can be enabled by explicitly setting the LOG_FILE environment variable.

### Log Levels

The application supports five logging levels that can be controlled via the `LOG_LEVEL` environment variable:

| Level | Description | Use Case |
|-------|-------------|----------|
| `QUIET` | Only error messages and above | Minimal output for production |
| `DEBUG` | Detailed diagnostic information | Troubleshooting and development |
| `INFO` | General information about application progress | Normal operation monitoring |
| `WARNING` | Warning messages about potential issues | Non-critical problems that should be noted |
| `ERROR` | Error events that might still allow the application to continue | Recoverable errors |
| `CRITICAL` | Critical errors that will likely lead to abort | Severe problems requiring immediate attention |

### Interaction with Certbot Verbosity

The `LOG_LEVEL` environment variable not only controls the verbosity of the application's and Python scripts' logging but also dynamically configures the verbosity of Certbot itself through the `VERBOSE_FLAGS` internal variable:

| `LOG_LEVEL` | Application Log Level | Certbot Verbosity (`VERBOSE_FLAGS`) |
|-------------|-----------------------|-------------------------------------|
| `QUIET`     | ERROR                 | `` (Default verbosity)              |
| `DEBUG`     | DEBUG                 | `-vvv` (Maximum verbosity)          |
| `INFO`      | INFO                  | `-vv` (High verbosity)              |
| `WARNING`   | WARNING               | `-v` (Standard verbosity)           |
| `ERROR`     | ERROR                 | `-v` (Standard verbosity)           |
| `CRITICAL`  | CRITICAL              | `` (Default verbosity)              |
| *Other*     | INFO (default)        | `` (Default verbosity)              |

Additionally, when `LOG_LEVEL` is set to `DEBUG`, the entrypoint script (`/app/scripts/entrypoint.sh`) enables its own debug mode (`set -x`), showing executed commands.

### Setting Log Level

Control the logging verbosity by setting the `LOG_LEVEL` environment variable:

```bash
# In .env file
LOG_LEVEL=DEBUG

# Or as environment variable
export LOG_LEVEL=WARNING
docker compose up

# Or directly in docker run
docker run --rm \
  -e LOG_LEVEL=DEBUG \
  -e DNSEXIT_API_KEY=your_key \
  -e LETSENCRYPT_EMAIL=your_email \
  certbot-dnsexit
```

### Log Output Locations

Logs are written to multiple locations for comprehensive monitoring:

1. **Console Output**: Real-time logging to stdout for container logs (default behavior)
2. **File Logs**: Persistent logging to `/var/log/letsencrypt/certbot.log` inside the container (only when LOG_FILE is explicitly set)
3. **Let's Encrypt Logs**: Certbot's native logs at `/var/log/letsencrypt/letsencrypt.log`

### Log Format

The application uses structured logging with timestamps and component identification:

```
[2025-07-30 16:48:00] Starting DNS Exit Certbot process
[2025-07-30 16:48:00] User: certbot (UID: 1000, GID: 1000)
[2025-07-30 16:48:00] Domains to process: example.com,*.example.com,api.example.com,www.example.com
```

Python-based hooks (auth_hook.py, cleanup_hook.py) use standard Python logging format:
```
2025-07-30 16:50:23 - __main__ - INFO - Adding TXT record for domain: example.com
2025-07-30 16:50:23 - __main__ - INFO - TXT record name: _acme-challenge.example.com
```

### Viewing Logs

Monitor application logs using various methods:

```bash
# View container logs in real-time
docker compose logs -f certbot

# View specific log file
docker compose exec certbot cat /var/log/letsencrypt/certbot.log

# View Let's Encrypt detailed logs
docker compose exec certbot cat /var/log/letsencrypt/letsencrypt.log

# View logs with specific level filtering
docker compose logs certbot | grep -E "(ERROR|WARNING)"
```

### Debugging with Verbose Logging

For detailed troubleshooting, enable DEBUG level logging. This will not only provide maximum verbosity for the application's internal logs but also configure Certbot to run with `-vvv` flags for its most detailed output:

```bash
# Enable debug logging
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LOG_LEVEL=DEBUG \
  -e LETSENCRYPT_EMAIL=your_email \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

Debug logs will show detailed information about:
- Domain processing and DNS record operations
- API request/response details (excluding sensitive data)
- Configuration parsing and validation
- Internal application state transitions
- Certbot's detailed ACME protocol interactions

### Log Rotation and Management

The application follows standard log rotation practices:
- Log files are rotated automatically by the container
- Old log files are cleaned up periodically
- Log retention can be configured via environment variables (future feature)

```bash
LOG_LEVEL=INFO
LOG_RETAIN_DAYS=30  # Keep logs for 30 days
```

## Advanced Certbot Arguments

You can pass additional arguments directly to the `certbot certonly` command using the `CERTBOT_CERTONLY_EXTRA_ARGS` environment variable.

### Examples

#### 1. Force Certificate Re-issuance (Ignore Existing Certificate)

To obtain a new certificate even if one for the same domain set already exists (useful if you've changed DNS providers or need to revoke and re-issue):

```bash
# Using environment variable
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your_email@example.com \
  -e DOMAINS=example.com \
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

Or via environment variable:
```bash
CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal
```

#### 2. Specify Certificate Name

To specify a custom certificate name (useful when managing multiple certificates):

```bash
# Using environment variable
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your_email@example.com \
  -e DOMAINS=example.com \
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--cert-name my-custom-cert \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

Or via environment variable:
```bash
CERTBOT_CERTONLY_EXTRA_ARGS=--cert-name my-custom-cert
```

#### 3. Use Let's Encrypt Staging Environment

To test your configuration without hitting Let's Encrypt production rate limits:

```bash
# Using environment variable
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your_email@example.com \
  -e DOMAINS=example.com \
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--server https://acme-staging-v02.api.letsencrypt.org/directory \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

Or via environment variable:
```bash
CERTBOT_CERTONLY_EXTRA_ARGS=--server https://acme-staging-v02.api.letsencrypt.org/directory
```

#### 4. Debugging Certbot Internals (Very Verbose)

For extremely detailed debugging of Certbot's internal operations, such as ACME protocol negotiations or specific plugin behaviors:

```bash
# Using environment variable (adds high verbosity to Certbot itself, in addition to LOG_LEVEL)
docker run --rm \
  # ... (other mounts and variables)
  -e LOG_LEVEL=DEBUG \ # For application and hook logs
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--debug --verbose \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```
> **Warning:** This will produce extremely verbose output, typically only needed for deep troubleshooting with Certbot developers.

#### 5. Specify Key Type or Size

To use a specific key type or size:

```bash
# Use ECDSA keys (P-256 curve)
CERTBOT_CERTONLY_EXTRA_ARGS=--key-type ecdsa --elliptic-curve secp256r1

# Or use RSA with larger key size
CERTBOT_CERTONLY_EXTRA_ARGS=--rsa-key-size 4096
```

#### 6. Avoid Random Sleep Before Renewal

In automated environments, you might want to prevent Certbot from adding a random sleep before attempting renewal, to ensure more predictable timing:

```bash
CERTBOT_CERTONLY_EXTRA_ARGS=--no-random-sleep-on-renew
```

#### 7. Enable Verbose Certbot Output

For detailed Certbot debugging output in addition to application logs:

```bash
# Using environment variable
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your_email@example.com \
  -e LOG_LEVEL=DEBUG \
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--verbose \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

Or via environment variable:
```bash
CERTBOT_CERTONLY_EXTRA_ARGS=--verbose
```

### Common Certbot Arguments

For a full list of available `certbot certonly` arguments, refer to the [official Certbot documentation](https://certbot.eff.org/docs/using.html#certbot-command-line-options).

Some particularly useful arguments include:
- `--force-renewal`: Renew the certificate even if it's not close to expiry.
- `--no-random-sleep-on-renew`: Don't sleep randomly before renewal (useful in automated environments).
- `--rsa-key-size <bits>`: Specify RSA key size (e.g., 2048, 3072, 4096).
- `--key-type ecdsa`: Use ECDSA keys instead of RSA.
- `--cert-name <name>`: Specify the certificate name (useful when multiple certificates could match domains).
- `--server <url>`: Specify ACME server URL (use for staging: https://acme-staging-v02.api.letsencrypt.org/directory).

### Important Notes on Extra Arguments:
- **Quoting:** When defining `CERTBOT_CERTONLY_EXTRA_ARGS` in your `.env` file or shell command, **DO NOT** include quotes around the entire value. Arguments should be space-separated without outer quotes.
  - ✅ Correct: `CERTBOT_CERTONLY_EXTRA_ARGS=--dry-run --force-renewal`
  - ❌ Wrong: `CERTBOT_CERTONLY_EXTRA_ARGS="--dry-run --force-renewal"`
  - For arguments with spaces: `CERTBOT_CERTONLY_EXTRA_ARGS=--cert-name "my cert"`
- **Order of Arguments:** Arguments passed via `CERTBOT_CERTONLY_EXTRA_ARGS` are appended at the end of the `certbot certonly` command. Core arguments like `--manual`, `--manual-auth-hook`, `--manual-cleanup-hook`, `--preferred-challenges`, `--email`, `--agree-tos`, `--non-interactive` are added by this script.
- **Conflicts:** Be mindful that custom arguments might conflict with those set by the script or with other arguments in `CERTBOT_CERTONLY_EXTRA_ARGS`. Test thoroughly, especially when using multiple arguments.
- **Staging for Testing:** For comprehensive testing without issuing real certificates, consider using Let's Encrypt's staging environment. This might involve setting `--staging` in `CERTBOT_CERTONLY_EXTRA_ARGS` *and* ensuring the Certbot server URL points to the staging ACME directory. This project's default is production. `LOG_LEVEL=DEBUG` is the primary method for testing configuration with real (but potentially discarded) certificates.

## Automation

### Using Docker Compose for Renewal
Certbot automatically handles renewal when certificates are close to expiration (typically within 30 days). You can run the container as a service to periodically check for renewals using the `RENEWAL_INTERVAL` environment variable.

Add to your crontab for a one-time daily check (though `RENEWAL_INTERVAL` is usually preferred):
```bash
# This is now less common due to RENEWAL_INTERVAL, but can be used
# 0 3 * * * cd /path/to/project && docker compose run --rm certbot
```

### RENEWAL_INTERVAL Environment Variable

The `RENEWAL_INTERVAL` environment variable sets the interval in seconds between certificate renewal checks.

- **Default Value**: `86400` seconds (1 day)
- **Special Value**: `0` - Disables periodic renewals. The script will run Certbot once and then exit.

**How it works:**
1. The container starts and runs Certbot once to obtain or renew certificates.
2. If `RENEWAL_INTERVAL` is greater than 0, the container enters a loop:
   - It sleeps for `RENEWAL_INTERVAL` seconds.
   - After sleeping, it runs Certbot again to check for renewals.
   - This process repeats indefinitely, or until the container is stopped.

**Use Cases:**

*   **Run Once (No Renewal Loop):**
    ```bash
    docker run --rm \
      -v /path/to/certs:/etc/letsencrypt \
      -v /path/to/config:/config \
      -e LETSENCRYPT_EMAIL=your-email@example.com \
      -e RENEWAL_INTERVAL=0 \
      -v /path/to/secrets:/run/secrets:ro \
      certbot-dnsexit
    ```
    This is useful for one-time certificate generation or within CI/CD pipelines.

*   **Custom Renewal Frequency (e.g., every 12 hours):**
    ```bash
    docker run -d \
      --name certbot-dnsexit \
      -v /path/to/certs:/etc/letsencrypt \
      -v /path/to/config:/config \
      -e LETSENCRYPT_EMAIL=your-email@example.com \
      -e RENEWAL_INTERVAL=43200 \ # 12 hours in seconds
      -v /path/to/secrets:/run/secrets:ro \
      certbot-dnsexit
    ```
    This runs the container as a daemon, checking for renewals every 12 hours.

*   **Default Daily Renewal:**
    If `RENEWAL_INTERVAL` is not set, it defaults to 86400 seconds (1 day).

**Important Notes:**
- Certbot itself has its own renewal logic and will only renew certificates if they are close to expiration (typically within 30 days).
- Setting `RENEWAL_INTERVAL` too frequently (e.g., every few minutes) is unnecessary and may lead to hitting Let's Encrypt rate limits. A daily check is usually sufficient.
- For production environments, running the container as a service (as shown above with `docker run -d`) is the most common approach. For cron jobs, you might typically set `RENEWAL_INTERVAL=0` and let the cron job schedule the frequency of `docker run` commands.

## Real-World Scenarios

### Multi-Domain Setup
```bash
DOMAINS="example.com,*.example.com,api.example.com" docker compose up
```

### Hybrid Deployment
```bash
# Combine with existing web server
docker run --rm \
  -v nginx_certs:/etc/letsencrypt \
  -v ./config:/config \
  certbot-dnsexit
```

### Force Re-newal with Extra Arguments
```bash
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -e LETSENCRYPT_EMAIL=your_email \
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--force-renewal --rsa-key-size 4096 \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

## Troubleshooting

1. **API Key Issues**
    - Ensure your dnsexit.com API key has DNS management permissions
    - Check API key format and validity
    - Verify Docker secrets are properly mounted at `/run/secrets/dnsexit_api_key`

2. **DNS Propagation**
   - Increase `dns_propagation_wait` in config if needed
   - Verify DNS TXT records are created correctly using `LOG_LEVEL=DEBUG`

3. **Rate Limits**
   - Use `LOG_LEVEL=DEBUG` for initial testing
   - Check Let's Encrypt rate limits
   - Consider using `--server https://acme-staging-v02.api.letsencrypt.org/directory` in `CERTBOT_CERTONLY_EXTRA_ARGS` for extensive testing

4. **Permission Issues**
   - Ensure volume mounts have correct permissions (UID 1000 inside container)
   - Check container runs as non-root user

5. **Certbot-Specific Issues**
   - Use `CERTBOT_CERTONLY_EXTRA_ARGS=--debug --verbose` for deep Certbot debugging.
   - Consult [Certbot's Troubleshooting Guide](https://certbot.eff.org/docs/using.html#troubleshooting).

### Debug Mode
Run with debug logging:
```bash
docker run --rm \
  -v $(pwd)/certs:/etc/letsencrypt \
  -v $(pwd)/config:/config \
  -e LETSENCRYPT_EMAIL=your_email@example.com \
  -e LOG_LEVEL=DEBUG \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

For maximum Certbot verbosity (in addition to application logs):
```bash
docker run --rm \
  # ... (other mounts and variables)
  -e CERTBOT_CERTONLY_EXTRA_ARGS=--debug --verbose \
  -v $(pwd)/secrets:/run/secrets:ro \
  certbot-dnsexit
```

## Security Operations Guide

### Key Rotation Procedure
1. Generate new API key in DNSExit dashboard
2. Update `.env` file with new values
3. Verify with debug run:
   ```bash
   docker compose run --rm certbot LOG_LEVEL=DEBUG
   ```
4. Full renewal will be handled automatically by Certbot when needed.

### Audit Checklist
- [ ] Verify certificate permissions (600 for privkey.pem, 644 for others)
- [ ] Confirm log rotation working
- [ ] Validate backup procedures for certificates
- [ ] Check last security scan results
- [ ] Review `CERTBOT_CERTONLY_EXTRA_ARGS` for unintended risks.

### Security Best Practices
- Never commit API keys or email addresses to version control
- Use Docker secrets for sensitive data (API keys are automatically loaded from `/run/secrets/dnsexit_api_key`)
- Ensure proper file permissions on certificate directories
- Regularly rotate API keys (as per DNSExit policy)
- Monitor certificate expiration dates
- Use `--force-renewal` or `--renew-by-default` in `CERTBOT_CERTONLY_EXTRA_ARGS` judiciously to avoid unnecessary issuance.

## Development

This section provides guidance for developers working on the Certbot DNSExit project, including setup, code quality tools, and contribution guidelines.

### Development Environment Setup

#### Prerequisites
- **Python 3.8+** (for development), Python 3.14+ (production container)
- **Docker and Docker Compose** for containerized development and testing
- **Git** for version control

#### Quick Setup with Makefile

The project uses Make for streamlined development workflow. All commands automatically handle virtual environment setup and dependencies.

```bash
# 1. Clone the repository
git clone <repository-url>
cd certbot-dnsexit

# 2. Create development environment (Python venv + dependencies)
make venv

# 3. Install pre-commit hooks for code quality
. venv/bin/activate && pre-commit install

# 4. Run tests to verify setup
make test

# 5. Build Docker image for integration testing
make build

# 6. Run full quality checks
make lint
```

#### Manual Setup (Alternative)

If you prefer manual setup without Makefile:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Install pre-commit hooks
pre-commit install

# Run tests
python -m pytest tests/ -v

# Build Docker image
docker build -t certbot-dnsexit .
```

### Code Quality Workflow

#### Pre-commit Hooks

The project uses pre-commit hooks to ensure code quality before commits. Hooks run automatically on `git commit` and include:

- **Ruff**: Fast Python linter and formatter
- **MyPy**: Static type checker
- **Bandit**: Security linter
- **Standard checks**: YAML/TOML syntax, large files, merge conflicts, etc.

```bash
# Run all pre-commit hooks manually
pre-commit run --all-files

# Run specific hook
pre-commit run ruff --all-files

# Update hooks to latest versions
pre-commit autoupdate
```

#### Code Quality Commands

```bash
# Run all linters (requires venv activation)
make lint

# Auto-fix linting issues
make lint-fix

# Run security scans
make security

# Run tests
make test

# Build and test
make build-test
```

### Making Code Changes

#### Development Workflow

1. **Create a feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes** following the project's coding standards

3. **Run quality checks:**
   ```bash
   make lint
   make test
   ```

4. **Test your changes:**
   ```bash
   # For application changes
   make build-test

   # For script changes
   make run-once
   ```

5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

6. **Push and create pull request:**
   ```bash
   git push origin feature/your-feature-name
   ```

#### Code Style Guidelines

- **Python**: Follow PEP 8 with Ruff formatting
- **Commits**: Use conventional commit format (`feat:`, `fix:`, `docs:`, etc.)
- **Documentation**: Update relevant docs for any user-facing changes
- **Tests**: Add tests for new functionality

#### Testing Your Changes

```bash
# Unit tests
make test

# Integration testing with Docker
make build-test

# Manual testing
make run-once LOG_LEVEL=DEBUG

# View logs
make logs
```

### Available Make Commands

| Command | Description | Dependencies |
|---------|-------------|--------------|
| `make venv` | Create Python virtual environment with all dependencies | Python 3.8+ |
| `make test` | Run unit tests with pytest | venv |
| `make build` | Build Docker image with docker compose | Docker |
| `make run` | Run container with renewal (RENEWAL_INTERVAL > 0) | Docker |
| `make run-once` | Run container once (RENEWAL_INTERVAL = 0) | Docker |
| `make logs` | View container logs | Docker |
| `make shell` | Get shell access to running container | Docker |
| `make clean` | Clean up containers, images, and venv | - |
| `make lint` | Run all code quality checks | venv |
| `make lint-fix` | Auto-fix linting issues | venv |
| `make security` | Run security scans | venv, Docker |
| `make build-test` | Build Docker image and run tests | Docker, venv |
| `make deploy` | Full deployment pipeline (check → build → test → run) | All |
| `make help` | Show all available commands | - |

### Troubleshooting Development Issues

#### Common Issues

1. **Pre-commit hooks fail:**
   ```bash
   # Skip hooks for this commit (not recommended)
   git commit --no-verify

   # Fix issues and commit again
   make lint-fix
   git add .
   git commit
   ```

2. **Virtual environment issues:**
   ```bash
   # Recreate venv
   make clean
   make venv
   ```

3. **Docker build fails:**
   ```bash
   # Clean and rebuild
   make clean
   make build
   ```

4. **Tests fail:**
   ```bash
   # Run with verbose output
   . venv/bin/activate && python -m pytest tests/ -v -s
   ```

#### Getting Help

- Check existing issues and documentation
- Review logs with `LOG_LEVEL=DEBUG`
- Test with staging environment using `CERTBOT_CERTONLY_EXTRA_ARGS=--server https://acme-staging-v02.api.letsencrypt.org/directory`

## Support

For issues with:
- dnsexit.com API: Contact dnsexit.com support
- Let's Encrypt: Check Let's Encrypt documentation and community forums
- This application: Review logs (especially with `LOG_LEVEL=DEBUG`), check configuration, and refer to this guide.
