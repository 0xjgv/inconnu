install:
	uv sync --group dev

activate:
	uv venv

model-en:
	uv run inconnu-download en

model-de:
	uv run inconnu-download de

model-it:
	uv run inconnu-download it

model-es:
	uv run inconnu-download es

model-fr:
	uv run inconnu-download fr

update-deps:
	uv update

fix:
	uv run ruff check --fix .

format:
	uv run ruff format .

lint:
	uv run ruff check .

clean: fix format lint
	rm -fr .pytest_cache */__pycache__ */*/__pycache__
	uv run ruff clean

install-models: model-en model-de model-it # Models required for testing

test: install-models
	uv run pytest -vv