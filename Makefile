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
	@PYTHONPATH=. pytest -s api/tests/unit --config-file=pyproject.toml --cov=api --cov-report=html --cov-report=term-missing --cov-branch

# test-integ -----------------------------------------------------------------------------------------------------------------------------------------
test-integ:
	@python cli.py --test-integ
	@bash -c 'set -a; . .github/.env.ci; PYTHONPATH=. pytest api/tests/integ --config-file=pyproject.toml --cov=./api --cov-report=xml'

.PHONY: help test-unit test-integ lint quickstart dev
