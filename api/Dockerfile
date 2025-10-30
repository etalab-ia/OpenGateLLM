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

RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv pip install ".[api,test]"

# Final stage
FROM python:3.12-slim

RUN groupadd --gid 1100 opengatellm && \
    useradd --home /api --gid 1100 --uid 1100 opengatellm

# Only runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

COPY scripts/startup_api.sh /startup.sh
RUN chown opengatellm:opengatellm /startup.sh
RUN chmod u+x /startup.sh

# Set a non-root user
USER opengatellm
WORKDIR /

# Copy application from builder
COPY --from=builder --chown=opengatellm:opengatellm /api /api
COPY ./scripts/ /scripts
COPY --from=builder --chown=opengatellm:opengatellm /.venv /.venv
ENV PATH="/.venv/bin:${PATH}"
ENV PYTHONPATH="/api:${PYTHONPATH}"

# Launch the application
CMD ["./startup.sh"]
