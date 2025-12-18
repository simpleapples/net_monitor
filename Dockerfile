FROM python:3.9-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    iputils-ping \
    dnsutils \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

COPY network_monitor.py .

RUN mkdir -p /logs

# Environment variables (can be overridden at runtime):
ENV TIMEOUT=1 \
    LOG_DIR=/logs \
    PING_TARGET=8.8.8.8 \
    DNS_TARGET=google.com \
    TCP_TARGET=google.com:80

ENTRYPOINT ["sh", "-c", "python3 network_monitor.py --timeout $TIMEOUT --log-dir $LOG_DIR --ping $PING_TARGET --dns $DNS_TARGET --tcp $TCP_TARGET"]
