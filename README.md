# Certbot DNSExit - Let's Encrypt DNS-01 Challenge

A Docker-based solution for obtaining Let's Encrypt certificates using DNS-01 challenge with dnsexit.com DNS provider.

## Overview

This application provides a secure, containerized way to obtain and renew Let's Encrypt certificates using the DNS-01 challenge method. It integrates with dnsexit.com's DNS API to automatically create and remove TXT records required for domain validation.

## Features

- **DNS-01 Challenge Support**: Automatic TXT record creation and cleanup
- **dnsexit.com Integration**: Full API support for DNS management
- **Docker Containerization**: Secure, isolated execution environment
- **Non-root Execution**: Runs as unprivileged user (UID 1000)
- **Flexible Configuration**: Environment variables with secure credential storage
- **Automatic Renewal**: Built-in certificate renewal support
- **Security First**: Multiple secure credential storage options including Docker secrets
- **Comprehensive Testing**: 49 unit tests with 100% pass rate
- **Modern Python**: Compatible with Python 3.8+ (development) and Python 3.14+ (production container)
- **Virtual Environment**: Migrated to Python 3.14+ for development environment
- **Code Quality**: Automated linting with ruff, mypy, and bandit

## Quick Start

### Prerequisites

#### Required Software
- **Docker and Docker Compose**: Container runtime and orchestration
- **dnsexit.com account**: With API access enabled
- **Domain**: Managed by dnsexit.com DNS
- **Python 3.8+** (for development), Python 3.14+ (production container)

#### Installation Guides by OS

| Operating System | Docker | Docker Compose | Git | Python |
|------------------|--------|----------------|-----|--------|
| **Ubuntu/Debian** | [Docker Ubuntu](https://docs.docker.com/engine/install/ubuntu/) | Included with Docker | `sudo apt install git` | `sudo apt install python3 python3-pip` |
| **CentOS/RHEL** | [Docker CentOS](https://docs.docker.com/engine/install/centos/) | Included with Docker | `sudo yum install git` | `sudo yum install python3 python3-pip` |
| **macOS** | [Docker Desktop Mac](https://docs.docker.com/desktop/mac/install/) | Included | [Git macOS](https://git-scm.com/download/mac) | [Python macOS](https://www.python.org/downloads/macos/) |
| **Windows** | [Docker Desktop Windows](https://docs.docker.com/desktop/windows/install/) | Included | [Git Windows](https://git-scm.com/download/win) | [Python Windows](https://www.python.org/downloads/windows/) |
| **Arch Linux** | `sudo pacman -S docker docker compose` | Included | `sudo pacman -S git` | `sudo pacman -S python python-pip` |

#### Quick Verification
```bash
# Verify installations
docker --version
docker compose version
git --version
python3 --version
```

### 1. Clone and Build
```bash
git clone <repository-url>
cd certbot-dnsexit
make build
```

### 2. Configure
```bash
# Copy environment template
cp .env.example .env

# Edit with your values
nano .env

# Create Docker secret for API key
mkdir -p secrets
echo "your_dnsexit_api_key_here" > secrets/dnsexit_api_key
chmod 600 secrets/dnsexit_api_key
```

### 3. Run
```bash
# For one-time certificate generation:
make run-once

# For continuous renewal (default):
make run
```

## Configuration

### Quick Setup

1. **Copy environment template:**
   ```bash
   cp .env.example .env
   ```

2. **Edit with your values:**
   ```bash
   nano .env
   ```

3. **Required settings:**
   ```bash
   LETSENCRYPT_EMAIL=your-email@example.com
   DOMAINS=your-domain.com,*.your-domain.com
   ```

### Configuration Overview

**Configuration Priority Order:**
1. **Docker secrets** (`/run/secrets/{key}`) - highest priority
2. **FILE__ environment variables** (`FILE__{KEY}=/path/to/file`)
3. **URL__ environment variables** (`URL__{KEY}=https://secret-manager/api`)
4. **Direct environment variables** (from `.env` file or command line)
5. **Default Values** (lowest priority)

**Key Configuration Elements:**
- **`.env` file**: Credentials and sensitive data (email, domains)
- **Docker secrets**: Secure API key storage (recommended)
- **External secret managers**: HTTP-based secret retrieval

See [USAGE.md](USAGE.md#environment-variables-reference) for complete configuration details and [SECURITY.md](SECURITY.md) for secure credential handling.

## Basic Usage

### Generate Certificates
```bash
# One-time certificate generation
make run-once

# Continuous renewal (background)
make run

# View logs
make logs

# Stop container
docker stop certbot-dnsexit

# Alternative: Using Docker Compose examples
docker-compose -f docker-compose.runonce.yml up
docker-compose -f docker-compose.run.yml up -d
```

### Certificate Locations
After successful generation, certificates are stored in:
- `certs/live/[domain]/fullchain.pem` - Full certificate chain
- `certs/live/[domain]/privkey.pem` - Private key
- `certs/live/[domain]/cert.pem` - Certificate only

For detailed usage instructions and advanced scenarios, see the [USAGE.md](USAGE.md) file.

## Project Structure

```
certbot-dnsexit/
├── src/               # Core application logic
├── scripts/           # Runtime scripts
├── tests/             # Unit tests
├── docker-compose.run.yml      # Continuous renewal orchestration
├── docker-compose.runonce.yml  # One-time execution orchestration
├── Makefile           # Development and deployment automation
├── .env.example       # Environment variables template
├── README.md          # This file
├── USAGE.md           # Detailed usage guide
└── SECURITY.md        # Security best practices
```

## Security

- **Non-root execution**: Container runs as unprivileged user (UID 1000)
- **Secure credential handling**: Multiple methods for API key storage including Docker secrets
- **Automatic log masking**: Sensitive data is automatically masked in logs
- **Minimal attack surface**: Alpine-based container with only necessary packages

For detailed security best practices and API key handling, see [SECURITY.md](SECURITY.md).

## Development

### Development Workflow

The project uses Make for common development tasks. All commands automatically handle virtual environment setup and dependencies.

#### Quick Setup
```bash
# Create development environment
make venv

# Run tests
make test

# Build and test
make build-test
```

#### Available Make Commands

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

#### Code Quality Tools
- **ruff**: Fast Python linter and formatter (replaces flake8, isort, black)
- **mypy**: Static type checker with relaxed configuration
- **bandit**: Security linter for Python code
- **pre-commit**: Automated checks before commits
- **Safety**: Dependency vulnerability scanning
- **Trivy**: Docker image security scanning

#### Development Environment Setup
```bash
# 1. Create virtual environment
make venv

# 2. Install pre-commit hooks
. venv/bin/activate && pre-commit install

# 3. Run quality checks
make lint

# 4. Run tests
make test
```

For detailed development setup and advanced usage, see [USAGE.md](USAGE.md#development).

## Documentation

- **[USAGE.md](USAGE.md)** - Detailed operational instructions and advanced scenarios
- **[SECURITY.md](SECURITY.md)** - API key security and secure deployment
- [Let's Encrypt Documentation](https://letsencrypt.org/docs/)
- [DNSExit API Reference](https://dnsexit.com/dns/dns-api/)

## License

This project is licensed under the BSD 3-Clause License - see the [LICENSE](LICENSE) file for details.

Please ensure compliance with Let's Encrypt's terms of service and dnsexit.com's API usage policies.

## Support

For issues:
- **dnsexit.com API**: Contact dnsexit.com support
- **Let's Encrypt**: Check Let's Encrypt documentation
- **This application**: Review logs and configuration
