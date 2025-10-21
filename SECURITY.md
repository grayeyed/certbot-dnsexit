# Security Best Practices

This document outlines security best practices for handling sensitive data, particularly the DNSEXIT_API_KEY, in the Certbot DNSExit project.

## API Key Security

The DNSEXIT_API_KEY is a sensitive credential that provides access to your DNS management capabilities. Proper handling of this secret is critical for maintaining security.

### Risk Assessment

| Risk Level | Description | Impact |
|------------|-------------|--------|
| **Critical** | API key exposed in logs | Unauthorized DNS modifications, potential domain takeover |
| **High** | API key stored in plain text files | Credential theft via file access |
| **Medium** | API key visible in environment variables | Exposure via process listings or debugging |
| **Low** | Weak API key format | Brute force or guessing attacks |

## Secure Secret Storage Methods

The application supports multiple methods for secure API key storage, prioritized by security level:

### 1. Docker Secrets (Recommended for Production)

Docker Secrets provide the highest level of security for containerized deployments.

#### Setup
```bash
# Create secrets directory
mkdir -p secrets

# Create API key file
echo "your-actual-api-key-here" > secrets/dnsexit_api_key
chmod 600 secrets/dnsexit_api_key

# Run with Docker secrets
docker compose up
```

#### docker compose.yml Configuration
```yaml
secrets:
  dnsexit_api_key:
    file: ./secrets/dnsexit_api_key

services:
  certbot-dnsexit:
    secrets:
      - dnsexit_api_key
```

#### Advantages
- Secrets are encrypted at rest
- Only accessible to containers that explicitly declare them
- Automatic key rotation support
- No plain text in environment variables

### 2. External Files

Store the API key in external files with restricted permissions.

#### Setup
```bash
# Create secure file
echo "your-actual-api-key-here" > /secure/dnsexit_api_key
chmod 600 /secure/dnsexit_api_key
chown root:root /secure/dnsexit_api_key

# Use FILE__ environment variable
export FILE__DNSEXIT_API_KEY=/secure/dnsexit_api_key
docker compose up
```

#### Advantages
- File permissions can be tightly controlled
- Supports standard file system security
- Easy to audit and monitor

### 3. External Secret Managers

Integrate with enterprise-grade secret management systems.

#### HashiCorp Vault
```bash
# Set URL for Vault secret
export URL__DNSEXIT_API_KEY="https://vault.example.com/v1/secret/dnsexit/api_key"
export URL__DNSEXIT_API_KEY_HEADERS='{"X-Vault-Token": "your-vault-token"}'
docker compose up
```

#### AWS Secrets Manager
```bash
# Use AWS CLI or SDK to retrieve secrets
export URL__DNSEXIT_API_KEY="https://secretsmanager.us-east-1.amazonaws.com"
# Headers would include AWS authentication
```

#### Custom Secret Manager
```bash
# Any HTTP endpoint that returns the secret
export URL__DNSEXIT_API_KEY="https://your-secret-manager.com/api/secrets/dnsexit-key"
export URL__DNSEXIT_API_KEY_HEADERS='{"Authorization": "Bearer your-token"}'
```

### 4. Environment Variables (Development Only)

For development and testing only - NOT recommended for production.

```bash
export DNSEXIT_API_KEY="your-api-key-here"
docker compose up
```

⚠️ **Warning**: Environment variables are visible in process listings and may be logged.

## Configuration Priority

Secrets are loaded in the following priority order (highest to lowest):

1. **Docker Secrets** (`/run/secrets/dnsexit_api_key`)
2. **FILE__ variables** (`FILE__DNSEXIT_API_KEY=/path/to/file`)
3. **URL__ variables** (`URL__DNSEXIT_API_KEY=https://secret-manager/api`)
4. **Direct environment variables** (`DNSEXIT_API_KEY=value`)
5. **YAML configuration** (`dnsexit_api_key: value`)
6. **Default values**

## Log Security

### Automatic Masking

The application automatically masks sensitive data in logs:

- API keys are replaced with `***MASKED***`
- Detection is based on field names containing: `key`, `secret`, `password`, `token`, `auth`
- Both structured data and plain text are protected

### Log Levels

Use appropriate log levels to control information exposure:

```bash
# Production - minimal logging
LOG_LEVEL=INFO

# Debugging - use with caution
LOG_LEVEL=DEBUG  # Will mask sensitive data but may expose other information
```

## Environment-Specific Configurations

### Development Environment
```bash
# Use local files with development keys
export FILE__DNSEXIT_API_KEY=./dev-secrets/api-key
LOG_LEVEL=DEBUG
```

### Staging Environment
```bash
# Use Docker secrets with staging keys
# docker compose.staging.yml with staging secrets
LOG_LEVEL=INFO
```

### Production Environment
```bash
# Use Docker secrets with production keys
# docker compose.prod.yml with production secrets
LOG_LEVEL=WARNING
```

## Key Rotation

### Manual Rotation
1. Update the API key in your secret storage
2. Restart the container: `docker compose restart`
3. Verify the new key works: `docker compose logs`

### Automated Rotation
```bash
# Example cron job for key rotation
0 2 * * * /path/to/rotate-dnsexit-key.sh && docker compose restart certbot-dnsexit
```

## Security Monitoring

### Audit Logging
Monitor for suspicious activities:

```bash
# Check for API key access patterns
docker compose logs | grep -i "dnsexit"

# Monitor file access
auditctl -w /run/secrets/dnsexit_api_key -p r -k secret_access
```

### Health Checks
```bash
# Verify secret is accessible
docker compose exec certbot-dnsexit test -f /run/secrets/dnsexit_api_key

# Check API key format (without exposing it)
docker compose exec certbot-dnsexit sh -c 'test -n "$DNSEXIT_API_KEY" && echo "API key configured"'
```

## Compliance Considerations

### GDPR
- API keys are considered personal data
- Implement proper data retention policies
- Provide data deletion mechanisms

### SOC 2
- Implement access logging
- Regular security audits
- Document incident response procedures

### PCI DSS (if applicable)
- Never log cardholder data
- Use encrypted channels for secret transmission
- Regular key rotation

## Troubleshooting Security Issues

### Common Issues

#### API Key Not Found
```bash
# Check if Docker secret exists
docker compose exec certbot-dnsexit ls -la /run/secrets/

# Check file permissions
ls -la /path/to/secret/file

# Test configuration loading
docker compose exec certbot-dnsexit python3 -c "from src.config_loader import get_config; print('API key loaded:', bool(get_config('dnsexit_api_key')))"
```

#### Log Shows Plain Text API Key
- Upgrade to latest version with masking
- Check custom logging configurations
- Review third-party library logging

#### Permission Denied
```bash
# Fix file permissions
chmod 600 /path/to/secret/file
chown root:root /path/to/secret/file

# Check Docker secret mounting
docker compose config
```

## Security Checklist

- [ ] API key stored using Docker secrets or external files
- [ ] File permissions set to 600 (owner read/write only)
- [ ] No plain text API keys in environment variables (production)
- [ ] Log masking verified (check debug logs)
- [ ] Key rotation procedure documented and tested
- [ ] Access logging enabled
- [ ] Regular security audits scheduled
- [ ] Incident response plan in place

## Contact

For security concerns or vulnerabilities, please refer to the main project's security policy or contact the maintainers directly.