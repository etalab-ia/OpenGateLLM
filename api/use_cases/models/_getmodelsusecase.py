from api.domain.model import ModelRepository


class GetModelsUseCase:
    def __init__(self, model_repository: ModelRepository):
        self.model_repository = model_repository

    def execute(self):
        return self.model_repository.get_all_models()
