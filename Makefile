.PHONY: help setup setup-llm models references generate reruns ci-rerun import-ci score experiments e1 e2 e3 e4 e5 results smoke test test-docker test-ui lint format web serve screenshots clean

help: ## List targets
	@grep -E '^[a-z0-9-]+:.*##' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

setup: ## Install Python (uv) and console (npm) dependencies
	uv sync --locked
	npm --prefix web ci

setup-llm: ## Also install llama-cpp-python, needed only to generate agent artifacts
	uv sync --locked --extra llm

models: ## Download the two local language models (about 4.8 GB, models/) and verify their SHA-256
	uv run reprobench models

references: ## Freeze the six hand-written control artifacts (skips frozen ones)
	OMP_NUM_THREADS=1 uv run reprobench references

generate: models ## Run both agents on the four problems and freeze their artifacts (hours on CPU; skips frozen ones)
	OMP_NUM_THREADS=1 uv run reprobench generate

reruns: ## Rerun every frozen artifact twice in a fresh python:3.12-slim container (needs Docker; skips done reruns)
	uv run reprobench rerun

ci-rerun: ## Trigger the third rerun on a GitHub Actions runner (needs gh and a pushed repository)
	gh workflow run reproduce.yml

import-ci: ## Import the CI rerun: make import-ci RUN=<run id>
	rm -rf reruns/scratch/ci && gh run download $(RUN) -n ci-reruns -D reruns/scratch/ci
	uv run reprobench import-ci reruns/scratch/ci

score: ## Print the RRS and its components for every artifact
	uv run reprobench score

experiments: ## THE one command: E1-E5 on the committed artifacts and reruns, then docs/generated/results.md
	uv run reprobench experiment all
	uv run reprobench results

e1: ## E1 RRS per artifact and agent
	uv run reprobench experiment e1
e2: ## E2 controls: does the score catch known defects?
	uv run reprobench experiment e2
e3: ## E3 failure taxonomy from the rerun logs
	uv run reprobench experiment e3
e4: ## E4 container vs CI runner, value by value
	uv run reprobench experiment e4
e5: ## E5 weight sensitivity
	uv run reprobench experiment e5

results: ## Render docs/generated/results.md from results/*/LATEST
	uv run reprobench results

smoke: ## E1-E5 into results/scratch (checks the pipeline on the committed reruns; not a result)
	uv run reprobench experiment all --results results/scratch

test: ## Unit, agent, rerun (venv) and API tests (offline; scripted model)
	uv run pytest

test-docker: ## The container rerun test (needs a running Docker daemon and network)
	uv run pytest -m docker

test-ui: web ## Browser, keyboard and axe accessibility tests (needs Chromium)
	uv run pytest -m ui

lint: ## Ruff, mypy, ESLint and TypeScript checks
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy src tests scripts
	npm --prefix web run lint
	npm --prefix web run typecheck

format: ## Auto-format Python
	uv run ruff format .
	uv run ruff check --fix .

web: ## Build the console into web/dist
	npm --prefix web run build

serve: web ## Serve the console and API on http://127.0.0.1:8000 (reads .env if present)
	set -a; [ -f .env ] && . ./.env; set +a; uv run reprobench serve

screenshots: web ## Capture docs/screenshots from the committed artifacts and results
	uv run python scripts/screenshots.py

clean: ## Remove build output, caches and smoke results (keeps artifacts/, reruns/ and results/)
	rm -rf web/dist results/scratch reruns/scratch .pytest_cache .mypy_cache .ruff_cache
