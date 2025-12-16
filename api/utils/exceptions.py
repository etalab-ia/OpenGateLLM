from fastapi import HTTPException


# 400
class MasterNotAllowedException(HTTPException):
    def __init__(self, detail: str = "Master is not allowed to process this action."):
        super().__init__(status_code=400, detail=detail)


class WrongSearchMethodException(HTTPException):
    def __init__(self, detail: str = "Wrong search method."):
        super().__init__(status_code=400, detail=detail)


class InsufficientBudgetException(HTTPException):
    def __init__(self, detail: str = "Insufficient budget."):
        super().__init__(status_code=400, detail=detail)


class InvalidTokenExpirationException(HTTPException):
    def __init__(self, detail: str = "Invalid token expiration."):
        super().__init__(status_code=400, detail=detail)


class InvalidProviderTypeException(HTTPException):
    def __init__(self, detail: str = "Invalid model provider type for this model router type."):
        super().__init__(status_code=400, detail=detail)


# 401
class InvalidCurrentPasswordException(HTTPException):
    def __init__(self, detail: str = "Invalid current password."):
        super().__init__(status_code=401, detail=detail)


class InvalidPasswordException(HTTPException):
    def __init__(self, detail: str = "Invalid password."):
        super().__init__(status_code=401, detail=detail)


# 403
class InvalidAuthenticationSchemeException(HTTPException):
    def __init__(self, detail: str = "Invalid authentication scheme.") -> None:
        super().__init__(status_code=403, detail=detail)


class InvalidAPIKeyException(HTTPException):
    def __init__(self, detail: str = "Invalid API key.") -> None:
        super().__init__(status_code=403, detail=detail)


class InsufficientPermissionException(HTTPException):
    def __init__(self, detail: str = "Insufficient rights.") -> None:
        super().__init__(status_code=403, detail=detail)


class ReservedEmailException(HTTPException):
    def __init__(self, detail: str = "Reserved email.") -> None:
        super().__init__(status_code=403, detail=detail)


class InconsistentModelVectorSizeException(HTTPException):
    def __init__(self, detail: str = "Inconsistent model vector size."):
        super().__init__(status_code=403, detail=detail)


class InconsistentModelMaxContextLengthException(HTTPException):
    def __init__(self, detail: str = "Inconsistent model max context length."):
        super().__init__(status_code=403, detail=detail)


class InconsistentModelCostsException(HTTPException):
    def __init__(self, detail: str = "Inconsistent model costs."):
        super().__init__(status_code=403, detail=detail)


# 404
class CollectionNotFoundException(HTTPException):
    def __init__(self, detail: str = "Collection not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class DocumentNotFoundException(HTTPException):
    def __init__(self, detail: str = "Document not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ChunkNotFoundException(HTTPException):
    def __init__(self, detail: str = "Chunk not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ModelNotFoundException(HTTPException):
    def __init__(self, detail: str = "Model not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class RouterNotFoundException(HTTPException):
    def __init__(self, detail: str = "Model router not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ProviderNotFoundException(HTTPException):
    def __init__(self, detail: str = "Model provider not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class RoleNotFoundException(HTTPException):
    def __init__(self, detail: str = "Role not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class TokenNotFoundException(HTTPException):
    def __init__(self, detail: str = "Token not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class ToolNotFoundException(HTTPException):
    def __init__(self, detail: str = "Tool not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class UserNotFoundException(HTTPException):
    def __init__(self, detail: str = "User not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class OrganizationNotFoundException(HTTPException):
    def __init__(self, detail: str = "Organization not found.") -> None:
        super().__init__(status_code=404, detail=detail)


class PasswordNotFoundException(HTTPException):
    def __init__(self, detail: str = "Password not set, please contact an administrator."):
        super().__init__(status_code=404, detail=detail)


# 409
class RoleAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Role already exists."):
        super().__init__(status_code=409, detail=detail)


class UserAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "User already exists."):
        super().__init__(status_code=409, detail=detail)


class OrganizationAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Organization already exists."):
        super().__init__(status_code=409, detail=detail)


class OrganizationNameAlreadyTakenException(HTTPException):
    def __init__(self, detail: str = "Organization name already taken. Please, choose another one."):
        super().__init__(status_code=409, detail=detail)


class ProviderAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Model provider already exists."):
        super().__init__(status_code=409, detail=detail)


class RouterAliasAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Name conflict with existing router or alias."):
        super().__init__(status_code=409, detail=detail)


class RouterAlreadyExistsException(HTTPException):
    def __init__(self, detail: str = "Model router already exists."):
        super().__init__(status_code=409, detail=detail)


class DeleteRoleWithUsersException(HTTPException):
    def __init__(self, detail: str = "Delete role with users is not allowed."):
        super().__init__(status_code=409, detail=detail)


class DeleteOrganizationWithUsersException(HTTPException):
    def __init__(self, detail: str = "Delete organization with users is not allowed."):
        super().__init__(status_code=409, detail=detail)


# 413
class FileSizeLimitExceededException(HTTPException):
    MAX_CONTENT_SIZE = 20 * 1024 * 1024  # 20MB

    def __init__(self, detail: str = f"File size limit exceeded (max: {MAX_CONTENT_SIZE} bytes).") -> None:
        super().__init__(status_code=413, detail=detail)


# 422
class ParsingDocumentFailedException(HTTPException):
    def __init__(self, detail: str = "Parsing document failed.") -> None:
        super().__init__(status_code=422, detail=detail)


class InvalidJSONFormatException(HTTPException):
    def __init__(self, detail: str = "Invalid JSON format.") -> None:
        super().__init__(status_code=422, detail=detail)


class WrongModelTypeException(HTTPException):
    def __init__(self, detail: str = "Wrong model type.") -> None:
        super().__init__(status_code=422, detail=detail)


class MaxTokensExceededException(HTTPException):
    def __init__(self, detail: str = "Max tokens exceeded.") -> None:
        super().__init__(status_code=422, detail=detail)


class DifferentCollectionsModelsException(HTTPException):
    def __init__(self, detail: str = "Different collections models.") -> None:
        super().__init__(status_code=422, detail=detail)


class UnsupportedFileTypeException(HTTPException):
    def __init__(self, detail: str = "Unsupported file type.") -> None:
        super().__init__(status_code=422, detail=detail)


class NotImplementedException(HTTPException):
    def __init__(self, detail: str = "Not implemented.") -> None:
        super().__init__(status_code=400, detail=detail)


class UnsupportedFileUploadException(HTTPException):
    def __init__(self, detail: str = "Unsupported collection name for upload file.") -> None:
        super().__init__(status_code=422, detail=detail)


# 424
class WebSearchNotAvailableException(HTTPException):
    def __init__(self, detail: str = "Web search is not available."):
        super().__init__(status_code=424, detail=detail)


class ProviderNotReachableException(HTTPException):
    def __init__(self, detail: str = "Model provider not reachable.") -> None:
        super().__init__(status_code=424, detail=detail)


# 429
class RateLimitExceeded(HTTPException):
    def __init__(self, detail: str = "Rate limit exceeded.") -> None:
        super().__init__(status_code=429, detail=detail)


# 500
class ChunkingFailedException(HTTPException):
    def __init__(self, detail: str = "Chunking failed.") -> None:
        super().__init__(status_code=500, detail=detail)


class VectorizationFailedException(HTTPException):
    def __init__(self, detail: str = "Vectorization failed.") -> None:
        super().__init__(status_code=500, detail=detail)


class TaskFailedException(HTTPException):
    def __init__(self, status_code: int = 500, detail: str = "Celery task failed.") -> None:
        super().__init__(status_code=status_code, detail=detail)


# 503
class ModelIsTooBusyException(HTTPException):
    def __init__(self, detail: str = "Model is too busy, please try again later.") -> None:
        super().__init__(status_code=503, detail=detail)
