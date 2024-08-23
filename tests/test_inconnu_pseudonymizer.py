import json
from pathlib import Path

import pytest

from inconnu import InconnuPseudonymizer
from inconnu.config import Config, Language

MOCKS_PATH = Path("tests/mocks")


@pytest.fixture
def inconnu_pseudonymizer_en() -> InconnuPseudonymizer:
    return InconnuPseudonymizer(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
            language=Language.EN,
        ),
    )


@pytest.fixture
def inconnu_pseudonymizer_de() -> InconnuPseudonymizer:
    return InconnuPseudonymizer(
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


def test_process_data_basic(inconnu_pseudonymizer_en):
    text = "John Doe visited New York."

    result = inconnu_pseudonymizer_en(text=text)

    assert result.entity_map["[PERSON_0]"] == "John Doe"
    assert result.entity_map["[GPE_0]"] == "New York"
    assert result.text_length == len(text)
    assert len(result.entity_map) == 2


def test_process_data_no_entities(inconnu_pseudonymizer_en):
    text = "The quick brown fox jumps over the lazy dog."

    result = inconnu_pseudonymizer_en(text=text)

    assert result.pseudonymized_text == text
    assert len(result.entity_map) == 0


def test_process_data_multiple_entities(inconnu_pseudonymizer_en):
    text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March."

    result = inconnu_pseudonymizer_en(text=text)

    assert result.entity_map["[DATE_1]"] == "last summer"
    assert result.entity_map["[DATE_0]"] == "March"

    assert result.entity_map["[PERSON_0]"] == "Jane Smith"
    assert result.entity_map["[PERSON_1]"] == "John Doe"

    assert result.entity_map["[GPE_1]"] == "California"
    assert result.entity_map["[GPE_3]"] == "New York"
    assert result.entity_map["[GPE_2]"] == "Paris"
    assert result.entity_map["[GPE_0]"] == "Tokyo"
    assert len(result.entity_map) == 8


def test_process_data_hashing(inconnu_pseudonymizer_en):
    text = "John Doe visited New York."

    result = inconnu_pseudonymizer_en(text=text)

    assert result.hashed_id.isalnum()  # Should be alphanumeric
    assert len(result.hashed_id) == 64  # SHA-256 hash length


def test_process_data_timestamp(inconnu_pseudonymizer_en):
    text = "John Doe visited New York."

    result = inconnu_pseudonymizer_en(text=text)

    assert result.timestamp is not None
    assert len(result.timestamp) > 0


def test_deanonymization(inconnu_pseudonymizer_en):
    text = "John Doe visited New York last summer."

    result = inconnu_pseudonymizer_en(text=text)

    deanonymized = inconnu_pseudonymizer_en.deanonymize(
        text=result.pseudonymized_text,
        entity_map=result.entity_map,
    )
    assert deanonymized == text


def test_deanonymization_multiple_entities(
    inconnu_pseudonymizer_en, multiple_entities_text, structured_output
):
    result = inconnu_pseudonymizer_en(text=multiple_entities_text)

    deanonymized = inconnu_pseudonymizer_en.deanonymize(
        text=json.dumps(structured_output),
        entity_map=result.entity_map,
    )

    assert json.loads(deanonymized) == [
        {
            "Person": "John Doe",
            "Origin": "New York",
            "Event": "Visit",
            "Location": "Paris",
            "Date": "last summer",
        },
        {
            "Person": "Jane Smith",
            "Origin": "California",
            "Event": "Conference Attendance",
            "Location": "Tokyo",
            "Date": "March",
        },
        {
            "Person": "Dr. Alice Johnson",
            "Origin": "Texas",
            "Event": "Lecture",
            "Location": "London",
            "Date": "last week",
        },
    ]


def test_prompt_processing_time(inconnu_pseudonymizer_en, en_prompt):
    result = inconnu_pseudonymizer_en(text=en_prompt)

    # Processing time should be less than 200ms
    assert 0 < result.processing_time_ms < 200


def test_de_prompt(inconnu_pseudonymizer_de, de_prompt):
    result = inconnu_pseudonymizer_de(text=de_prompt)

    deanonymized = inconnu_pseudonymizer_de.deanonymize(
        text=result.pseudonymized_text,
        entity_map=result.entity_map,
    )

    # Custom NER components
    assert result.entity_map.get("[EMAIL_0]") == "emma.schmidt@solartech.de"
    assert result.entity_map.get("[PHONE_NUMBER_0]") == "+49 30 9876543"
    assert result.entity_map.get("[PHONE_NUMBER_1]") == "+49 89 1234567"

    assert result.entity_map.get("[PERSON_3]") == "Max Mustermann"
    assert result.entity_map.get("[PERSON_0]") == "Emma Schmidt"
    assert result.entity_map.get("[PERSON_1]") == "Mustermann"
    assert result.entity_map.get("[PERSON_2]") == "Re"

    assert de_prompt == deanonymized
