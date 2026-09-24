import logging

from api.infrastructure.configuration import ConfigFile, Settings


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


REQUIRED_DEPENDENCIES = {
    "postgres": {"url": "postgresql+asyncpg://postgres:changeme@localhost:5432/postgres"},
    "redis": {"url": "redis://:changeme@localhost:6379"},
}
LANGFUSE_DEPENDENCY = {"public_key": "pk-lf-test", "secret_key": "sk-lf-test"}


class TestUsageRepositorySelection:
    """The usage backend is picked from the presence of the `langfuse` dependency,
    without any dedicated `usage_source` setting."""

    def _resolve(self, langfuse_dependency):
        from unittest.mock import MagicMock, patch

        import api.dependencies as dependencies
        from api.infrastructure.langfuse import LangfuseUsageRepository
        from api.infrastructure.postgres import PostgresUsageRepository

        config = ConfigFile(dependencies={**REQUIRED_DEPENDENCIES, **({"langfuse": langfuse_dependency} if langfuse_dependency else {})})
        with (
            patch.object(dependencies, "configuration", config),
            patch.object(dependencies.global_context, "langfuse", MagicMock()),
        ):
            repository = dependencies._usage_repository(background_tasks=MagicMock(), postgres_session=MagicMock())
        return repository, LangfuseUsageRepository, PostgresUsageRepository

    def test_defaults_to_postgres_without_langfuse_dependency(self):
        repository, LangfuseUsageRepository, PostgresUsageRepository = self._resolve(langfuse_dependency=None)
        assert isinstance(repository, PostgresUsageRepository)

    def test_uses_langfuse_when_langfuse_dependency_is_configured(self):
        repository, LangfuseUsageRepository, PostgresUsageRepository = self._resolve(langfuse_dependency=LANGFUSE_DEPENDENCY)
        assert isinstance(repository, LangfuseUsageRepository)
