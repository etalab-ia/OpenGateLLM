import logging
import time
from urllib.parse import urlparse

import streamlit as st
from streamlit_extras.stylable_container import stylable_container

from playground.backend.login import call_oauth2_logout, decrypt_oauth_token, login, oauth_login
from playground.configuration import configuration  # Ensure configuration is imported

from .proconnect import css_proconnect, html_proconnect

logger = logging.getLogger(__name__)


def header():
    def authenticate():
        @st.dialog(title="Login")
        def login_form():
            with st.form(key="login"):  # ProConnect login
                if configuration.playground.proconnect_enabled:
                    with stylable_container(key="ProConnect", css_styles=css_proconnect):
                        if not configuration.playground.home_url.startswith("https"):  # if no https you must be working locally
                            proconnect_login_url = f"{configuration.playground.api_url}/v1/auth/proconnect"
                        else:  # else we are working in production and must use the proper API URL from the home_url
                            parsed_home_url = urlparse(configuration.playground.home_url)
                            api_base_url = f"{parsed_home_url.scheme}://{parsed_home_url.netloc}"
                            proconnect_login_url = f"{api_base_url}/v1/auth/proconnect"
                        st.markdown(
                            html_proconnect.format(
                                proconnect_login_url=proconnect_login_url,
                            ),
                            unsafe_allow_html=True,
                        )
                # Traditional login
                user_name = st.text_input(label="Email", type="default", key="user_id", icon=":material/email:")
                user_password = st.text_input(label="Password", type="password", key="password", icon=":material/lock:")

                # Strip input
                user_name = user_name.strip()
                user_password = user_password.strip()

                submit = st.form_submit_button(label="Submit")
                if submit:
                    login(user_name, user_password)

        # Access the encrypted token parameter
        encrypted_token = st.query_params.get("encrypted_token", None)

        if st.session_state.get("login_status") is None and encrypted_token:
            # Decrypt the token
            decrypted_data = decrypt_oauth_token(encrypted_token)
            if decrypted_data:
                api_key = decrypted_data.get("app_token")
                api_key_id = decrypted_data.get("token_id")
                proconnect_token = decrypted_data.get("proconnect_token")
                oauth_login(api_key, api_key_id, proconnect_token)

        if st.session_state.get("login_status") is None:
            login_form()

    with stylable_container(key="Header", css_styles="button{float: right;}"):
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Albert playground")

        # Authentication
        authenticate()
        if st.session_state.get("login_status") is None:
            st.stop()

        with col2:
            logout = st.button("Logout")
        if logout:
            api_key = st.session_state["user"].api_key if st.session_state.get("user") else None
            proconnect_token = st.session_state["user"].proconnect_token if st.session_state.get("user") else None

            # Call logout endpoint if we have an API token
            if api_key and proconnect_token:
                with st.spinner("Déconnexion en cours..."):
                    try:
                        # Call logout endpoint with optional ProConnect token
                        call_oauth2_logout(api_key, proconnect_token)
                    except Exception as e:
                        st.warning(f"Erreur lors de la déconnexion: {e}")

            # Always perform local logout regardless of API result
            st.session_state.pop("login_status", None)
            st.session_state.pop("user", None)
            st.cache_data.clear()
            st.rerun()

        if st.session_state.get("user") and st.session_state["user"].name == "master":
            st.warning("You are logged in as the master user. This is not recommended for production use, please use a regular user instead.")
        if st.session_state.get("user") and st.session_state["user"].expires_at and st.session_state["user"].expires_at < int(time.time()):  # fmt: off
            st.warning("**Your account has expired. Please contact support to renew your account.**")
        st.markdown("***")
