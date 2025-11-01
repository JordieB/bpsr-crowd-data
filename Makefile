ENV_FILE ?= .env
PORT ?= 8000

_define_env = \
	if [ -f $(ENV_FILE) ]; then \
		set -a; . $(ENV_FILE); set +a; \
	fi;

.PHONY: dev db-local smoke fly-deploy

db-local:
	@$(call _define_env)
	python -m app.cli apply

.dev-server:
	@$(call _define_env)
	uvicorn app.main:app --host 0.0.0.0 --port $(PORT)

dev: .dev-server

smoke:
	@$(call _define_env)
	python scripts/smoke.py

fly-deploy:
	fly deploy --remote-only
