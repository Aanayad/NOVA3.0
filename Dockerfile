FROM python:3.12-slim

WORKDIR /app

# System deps needed by some optional automation libraries; safe to keep
# even if system control is disabled (the default) in containerized deploys.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p logs database

ENV FLASK_ENV=production
EXPOSE 5000

# NOTE: ENABLE_SYSTEM_CONTROL should remain "false" in Docker/cloud deploys -
# there is no meaningful "shutdown the host" action to perform in a container.
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
