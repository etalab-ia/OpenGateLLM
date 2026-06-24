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
        supervisord_config_path = "/etc/supervisor/conf.d/supervisord.oauth2-proxy.conf"

        settings = configuration.settings
        env["OAUTH2_PROXY_OIDC_ISSUER_URL"] = settings.auth_sso_oidc_issuer_url
        env["OAUTH2_PROXY_CLIENT_ID"] = settings.auth_sso_client_id
        env["OAUTH2_PROXY_CLIENT_SECRET"] = settings.auth_sso_client_secret
        env["OAUTH2_PROXY_COOKIE_SECRET"] = settings.auth_sso_cookie_secret
        env["OAUTH2_PROXY_COOKIE_SECURE"] = str(settings.auth_sso_cookie_secure).lower()
        base = settings.auth_playground_url + "/" if not settings.auth_playground_url.endswith("/") else settings.auth_playground_url
        env["OAUTH2_PROXY_REDIRECT_URL"] = urljoin(base=base, url="oauth2/callback")
        env["OAUTH2_PROXY_SCOPE"] = settings.auth_sso_oidc_scope
        env["OAUTH2_PROXY_LOGOUT_REDIRECT_URI"] = settings.auth_sso_logout_redirect_uri
        env["OAUTH2_PROXY_COOKIE_EXPIRE"] = f"{settings.auth_login_session_duration}s"

        issuer_domain = urlparse(url=settings.auth_sso_oidc_issuer_url).netloc
        app_domain = urlparse(url=settings.auth_playground_url).netloc
        env["OAUTH2_PROXY_WHITELIST_DOMAINS"] = f"{app_domain},{issuer_domain}"

    else:
        supervisord_config_path = "/etc/supervisor/conf.d/supervisord.conf"
        logger.info("playground: SSO disabled, using default nginx configuration")
        shutil.copy("/playground/nginx.conf", nginx_conf_dst)

    supervisord_path = shutil.which("supervisord")
    if not supervisord_path:
        raise RuntimeError("supervisord executable not found in PATH")

    os.execve(
        path=supervisord_path,
        argv=["supervisord", "-c", supervisord_config_path],
        env=env,
    )


if __name__ == "__main__":
    main()
