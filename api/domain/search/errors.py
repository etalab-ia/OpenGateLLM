from dataclasses import dataclass


@dataclass
class SearchArgsValidationError:
    errors: list[dict]


@dataclass
class SearchStatusCodeError:
    status_code: int
    detail: str | dict | list


@dataclass
class SearchUnreachableError:
    detail: str
