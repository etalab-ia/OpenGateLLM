from fastapi import HTTPException


# 400
class InvalidProviderTypeHTTPException(HTTPException):
    def __init__(self, incorrect_provider_type: str, router_type: str) -> None:
        super().__init__(status_code=400, detail=f"Invalid model provider type {incorrect_provider_type} for {router_type} router.")


# 401


# 403
class InvalidAuthenticationSchemeException(HTTPException):
    def __init__(self, detail: str = "Invalid authentication scheme.") -> None:
        super().__init__(status_code=403, detail=detail)


class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key.") -> None:
        super().__init__(status_code=403, detail=detail)


class InsufficientPermissionHTTPException(HTTPException):
    def __init__(self, detail: str = "Insufficient rights.") -> None:
        super().__init__(status_code=403, detail=detail)


class InconsistentModelMaxContextLengthHTTPException(HTTPException):
    def __init__(self, input_max_context_length: int, model_max_context_length: int, model_name: str) -> None:
        super().__init__(
            status_code=403,
            detail=f"Inconsistent max context length for {model_name}. Expected: {model_max_context_length}. Actual: {input_max_context_length}",
        )


class InconsistentModelVectorSizeHTTPException(HTTPException):
    def __init__(self, input_vector_size: int, model_vector_size: int, model_name: str) -> None:
        super().__init__(
            status_code=403, detail=f"Inconsistent vector size for {model_name}. Expected: {model_vector_size}. Actual: {input_vector_size}"
        )


# 404
class ModelNotFoundHTTPException(HTTPException):
    def __init__(self, detail: str = "Model not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class RouterNotFoundHTTPException(HTTPException):
    def __init__(self, router_id: int) -> None:
        super().__init__(status_code=404, detail=f"Model router {router_id} not found.")


# 409
class RouterAliasAlreadyExistsHTTPException(HTTPException):
    def __init__(self, aliases: list[str]):
        super().__init__(status_code=409, detail=f"Following aliases already exist: '{aliases}'")


class RouterAlreadyExistsHTTPException(HTTPException):
    def __init__(self, name: str):
        super().__init__(status_code=409, detail=f"Router '{name}' already exists.")


class ProviderAlreadyExistsHTTPException(HTTPException):
    def __init__(self, model_name: str, url: str, router_id: int) -> None:
        super().__init__(status_code=409, detail=f"Model provider {model_name} for url {url} already exists for router {router_id}.")


# 413


# 422


# 424
class ProviderNotReachableHTTPException(HTTPException):
    def __init__(self, name: str) -> None:
        super().__init__(status_code=424, detail=f"Model provider {name} not reachable.")


# 429


# 500
class InternalServerHTTPException(HTTPException):
    """Exception for unexpected internal errors."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        super().__init__(status_code=500, detail=detail)


# 503
