from fastapi import HTTPException

# 400


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


# 404
class ModelNotFoundHTTPException(HTTPException):
    def __init__(self, detail: str = "Model not found.") -> None:
        super().__init__(status_code=404, detail=detail)


# 409
class RouterAliasAlreadyExistsHTTPException(HTTPException):
    def __init__(self, aliases: list[str]):
        super().__init__(status_code=409, detail=f"Following aliases already exist: '{aliases}'")


class RouterAlreadyExistsHTTPException(HTTPException):
    def __init__(self, name: str):
        super().__init__(status_code=409, detail=f"Router '{name}' already exists.")


# 413


# 422


# 424


# 429


# 500
class InternalServerHTTPException(HTTPException):
    """Exception for unexpected internal errors."""

    def __init__(self, detail: str = "An unexpected error occurred"):
        super().__init__(status_code=500, detail=detail)


# 503
