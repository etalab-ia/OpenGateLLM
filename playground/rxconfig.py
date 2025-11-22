import os

import reflex as rx

from app.core.configuration import configuration

redis_url = None
if hasattr(configuration, "dependencies") and configuration.dependencies and configuration.dependencies.redis:
    redis_url = configuration.dependencies.redis.url

config = rx.Config(
    app_name="app",
    plugins=[rx.plugins.SitemapPlugin()],
    backend_port=8500,
    frontend_port=8501,
    backend_host="0.0.0.0",
    api_url=os.environ.get("REFLEX_BACKEND_URL", "http://localhost:8500"),
    deploy_url=os.environ.get("REFLEX_FRONTEND_URL", "http://localhost:8501"),
    frontend_path=os.environ.get("REFLEX_FRONTEND_PATH", ""),
    redis_url=redis_url,
)
