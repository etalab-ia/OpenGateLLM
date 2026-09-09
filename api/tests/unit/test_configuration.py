import logging

from api.schemas.core.configuration import Settings
from common.configuration import load_yaml_config, replace_environment_variables


class TestSettingsDefaults:
    def test_default_values_when_no_values_provided(self):
        settings = Settings()
        assert settings.auth_master_key == "changeme"
        assert settings.auth_bootsrap_admin_username == "admin"
        assert settings.auth_bootsrap_admin_password == "changeme"
        assert settings.auth_key_max_expiration_days is None

    def test_auth_secret_key_falls_back_to_master_key_when_not_set(self):
        """When auth_secret_key is omitted, the validator copies auth_master_key into it."""
        settings = Settings(auth_master_key="my-master", auth_secret_key=None)
        assert settings.auth_secret_key == "my-master"

    def test_auth_secret_key_is_used_as_is_when_provided(self):
        """When auth_secret_key is explicitly set it must not be replaced by auth_master_key."""
        settings = Settings(auth_master_key="my-master", auth_secret_key="my-secret")
        assert settings.auth_secret_key == "my-secret"

    def test_auth_master_key_does_not_override_explicit_secret_key(self):
        """Changing auth_master_key must have no effect on encryption when auth_secret_key is set."""
        settings_a = Settings(auth_master_key="key-A", auth_secret_key="shared-secret")
        settings_b = Settings(auth_master_key="key-B", auth_secret_key="shared-secret")
        assert settings_a.auth_secret_key == settings_b.auth_secret_key == "shared-secret"


class TestAuthMasterKeyDeprecation:
    def test_deprecation_warning_emitted_when_secret_key_not_set(self, caplog):
        with caplog.at_level(logging.WARNING):
            Settings(auth_master_key="changeme", auth_secret_key=None)
        assert any("auth_secret_key" in msg and "DEPRECATED" not in msg.upper() or "auth_master_key" in msg for msg in caplog.messages)
        assert any("auth_secret_key" in msg for msg in caplog.messages)

    def test_no_deprecation_warning_when_secret_key_is_set(self, caplog):
        with caplog.at_level(logging.WARNING):
            Settings(auth_master_key="changeme", auth_secret_key="dedicated-secret")
        assert not any("Falling back to" in msg for msg in caplog.messages)

    def test_deprecation_message_mentions_v1_removal(self, caplog):
        """The deprecation warning must state when auth_master_key fallback will be removed."""
        with caplog.at_level(logging.WARNING):
            Settings(auth_master_key="changeme", auth_secret_key=None)
        assert any("v1.0.0" in msg for msg in caplog.messages)


class TestSharedSettings:
    def test_should_inherit_shared_defaults(self):
        settings = Settings()
        assert settings.app_title == "OpenGateLLM"
        assert settings.routing_max_priority == 4
        assert settings.auth_login_session_duration == 3600


class TestLoadYamlConfig:
    def test_should_substitute_environment_variables(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "secret-value")
        config_path = tmp_path / "config.yml"
        config_path.write_text("key: ${MY_SECRET}\n")

        assert load_yaml_config(str(config_path)) == {"key": "secret-value"}

    def test_should_use_default_when_environment_variable_is_missing(self, tmp_path, monkeypatch):
        monkeypatch.delenv("MY_SECRET", raising=False)
        config_path = tmp_path / "config.yml"
        config_path.write_text("key: ${MY_SECRET:-fallback}\n")

        assert load_yaml_config(str(config_path)) == {"key": "fallback"}

    def test_should_keep_placeholder_when_environment_variable_is_missing_without_default(self, tmp_path, monkeypatch, caplog):
        monkeypatch.delenv("MY_SECRET", raising=False)
        config_path = tmp_path / "config.yml"
        config_path.write_text("key: ${MY_SECRET}\n")

        with caplog.at_level(logging.WARNING):
            assert load_yaml_config(str(config_path)) == {"key": "${MY_SECRET}"}
        assert any("MY_SECRET" in msg for msg in caplog.messages)

    def test_should_strip_commented_lines(self, tmp_path):
        config_path = tmp_path / "config.yml"
        config_path.write_text("key: value\n# ignored: true\n")

        assert load_yaml_config(str(config_path)) == {"key": "value"}

    def test_should_prefer_environment_variable_over_default(self, monkeypatch):
        monkeypatch.setenv("MY_SECRET", "from-env")

        assert replace_environment_variables("key: ${MY_SECRET:-fallback}") == "key: from-env"
