# MemoryBridge: AI-Powered Conversational Avatar
# Multi-stage Docker build for optimal size and security

# Stage 1: Base Python environment
FROM python:3.10-slim as base

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    PORT=5000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    ffmpeg \
    libsndfile1 \
    portaudio19-dev \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash memorybridge

# Stage 2: Application build
FROM base as builder

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Download models during build to reduce startup time
RUN python -c "from transformers import pipeline; \
    pipeline('text-classification', model='j-hartmann/emotion-english-distilroberta-base')" && \
    python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('all-MiniLM-L6-v2')" && \
    python -c "from TTS.api import TTS; \
    print('TTS models will be downloaded on first run')"

# Stage 3: Final runtime image
FROM base as runtime

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create application directories
RUN mkdir -p /app/static /app/generated_audio /app/voice_samples /app/output && \
    chown -R memorybridge:memorybridge /app

# Switch to non-root user
USER memorybridge

# Set working directory
WORKDIR /app

# Copy application files
COPY --chown=memorybridge:memorybridge . .

# Create necessary directories with proper permissions
RUN mkdir -p memory_index.faiss generated_audio voice_samples output && \
    chmod 755 static generated_audio voice_samples output

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# Default command
CMD ["python", "server.py"]
