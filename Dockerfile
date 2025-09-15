# Use Python 3.11 as base image (matches runtime.txt)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyMuPDF, Pillow, pydub, and other libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libfreetype6-dev \
    libjpeg-dev \
    libffi-dev \
    libssl-dev \
    zlib1g-dev \
    liblcms2-dev \
    libwebp-dev \
    libopenjp2-7-dev \
    libtiff5-dev \
    tcl8.6-dev \
    tk8.6-dev \
    python3-dev \
    swig \
    libmupdf-dev \
    libmujs-dev \
    libharfbuzz-dev \
    libjbig2dec0-dev \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    espeak \
    libespeak1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching (use a slim set for deploy)
ARG REQS_FILE=requirements_minimal.txt
COPY ${REQS_FILE} /app/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy the rest of the application
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p data/documents/telegram_uploads data/knowledge_base

# Expose the port the app runs on (Render sets PORT env)
ENV PORT=5000
EXPOSE 5000

# Default to disabling heavy models in container
ENV DISABLE_EMBEDDINGS=true
ENV DISABLE_WHISPER=true

# Command to run the application (Flask app factory)
CMD gunicorn app:create_app --bind 0.0.0.0:$PORT --timeout 120