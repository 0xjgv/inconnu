install:
	uv sync --group dev

activate:
	uv venv

install-pip:
	uv pip install pip --upgrade

model-de: install-pip
	uv run python -m spacy download de_core_news_sm

model-it: install-pip
	uv run python -m spacy download it_core_news_sm

model-es: install-pip
	uv run python -m spacy download es_core_news_sm

model-fr: install-pip
	uv run python -m spacy download fr_core_news_sm

install-corgea:
	uv pip install corgea-cli

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