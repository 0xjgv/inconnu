.PHONY: install activate model-en model-de model-it model-es model-fr update-deps fix format lint clean test install-models

install: # Install dependencies (includes dev group)
	uv sync --group dev

activate: # Activate virtual environment
	uv venv

model-en: # Download English model
	uv run inconnu-download en

model-de: # Download German model
	uv run inconnu-download de

model-it: # Download Italian model
	uv run inconnu-download it

model-es: # Download Spanish model
	uv run inconnu-download es

model-fr: # Download French model
	uv run inconnu-download fr

update-deps: # Update dependencies
	uv update

fix: # Fix code style issues
	uv run ruff check --fix .

format: # Format code
	uv run ruff format .

lint: # Lint code
	uv run ruff check .

clean: fix format lint # Clean up cache and build artifacts
	rm -fr .pytest_cache */__pycache__ */*/__pycache__
	uv run ruff clean

install-models: model-en model-de model-it # Install models required for testing

test: install-models # Run tests
	uv run pytest -vv