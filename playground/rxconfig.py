import os

from app.core.configuration import configuration
import reflex as rx

redis_url = None
state_manager_mode = rx.constants.StateManagerMode.DISK
if configuration.dependencies.redis is not None:
    redis_url = configuration.dependencies.redis.url
    state_manager_mode = rx.constants.StateManagerMode.REDIS


config = rx.Config(
    app_name="app",
    plugins=[rx.plugins.SitemapPlugin()],
    backend_port=8500,
    backend_host="0.0.0.0",
    api_url=os.environ.get("REFLEX_BACKEND_URL", "http://localhost:8500"),
    deploy_url=os.environ.get("REFLEX_FRONTEND_URL", "http://localhost:8501"),
    frontend_path=os.environ.get("REFLEX_FRONTEND_PATH", ""),
    redis_url=redis_url,
    state_manager_mode=state_manager_mode,
)
