import textwrap
from app.schemas.core.configuration import Configuration


def write_tmp_config(path: str, content: str):
    with open(path, "w") as f:
        f.write(textwrap.dedent(content))


def test_missing_proconnect_creates_default(tmp_path):
    cfg = tmp_path / "config_no_proconnect.yml"
    content = """
    models:
      - name: dummy-embed
        type: text-embeddings-inference
        model_name: embed-test
        providers:
          - type: albert
            model_name: embed-test

    dependencies:
      postgres:
        url: postgresql+asyncpg://postgres@localhost:5432/api
      redis: {}
    """
    write_tmp_config(cfg, content)

    c = Configuration(config_file=str(cfg))
    # When the key is absent, proconnect should remain None (no default factory)
    assert c.dependencies.proconnect is None


def test_present_but_empty_proconnect_is_normalized(tmp_path):
    cfg = tmp_path / "config_null_proconnect.yml"
    content = """
    models:
      - name: dummy-embed
        type: text-embeddings-inference
        model_name: embed-test
        providers:
          - type: albert
            model_name: embed-test

    dependencies:
      postgres:
        url: postgresql+asyncpg://postgres@localhost:5432/api
      proconnect:
      redis: {}
    """
    write_tmp_config(cfg, content)

    c = Configuration(config_file=str(cfg))
    assert c.dependencies.proconnect is not None


def test_present_but_empty_qdrant_is_normalized(tmp_path):
    cfg = tmp_path / "config_null_qdrant.yml"
    content = """
    models:
      - name: dummy-embed
        type: text-embeddings-inference
        model_name: embed-test
        providers:
          - type: albert
            model_name: embed-test

    dependencies:
      postgres:
        url: postgresql+asyncpg://postgres@localhost:5432/api
      qdrant:
      redis: {}

    settings:
      vector_store_model: dummy-embed
    """
    write_tmp_config(cfg, content)

    c = Configuration(config_file=str(cfg))
    # qdrant is Optional[QdrantDependency], normalized should create an object (not None)
    assert hasattr(c.dependencies, "qdrant")
    assert c.dependencies.qdrant.model == "embeddings-small"
    assert c.dependencies.qdrant.args == {"url": "http://qdrant", "api_key": "changeme", "prefer_grpc": False, "timeout": 10}
