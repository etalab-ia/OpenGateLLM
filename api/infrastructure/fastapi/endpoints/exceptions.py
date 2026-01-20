from fastapi import HTTPException

# 400


# 401


# 403
class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key.") -> None:
        super().__init__(status_code=403, detail=detail)


class InsufficientPermissionHTTPException(HTTPException):
    def __init__(self, detail: str = "Insufficient rights.") -> None:
        super().__init__(status_code=403, detail=detail)


# 404


# 409
class RouterAliasAlreadyExistsHTTPException(HTTPException):
    def __init__(self, detail: str = "Name conflict with existing router or alias."):
        super().__init__(status_code=409, detail=detail)


class RouterAlreadyExistsHTTPException(HTTPException):
    def __init__(self, name: str):
        super().__init__(status_code=409, detail=f"Router '{name}' already exists.")


# 413


# 422


# 424


# 429


# 500


# 503
