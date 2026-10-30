FROM python:3.11-slim

# Set environment settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV HOST=0.0.0.0

# Install system dependencies for image/DICOM processing and PDF generation
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Pre-install PyTorch dependencies from PyPI so pip doesn't hang searching pytorch.org
RUN pip install --no-cache-dir filelock typing-extensions sympy networkx jinja2 fsspec pillow numpy

# Install CPU-optimized PyTorch and torchvision using --extra-index-url
RUN pip install --no-cache-dir torch torchvision --extra-index-url https://download.pytorch.org/whl/cpu

# Copy and install application requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code and models
COPY . .

# Verify neural network checkpoints and resolve Git LFS pointers if needed
RUN python ensure_models.py

# Expose port
EXPOSE 8000

# Start server using Railway dynamic PORT or default 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
