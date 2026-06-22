#!/usr/bin/env python3

import logging
import os
import shutil
from urllib.parse import urljoin, urlparse

from app.core.configuration import configuration

logger = logging.getLogger(__name__)


def main():
    env = os.environ.copy()
    nginx_conf_dst = "/etc/nginx/conf.d/default.conf"

    if configuration.settings.auth_login_type == "oidc":
        logger.info("playground: SSO enabled, using oauth2-proxy nginx configuration")
        shutil.copy("/playground/nginx.oauth2-proxy.conf", nginx_conf_dst)

        settings = configuration.settings
        env["OAUTH2_PROXY_OIDC_ISSUER_URL"] = env.get("OAUTH2_PROXY_OIDC_ISSUER_URL", settings.auth_sso_oidc_issuer_url)
        env["OAUTH2_PROXY_CLIENT_ID"] = env.get("OAUTH2_PROXY_CLIENT_ID", settings.auth_sso_client_id)
        env["OAUTH2_PROXY_CLIENT_SECRET"] = env.get("OAUTH2_PROXY_CLIENT_SECRET", settings.auth_sso_client_secret)
        env["OAUTH2_PROXY_COOKIE_SECRET"] = env.get("OAUTH2_PROXY_COOKIE_SECRET", settings.auth_sso_cookie_secret)
        env["OAUTH2_PROXY_REDIRECT_URL"] = env.get("OAUTH2_PROXY_REDIRECT_URL", urljoin(base=settings.auth_app_url, url="/oauth2/callback"))
        env["OAUTH2_PROXY_SCOPE"] = env.get("OAUTH2_PROXY_SCOPE", settings.auth_sso_oidc_scope)
        env["OAUTH2_PROXY_COOKIE_SECURE"] = env.get("OAUTH2_PROXY_COOKIE_SECURE", str(settings.auth_sso_cookie_secure).lower())

        env["OAUTH2_PROXY_LOGOUT_REDIRECT_URI"] = env.get("OAUTH2_PROXY_LOGOUT_REDIRECT_URI", settings.auth_sso_logout_redirect_uri)

        issuer_domain = urlparse(url=settings.auth_sso_oidc_issuer_url).netloc
        app_domain = urlparse(url=settings.auth_app_url).netloc
        env["OAUTH2_PROXY_WHITELIST_DOMAINS"] = env.get("OAUTH2_PROXY_WHITELIST_DOMAINS", f"{app_domain},{issuer_domain}")

    else:
        logger.info("playground: SSO disabled, using default nginx configuration")
        shutil.copy("/playground/nginx.conf", nginx_conf_dst)

    supervisord_path = shutil.which("supervisord")
    if not supervisord_path:
        raise RuntimeError("supervisord executable not found in PATH")

    os.execve(
        path=supervisord_path,
        argv=["supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"],
        env=env,
    )


if __name__ == "__main__":
    main()
