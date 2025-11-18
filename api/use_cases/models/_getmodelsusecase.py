class GetModelsUseCase:
    def __init__(self, model_repository):
        self.model_repository = model_repository

    def execute(self):
        return self.model_repository.get_all_models()