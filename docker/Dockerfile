# Multi-stage build for Korean Flashcard Pipeline
# Stage 1: Build Rust components
FROM rust:1.75-slim as rust-builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Rust source files
COPY Cargo.toml Cargo.lock ./
COPY src/rust ./src/rust

# Build Rust components in release mode
RUN cargo build --release

# Stage 2: Python runtime
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    sqlite3 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy Rust binaries from builder
COPY --from=rust-builder /app/target/release/flashcard_pipeline /usr/local/bin/

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY src/python ./src/python
COPY migrations ./migrations
COPY scripts ./scripts

# Copy example environment file
COPY .env.example .env.example

# Create necessary directories
RUN mkdir -p logs data/input data/output cache

# Set environment variables
ENV PYTHONPATH=/app/src/python
ENV DATABASE_PATH=/app/pipeline.db
ENV LOG_FILE=/app/logs/pipeline.log

# Create volume mount points
VOLUME ["/app/data", "/app/logs", "/app/cache"]

# Expose port for potential future web interface
EXPOSE 8080

# Default command - show help
CMD ["python", "-m", "flashcard_pipeline.pipeline_cli", "--help"]

# Example usage:
# docker build -t korean-flashcard-pipeline .
# docker run -v $(pwd)/data:/app/data -v $(pwd)/.env:/app/.env korean-flashcard-pipeline python -m flashcard_pipeline.pipeline_cli process /app/data/input/vocabulary.csv