from api.infrastructure.fastapi.schemas.models import ModelResponse, ModelsResponse
from api.infrastructure.http.model._modelhttpclient import ModelHttpClient, ModelHttpClientEndpoints
from api.schemas.core.models import RequestContent


class VllmModelHttpClient(ModelHttpClient):
    ENDPOINT_TABLE = ModelHttpClientEndpoints(rerank="/v2/rerank")

    # response formatting
    @staticmethod
    def format_response_to_models_response(request_content: RequestContent, response_data: dict) -> ModelsResponse:
        data = [
            ModelResponse(
                id=model.get("id"),
                created=model.get("created"),
                owned_by=model.get("owned_by"),
                max_context_length=model.get("max_model_len"),
            )
            for model in response_data.get("data", [])
        ]
        return ModelsResponse(data=data)
