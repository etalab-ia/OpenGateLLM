from tiktoken import Encoding

from api.domain.model import ModelTokenizer


class TiktokenModelTokenizer(ModelTokenizer):
    def __init__(self, model: Encoding):
        self.model = model

    def compute_tokens(self, texts: list[str]) -> int:
        return len(self.model.encode(" ".join(texts).strip()))
