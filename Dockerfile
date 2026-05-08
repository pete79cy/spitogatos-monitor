FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir requests>=2.31.0 beautifulsoup4>=4.12.0

COPY spitogatos_monitor.py dashboard.py serve.py ./

# Persistent dir (Coolify volume) — holds seen_apartments.json + web/
RUN mkdir -p /app/data/web
ENV DATA_DIR=/app/data
ENV WEB_DIR=/app/data/web
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8
ENV LANG=C.UTF-8

EXPOSE 3000

# Serves the dashboard with HTTP Basic Auth (if DASHBOARD_USER/PASSWORD set).
# The Coolify Scheduled Task runs `python /app/spitogatos_monitor.py` which
# regenerates /app/data/web/index.html on each cron tick.
CMD ["python", "/app/serve.py"]
