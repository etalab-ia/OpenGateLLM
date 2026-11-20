# A named stage rather than a download pinned in an ARG, which Dependabot does not read
FROM quay.io/oauth2-proxy/oauth2-proxy:v7.15.4 AS oauth2-proxy

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

RUN apt-get update && \
    apt-get install -y unzip curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /playground

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    uv sync --locked --no-install-project --extra playground

ARG CONFIG_FILE=config.example.yml \
    LOGO=./playground/assets/logo.svg \
    FAVICON=./playground/assets/logo.svg \
    REFLEX_BACKEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_URL=http://localhost:8501 \
    REFLEX_FRONTEND_PATH='' \
    PLAYGROUND_DISABLED_PAGES='' \
    BUILD_PLACEHOLDER_VARIABLES=''

COPY $CONFIG_FILE ./config.yml
COPY ./playground/ .
COPY $FAVICON ./assets/favicon.svg
COPY $LOGO ./assets/logo.svg

ENV CONFIG_FILE=config.yml \
    REFLEX_BACKEND_URL=$REFLEX_BACKEND_URL \
    REFLEX_FRONTEND_URL=$REFLEX_FRONTEND_URL \
    REFLEX_FRONTEND_PATH=$REFLEX_FRONTEND_PATH

# The export loads the configuration file: a variable only available at run time gets a placeholder here, never its real value, which would stay in the image history.
RUN env $BUILD_PLACEHOLDER_VARIABLES .venv/bin/reflex export --frontend-only --no-zip  --loglevel debug

FROM python:3.12-slim

WORKDIR /playground

# Changes once a day in CI, so that the next layer is rebuilt and brings the Debian fixes instead of being reused from the cache
ARG APT_REFRESH

RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get upgrade -y && \
    apt-get install -y nginx supervisor curl unzip ca-certificates && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

COPY --from=oauth2-proxy /usr/bin/oauth2-proxy /usr/local/bin/oauth2-proxy

RUN groupadd --gid 1100 opengatellm && \
    useradd --home /playground --gid 1100 --uid 1100 --create-home opengatellm

COPY --chown=opengatellm:opengatellm ./playground/rxconfig.py ./rxconfig.py
COPY --chown=opengatellm:opengatellm ./playground/app ./app
COPY --chown=opengatellm:opengatellm ./playground/assets ./assets
COPY --chown=opengatellm:opengatellm ./playground/nginx.conf /playground/nginx.conf
COPY --chown=opengatellm:opengatellm ./playground/nginx.oauth2-proxy.conf /playground/nginx.oauth2-proxy.conf
COPY --chown=opengatellm:opengatellm ./playground/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY --chown=opengatellm:opengatellm ./playground/supervisord.oauth2-proxy.conf /etc/supervisor/conf.d/supervisord.oauth2-proxy.conf
COPY --chown=opengatellm:opengatellm ./playground/oauth2-proxy-alpha.yaml.j2 /playground/oauth2-proxy-alpha.yaml.j2
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