env ?= .env

# help -----------------------------------------------------------------------------------------------------------------------------------------------
help:
	@python cli.py --make-help

# quickstart -----------------------------------------------------------------------------------------------------------------------------------------
quickstart:
	@python cli.py --quickstart --env-file $(env)

# create-user ----------------------------------------------------------------------------------------------------------------------------------------
create-user:
	@python scripts/create_first_user.py

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
	@python cli.py --test-integ && \
	set -a; . .github/.env.ci; set +a; \
	PYTHONPATH=. pytest api/tests/integ$(TEST_INTEG_SUFFIX) --config-file=pyproject.toml --cov=./api --cov-report=xml;

%:
	@:

.PHONY: help quickstart dev lint test-unit test-integ
