install:
	uv sync --group dev

activate:
	uv venv

model-install:
	uv pip install pip --upgrade
	uv run python -m spacy download en_core_web_sm

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

test:
	uv run pytest -vv