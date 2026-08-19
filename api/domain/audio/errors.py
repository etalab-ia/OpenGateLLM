from dataclasses import dataclass


@dataclass
class AudioFileSizeLimitExceededError:
    size: int
    expected_size: int | None
