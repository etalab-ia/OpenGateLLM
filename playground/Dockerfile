FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y unzip curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /playground

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv pip install ".[playground]"

ARG CONFIG_FILE=config.example.yml \
    LOGO=./playground/assets/logo.svg \
    FAVICON=./playground/assets/logo.svg \
    REFLEX_BACKEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_PATH='' \
    PLAYGROUND_DISABLED_PAGES=''

COPY $CONFIG_FILE ./config.yml
COPY ./playground/ .
COPY $FAVICON ./assets/favicon.svg
COPY $LOGO ./assets/logo.svg

ENV CONFIG_FILE=config.yml \
    REFLEX_BACKEND_URL=$REFLEX_BACKEND_URL \
    REFLEX_FRONTEND_URL=$REFLEX_FRONTEND_URL \
    REFLEX_FRONTEND_PATH=$REFLEX_FRONTEND_PATH

RUN .venv/bin/reflex export --frontend-only --no-zip  --loglevel debug

FROM python:3.12-slim

WORKDIR /playground

ARG OAUTH2_PROXY_VERSION=v7.15.3
ARG TARGETARCH=amd64

RUN apt-get update && \
    apt-get install -y nginx supervisor curl unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

RUN case "${TARGETARCH}" in \
        amd64) OAUTH2_PROXY_ARCH=amd64 ;; \
        arm64) OAUTH2_PROXY_ARCH=arm64 ;; \
        *) echo "unsupported TARGETARCH: ${TARGETARCH}" >&2; exit 1 ;; \
    esac && \
    curl -fsSL "https://github.com/oauth2-proxy/oauth2-proxy/releases/download/${OAUTH2_PROXY_VERSION}/oauth2-proxy-${OAUTH2_PROXY_VERSION}.linux-${OAUTH2_PROXY_ARCH}.tar.gz" \
        -o /tmp/oauth2-proxy.tar.gz && \
    tar -xzf /tmp/oauth2-proxy.tar.gz -C /tmp && \
    mv "/tmp/oauth2-proxy-${OAUTH2_PROXY_VERSION}.linux-${OAUTH2_PROXY_ARCH}/oauth2-proxy" /usr/local/bin/oauth2-proxy && \
    chmod +x /usr/local/bin/oauth2-proxy && \
    rm -rf /tmp/oauth2-proxy.tar.gz "/tmp/oauth2-proxy-${OAUTH2_PROXY_VERSION}.linux-${OAUTH2_PROXY_ARCH}"

RUN groupadd --gid 1100 opengatellm && \
    useradd --home /playground --gid 1100 --uid 1100 --create-home opengatellm

COPY --chown=opengatellm:opengatellm ./playground/rxconfig.py ./rxconfig.py
COPY --chown=opengatellm:opengatellm ./playground/app ./app
COPY --chown=opengatellm:opengatellm ./playground/assets ./assets
COPY --chown=opengatellm:opengatellm ./playground/nginx.conf /playground/nginx.conf
COPY --chown=opengatellm:opengatellm ./playground/nginx.oauth2-proxy.conf /playground/nginx.oauth2-proxy.conf
COPY --chown=opengatellm:opengatellm ./playground/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=opengatellm:opengatellm ./playground/oauth2-proxy.cfg /playground/oauth2-proxy.cfg
COPY --chown=opengatellm:opengatellm ./playground/oauth2-proxy-entrypoint.sh /playground/oauth2-proxy-entrypoint.sh
COPY --chown=opengatellm:opengatellm ./playground/playground-entrypoint.py /playground/playground-entrypoint.py

RUN chmod +x /playground/oauth2-proxy-entrypoint.sh

COPY --from=builder --chown=opengatellm:opengatellm /playground/config.yml ./config.yml
COPY --from=builder --chown=opengatellm:opengatellm /playground/.venv ./.venv
COPY --from=builder --chown=opengatellm:opengatellm /playground/.web/build/client /usr/share/nginx/html

ENV CONFIG_FILE=config.yml \
    PATH="/playground/.venv/bin:${PATH}" \
    PYTHONPATH="/playground:"

RUN chown -R opengatellm:opengatellm /playground /var/lib/nginx /var/log/nginx /run /etc/supervisor /etc/nginx/conf.d /usr/share/nginx/html

EXPOSE 8501 4180

USER opengatellm

CMD ["python", "/playground/playground-entrypoint.py"]