FROM python:3.11-slim

# Librerie di sistema necessarie a OpenCV (headless) e Pillow.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Dipendenze prima (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Codice
COPY . .

ENV PYTHONUNBUFFERED=1

# Render/Railway forniscono $PORT; default 8000 in locale.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
