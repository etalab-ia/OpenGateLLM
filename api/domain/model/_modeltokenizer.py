from abc import ABC, abstractmethod
from typing import Literal, get_args

TiktokenTokenizerName = Literal[
    "tiktoken_gpt2",
    "tiktoken_r50k_base",
    "tiktoken_p50k_base",
    "tiktoken_p50k_edit",
    "tiktoken_cl100k_base",
    "tiktoken_o200k_base",
]
TIKTOKEN_TOKENIZER_NAMES: tuple[str, ...] = get_args(TiktokenTokenizerName)


class ModelTokenizer(ABC):
    @abstractmethod
    def compute_tokens(self, texts: list[str]) -> int:
        pass
