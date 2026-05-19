from unittest.mock import AsyncMock, patch

import pytest

from api.schemas.core.configuration import Configuration, Dependencies, Settings
from api.use_cases.admin import BootstrapAdminCommand, BootstrapAdminUseCaseSkipped, BootstrapAdminUseCaseSuccess
from api.utils.lifespan import bootstrap_admin_role_and_user

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "s3cr3t"


@pytest.fixture
def bootstrap_configuration() -> Configuration:
    return Configuration.model_construct(
        settings=Settings.model_construct(
            auth_bootsrap_admin_username=ADMIN_USERNAME,
            auth_bootsrap_admin_password=ADMIN_PASSWORD,
        ),
        dependencies=Dependencies.model_construct(sentry=None),
    )


@pytest.fixture
def postgres_session():
    return AsyncMock()


class TestBootstrapAdmin:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "use_case_result,expected_user_id",
        [
            (BootstrapAdminUseCaseSuccess(user_id=10, email=ADMIN_USERNAME, role_id=42), 10),
            (BootstrapAdminUseCaseSkipped(user_id=7, email=ADMIN_USERNAME, role_id=99), 7),
        ],
    )
    async def test_happy_path(self, bootstrap_configuration, postgres_session, use_case_result, expected_user_id):
        mock_use_case = AsyncMock()
        mock_use_case.execute.return_value = use_case_result

        with patch("api.utils.lifespan.BootstrapAdminUseCase", return_value=mock_use_case):
            result = await bootstrap_admin_role_and_user(
                configuration=bootstrap_configuration,
                postgres_session=postgres_session,
            )

        assert result == expected_user_id
        mock_use_case.execute.assert_awaited_once_with(
            BootstrapAdminCommand(email=ADMIN_USERNAME, password=ADMIN_PASSWORD),
        )
