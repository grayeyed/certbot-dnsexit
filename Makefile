.PHONY: build test run run-once clean shell venv-activate lint lint-fix security security-deps security-docker security-licenses

# Load environment variables from .env file
RENEWAL_INTERVAL := $(shell grep '^RENEWAL_INTERVAL=' .env 2>/dev/null | cut -d'=' -f2)

# Build the Docker image
build:
	docker build -t certbot-dnsexit .

# Create virtual environment
venv: requirements.txt requirements-dev.txt
	test -d venv || python3 -m venv venv
	. venv/bin/activate && pip install -r requirements.txt -r requirements-dev.txt

# Run tests
test: venv
	. venv/bin/activate && python -m pytest tests/ -v

# Deployment checks
check-env:
	@test -n "$(DNSEXIT_API_KEY)" || (echo "ERROR: DNSEXIT_API_KEY not set"; exit 1)
	@test -n "$(LETSENCRYPT_EMAIL)" || (echo "ERROR: LETSENCRYPT_EMAIL not set"; exit 1)

# Full deployment pipeline
deploy: check-env build test run
	@echo "✓ Deployment completed"

# Run the container with renewal (RENEWAL_INTERVAL > 0)
run:
	@echo "🚀 Running certbot-dnsexit with renewal (RENEWAL_INTERVAL=${RENEWAL_INTERVAL:-86400})"
	@if [ ! -f ".env" ]; then \
		echo "❌ Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@if [ ! -f "secrets/dnsexit_api_key" ]; then \
		echo "❌ Error: Docker secret file not found. Create secrets/dnsexit_api_key with your API key."; \
		exit 1; \
	fi
	@if [ -n "$(RENEWAL_INTERVAL)" ] && [ "$(RENEWAL_INTERVAL)" != "0" ] && [ "$(RENEWAL_INTERVAL)" -lt 3600 ] 2>/dev/null; then \
		echo "❌ Error: RENEWAL_INTERVAL must be at least 3600 seconds (1 hour) for daemon mode."; \
		echo "   Current value: $(RENEWAL_INTERVAL)"; \
		echo "   Use 'make run-once' for one-time execution."; \
		exit 1; \
	fi
	docker run -d \
		--name certbot-dnsexit \
		--restart unless-stopped \
		--env-file .env \
		-v "$(PWD)/certs:/etc/letsencrypt" \
		-v "$(PWD)/work:/var/lib/letsencrypt" \
		-v "$(PWD)/work/logs:/var/log/letsencrypt" \
		-v "$(PWD)/secrets/dnsexit_api_key:/run/secrets/dnsexit_api_key:ro" \
		--health-cmd "/app/scripts/healthcheck.sh" \
		--health-interval 5m \
		--health-timeout 30s \
		--health-retries 3 \
		--health-start-period 10s \
		certbot-dnsexit
	@echo "✅ Container started with health checks. Use 'docker logs -f certbot-dnsexit' to view logs"
	@echo "✅ Use 'docker stop certbot-dnsexit' to stop the container"
	@echo "✅ Use 'docker inspect certbot-dnsexit | grep -A 10 Health' to check health status"

# View logs
logs:
	docker logs -f certbot-dnsexit

# Clean up
clean:
	docker stop certbot-dnsexit || true
	docker rm certbot-dnsexit || true
	docker rmi certbot-dnsexit || true
	rm -rf venv

# Get shell in container
shell:
	docker run --rm -it \
		--env-file .env \
		-v "$(PWD)/certs:/etc/letsencrypt" \
		-v "$(PWD)/work:/var/lib/letsencrypt" \
		-v "$(PWD)/work/logs:/var/log/letsencrypt" \
		-v "$(PWD)/secrets/dnsexit_api_key:/run/secrets/dnsexit_api_key:ro" \
		certbot-dnsexit /bin/bash

# Run the container once (RENEWAL_INTERVAL = 0)
run-once:
	@echo "🔄 Running certbot-dnsexit once (RENEWAL_INTERVAL=0)"
	@if [ ! -f ".env" ]; then \
		echo "❌ Error: .env file not found. Copy .env.example to .env and configure it."; \
		exit 1; \
	fi
	@if [ ! -f "secrets/dnsexit_api_key" ]; then \
		echo "❌ Error: Docker secret file not found. Create secrets/dnsexit_api_key with your API key."; \
		exit 1; \
	fi
	docker run --rm --no-healthcheck \
		--env-file .env \
		-e RENEWAL_INTERVAL=0 \
		-v "$(PWD)/certs:/etc/letsencrypt" \
		-v "$(PWD)/work:/var/lib/letsencrypt" \
		-v "$(PWD)/work/logs:/var/log/letsencrypt" \
		-v "$(PWD)/secrets/dnsexit_api_key:/run/secrets/dnsexit_api_key:ro" \
		certbot-dnsexit
	@echo "✅ One-time execution completed"

# Build and test
build-test: build test

# Activate virtual environment (source this in your shell)
venv-activate:
	@echo "To activate the virtual environment, run:"
	@echo "  source venv/bin/activate"
	@echo ""
	@echo "To deactivate, run:"
	@echo "  deactivate"
	@echo ""
	@echo "Or use this alias:"
	@echo "  alias activate-venv='source venv/bin/activate'"

# Lint code quality
lint:
	. venv/bin/activate && ruff check src/ tests/
	. venv/bin/activate && ruff format --check src/ tests/
	. venv/bin/activate && mypy src/
	. venv/bin/activate && bandit -r src/

# Security checks
security: security-deps security-docker

security-deps:
	@echo "🔍 Running dependency vulnerability scan..."
	. venv/bin/activate && safety scan --output json > safety-report.json 2>/dev/null || true
	@if [ -f safety-report.json ] && grep -q '"vulnerabilities"' safety-report.json; then \
		echo "❌ Dependency vulnerabilities found:"; \
		cat safety-report.json | jq '.vulnerabilities[]? | {package: .package, vulnerability: .vulnerability, severity: .severity}' 2>/dev/null || echo "Unable to parse report"; \
		exit 1; \
	else \
		echo "✅ No dependency vulnerabilities found"; \
	fi

security-licenses:
	@echo "🔍 Checking license compliance..."
	. venv/bin/activate && pip-licenses --format=json --output-file=licenses-report.json || true
	@if [ -f licenses-report.json ]; then \
		echo "📋 License compliance report:"; \
		cat licenses-report.json | jq '.[] | select(.License | contains("GPL") or contains("AGPL") or contains("LGPL")) | {name: .Name, version: .Version, license: .License}' || echo "✅ No problematic licenses found"; \
	else \
		echo "⚠️  pip-licenses not available. Install with: pip install pip-licenses"; \
	fi

security-docker:
	@echo "🔍 Running Docker security scan with Trivy..."
	@if command -v ~/.local/bin/trivy >/dev/null 2>&1; then \
		~/.local/bin/trivy image --format json --output trivy-report.json certbot-dnsexit:test || true; \
		if [ -f trivy-report.json ] && grep -q '"Vulnerabilities"' trivy-report.json; then \
			echo "❌ Docker image vulnerabilities found:"; \
			cat trivy-report.json | jq '.Results[]?.Vulnerabilities[]? | select(.Severity == "CRITICAL" or .Severity == "HIGH") | {package: .PkgName, vulnerability: .VulnerabilityID, severity: .Severity, title: .Title}' | head -10; \
			exit 1; \
		else \
			echo "✅ No critical/high Docker image vulnerabilities found"; \
		fi \
	else \
		echo "⚠️  Trivy not found. Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b ~/.local/bin"; \
	fi

# Fix linting issues automatically
lint-fix:
	. venv/bin/activate && ruff check --fix src/ tests/
	. venv/bin/activate && ruff format src/ tests/

# Help
help:
	@echo "Available commands:"
	@echo "  build         - Build Docker image"
	@echo "  test          - Run unit tests"
	@echo "  venv          - Create virtual environment"
	@echo "  venv-activate - Show virtual environment activation instructions"
	@echo "  run           - Run container with renewal (RENEWAL_INTERVAL > 0)"
	@echo "  run-once      - Run container once (RENEWAL_INTERVAL = 0)"
	@echo "  clean         - Clean up containers and images"
	@echo "  shell         - Get shell in container"
	@echo "  logs          - View container logs"
	@echo "  build-test    - Build and test"
	@echo "  lint          - Run all linters (requires venv)"
	@echo "  lint-fix      - Auto-fix linting issues (requires venv)"
	@echo "  help          - Show this help"
