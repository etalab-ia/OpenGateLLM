from tiktoken import Encoding

from api.domain.model import ModelTokenizer


class TiktokenModelTokenizer(ModelTokenizer):
    def __init__(self, model: Encoding):
        self.model = model

    def compute_tokens(self, texts: list[str]) -> int:
        if texts:
            # encode() rejects text matching a special token (<|endoftext|>): user text is counted as ordinary text.
            return len(self.model.encode_ordinary(" ".join(texts).strip()))
        return 0
