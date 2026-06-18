from dataclasses import dataclass


@dataclass
class InvalidOidcTokenError:
    message: str | None = None
    stale_jwks: bool = False


@dataclass
class OidcProviderNotAvailableError:
    message: str | None = None
