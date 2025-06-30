# 1. Offizielles Python-Image als Basis
FROM python:3.12-slim

# 2. Systemabhängigkeiten installieren (z.B. für slugify, influxdb, uv)
RUN apt-get update && \
    apt-get install -y gcc build-essential && \
    rm -rf /var/lib/apt/lists/*

# 3. Arbeitsverzeichnis setzen
WORKDIR /app

# 4. Projektdateien kopieren
COPY . /app

# 5. uv installieren (falls nicht im base image)
RUN pip install uv

# 6. Abhängigkeiten installieren
RUN uv pip install --system --no-cache-dir .

# 7. Skript als Entrypoint ausführen
CMD ["python", "get_data.py"]
