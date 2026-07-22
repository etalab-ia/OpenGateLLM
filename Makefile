env ?= .env

# help -----------------------------------------------------------------------------------------------------------------------------------------------
help:
	@python cli.py --make-help

# quickstart -----------------------------------------------------------------------------------------------------------------------------------------
quickstart:
	@python cli.py --quickstart --env-file $(env)

# create-admon ----------------------------------------------------------------------------------------------------------------------------------------
create-api-key:
	@python scripts/create_api_key.py

# dev ------------------------------------------------------------------------------------------------------------------------------------------------
dev:
	@python cli.py --dev --env-file $(env)

# lint -----------------------------------------------------------------------------------------------------------------------------------------------
lint:
	@pre-commit run --all-files

# test -----------------------------------------------------------------------------------------------------------------------------------------------
test-unit:
	@PYTHONPATH=. pytest -s api/tests/unit --config-file=pyproject.toml --cov=./api --cov-report=html --cov-report=term-missing --cov-branch --cov-report=xml

TEST_INTEG_ARG := $(word 2,$(MAKECMDGOALS))
TEST_INTEG_SUFFIX := $(if $(TEST_INTEG_ARG),/$(TEST_INTEG_ARG),)

# test-integ -----------------------------------------------------------------------------------------------------------------------------------------
test-integ:
	@if [ -z "$${ALBERT_API_KEY}" ]; then \
		echo "ALBERT_API_KEY is not set. Export it first, see .github/.env.ci.example"; \
		exit 1; \
	fi; \
	export CONFIG_FILE=./api/tests/integ/config.test.yml; \
	docker compose --file compose.example.yml up --detach --quiet-pull --wait postgres redis; \
	PYTHONPATH=. pytest api/tests/integ$(TEST_INTEG_SUFFIX) --config-file=pyproject.toml --cov=./api --cov-report=xml;

.PHONY: help quickstart dev lint test-unit test-integ create-api-key
