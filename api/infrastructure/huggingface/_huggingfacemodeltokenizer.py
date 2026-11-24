from tokenizers import Tokenizer

from api.domain.model import ModelTokenizer


class HuggingFaceModelTokenizer(ModelTokenizer):
    def __init__(self, model: Tokenizer):
        self.model = model

    def compute_tokens(self, texts: list[str]) -> int:
        if texts:
            return len(self.model.encode(" ".join(texts).strip(), add_special_tokens=False).ids)
        return 0
