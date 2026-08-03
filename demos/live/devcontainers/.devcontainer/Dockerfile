FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd --gid 1000 sandbox \
    && useradd --uid 1000 --gid 1000 --create-home sandbox

WORKDIR /workspace

USER sandbox
