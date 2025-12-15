.PHONY: help
help: # Show this help message
	@echo "Available targets:"
	@grep -E '^[a-zA-Z_-]+:.*?# .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?# "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

.DEFAULT_GOAL := help

.PHONY: install
install: # Install dependencies (includes dev group)
	uv sync --group dev

.PHONY: venv
venv: # Create virtual environment
	uv venv

.PHONY: model-en
model-en: # Download English model
	uv run inconnu-download en

.PHONY: model-de
model-de: # Download German model
	uv run inconnu-download de

.PHONY: model-it
model-it: # Download Italian model
	uv run inconnu-download it

.PHONY: model-es
model-es: # Download Spanish model
	uv run inconnu-download es

.PHONY: model-fr
model-fr: # Download French model
	uv run inconnu-download fr

.PHONY: update-deps
update-deps: # Update dependencies
	uv update

.PHONY: fix
fix: # Fix code style issues
	uv run ruff check --fix .

.PHONY: format
format: # Format code
	uv run ruff format .

.PHONY: lint
lint: # Lint code
	uv run ruff check .

.PHONY: clean
clean: fix format lint # Clean up cache and build artifacts
	rm -fr .pytest_cache */__pycache__ */*/__pycache__
	uv run ruff clean

.PHONY: install-models
install-models: model-en model-de model-it # Install models required for testing

.PHONY: test
test: install-models # Run tests
	uv run pytest -vv