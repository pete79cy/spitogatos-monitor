FROM python:3.11-slim

WORKDIR /app

# ScrapingBee path needs only requests + bs4 — install just those for a slim image
RUN pip install --no-cache-dir requests>=2.31.0 beautifulsoup4>=4.12.0

COPY spitogatos_monitor.py .

RUN mkdir -p /app/data
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Idle by default. Coolify Scheduled Task execs the script on cron.
# Manual run inside container:
#   python /app/spitogatos_monitor.py
CMD ["sleep", "infinity"]
