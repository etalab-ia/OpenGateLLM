import textwrap

from api.schemas.core.configuration import Configuration


def write_tmp_config(path: str, content: str):
    with open(path, "w") as f:
        f.write(textwrap.dedent(content))


def test_missing_proconnect_is_none(tmp_path):
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
        url: postgresql+asyncpg://postgres@localhost:5432/postgres
      redis: {}
    """
    write_tmp_config(cfg, content)

    c = Configuration(config_file=str(cfg))
    # When the key is absent, proconnect should remain None
    assert c.dependencies.proconnect is None


def test_present_but_empty_proconnect_default(tmp_path):
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
        url: postgresql+asyncpg://postgres@localhost:5432/postgres
      proconnect: {}
      redis: {}
    """
    write_tmp_config(cfg, content)

    c = Configuration(config_file=str(cfg))
    assert c.dependencies.proconnect is not None
