from tiktoken import Encoding

from api.domain.model import ModelTokenizer
from api.domain.model.errors import TextNotTokenizableError


class TiktokenModelTokenizer(ModelTokenizer):
    def __init__(self, model: Encoding):
        self.model = model

    def compute_tokens(self, texts: list[str]) -> int | TextNotTokenizableError:
        if not texts:
            return 0

        try:
            # encode() rejects text matching a special token (<|endoftext|>): user text is counted as ordinary text.
            return len(self.model.encode_ordinary(" ".join(texts).strip()))
        except ValueError:
            # tiktoken raises it when its regex runs out of stack, on a long run of whitespace for instance
            return TextNotTokenizableError()
