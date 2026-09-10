FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssh-client && \
    pip install --no-cache-dir ansible && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /ansible

CMD ["ansible", "--version"]