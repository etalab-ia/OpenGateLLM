import pytest

from api.tests.unit.use_case.factories import UserFactory

_MATCHING_IDENTITY = {
    "email": "user@test.com",
    "name": "Test User",
    "iss": "https://issuer.example.com",
    "sub": "oidc-subject",
    "claims": {"name": "Test User"},
    "organization_id": 1,
    "role_id": 10,
}


class TestUserNeedToUpdate:
    def test_should_return_false_when_all_fields_match(self):
        # Arrange
        user = UserFactory(
            email=_MATCHING_IDENTITY["email"],
            name=_MATCHING_IDENTITY["name"],
            iss=_MATCHING_IDENTITY["iss"],
            sub=_MATCHING_IDENTITY["sub"],
            claims=_MATCHING_IDENTITY["claims"],
            organization_id=_MATCHING_IDENTITY["organization_id"],
            role=_MATCHING_IDENTITY["role_id"],
        )

        # Act / Assert
        assert user.need_to_update(**_MATCHING_IDENTITY) is False

    @pytest.mark.parametrize(
        "field,value",
        [
            ("email", "other@test.com"),
            ("name", "Other User"),
            ("iss", "https://other-issuer.example.com"),
            ("sub", "other-subject"),
            ("claims", {"other": True}),
            ("organization_id", 99),
            ("role_id", 99),
        ],
    )
    def test_should_return_true_when_a_field_differs(self, field, value):
        # Arrange
        user = UserFactory(
            email=_MATCHING_IDENTITY["email"],
            name=_MATCHING_IDENTITY["name"],
            iss=_MATCHING_IDENTITY["iss"],
            sub=_MATCHING_IDENTITY["sub"],
            claims=_MATCHING_IDENTITY["claims"],
            organization_id=_MATCHING_IDENTITY["organization_id"],
            role=_MATCHING_IDENTITY["role_id"],
        )
        identity = {**_MATCHING_IDENTITY, field: value}

        # Act / Assert
        assert user.need_to_update(**identity) is True
