# Multi-stage build for Discord bot
FROM python:3.11-slim as builder

# Install uv for faster dependency management
RUN pip install uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Create virtual environment and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN uv pip install -e .

# Production stage
FROM python:3.11-slim as production

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash --uid 1001 app
RUN chown -R app:app /app
USER app

# Health check - check if bot process is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD pgrep -f "python.*main.py" || exit 1

CMD ["python", "main.py"]