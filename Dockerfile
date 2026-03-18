FROM python:3.14-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Create data directories if they don't exist
RUN mkdir -p /app/data/logs /app/data/live /app/data/historical

# Set environment for unbuffered output (real-time logs)
ENV PYTHONUNBUFFERED=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8501/healthz', timeout=5)" || exit 1

# Default: run scheduler in paper trading mode
CMD ["python", "main.py", "--schedule", "--paper"]
