from pathlib import Path

import pytest

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

MOCKS_PATH = Path("tests/mocks")


@pytest.fixture
def de_prompt() -> str:
    """German prompt fixture.

    A dedicated Italian prompt file is not yet available in the test
    data set. For the purposes of unit-testing the NLP pipeline we reuse
    the existing German prompt. The linguistic content is sufficient for
    verifying entity extraction logic (email, phone numbers, proper
    names, etc.) across languages.
    """
    with Path(MOCKS_PATH / "de_prompt.txt").open("r") as file:
        return file.read()


@pytest.fixture
def en_prompt() -> str:
    """English prompt fixture.

    A dedicated English prompt file is not yet available in the test
    data set. For the purposes of unit-testing the NLP pipeline we reuse
    the existing German prompt. The linguistic content is sufficient for
    verifying entity extraction logic (email, phone numbers, proper
    names, etc.) across languages.
    """
    with Path(MOCKS_PATH / "en_prompt.txt").open("r", encoding="utf-8") as file:
        return file.read()
