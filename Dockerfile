# Use Python 3.11 as base image (matches runtime.txt)
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for PyMuPDF, Pillow, pydub, and other libraries
RUN apt-get update && apt-get install -y \\\n    build-essential \\\n    pkg-config \\\n    libfreetype6-dev \\\n    libjpeg-dev \\\n    libffi-dev \\\n    libssl-dev \\\n    zlib1g-dev \\\n    liblcms2-dev \\\n    libwebp-dev \\\n    libopenjp2-7-dev \\\n    libtiff5-dev \\\n    tcl8.6-dev \\\n    tk8.6-dev \\\n    python3-dev \\\n    swig \\\n    libmupdf-dev \\\n    libmujs-dev \\\n    libharfbuzz-dev \\\n    libjbig2dec0-dev \\\n    ffmpeg \\\n    libsndfile1 \\\n    libportaudio2 \\\n    && rm -rf /var/lib/apt/lists/*

# Copy requirements file first for better caching
COPY requirements_new.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements_new.txt

# Copy the rest of the application
COPY . .

# Create necessary directories if they don't exist
RUN mkdir -p data/documents/telegram_uploads data/knowledge_base

# Expose the port the app runs on
EXPOSE $PORT

# Command to run the application
CMD gunicorn app:create_app() --bind 0.0.0.0:$PORT --config gunicorn.conf.py