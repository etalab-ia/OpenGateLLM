from fastapi import HTTPException
from humanize import naturalsize

from api.domain.role.entities import LimitType


# 400
class InconsistentModelMaxContextLengthHTTPException(HTTPException):
    status_code = 400
    detail = "Inconsistent max context length for {model_name}. Expected: {expected_length}. Actual: {actual_length}"

    def __init__(self, input_max_context_length: int, model_max_context_length: int, model_name: str) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=f"Inconsistent max context length for {model_name}. Expected: {model_max_context_length}. Actual: {input_max_context_length}",
        )


class InconsistentModelVectorSizeHTTPException(HTTPException):
    status_code = 400
    detail = "Inconsistent vector size for {model_name}. Expected: {expected_size}. Actual: {actual_size}"

    def __init__(self, input_vector_size: int, model_vector_size: int, model_name: str) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=f"Inconsistent vector size for {model_name}. Expected: {model_vector_size}. Actual: {input_vector_size}",
        )


class InvalidProviderTypeHTTPException(HTTPException):
    status_code = 400
    detail = "Invalid model provider type {input_type} for {expected_type} router."

    def __init__(self, incorrect_provider_type: str, router_type: str) -> None:
        super().__init__(status_code=self.status_code, detail=f"Invalid model provider type {incorrect_provider_type} for {router_type} router.")


class InsufficientBudgetHTTPException(HTTPException):
    status_code = 400
    detail = "Insufficient budget."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class KeyExpirationInvalidHTTPException(HTTPException):
    status_code = 400
    detail = "Key expiration timestamp cannot be greater than {max_expiration_days} days from now."

    def __init__(self, max_expiration_days: int) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=f"Key expiration timestamp cannot be greater than {max_expiration_days} days from now.",
        )


# 401
class InvalidAPIKeyHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid API key."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidCredentialsHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid email or password."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidCurrentPasswordHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid current password."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidAuthenticationSchemeHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid authentication scheme."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class SsoInvalidSessionHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid SSO session."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


# 403
class AccountExpiredHTTPException(HTTPException):
    status_code = 403
    detail = "Your account has expired. Please contact support to renew your account."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class NotAdminUserHTTPException(HTTPException):
    status_code = 403
    detail = "User has no admin rights."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class SSOAccessDeniedHTTPException(HTTPException):
    status_code = 403
    detail = "Access denied, please contact your administrator."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


# 404
class ModelNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Model {name} not found."

    def __init__(self, name: str) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model {name} not found.")


class RoleNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Role {role_id}|{name} not found."

    def __init__(self, role_id: int | None = None, name: str | None = None) -> None:
        if role_id is not None:
            detail = f"Role {role_id} not found."
        elif name is not None:
            detail = f"Role {name} not found."
        else:
            detail = "Role not found."

        super().__init__(status_code=self.status_code, detail=detail)


class OrganizationNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Organization {organization_id}|{name} not found."

    def __init__(self, organization_id: int | None = None, name: str | None = None) -> None:
        if organization_id is not None:
            detail = f"Organization {organization_id} not found."
        elif name is not None:
            detail = f"Organization {name} not found."
        else:
            detail = "Organization not found."

        super().__init__(status_code=self.status_code, detail=detail)


class RouterNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Model router {router_id} not found."

    def __init__(self, router_id: int) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model router {router_id} not found.")


class ProviderNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Model provider {provider_id} not found."

    def __init__(self, provider_id: int) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model provider {provider_id} not found.")


class UserNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "User {user_id}|{email} not found."

    def __init__(self, user_id: int | None = None, email: str | None = None) -> None:

        if user_id is not None:
            detail = f"User {user_id} not found."
        elif email is not None:
            detail = f"User {email} not found."
        else:
            detail = "User not found."

        super().__init__(status_code=self.status_code, detail=detail)


class KeyNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Key {key_id} not found."

    def __init__(self, key_id: int) -> None:
        super().__init__(status_code=self.status_code, detail=f"Key {key_id} not found.")


# 409
class KeyAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Key {name} already exists."

    def __init__(self, name: str):
        super().__init__(status_code=self.status_code, detail=f"Key {name} already exists.")


class UserAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "User {email} already exists."

    def __init__(self, email: str):
        super().__init__(status_code=self.status_code, detail=f"User {email} already exists.")


class RoleAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Role {role_name} already exists."

    def __init__(self, name: str):
        super().__init__(status_code=self.status_code, detail=f"Role {name} already exists.")


class RouterAliasAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Following aliases already exist: '{router_aliases}'"

    def __init__(self, aliases: list[str]):
        super().__init__(status_code=self.status_code, detail=f"Following aliases already exist: '{aliases}'")


class RouterAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Router {router_name} already exists."

    def __init__(self, name: str):
        super().__init__(status_code=self.status_code, detail=f"Router {name} already exists.")


class OrganizationAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Organization {name} already exists."

    def __init__(self, name: str):
        super().__init__(status_code=self.status_code, detail=f"Organization {name} already exists.")


class ProviderAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Model provider {model_name} for url {url} already exists for router {router_id}."

    def __init__(self, model_name: str, url: str, router_id: int) -> None:
        super().__init__(status_code=409, detail=f"Model provider {model_name} for url {url} already exists for router {router_id}.")


class RoleHasUsersHTTPException(HTTPException):
    status_code = 409
    detail = "Role {role_id} still has users and cannot be removed."

    def __init__(self, role_id: int) -> None:
        super().__init__(status_code=409, detail=f"Role {role_id} still has users and cannot be removed.")


class OrganizationHasUsersHTTPException(HTTPException):
    status_code = 409
    detail = "Organization {organization_id} still has users and cannot be removed."

    def __init__(self, organization_id: int) -> None:
        super().__init__(status_code=409, detail=f"Organization {organization_id} still has users and cannot be removed.")


class UserHasRoutersHTTPException(HTTPException):
    status_code = 409
    detail = "User {user_id} still has routers and cannot be removed."

    def __init__(self, user_id: int) -> None:
        super().__init__(status_code=409, detail=f"User {user_id} still has routers and cannot be removed.")


class UserHasProvidersHTTPException(HTTPException):
    status_code = 409
    detail = "User {user_id} still has providers and cannot be removed."

    def __init__(self, user_id: int) -> None:
        super().__init__(status_code=409, detail=f"User {user_id} still has providers and cannot be removed.")


# 413
class FileSizeLimitExceededHTTPException(HTTPException):
    status_code = 413
    detail = "File size limit exceeded. Expected: {expected_size}. Actual: {size}."

    def __init__(self, size: int, expected_size: int) -> None:
        size, expected_size = naturalsize(size), naturalsize(expected_size)
        super().__init__(status_code=self.status_code, detail=f"File size limit exceeded. Expected: {expected_size}. Actual: {size}.")


# 422
class WrongModelTypeHTTPException(HTTPException):
    status_code = 422
    detail = "Model has wrong type. Expected: {expected_type}. Actual: {actual_type}."

    def __init__(self, actual_type: str, expected_type: str) -> None:
        super().__init__(status_code=422, detail=f"Model has wrong type. Expected: {expected_type}. Actual: {actual_type}.")


# 424
class ProviderNotReachableHTTPException(HTTPException):
    status_code = 424
    detail = "Model provider {name} not reachable ({status_code}): {detail}"

    def __init__(self, name: str, status_code: int, detail: str) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model provider {name} not reachable ({status_code}): {detail}")


class ProviderInvalidResponseHTTPException(HTTPException):
    status_code = 424
    detail = "Model provider {name} returned an invalid response: {detail}"

    def __init__(self, name: str, detail: str) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model provider {name} returned an invalid response: {detail}")


# 429
class RateLimitExceededHTTPException(HTTPException):
    status_code = 429
    detail = "Token/request limit per minute/day exceeded."

    def __init__(self, limit_type: LimitType, headers: dict[str, str]) -> None:
        match limit_type:
            case LimitType.TPM:
                detail = "Token limit per minute exceeded."
            case LimitType.TPD:
                detail = "Token limit per day exceeded."
            case LimitType.RPM:
                detail = "Request limit per minute exceeded."
            case LimitType.RPD:
                detail = "Request limit per day exceeded."
        super().__init__(status_code=self.status_code, detail=detail, headers=headers)


# 500
class InternalServerHTTPException(HTTPException):
    status_code = 500
    detail = "An unexpected error occurred"

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


# 503
class ModelIsTooBusyExceptionHTTPException(HTTPException):
    status_code = 503
    detail = "Model is too busy, please try again later."

    def __init__(self, error_type: str | None = None) -> None:
        super().__init__(
            status_code=self.status_code,
            detail="Model is too busy, please try again later.",
            headers={"Retry-After": "10"},
        )


class SsoProviderNotAvailableHTTPException(HTTPException):
    status_code = 503
    detail = "SSO provider is not available."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)
