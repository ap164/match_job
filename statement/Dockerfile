FROM python:3.10-slim

RUN apt-get update && apt-get install -y cron

WORKDIR /app

COPY requirements.txt .
COPY requirements_config.yaml .
COPY statement.ipynb .
COPY crontab.txt /etc/cron.d/biweekly-cron

RUN pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir papermill ipykernel && \
    python -m ipykernel install --name python3 --display-name "Python 3" --prefix=/usr/local && \
    chmod 0644 /etc/cron.d/biweekly-cron && \
    crontab /etc/cron.d/biweekly-cron && \
    mkdir -p /var/log

CMD touch /var/log/cron.log && cron && tail -f /var/log/cron.log
 