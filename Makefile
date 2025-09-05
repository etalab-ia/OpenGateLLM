# Default variables
export CONFIG_FILE ?= ./config.yml

# Default options
service ?= both
env ?= .env
action ?= all
compose ?= compose.yml
execute ?= local

# help -----------------------------------------------------------------------------------------------------------------------------------------------
help:
	@echo "Usage: make COMMAND [OPTIONS]"
	@echo ""
	@echo "quickstart [env=.env] [compose=compose.yml]		Start services in docker environment"
	@echo ""
	@echo " env 						Optional, environment file to use. Default: .env"
	@echo " compose 					Optional, compose file to use. Default: compose.yml"
	@echo ""
	@echo "dev [service=api|playground|both] [env=.env] [compose=compose.yml]	Start services in local development mode"
	@echo ""
	@echo " service 					Optional, start specific service or both. Default: both"
	@echo " env 						Optional, environment file to use. Default: .env"
	@echo " compose 					Optional, compose file to use. Default: compose.yml"
	@echo ""
	@echo "create-user						    Create a first user"
	@echo "test									Run unit tests"
	@echo "lint									Run linter"
	@echo ""
	@echo "test-integ [action=up|run|all] [execute=local|docker]	Run integration tests"
	@echo ""
	@echo " action						Optional, 'up' to start services without running tests, 'run' to run tests without"
	@echo "							starting services, 'all' to start services and run tests. Default: all"
	@echo " execute						Optional, run integration tests in local or docker environment. Default: local"
	@echo ""

# utils ----------------------------------------------------------------------------------------------------------------------------------------------
.banner:
	@echo ""
	@echo " ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  █████╗ ████████╗███████╗██╗     ██╗     ███╗   ███╗"
	@echo "██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝██║     ██║     ████╗ ████║"
	@echo "██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ███╗███████║   ██║   █████╗  ██║     ██║     ██╔████╔██║"
	@echo "██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║   ██║██╔══██║   ██║   ██╔══╝  ██║     ██║     ██║╚██╔╝██║"
	@echo "╚██████╔╝██║     ███████╗██║ ╚████║╚██████╔╝██║  ██║   ██║   ███████╗███████╗███████╗██║ ╚═╝ ██║"
	@echo " ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝"
	@echo ""

.start-api:
	@bash -c 'set -a; . $(env); \
	GUNICORN_CMD_ARGS="--reload --log-level debug --access-logfile - --error-logfile -" \
	./scripts/startup_api.sh &' \
	&& sleep 2 \
	&& open http://localhost:8080/docs


.start-playground:
	@mkdir -p ~/.streamlit/
	@echo "[general]"  > ~/.streamlit/credentials.toml
	@echo "email = \"\""  >> ~/.streamlit/credentials.toml
	@bash -c 'set -a; . $(env); ./scripts/startup_ui.sh'

.pre-checks:
	@if [ ! -f $(env) ]; then \
		echo "⚠️ Environment file $(env) does not exist, creating it from $(env).example and using it"; \
		cp $(env).example $(env); \
		exit 1; \
	fi

	@bash -c 'set -a; . $(env); \
	if [ ! -f "$$CONFIG_FILE" ]; then \
		echo "⚠️ Configuration file $$CONFIG_FILE does not exist, creating it from config.example.yml and using it"; \
		cp config.example.yml "$$CONFIG_FILE"; \
	fi'

	@if [ ! -f $(compose) ]; then \
		echo "⚠️ Compose file $(compose) does not exist, creating it from compose.example.yml and using it"; \
		cp compose.example.yml $(compose); \
	fi

.docker-compose:
	@echo "🚀 Starting services with $(env) file and $(compose) file..."
	@if [ "$(services)" = "" ]; then \
		services=$$(docker compose --file $(compose) config --services 2>/dev/null); \
	fi;
	@docker compose --env-file $(env) --file $(compose) up $$services --detach --quiet-pull --wait
	@sleep 4
	for service in $$services; do \
		if ! $(MAKE) --silent .check-service-status service=$$service env=$(env) compose=$(compose); then \
			exit 1; \
		fi; \
	done
	@$(MAKE) .banner
	@printf "┌─────────────────────────────────────────────────────────────────────────────────────────┐\n"
	@printf "│                                   \033[1m🐳 Docker services\033[0m                                    │\n"
	@printf "├─────────────────────────────────────────────────────────────────────────────────────────┤\n"
	@printf "\n"
	@printf " %-30s		%s\n" "Compose file:" "$(compose)"
	@printf " %-30s		%s\n" "Environment file:" "$(env)"
	@printf " Services:\n"
	for service in $$services; do \
		port=$$(docker compose --file $(compose) config --format json 2>/dev/null | jq -r ".services.\"$$service\".ports[0].published"); \
		printf " %30s\t\t%s\n" "$$service:" "http://localhost:$$port"; \
	done
	@printf "\n"
	@printf "  \033[1m⏸️  To stop services, run:\033[0m\n"
	@printf "     \033[1m\033[32mdocker compose --file $(compose) --env-file $(env) down\033[0m\n"
	@printf "└─────────────────────────────────────────────────────────────────────────────────────────┘\n"
	@printf "\n"

.check-service-status:
	status=$$(docker compose -f $(compose) --env-file $(env) ps -a $(service) --format "table {{.State}}" 2>/dev/null | tail -n +2); \
	if [ "$$status" != "running" ]; then \
		echo "🐳 $(service) container is not running (status: $$status). Please check the logs of the container"; \
		false; \
	fi

# dev ------------------------------------------------------------------------------------------------------------------------------------------------
dev:
	@$(MAKE) .pre-checks
	@services=$$(docker compose --file $(compose) config --services 2>/dev/null | grep -v -E '^(api|playground)$$' | tr '\n' ' '); \
	if ! $(MAKE) --silent .docker-compose env=$(env) compose=$(compose) services="$$services"; then \
		exit 1; \
	fi

	@if [ "$(service)" = "api" ]; then \
		$(MAKE) .start-api; \
		wait; \
	elif [ "$(service)" = "playground" ]; then \
		$(MAKE) .start-playground; \
		wait; \
	elif [ "$(service)" = "both" ]; then \
		$(MAKE) .start-playground & \
		$(MAKE) .start-api & \
		wait; \
	else \
		echo "❌ Error: service must be 'api' or 'playground' or 'both'"; \
		exit 1; \
	fi

# quickstart -----------------------------------------------------------------------------------------------------------------------------------------
quickstart:
	@$(MAKE) .pre-checks
	@if ! $(MAKE) --silent .docker-compose env=$(env) compose=$(compose); then \
		exit 1; \
	fi

# test -----------------------------------------------------------------------------------------------------------------------------------------------
test:
	PYTHONPATH=. pytest api/tests/unit --config-file=pyproject.toml

# lint -----------------------------------------------------------------------------------------------------------------------------------------------
lint:
	pre-commit run --all-files

# create-user ----------------------------------------------------------------------------------------------------------------------------------------
create-user:
	docker compose exec -ti api python scripts/create_first_user.py --playground_postgres_host postgres

# test-integ -----------------------------------------------------------------------------------------------------------------------------------------
.test-integ-up:
	@if [ ! -f .github/.env.ci ]; then \
		echo "⚠️ Creating .github/.env.ci file from .github/.env.ci.example and using it"; \
		cp .github/.env.ci.example .github/.env.ci; \
	fi
	@bash -c ' \
		if [ -z "$$ALBERT_API_KEY" ] || [ -z "$$BRAVE_API_KEY" ]; then \
			set -a; [ -f .github/.env.ci ] && . .github/.env.ci; set +a; \
		fi; \
		if [ -z "$$ALBERT_API_KEY" ] || [ -z "$$BRAVE_API_KEY" ]; then \
			echo "❌ ALBERT_API_KEY and BRAVE_API_KEY must be set (exported in environment or in .github/.env.ci) to run the integration tests"; \
			exit 1; \
		fi'
	@bash -c 'set -a; . .github/.env.ci; \
	if [ "$(execute)" = "local" ]; then \
		if [ $$POSTGRES_HOST != "localhost" ]; then \
			echo "❌ POSTGRES_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_HOST != "localhost" ]; then \
			echo "❌ REDIS_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_HOST != "localhost" ]; then \
			echo "❌ ELASTICSEARCH_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_HOST != "localhost" ]; then \
			echo "❌ SECRETIVESHELL_HOST must be set to 'localhost' in order to run the integration tests local execute"; \
			exit 1; \
		fi; \
	else \
		if [ $$POSTGRES_HOST != "postgres" ]; then \
			echo "❌ POSTGRES_HOST must be set to 'postgres' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_HOST != "redis" ]; then \
			echo "❌ REDIS_HOST must be set to 'redis' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_HOST != "elasticsearch" ]; then \
			echo "❌ ELASTICSEARCH_HOST must be set to 'elasticsearch' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_HOST != "secretiveshell" ]; then \
			echo "❌ SECRETIVESHELL_HOST must be set to 'secretiveshell' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$POSTGRES_PORT != "5432" ]; then \
			echo "❌ POSTGRES_PORT must be set to '5432' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$REDIS_PORT != "6379" ]; then \
			echo "❌ REDIS_PORT must be set to '6379' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$ELASTICSEARCH_PORT != "9200" ]; then \
			echo "❌ ELASTICSEARCH_PORT must be set to '9200' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
		if [ $$SECRETIVESHELL_PORT != "8000" ]; then \
			echo "❌ SECRETIVESHELL_PORT must be set to '8000' in order to run the integration tests in docker execute"; \
			exit 1; \
		fi; \
	fi'
	@if [ "$(execute)" = "local" ]; then \
		services=$$(docker compose --file .github/compose.ci.yml config --services 2>/dev/null | grep -v -E "^(api|playground)$$" | tr "\n" " "); \
	fi; \
	if ! $(MAKE) --silent .docker-compose env=.github/.env.ci compose=.github/compose.ci.yml services="$$services"; then \
		exit 1; \
	fi

.test-integ-run:
	@if [ "$(execute)" = "local" ]; then \
		bash -c 'set -a; . .github/.env.ci; \
		CONFIG_FILE=api/tests/integ/config.test.yml PYTHONPATH=. pytest api/tests/integ --config-file=pyproject.toml'; \
	elif [ "$(execute)" = "docker" ]; then \
		docker compose --file .github/compose.ci.yml --env-file .github/.env.ci run -T --user $$(id -u):$$(id -g) -v $$(pwd)/api:/api api pytest api/tests --cov=./api --cov-report=xml; \
	fi

test-integ:
	@if [ "$(execute)" != "local" ] && [ "$(execute)" != "docker" ]; then \
		echo "❌ Error: execute must be 'local' or 'docker'"; \
		echo "Usage: make test-integ [action=up|run|all] [execute=local|docker]"; \
		echo "Use 'make help' for more information."; \
		exit 1; \
	fi

	@if [ "$(action)" = "up" ] || [ "$(action)" = "all" ]; then \
		if ! $(MAKE) --silent .test-integ-up execute=$(execute); then \
			exit 1; \
		fi; \
		echo "✅ Environment setup completed: run tests with 'make test-integ action=run execute=$(execute)'"; \
	fi
	@if [ "$(action)" = "run" ] || [ "$(action)" = "all" ]; then \
		if ! $(MAKE) --silent .test-integ-run execute=$(execute); then \
			exit 1; \
		fi; \
		echo "✅ Integration tests completed."; \
	fi

.PHONY: help test test-integ lint setup quickstart dev
