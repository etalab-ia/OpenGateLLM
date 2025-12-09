# Default variables
export CONFIG_FILE ?= ./config.yml

# Default options
service ?= both
env ?= .env
action ?= all
compose ?= compose.yml

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
	@echo "test-unit								Run unit tests"
	@echo "lint									Run linter"
	@echo ""
	@echo "test-integ [action=up|run|all]	Run integration tests"
	@echo ""
	@echo " action						Optional, 'up' to start services without running tests, 'run' to run tests without"
	@echo "							starting services, 'all' to start services and run tests. Default: all"
	@echo ""

# utils ----------------------------------------------------------------------------------------------------------------------------------------------
.banner:
	@printf "\n"
	@printf "\e[0;95m ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  █████╗ ████████╗███████╗██╗     ██╗     ███╗   ███╗\e[0m\n"
	@printf "\e[0;95m██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔══██╗╚══██╔══╝██╔════╝██║     ██║     ████╗ ████║\e[0m\n"
	@printf "\e[0;95m██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ███╗███████║   ██║   █████╗  ██║     ██║     ██╔████╔██║\e[0m\n"
	@printf "\e[0;95m██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║   ██║██╔══██║   ██║   ██╔══╝  ██║     ██║     ██║╚██╔╝██║\e[0m\n"
	@printf "\e[0;95m╚██████╔╝██║     ███████╗██║ ╚████║╚██████╔╝██║  ██║   ██║   ███████╗███████╗███████╗██║ ╚═╝ ██║\e[0m\n"
	@printf "\e[0;95m ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝     ╚═╝\e[0m\n"
	@printf "\n"

.start-api:
	@bash -c 'set -a; . $(env); \
	trap "trap - SIGTERM && kill -- -$$$$" SIGINT SIGTERM EXIT; \
	python -m alembic -c api/alembic.ini upgrade head \
	&& uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload --log-level debug & \
	sleep 10; \
	open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null || true; \
	wait'


.start-playground:
	@bash -c 'set -a; . $(env); \
	trap "trap - SIGTERM && kill -- -$$$$" SIGINT SIGTERM EXIT; \
	cd ./playground \
	&& CONFIG_FILE=../$${CONFIG_FILE} API_URL="http://localhost:8500" reflex run --env dev --loglevel debug & \
	sleep 10; \
	open http://localhost:8501 2>/dev/null || xdg-open http://localhost:8501 2>/dev/null || true; \
	wait'

.pre-checks:
	@if [ ! -f $(env) ]; then \
		echo "⚠️ Environment file $(env) does not exist, creating it from $(env).example and using it"; \
		cp $(env).example $(env); \
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
	@sleep 2
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
		SERVER=uvicorn $(MAKE) .start-api; \
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
	@sleep 4;
	@open http://localhost:8000/docs 2>/dev/null || xdg-open http://localhost:8000/docs 2>/dev/null || true;
	@open http://localhost:8501 2>/dev/null || xdg-open http://localhost:8501 2>/dev/null || true;

# test -----------------------------------------------------------------------------------------------------------------------------------------------
test-unit:
	PYTHONPATH=. pytest api/tests/unit --config-file=pyproject.toml --cov=./api --cov-report=term-missing --cov-report=xml --cov-report=html

# lint -----------------------------------------------------------------------------------------------------------------------------------------------
lint:
	pre-commit run --all-files

# create-user ----------------------------------------------------------------------------------------------------------------------------------------
create-user:
	python scripts/create_first_user.py

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
	if ! $(MAKE) --silent .docker-compose env=.github/.env.ci compose=.github/compose.ci.yml; then \
		exit 1; \
	fi

.test-integ-run:
	bash -c 'set -a; . .github/.env.ci; \
	PYTHONPATH=. pytest api/tests/integ --config-file=pyproject.toml --cov=./api --cov-report=xml'; \

test-integ:
	@if [ "$(action)" = "up" ] || [ "$(action)" = "all" ]; then \
		if ! $(MAKE) --silent .test-integ-up; then \
			exit 1; \
		fi; \
		echo "✅ Environment setup completed: run tests with 'make test-integ action=run'"; \
	fi
	@if [ "$(action)" = "run" ] || [ "$(action)" = "all" ]; then \
		if ! $(MAKE) --silent .test-integ-run; then \
			exit 1; \
		fi; \
		echo "✅ Integration tests completed."; \
	fi
	@if [ "$(action)" = "down" ]; then \
		docker compose --file .github/compose.ci.yml --env-file .github/.env.ci down; \
		echo "✅ Docker Compose services stopped."; \
	fi

.PHONY: help test-unit test-integ lint setup quickstart dev
