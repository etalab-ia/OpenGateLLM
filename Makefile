env ?= .env

help:
	@python cli.py --make-help

quickstart:
	@python cli.py --quickstart --env-file $(env)

create-api-key:
	@python scripts/create_api_key.py

dev:
	@python cli.py --dev --env-file $(env)

lint:
	@pre-commit run --all-files

test-unit:
	@PYTHONPATH=. pytest -s api/tests/unit --config-file=pyproject.toml --cov=./api --cov-report=html --cov-report=term-missing --cov-branch --cov-report=xml

TEST_INTEG_ARG := $(word 2,$(MAKECMDGOALS))
TEST_INTEG_SUFFIX := $(if $(TEST_INTEG_ARG),/$(TEST_INTEG_ARG),)

test-integ:
	@if [ -z "$${ALBERT_API_KEY}" ]; then \
		echo "ALBERT_API_KEY is not set. Export it first, see .github/.env.ci.example"; \
		exit 1; \
	fi; \
	export CONFIG_FILE=./api/tests/integ/config.test.yml; \
	docker compose --file compose.example.yml up --detach --quiet-pull --wait postgres redis; \
	PYTHONPATH=. pytest api/tests/integ$(TEST_INTEG_SUFFIX) --config-file=pyproject.toml --cov=./api --cov-report=xml;

semgrep: 
	@semgrep semgrep ci --config auto --verbose

FGA_DIR := api/infrastructure/openfga

fga-test:
	@fga model test --tests api/tests/store.fga.yaml

# model.json is what the API pushes at startup; model.fga is the reviewed source.
# Regenerate after every change to model.fga, and commit both.
fga-model:
	@fga model validate --file $(FGA_DIR)/model.fga
	@fga model transform --file $(FGA_DIR)/model.fga | python -m json.tool --indent 2 > $(FGA_DIR)/model.json
	@echo "$(FGA_DIR)/model.json regenerated"

.PHONY: help quickstart dev lint test-unit test-integ create-api-key semgrep fga-test fga-model
