ENV_FILE ?= .env
PORT ?= 8000

.PHONY: dev db-local smoke fly-deploy

db-local:
	python -m bpsr_crowd_data.cli_db apply

.dev-server:
	uvicorn bpsr_crowd_data.main:app --host 0.0.0.0 --port $(PORT)

dev: .dev-server

smoke:
	python scripts/smoke.py

fly-deploy:
	fly deploy --remote-only
