#!/usr/bin/env python3

import json
import logging
import os
from pathlib import Path
import shutil
from urllib.parse import urljoin, urlparse

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from app.core.configuration import configuration

logger = logging.getLogger(__name__)

# Read by oauth2-proxy-entrypoint.sh.
OAUTH2_PROXY_ALPHA_CONFIG_PATH = "/playground/oauth2-proxy-alpha.yaml"


def write_oauth2_proxy_alpha_config(settings) -> None:
    claims = settings.auth_sso_oidc_claims or {}
    acr = claims.get("id_token", {}).get("acr", {})
    environment = Environment(loader=FileSystemLoader(Path(__file__).parent), undefined=StrictUndefined, trim_blocks=True, lstrip_blocks=True)
    rendered = environment.get_template("oauth2-proxy-alpha.yaml.j2").render(
        client_id=settings.auth_sso_client_id,
        client_secret=settings.auth_sso_client_secret,
        issuer_url=settings.auth_sso_oidc_issuer_url,
        scope=settings.auth_sso_oidc_scope or "",
        claims_json=json.dumps(claims, separators=(",", ":")) if claims else "",
        acr_values=acr.get("values") or ([acr["value"]] if "value" in acr else []),
    )
    descriptor = os.open(OAUTH2_PROXY_ALPHA_CONFIG_PATH, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(rendered)


def main():
    logging.basicConfig(level=logging.INFO)
    settings = configuration.settings
    env = os.environ.copy()

    if settings.auth_login_type == "oidc":
        logger.info("playground: SSO enabled, using oauth2-proxy nginx configuration")
        nginx_config_path = "/playground/nginx.oauth2-proxy.conf"
        supervisord_config_path = "/etc/supervisor/conf.d/supervisord.oauth2-proxy.conf"

        write_oauth2_proxy_alpha_config(settings)
        # Options with no alpha config field: oauth2-proxy reads them from the environment.
        env.update(
            {
                "OAUTH2_PROXY_COOKIE_SECRET": settings.auth_sso_cookie_secret,
                "OAUTH2_PROXY_COOKIE_SECURE": str(settings.auth_sso_cookie_secure).lower(),
                "OAUTH2_PROXY_COOKIE_EXPIRE": f"{settings.auth_login_session_duration}s",
                "OAUTH2_PROXY_COOKIE_REFRESH": "5m",
                "OAUTH2_PROXY_COOKIE_NAME": "_oauth2_proxy_opengatellm",
                "OAUTH2_PROXY_COOKIE_SAMESITE": "lax",
                "OAUTH2_PROXY_EMAIL_DOMAINS": "*",
                "OAUTH2_PROXY_SKIP_AUTH_ROUTES": "/ping",
                "OAUTH2_PROXY_SKIP_PROVIDER_BUTTON": "true",
                "OAUTH2_PROXY_REQUEST_LOGGING": "true",
                "OAUTH2_PROXY_AUTH_LOGGING": "true",
                "OAUTH2_PROXY_STANDARD_LOGGING": "true",
                "OAUTH2_PROXY_LOGOUT_REDIRECT_URI": settings.auth_sso_logout_redirect_uri,
                "OAUTH2_PROXY_REDIRECT_URL": urljoin(settings.auth_playground_url.rstrip("/") + "/", "oauth2/callback"),
                "OAUTH2_PROXY_WHITELIST_DOMAINS": f"{urlparse(settings.auth_playground_url).netloc},{urlparse(settings.auth_sso_oidc_issuer_url).netloc}",
            }
        )
    else:
        logger.info("playground: SSO disabled, using default nginx configuration")
        nginx_config_path = "/playground/nginx.conf"
        supervisord_config_path = "/etc/supervisor/conf.d/supervisord.conf"

    shutil.copy(nginx_config_path, "/etc/nginx/conf.d/default.conf")

    supervisord_path = shutil.which("supervisord")
    if not supervisord_path:
        raise RuntimeError("supervisord executable not found in PATH")

    os.execve(supervisord_path, ["supervisord", "-c", supervisord_config_path], env)


if __name__ == "__main__":
    main()
