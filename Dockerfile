FROM ubuntu:24.04 AS builder

RUN apt-get update && \
    apt-get install -y ocproxy openconnect supervisor && \
    rm -rf /var/lib/apt/lists/*

# uv for Python dependency management
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv

# glider forward proxy with rule-based routing
COPY --from=nadoo/glider:0.16.4 /app/glider /usr/local/bin/glider

# Python dependencies (separate layer for caching)
ENV UV_PYTHON=3.14 \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PYTHON_INSTALL_DIR=/opt/uv/python \
    OCPM_SOCKS_PORT=1080 \
    OCPM_HTTP_PORT=8080 \
    OCPM_WEBUI_PORT=8081
WORKDIR /ocpm
RUN uv python install 3.14
COPY webapp/pyproject.toml webapp/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev

# App code
COPY webapp/ .
COPY supervisor/supervisord.conf /etc/supervisor/conf.d/ocpm.conf
COPY glider/glider.conf /etc/ocpm/glider.conf
COPY glider/rules.example.rule /etc/ocpm/rules.rule
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh /usr/local/bin/glider

EXPOSE 1080 8080 8081

ENTRYPOINT ["/entrypoint.sh"]
