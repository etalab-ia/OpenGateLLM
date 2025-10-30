import os

import reflex as rx


config = rx.Config(
    app_name="app",
    plugins=[rx.plugins.SitemapPlugin()],
    backend_port=8500,
    frontend_port=8501,
    backend_host="0.0.0.0",
    api_url=os.environ.get("API_URL", "http://localhost:8501"),
)
