import json

import pytest

from api.utils.configuration import configuration
from api.utils.variables import ENDPOINT__MODELS, ENDPOINT__MODELS_ALIAS, ENDPOINT__ROUTERS

CONFIG_EXPECTED = [
    {
        "type": "image-text-to-text",
        "aliases": ["mistralai/Mistral-Small-3.1-24B-Instruct-2503"],
        "owned_by": "test",
        "routing_strategy": "shuffle",
        "providers": [{"type": "albert", "model_name": "albert-large"}],
        "name": "albert-large",
    },
    {
        "type": "text-generation",
        "aliases": ["meta-llama/Llama-3.1-8B-Instruct"],
        "owned_by": "OpenGateLLM",
        "routing_strategy": "round_robin",
        "providers": [
            {"type": "albert", "model_name": "albert-small"},
            {"type": "albert", "model_name": "albert-small"},
        ],
        "name": "albert-small",
    },
    {
        "type": "text-embeddings-inference",
        "aliases": ["BAAI/bge-m3"],
        "owned_by": "OpenGateLLM",
        "routing_strategy": "shuffle",
        "providers": [{"type": "albert", "model_name": "embeddings-small"}],
        "name": "embeddings-small",
    },
    {
        "type": "automatic-speech-recognition",
        "aliases": ["openai/whisper-large-v3"],
        "owned_by": "OpenGateLLM",
        "routing_strategy": "shuffle",
        "providers": [{"type": "albert", "model_name": "audio-large"}],
        "name": "audio-large",
    },
    {
        "type": "text-classification",
        "aliases": ["BAAI/bge-reranker-v2-m3"],
        "owned_by": "OpenGateLLM",
        "routing_strategy": "shuffle",
        "providers": [{"type": "albert", "model_name": "rerank-small"}],
        "name": "rerank-small",
    },
]


@pytest.mark.usefixtures("client")
class TestModelProvision:
    def test_get_routers(self, client):
        response = client.get_master(url=f"v1{ENDPOINT__ROUTERS}")
        assert response.status_code == 200
        data = response.json()

        routers = data.get("routers", [])
        assert len(routers) == len(CONFIG_EXPECTED)

        for idx, expected in enumerate(CONFIG_EXPECTED):
            router = routers[idx]

            # check top-level fields
            assert router["type"] == expected["type"]
            assert router["aliases"] == expected["aliases"]
            assert router["owned_by"] == expected["owned_by"]
            assert router["routing_strategy"] == expected["routing_strategy"]
            assert router["name"] == expected["name"]

            # check providers
            providers = router["providers"]
            assert len(providers) == len(expected["providers"])
            for p, exp_p in zip(providers, expected["providers"]):
                assert p["type"] == exp_p["type"]
                assert p["model_name"] == exp_p["model_name"]

    def test_add_model(self, client):
        payload = {
            "router_name": "cs-chat",
            "model": {
                "type": "vllm",
                "url": "https://dispatcher-preprod.kubic.aristote.centralesupelec.fr",
                "key": configuration.dependencies.centralesupelec.token,
                "timeout": 10,
                "model_name": "casperhansen/llama-3.3-70b-instruct-awq",
                "model_cost_prompt_tokens": 0.1,
                "model_cost_completion_tokens": 0.1,
                "model_carbon_footprint_zone": "WOR",
                "model_carbon_footprint_total_params": 8,
                "model_carbon_footprint_active_params": 8,
            },
            "model_type": "text-generation",
            "aliases": ["cs-router-alias-1", "cs-router-alias-2"],
            "routing_strategy": "round_robin",
            "owner": "centralesupelec",
            "additional_field": {
                "description": "This is a test model entry",
                "version": "1.0.0",
            },
        }
        response = client.post_master(url=f"v1{ENDPOINT__MODELS}", json=payload)
        assert response.status_code == 201

        response = client.get_master(url=f"v1{ENDPOINT__ROUTERS}")
        assert response.status_code == 200
        data = response.json()

        routers = data.get("routers", [])
        assert len(routers) == len(CONFIG_EXPECTED) + 1

    def test_add_alias(self, client):
        payload = {"router_name": "cs-chat", "aliases": ["test-alias"]}
        response = client.post_master(url=f"v1{ENDPOINT__MODELS_ALIAS}", json=payload)
        assert response.status_code == 201

        response = client.get_master(url=f"v1{ENDPOINT__ROUTERS}")
        assert response.status_code == 200
        data = response.json()

        routers = data.get("routers", [])
        assert len(routers[-1]["aliases"]) == 3
        assert routers[-1]["aliases"][-1] == "test-alias"

    def test_delete_alias(self, client):
        payload = {"router_name": "cs-chat", "aliases": ["test-alias"]}
        response = client.request(
            "DELETE", f"v1{ENDPOINT__MODELS_ALIAS}", content=json.dumps(payload), headers={**client.headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 204

        response = client.get_master(url=f"v1{ENDPOINT__ROUTERS}")
        assert response.status_code == 200
        data = response.json()

        routers = data.get("routers", [])
        assert len(routers[-1]["aliases"]) == 2

    def test_delete_model(self, client):
        payload = {
            "router_name": "cs-chat",
            "url": "https://dispatcher-preprod.kubic.aristote.centralesupelec.fr",
            "model_name": "casperhansen/llama-3.3-70b-instruct-awq",
        }
        response = client.request(
            "DELETE", f"v1{ENDPOINT__MODELS}", content=json.dumps(payload), headers={**client.headers, "Content-Type": "application/json"}
        )
        assert response.status_code == 204

        response = client.get_master(url=f"v1{ENDPOINT__ROUTERS}")
        assert response.status_code == 200
        data = response.json()

        routers = data.get("routers", [])
        assert len(routers) == len(CONFIG_EXPECTED)
