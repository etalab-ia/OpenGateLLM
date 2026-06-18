from dataclasses import dataclass


@dataclass
class InvalidOidcTokenError:
    message: str | None = None


@dataclass
class SsoProviderNotAvailableError:
    message: str | None = None
