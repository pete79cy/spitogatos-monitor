FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

WORKDIR /app

# xvfb for headed Chromium under no-display environment
RUN apt-get update \
 && apt-get install -y --no-install-recommends xvfb \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY spitogatos_monitor.py .

# seen_apartments.json lives here; mount this as a Coolify volume for persistence
RUN mkdir -p /app/data
ENV DATA_DIR=/app/data
ENV PYTHONUNBUFFERED=1

# Idle by default. Coolify Scheduled Task execs the script on cron.
# Manual run inside container:
#   xvfb-run --auto-servernum --server-args='-screen 0 1920x1080x24' python spitogatos_monitor.py
CMD ["sleep", "infinity"]
