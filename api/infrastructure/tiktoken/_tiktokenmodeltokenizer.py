from tiktoken import Encoding

from api.domain.model import ModelTokenizer


class TiktokenModelTokenizer(ModelTokenizer):
    def __init__(self, model: Encoding):
        self.model = model

    def encode(self, text: str) -> int:
        return self.model.encode(text)
