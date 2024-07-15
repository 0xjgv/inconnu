deps-install:
	hash poetry 2>/dev/null || pip install poetry;
	poetry config virtualenvs.in-project true
	poetry env use python3.11
	poetry install -vv

model-install:
	# poetry run python -m spacy download en_core_web_trf
	poetry run python -m spacy download en_core_web_sm
	poetry run pip install --upgrade pip

install: deps-install

update-deps:
	poetry config virtualenvs.in-project true
	poetry update

fix:
	poetry run ruff check --fix .

format:
	poetry run ruff format .

lint:
	poetry run ruff check .

clean: fix format lint
	rm -fr **/__pycache__ .pytest_cache
	poetry run ruff clean

test:
	poetry run pytest -vv