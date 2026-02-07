FROM python:3.11-slim

WORKDIR /app

# system deps (opencv runtime needs these sometimes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg libsm6 libxext6 libpq-dev \
  && rm -rf /var/lib/apt/lists/*

# Layer 1: heavy, rarely-changing deps (torch, opencv, numpy, etc.)
# This layer is cached and won't re-download when you only change requirements.txt
COPY requirements.base.txt .
RUN pip install --no-cache-dir -r requirements.base.txt

# Layer 2: lighter, frequently-changing deps (fastapi, auth libs, etc.)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
EXPOSE 8000

CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
