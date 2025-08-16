import pytest
from fastapi.testclient import TestClient
from app.schemas.admin.roles import PermissionType
from app.utils.variables import ENDPOINT__ADMIN_ROLES


@pytest.mark.usefixtures("client")
class TestIdentityAccessManager:
    def test_update_role(self, client: TestClient):
        """Test the update_role function through the API."""

        # Create a role to update
        role_data = {
            "name": "test-role",
            "permissions": [PermissionType.ADMIN.value],
            "limits": [
                {"model": "test-model", "type": "rpm", "value": 100},
                {"model": "test-model", "type": "rpd", "value": 1000},
            ],
        }

        # Create role via API
        response = client.post_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROLES}", json=role_data)
        assert response.status_code == 201, response.text
        role_id = response.json()["id"]

        # Update the role
        updated_role_data = {
            "name": "updated-role",
            "permissions": [PermissionType.ADMIN.value],
            "limits": [
                {"model": "new-model", "type": "rpm", "value": 200},
            ],
        }

        # Update role via API
        response = client.patch_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROLES}/{role_id}", json=updated_role_data)
        assert response.status_code == 204, response.text

        # Fetch the updated role
        response = client.get_with_permissions(url=f"/v1{ENDPOINT__ADMIN_ROLES}/{role_id}")
        assert response.status_code == 200, response.text
        updated_role = response.json()

        # Verify the updates
        assert updated_role["name"] == "updated-role"
        assert len(updated_role["limits"]) == 1
        assert updated_role["limits"][0]["model"] == "new-model"
        assert updated_role["limits"][0]["type"] == "rpm"
        assert updated_role["limits"][0]["value"] == 200
        assert len(updated_role["permissions"]) == 1
        assert updated_role["permissions"][0] == PermissionType.ADMIN.value
