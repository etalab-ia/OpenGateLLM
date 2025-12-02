FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /

COPY ./api/ /api

ARG BUILD_TARGET=api

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv pip install ".[${BUILD_TARGET}]"

# Runtime stage
FROM python:3.12-slim AS runtime

RUN groupadd --gid 1100 opengatellm && \
    useradd --home /api --gid 1100 --uid 1100 opengatellm

# Only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Set a non-root user
USER opengatellm
WORKDIR /

# Copy application from builder
COPY --from=builder --chown=opengatellm:opengatellm /api /api
COPY --from=builder --chown=opengatellm:opengatellm /.venv /.venv
COPY --chown=opengatellm:opengatellm ./scripts/ /scripts

ENV PATH="/.venv/bin:${PATH}"
ENV PYTHONPATH="/api"

# Final stage: uses BUILD_TARGET to select script and command
FROM runtime AS final
ARG BUILD_TARGET=api
ENV BUILD_TARGET=${BUILD_TARGET}

RUN chmod u+x /scripts/startup_worker.sh /scripts/startup_api.sh
CMD ["/bin/bash", "-c", "/scripts/startup_${BUILD_TARGET}.sh"]
