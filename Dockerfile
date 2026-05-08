FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests>=2.31.0 beautifulsoup4>=4.12.0 flask>=3.0.0

COPY spitogatos_monitor.py dashboard.py app.py ./
COPY templates/ ./templates/

# Persistent dir (Coolify volume) — holds seen_apartments.json + favorites.json + chat.json + web/
RUN mkdir -p /app/data/web
ENV DATA_DIR=/app/data
ENV WEB_DIR=/app/data/web
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

EXPOSE 3000

# Flask app: serves dashboard snapshots + favorites room + APIs.
# Coolify Scheduled Task runs `python /app/spitogatos_monitor.py` (regenerates dashboard).
CMD ["python", "/app/app.py"]
