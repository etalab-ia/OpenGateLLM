from dataclasses import dataclass


@dataclass
class DefaultSsoPolicyOrganizationIsNotSetError:
    message: str | None = None


@dataclass
class DefaultSsoPolicyRoleIsNotSetError:
    message: str | None = None


@dataclass
class SsoInvalidSessionError:
    message: str | None = None


@dataclass
class SsoProviderNotAvailableError:
    message: str | None = None


@dataclass
class SsoAccessDeniedError:
    message: str | None = None


@dataclass
class SsoPolicyRuleAlreadyExistsError:
    message: str | None = None


@dataclass
class SsoPolicyRuleNotFoundError:
    message: str | None = None
