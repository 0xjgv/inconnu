from pathlib import Path

import pytest

from inconnu import InconnuAnonymizer
from inconnu.config import Config, Language

MOCKS_PATH = Path("tests/mocks")


@pytest.fixture
def inconnu_anonymizer_en() -> InconnuAnonymizer:
    return InconnuAnonymizer(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
            language=Language.EN,
        ),
    )


@pytest.fixture
def inconnu_anonymizer_de() -> InconnuAnonymizer:
    return InconnuAnonymizer(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
            language=Language.DE,
        ),
    )


@pytest.fixture
def multiple_entities_text() -> str:
    return "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March. Dr. Alice Johnson from Texas gave a lecture in London last week."


@pytest.fixture
def structured_output() -> list[dict[str, str]]:
    # Given the anonymized text from `multiple_entities_text`, the following is the expected output
    # OpenAI (GPT-4o) generated output
    return [
        {
            "Person": "[PERSON_2]",
            "Origin": "[GPE_5]",
            "Event": "Visit",
            "Location": "[GPE_4]",
            "Date": "[DATE_2]",
        },
        {
            "Person": "[PERSON_1]",
            "Origin": "[GPE_3]",
            "Event": "Conference Attendance",
            "Location": "[GPE_2]",
            "Date": "[DATE_1]",
        },
        {
            "Person": "[PERSON_0]",
            "Origin": "[GPE_1]",
            "Event": "Lecture",
            "Location": "[GPE_0]",
            "Date": "[DATE_0]",
        },
    ]


@pytest.fixture
def en_prompt() -> str:
    with Path(MOCKS_PATH / "en_prompt.txt").open("r") as file:
        return file.read()


@pytest.fixture
def de_prompt() -> str:
    with Path(MOCKS_PATH / "de_prompt.txt").open("r") as file:
        return file.read()


@pytest.mark.parametrize(
    "text, expected_anonymized_text",
    [
        ("John Doe visited New York last summer.", "[PERSON] visited [GPE] [DATE]."),
        ("John Doe visited New York.", "[PERSON] visited [GPE]."),
        (
            "Michael Brown and Lisa White saw a movie in San Francisco yesterday.",
            "[PERSON] and [PERSON] saw a movie in [GPE] [DATE].",
        ),
        (
            "Dr. Alice Johnson gave a lecture in London last week.",
            "[PERSON] gave a lecture in [GPE] [DATE].",
        ),
        (
            "Jane Smith attended a conference in Tokyo in March.",
            "[PERSON] attended a conference in [GPE] in [DATE].",
        ),
    ],
)
def test_basic_anonymization(inconnu_anonymizer_en, text, expected_anonymized_text):
    result = inconnu_anonymizer_en(text=text)

    assert result.anonymized_text == expected_anonymized_text
    assert result.text_length == len(text)


def test_process_data_no_entities(inconnu_anonymizer_en):
    text = "The quick brown fox jumps over the lazy dog."

    result = inconnu_anonymizer_en(text=text)

    assert result.anonymized_text == text


@pytest.mark.skip(reason="Not implemented yet")
def test_process_data_max_length(inconnu_anonymizer_en):
    text = "a" * 501  # Exceeds max_text_length of 500

    with pytest.raises(ValueError, match="Text exceeds maximum length of 500"):
        inconnu_anonymizer_en(text=text)


def test_process_data_multiple_entities(inconnu_anonymizer_en):
    text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March."

    result = inconnu_anonymizer_en(text=text)

    # Date
    assert "last summer" not in result.anonymized_text
    assert "March" not in result.anonymized_text

    # Person
    assert "Jane Smith" not in result.anonymized_text
    assert "John Doe" not in result.anonymized_text

    # GPE (Location)
    assert "California" not in result.anonymized_text
    assert "New York" not in result.anonymized_text
    assert "Paris" not in result.anonymized_text
    assert "Tokyo" not in result.anonymized_text


def test_process_data_hashing(inconnu_anonymizer_en):
    text = "John Doe visited New York."

    result = inconnu_anonymizer_en(text=text)

    assert result.hashed_id.isalnum()  # Should be alphanumeric
    assert len(result.hashed_id) == 64  # SHA-256 hash length


def test_process_data_timestamp(inconnu_anonymizer_en):
    text = "John Doe visited New York."

    result = inconnu_anonymizer_en(text=text)

    assert result.timestamp is not None
    assert len(result.timestamp) > 0


def test_prompt_processing_time(inconnu_anonymizer_en, en_prompt):
    result = inconnu_anonymizer_en(text=en_prompt)

    # Processing time should be less than 200ms
    assert 0 < result.processing_time_ms < 200


def test_de_prompt(inconnu_anonymizer_de, de_prompt):
    result = inconnu_anonymizer_de(text=de_prompt)

    # Custom NER components
    assert "emma.schmidt@solartech.de" not in result.anonymized_text
    assert "+49 30 9876543" not in result.anonymized_text
    assert "+49 89 1234567" not in result.anonymized_text

    assert "Reinhard Müller" not in result.anonymized_text
    assert "Max Mustermann" not in result.anonymized_text
    assert "Emma Schmidt" not in result.anonymized_text
