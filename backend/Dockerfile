# Use official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    graphviz \
    libgraphviz-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Expose port
EXPOSE 8000

# Start the application. We use 'exec' so that uvicorn runs as PID 1 and handles signals properly.
# The shell expands the PORT environment variable provided by Render.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
