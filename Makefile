BUMP ?= patch

.PHONY: help install install-cli test lint format package release eval eval-baseline eval-scorer

help: ## Show targets
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "  %-14s %s\n", $$1, $$2}'

install: ## Install the package with the dev and eval groups
	uv sync --group dev --group eval

install-cli: package ## Build this checkout and install it as the global inconnu command
	INCONNU_LOCAL_BUILD=1 INCONNU_DOWNLOAD_BASE="$(CURDIR)/dist-release" sh install.sh

package: ## Build the release assets in dist-release/
	sh scripts/package-release.sh

release: ## Tag the next version on main and push it (BUMP=patch|minor|major); CI publishes the release
	BUMP=$(BUMP) sh scripts/release.sh

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
	evals/.baseline-venv/bin/python -c "import inconnu, spacy; assert inconnu.__version__ == '0.1.1'; spacy.load('en_core_web_sm')" 2>/dev/null || \
		(rm -rf evals/.baseline-venv && uv venv evals/.baseline-venv --python 3.12 && \
		uv pip install --python evals/.baseline-venv/bin/python inconnu==0.1.1 pip && \
		evals/.baseline-venv/bin/inconnu-download en)
	evals/.baseline-venv/bin/python evals/baseline.py dev test
	uv run --group eval python evals/run.py

eval-scorer: ## Live scorer check on the dev band (needs provider keys; at most 120 calls)
	uv run --group eval python evals/generate.py
	cd evals && uv run --group eval python scorer_eval.py --max-calls 120
