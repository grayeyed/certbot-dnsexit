FROM python:3.14-slim

# Install system dependencies with security updates
RUN apt-get update && apt-get upgrade -y && \
    apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 certbot && \
    useradd -m -s /bin/sh -u 1000 -g certbot certbot

# Create necessary directories
RUN mkdir -p /app /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt && \
    chown -R certbot:certbot /app /etc/letsencrypt /var/lib/letsencrypt /var/log/letsencrypt

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies including certbot
COPY requirements.txt .
RUN pip install --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org --no-cache-dir -r requirements.txt certbot

# Copy application files
COPY src/ ./src/
COPY scripts/ ./scripts/

# Make scripts executable
RUN chmod +x scripts/*.sh src/*.py && \
    chown -R certbot:certbot /app

# Add health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD ["/app/scripts/healthcheck.sh"] || exit 1

# Switch to non-root user
USER certbot

# Set environment variables
ENV PATH="/home/certbot/.local/bin:$PATH"
ENV PYTHONPATH="/app"

# Default command
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
