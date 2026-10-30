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

# Upgrade pip and install CPU-optimized PyTorch first (efficient container caching)
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Copy requirements and install dependencies
COPY requirements.txt .
RUN grep -v "torch" requirements.txt > req_no_torch.txt && \
    pip install --no-cache-dir -r req_no_torch.txt || pip install --no-cache-dir fastapi "uvicorn[standard]" python-multipart pydicom bcrypt pyjwt sqlalchemy pydantic reportlab pillow numpy tensorflow-cpu keras pymupdf

# Copy application source code and models
COPY . .

# Verify neural network checkpoints and resolve Git LFS pointers if needed
RUN python ensure_models.py

# Expose port
EXPOSE 8000

# Start server using Railway dynamic PORT or default 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
