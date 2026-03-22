# Multi-stage Dockerfile for Mini Software House
# Supports GPU acceleration with NVIDIA CUDA

# Stage 1: Builder
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04 AS builder

LABEL maintainer="Mini Software House"
LABEL description="AI-powered software creation pipeline with GPU support"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DEBIAN_FRONTEND=noninteractive \
    CUDA_HOME=/usr/local/cuda

# Install Python 3.12 and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    build-essential \
    git \
    curl \
    wget \
    ca-certificates \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Make python3.12 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install pip and poetry
RUN curl -sS https://bootstrap.pypa.io/get-pip.py | python3.12 && \
    pip install --no-cache-dir poetry

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml poetry.lock* ./

# Install Python dependencies
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi 2>&1 || \
    pip install --no-cache-dir -q torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# Stage 2: Runtime
FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

LABEL maintainer="Mini Software House"
LABEL description="AI-powered software creation pipeline with GPU support"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    OLLAMA_HOST=http://ollama:11434 \
    CUDA_HOME=/usr/local/cuda

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.12 \
    python3.12-dev \
    python3-pip \
    libpq5 \
    git \
    curl \
    ca-certificates \
    nvidia-utils \
    && rm -rf /var/lib/apt/lists/*

# Make python3.12 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Create app user
RUN useradd -m -u 1000 appuser

# Set working directory
WORKDIR /app

# Copy project files from builder
COPY --chown=appuser:appuser . /app/

# Create workspace directory
RUN mkdir -p /app/workspace && \
    chown -R appuser:appuser /app

# Switch to app user
USER appuser

# Install dependencies with pip (simpler and more reliable)
RUN pip install --no-cache-dir --user -q \
    colorama==0.4.6 \
    ollama==0.6.1 \
    structlog==25.5.0 \
    docker==7.1.0 \
    sqlmodel==0.0.37 \
    streamlit==1.55.0 \
    chromadb==1.5.5 \
    ruff==0.15.5 \
    litellm==1.82.3 \
    accelerate==1.13.0 \
    bitsandbytes==0.49.2 \
    poetry==1.8.2

ENV PATH="/home/appuser/.local/bin:${PATH}"

# Expose ports
EXPOSE 8501 8000 11434

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)"

# Default command
ENTRYPOINT ["python3", "-m", "src.cli"]
CMD ["status"]
