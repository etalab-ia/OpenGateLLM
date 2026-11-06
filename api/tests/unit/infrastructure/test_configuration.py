import os
from pathlib import Path
import subprocess
import sys

import pytest

from api.infrastructure.configuration import (
    Configuration,
    ConfigurationValidationError,
    ConfigurationVariableError,
    get_postgres_dependency,
    interpolate_variables,
)

REPOSITORY_ROOT = Path(__file__).parents[4]
CONFIG_FILE_DEPENDENCIES = """
dependencies:
  postgres:
    url: postgresql+asyncpg://localhost/postgres
  redis:
    url: redis://localhost:6379
"""
CONFIG_FILE_WITH_VARIABLES = """
dependencies:
  postgres:
    url: postgresql+asyncpg://postgres:${POSTGRES_PASSWORD}@localhost:5432/postgres
  redis:
    url: redis://:${REDIS_PASSWORD}@localhost:6379
"""


@pytest.fixture
def write_config_file(tmp_path):
    def write(content: str) -> str:
        config_file = tmp_path / "config.yml"
        config_file.write_text(content)
        return str(config_file)

    return write


class TestConfiguration:
    def test_should_import_the_app_modules_without_a_configuration_file(self, tmp_path):
        # Arrange
        # A fresh interpreter: in the pytest process these modules are already imported, so importing them again would prove nothing.
        environment = {**os.environ, "CONFIG_FILE": str(tmp_path / "missing.yml")}

        # Act
        result = subprocess.run(
            [sys.executable, "-c", "import api.infrastructure.configuration, api.dependencies, api.app"],
            cwd=REPOSITORY_ROOT,
            env=environment,
            capture_output=True,
            text=True,
        )

        # Assert
        assert result.returncode == 0, result.stderr

    @pytest.mark.parametrize("value", ["#abcdef", "abc #def", "abc: value", "{value", "12345", "${OTHER}", r"\1"])
    def test_should_keep_the_value_of_a_variable_unchanged(self, monkeypatch, value):
        # Arrange
        monkeypatch.setenv("SECRET", value)

        # Act
        interpolated = interpolate_variables({"nested": [{"setting": "${SECRET}"}], "number": 1})

        # Assert
        assert interpolated == {"nested": [{"setting": value}], "number": 1}

    def test_should_replace_a_variable_inside_a_longer_value(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("PASSWORD", "abc #def")

        # Act
        interpolated = interpolate_variables("postgresql+asyncpg://postgres:${PASSWORD}@${HOST:-localhost}:5432/postgres")

        # Assert
        assert interpolated == "postgresql+asyncpg://postgres:abc #def@localhost:5432/postgres"

    @pytest.mark.parametrize("environment_value", [None, ""])
    @pytest.mark.parametrize(("definition", "expected"), [("${VARIABLE:-default}", "default"), ("${VARIABLE:-}", "")])
    def test_should_apply_the_default_of_a_missing_or_empty_variable(self, monkeypatch, environment_value, definition, expected):
        # Arrange
        monkeypatch.delenv("VARIABLE", raising=False)
        if environment_value is not None:
            monkeypatch.setenv("VARIABLE", environment_value)

        # Act
        interpolated = interpolate_variables(definition)

        # Assert
        assert interpolated == expected

    def test_should_prefer_the_value_of_a_variable_to_its_default(self, monkeypatch):
        # Arrange
        monkeypatch.setenv("VARIABLE", "value")

        # Act
        interpolated = interpolate_variables("${VARIABLE:-default}")

        # Assert
        assert interpolated == "value"

    @pytest.mark.parametrize("environment_value", [None, ""])
    def test_should_raise_on_a_missing_or_empty_variable_without_a_default(self, monkeypatch, environment_value):
        # Arrange
        monkeypatch.delenv("VARIABLE", raising=False)
        if environment_value is not None:
            monkeypatch.setenv("VARIABLE", environment_value)

        # Act & Assert
        with pytest.raises(ConfigurationVariableError, match="VARIABLE"):
            interpolate_variables("${VARIABLE}")

    @pytest.mark.parametrize("definition", ["${secret}", "${secret:-changeme}", "${}", "${NAME WITH SPACE}"])
    def test_should_raise_on_an_invalid_variable_name_without_printing_its_default(self, definition):
        # Act & Assert
        with pytest.raises(ConfigurationVariableError, match="Invalid environment variable name") as error:
            interpolate_variables(definition)
        assert "changeme" not in str(error.value)

    def test_should_stop_the_configuration_on_a_missing_variable_without_printing_any_value(self, monkeypatch, write_config_file):
        # Arrange
        config_file = write_config_file(CONFIG_FILE_WITH_VARIABLES)
        monkeypatch.setenv("POSTGRES_PASSWORD", "postgres-secret")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        # Act & Assert
        with pytest.raises(ConfigurationVariableError, match="REDIS_PASSWORD") as error:
            Configuration(config_file=config_file)
        assert "postgres-secret" not in str(error.value)

    def test_should_load_the_postgres_dependency_without_the_variables_of_the_other_sections(self, monkeypatch, write_config_file):
        # Arrange
        monkeypatch.setenv("CONFIG_FILE", write_config_file(CONFIG_FILE_WITH_VARIABLES))
        monkeypatch.setenv("POSTGRES_PASSWORD", "abc #def")
        monkeypatch.delenv("REDIS_PASSWORD", raising=False)

        # Act
        postgres = get_postgres_dependency()

        # Assert
        assert postgres.url == "postgresql+asyncpg://postgres:abc #def@localhost:5432/postgres"

    def test_should_ignore_the_variables_of_the_yaml_comments(self, monkeypatch, write_config_file):
        # Arrange
        monkeypatch.delenv("COMMENTED_VARIABLE", raising=False)
        config_file = write_config_file(f"""{CONFIG_FILE_DEPENDENCIES}
settings:
  # A line holding ${{COMMENTED_VARIABLE}}
  auth_secret_key: secret # A value followed by ${{COMMENTED_VARIABLE}}
""")

        # Act
        configuration = Configuration(config_file=config_file)

        # Assert
        assert configuration.settings.auth_secret_key == "secret"

    def test_should_refuse_a_configuration_without_the_secret_key(self, write_config_file):
        # Arrange
        config_file = write_config_file(f"""{CONFIG_FILE_DEPENDENCIES}
settings:
  auth_bootsrap_admin_password: admin-secret
""")

        # Act & Assert
        with pytest.raises(ConfigurationValidationError, match="auth_secret_key") as error:
            Configuration(config_file=config_file)
        assert "input_value" not in str(error.value)

    def test_should_refuse_a_misspelled_secret_key_without_printing_its_value(self, write_config_file):
        # Arrange
        config_file = write_config_file(f"""{CONFIG_FILE_DEPENDENCIES}
settings:
  auth_secret_keyy: misspelled-secret
""")

        # Act & Assert
        with pytest.raises(ConfigurationValidationError, match="auth_secret_key") as error:
            Configuration(config_file=config_file)
        assert "input_value" not in str(error.value)

    def test_should_ignore_a_remaining_master_key(self, write_config_file):
        # Arrange
        config_file = write_config_file(f"""{CONFIG_FILE_DEPENDENCIES}
settings:
  auth_master_key: master
  auth_secret_key: secret
""")

        # Act
        configuration = Configuration(config_file=config_file)

        # Assert
        assert configuration.settings.auth_secret_key == "secret"
