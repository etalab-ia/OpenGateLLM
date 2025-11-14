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
    FAVICON=./playground/assets/favicon.ico \
    REFLEX_BACKEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_PATH=''

COPY $CONFIG_FILE ./config.yml
COPY ./playground/ .
COPY $FAVICON ./assets/favicon.ico

ENV CONFIG_FILE=config.yml \
    REFLEX_BACKEND_URL=$REFLEX_BACKEND_URL \
    REFLEX_FRONTEND_URL=$REFLEX_FRONTEND_URL \
    REFLEX_FRONTEND_PATH=$REFLEX_FRONTEND_PATH

RUN .venv/bin/reflex export --frontend-only --no-zip  --loglevel debug

FROM python:3.12-slim

WORKDIR /playground

RUN apt-get update && \
    apt-get install -y nginx supervisor curl unzip && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

RUN groupadd --gid 1100 opengatellm && \
    useradd --home /playground --gid 1100 --uid 1100 --create-home opengatellm

COPY --chown=opengatellm:opengatellm ./playground/rxconfig.py ./rxconfig.py
COPY --chown=opengatellm:opengatellm ./playground/app ./app
COPY --chown=opengatellm:opengatellm ./playground/assets ./assets
COPY --chown=opengatellm:opengatellm ./playground/nginx.conf /etc/nginx/conf.d/default.conf
COPY --chown=opengatellm:opengatellm ./playground/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

COPY --from=builder --chown=opengatellm:opengatellm /playground/config.yml ./config.yml
COPY --from=builder --chown=opengatellm:opengatellm /playground/.venv ./.venv
COPY --from=builder --chown=opengatellm:opengatellm /playground/.web/build/client /usr/share/nginx/html

ENV CONFIG_FILE=config.yml \
    PATH="/playground/.venv/bin:${PATH}" \
    PYTHONPATH="/playground:"

RUN chown -R opengatellm:opengatellm /playground /var/lib/nginx /var/log/nginx /run /etc/supervisor /usr/share/nginx/html

EXPOSE 8501

USER opengatellm

CMD ["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]