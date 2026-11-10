import os
from pathlib import Path
import subprocess
import sys

import pytest

PLAYGROUND_ROOT = Path(__file__).parents[4] / "playground"
# The variables of the configuration below, removed from the environment so a value set on the machine running the tests cannot hide a failure.
TEST_VARIABLES = ("AUTH_PLAYGROUND_URL", "AUTH_SSO_CLIENT_SECRET", "OPENGATELLM_URL")
CONFIG_FILE_SSO = """
dependencies:
  redis:
    url: redis://localhost:6379
settings:
  auth_login_type: oidc
  auth_sso_oidc_issuer_url: https://issuer.example.com
  auth_sso_logout_redirect_uri: https://playground.example.com/logout
  auth_sso_client_id: client
  auth_sso_client_secret: ${AUTH_SSO_CLIENT_SECRET}
  auth_playground_url: ${AUTH_PLAYGROUND_URL}
  playground_opengatellm_url: ${OPENGATELLM_URL:-http://api:8000}
"""
IMPORT_CONFIGURATION = "import app.core.configuration"
LOAD_SETTINGS_LOGIN_OIDC = "from app.core.configuration import get_settings_login_oidc; print(get_settings_login_oidc().auth_playground_url)"


@pytest.fixture
def run_in_playground(tmp_path):
    def run(program: str, config: str, **variables: str) -> subprocess.CompletedProcess:
        config_file = tmp_path / "config.yml"
        config_file.write_text(config)
        # A fresh interpreter with the playground as working directory, the way `reflex export` and the container entrypoint run it.
        environment = {key: value for key, value in os.environ.items() if key not in TEST_VARIABLES}
        environment.update({"CONFIG_FILE": str(config_file), **variables})

        return subprocess.run([sys.executable, "-c", program], cwd=PLAYGROUND_ROOT, env=environment, capture_output=True, text=True)

    return run


class TestPlaygroundConfiguration:
    def test_should_build_the_application_configuration_without_the_run_time_variables(self, run_in_playground):
        # Arrange & Act
        result = run_in_playground(IMPORT_CONFIGURATION, CONFIG_FILE_SSO)

        # Assert
        assert result.returncode == 0, result.stderr

    def test_should_stop_the_application_configuration_on_a_missing_variable_it_reads(self, run_in_playground):
        # Arrange
        config = CONFIG_FILE_SSO.replace("${OPENGATELLM_URL:-http://api:8000}", "${OPENGATELLM_URL}")

        # Act
        result = run_in_playground(IMPORT_CONFIGURATION, config)

        # Assert
        assert result.returncode != 0
        assert "OPENGATELLM_URL" in result.stderr

    def test_should_stop_the_settings_login_oidc_on_a_missing_variable(self, run_in_playground):
        # Arrange & Act
        result = run_in_playground(LOAD_SETTINGS_LOGIN_OIDC, CONFIG_FILE_SSO, AUTH_SSO_CLIENT_SECRET="3VJJvfX1")

        # Assert
        assert result.returncode != 0
        assert "AUTH_PLAYGROUND_URL" in result.stderr
        assert "3VJJvfX1" not in result.stderr

    def test_should_load_the_settings_login_oidc_from_the_environment(self, run_in_playground):
        # Arrange & Act
        result = run_in_playground(
            LOAD_SETTINGS_LOGIN_OIDC,
            CONFIG_FILE_SSO,
            AUTH_SSO_CLIENT_SECRET="3VJJvfX1",
            AUTH_PLAYGROUND_URL="https://playground.example.com",
        )

        # Assert
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "https://playground.example.com"
