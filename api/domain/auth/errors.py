from dataclasses import dataclass


@dataclass
class SSOAccessDeniedError:
    message: str | None = None


@dataclass
class SsoProviderNotAvailableError:
    message: str | None = None


@dataclass
class SsoInvalidSessionError:
    message: str | None = None
