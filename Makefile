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

semgrep: 
	@semgrep semgrep ci --config auto --verbose
	
.PHONY: help quickstart dev lint test-unit create-api-key semgrep
