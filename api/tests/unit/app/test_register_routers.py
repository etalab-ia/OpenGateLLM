from types import SimpleNamespace
from unittest.mock import Mock, call, patch

import pytest

from api.app import _register_routers
from api.utils.variables import RouterName


class TestRegisterRouter:
    def test_should_register_enabled_routers_with_visibility_flags(self):
        # Arrange
        app = Mock()
        configuration = SimpleNamespace(
            settings=SimpleNamespace(
                disabled_routers=[router for router in RouterName if router not in {RouterName.ADMIN, RouterName.AUTH}],
                hidden_routers=[RouterName.AUTH],
            )
        )
        auth_router = object()
        admin_router = object()
        legacy_admin_router = object()

        modules_by_path = {
            RouterName.ADMIN.module_path: SimpleNamespace(router=admin_router),
            RouterName.AUTH.module_path: SimpleNamespace(router=auth_router),
            "api.infrastructure.fastapi.endpoints.admin_router": SimpleNamespace(router=legacy_admin_router),
        }

        # Act
        with patch("api.app.import_module", side_effect=lambda path: modules_by_path[path]) as mocked_import_module:
            _register_routers(app=app, configuration=configuration)

        # Assert
        assert mocked_import_module.call_args_list == [
            call(RouterName.ADMIN.module_path),
            call(RouterName.AUTH.module_path),
            call("api.infrastructure.fastapi.endpoints.admin_router"),
        ]
        assert app.include_router.call_args_list == [
            call(router=admin_router, include_in_schema=True),
            call(router=auth_router, include_in_schema=False),
            call(router=legacy_admin_router, include_in_schema=True),
        ]

    def test_should_skip_admin_router_when_admin_is_disabled(self):
        # Arrange
        app = Mock()
        configuration = SimpleNamespace(
            settings=SimpleNamespace(
                disabled_routers=[router for router in RouterName if router != RouterName.AUTH] + [RouterName.ADMIN],
                hidden_routers=[],
            )
        )
        auth_router = object()

        modules_by_path = {RouterName.AUTH.module_path: SimpleNamespace(router=auth_router)}

        # Act
        with patch("api.app.import_module", side_effect=lambda path: modules_by_path[path]) as mocked_import_module:
            _register_routers(app=app, configuration=configuration)

        # Assert
        assert mocked_import_module.call_args_list == [call(RouterName.AUTH.module_path)]
        app.include_router.assert_called_once_with(router=auth_router, include_in_schema=True)

    def test_should_raise_attribute_error_when_router_attribute_is_missing(self):
        # Arrange
        app = Mock()
        configuration = SimpleNamespace(
            settings=SimpleNamespace(
                disabled_routers=[router for router in RouterName if router != RouterName.AUTH] + [RouterName.ADMIN],
                hidden_routers=[],
            )
        )

        # Act / Assert
        with patch("api.app.import_module", return_value=SimpleNamespace()):
            with pytest.raises(AttributeError):
                _register_routers(app=app, configuration=configuration)
