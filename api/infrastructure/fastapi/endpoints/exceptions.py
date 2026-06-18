from fastapi import HTTPException

from api.schemas.admin.roles import LimitType


# 400
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


# 401
class InvalidAPIKeyHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid API key."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidOidcTokenHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid OIDC token."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidPasswordHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid password."

    def __init__(self) -> None:
        super().__init__(status_code=self.status_code, detail=self.detail)


class InvalidAuthenticationSchemeHTTPException(HTTPException):
    status_code = 401
    detail = "Invalid authentication scheme."

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


class InconsistentModelMaxContextLengthHTTPException(HTTPException):
    status_code = 403
    detail = "Inconsistent max context length for {model_name}. Expected: {expected_length}. Actual: {actual_length}"

    def __init__(self, input_max_context_length: int, model_max_context_length: int, model_name: str) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=f"Inconsistent max context length for {model_name}. Expected: {model_max_context_length}. Actual: {input_max_context_length}",
        )


class InconsistentModelVectorSizeHTTPException(HTTPException):
    status_code = 403
    detail = "Inconsistent vector size for {model_name}. Expected: {expected_size}. Actual: {actual_size}"

    def __init__(self, input_vector_size: int, model_vector_size: int, model_name: str) -> None:
        super().__init__(
            status_code=self.status_code,
            detail=f"Inconsistent vector size for {model_name}. Expected: {model_vector_size}. Actual: {input_vector_size}",
        )


# 404
class ModelNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Model {name} not found."

    def __init__(self, name: str) -> None:
        super().__init__(status_code=self.status_code, detail=f"Model {name} not found.")


class RoleNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Role {role_id} not found."

    def __init__(self, role_id: int) -> None:
        super().__init__(status_code=self.status_code, detail=f"Role {role_id} not found.")


class OrganizationNotFoundHTTPException(HTTPException):
    status_code = 404
    detail = "Organization {organization_id} not found."

    def __init__(self, organization_id: int) -> None:
        super().__init__(status_code=self.status_code, detail=f"Organization {organization_id} not found.")


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


class ProviderAlreadyExistsHTTPException(HTTPException):
    status_code = 409
    detail = "Model provider {model_name} for url {url} already exists for router {router_id}."

    def __init__(self, model_name: str, url: str, router_id: int) -> None:
        super().__init__(status_code=409, detail=f"Model provider {model_name} for url {url} already exists for router {router_id}.")


class RoleHasUsersHTTPException(HTTPException):
    status_code = 409
    detail = "Role {role_id} has {number_of_users} users and cannot be removed."

    def __init__(self, role_id: int, number_of_users: int) -> None:
        super().__init__(status_code=409, detail=f"Role {role_id} has {number_of_users} users and cannot be removed.")


class DeleteUserWithRoutersHTTPException(HTTPException):
    status_code = 409
    detail = "User cannot be deleted because the user owns routers: {router_ids}."

    def __init__(self, router_ids: list[int] | None) -> None:
        super().__init__(status_code=409, detail=f"User cannot be deleted because the user owns routers: {router_ids}.")


class DeleteUserWithProvidersHTTPException(HTTPException):
    status_code = 409
    detail = "User cannot be deleted because the user owns providers: {provider_ids}."

    def __init__(self, provider_ids: list[int] | None) -> None:
        super().__init__(status_code=409, detail=f"User cannot be deleted because the user owns providers: {provider_ids}.")


# 413


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
