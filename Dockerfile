# Mermaid-GIF Containerized Deployment
# Base: Python 3.11 on Debian (required for Playwright system dependencies)

FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
# - nodejs, npm: Required for mermaid-parser-py
# - ffmpeg: Required for video to GIF conversion
# - curl: Utility for health checks
# - Playwright system dependencies installed via playwright install --with-deps
RUN apt-get update && apt-get install -y \
    nodejs \
    npm \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create application directory
WORKDIR /app

# Copy dependency files first (for layer caching)
COPY pyproject.toml ./
COPY README.md ./

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY tests/ ./tests/

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install .

# Install Playwright and Chromium with system dependencies
RUN pip install playwright && \
    playwright install chromium --with-deps

# Create output directory
RUN mkdir -p /app/output

# Set working directory for output
WORKDIR /app

# Health check (optional)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (placeholder - will be replaced with actual CLI)
# For now, this runs a Python module check
CMD ["python", "-c", "from src.core.graph import run_graph; print('Mermaid-GIF container ready')"]

# Expose port (if running as a service in the future)
EXPOSE 8000

# Labels
LABEL maintainer="Mermaid-GIF Team" \
      version="1.0.0" \
      description="Autonomous Mermaid to Flow-Animated GIF Converter"
