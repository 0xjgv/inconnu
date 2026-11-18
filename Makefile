.PHONY: help install test lint format eval eval-baseline eval-scorer

help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install the package with the dev and eval groups
	uv sync --group dev --group eval

test: ## Run the tests
	uv run pytest -rf

lint: ## Check style
	uv run ruff check .
	uv run ruff format --check .

format: ## Fix style
	uv run ruff check --fix .
	uv run ruff format .

eval: ## Generate eval data, score every detector, print the table, write evals/results/
	uv run --group eval python evals/generate.py
	uv run --group eval python evals/run.py

eval-baseline: ## eval, plus inconnu 0.1.1 and spaCy en_core_web_sm predictions from their own venv
	uv run --group eval python evals/generate.py
	test -x evals/.baseline-venv/bin/python || (uv venv evals/.baseline-venv --python 3.12 && \
		uv pip install --python evals/.baseline-venv/bin/python inconnu==0.1.1 pip && \
		evals/.baseline-venv/bin/inconnu-download en)
	evals/.baseline-venv/bin/python evals/baseline.py dev test
	uv run --group eval python evals/run.py

eval-scorer: ## Live scorer check on the dev band (needs provider keys; at most 120 calls)
	cd evals && uv run --group eval python scorer_eval.py --max-calls 120
