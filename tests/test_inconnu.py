import json
from pathlib import Path

import pytest

from inconnu.config import Config
from inconnu.main import Inconnu
from inconnu.nlp.pseudonymizer import EntityPseudonymizer

MOCKS_PATH = Path("tests/mocks")


@pytest.fixture
def inconnu() -> Inconnu:
    return Inconnu(
        pseudonymizer=EntityPseudonymizer(),
        config=Config(
            pseudonymize_entities=True,
            data_retention_days=30,
            max_text_length=7_000,
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
            "Person": "Dr. [PERSON_0]",
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


def test_process_data_basic(inconnu):
    text = "John Doe visited New York."

    result = inconnu.process_data(text=text)

    assert result.entity_map["[PERSON_0]"] == "John Doe"
    assert result.entity_map["[GPE_0]"] == "New York"
    assert result.text_length == len(text)
    assert len(result.entity_map) == 2


def test_process_data_no_entities(inconnu):
    text = "The quick brown fox jumps over the lazy dog."

    result = inconnu.process_data(text=text)

    assert result.pseudonymized_text == text
    assert len(result.entity_map) == 0


@pytest.mark.skip(reason="Not implemented yet")
def test_process_data_max_length(inconnu):
    text = "a" * 501  # Exceeds max_text_length of 500

    with pytest.raises(ValueError, match="Text exceeds maximum length of 500"):
        inconnu.process_data(text=text)


def test_process_data_multiple_entities(inconnu):
    text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March."

    result = inconnu.process_data(text=text)

    assert result.entity_map["[DATE_1]"] == "last summer"
    assert result.entity_map["[DATE_0]"] == "March"

    assert result.entity_map["[PERSON_0]"] == "Jane Smith"
    assert result.entity_map["[PERSON_1]"] == "John Doe"

    assert result.entity_map["[GPE_1]"] == "California"
    assert result.entity_map["[GPE_3]"] == "New York"
    assert result.entity_map["[GPE_2]"] == "Paris"
    assert result.entity_map["[GPE_0]"] == "Tokyo"
    assert len(result.entity_map) == 8


def test_process_data_no_pseudonymization(inconnu):
    inconnu.config.pseudonymize_entities = False
    text = "John Doe visited New York."

    result = inconnu.process_data(text=text)

    assert result.pseudonymized_text == ""
    assert len(result.entity_map) == 0
    assert not result.pseudonymized
    assert result.text == text


def test_process_data_hashing(inconnu):
    text = "John Doe visited New York."

    result = inconnu.process_data(text=text)

    assert result.hashed_id.isalnum()  # Should be alphanumeric
    assert len(result.hashed_id) == 64  # SHA-256 hash length


def test_process_data_timestamp(inconnu):
    text = "John Doe visited New York."

    result = inconnu.process_data(text=text)

    assert result.timestamp is not None
    assert len(result.timestamp) > 0


def test_deanonymization(inconnu):
    text = "John Doe visited New York last summer."

    result = inconnu.process_data(text=text)

    deanonymized = inconnu.pseudonymizer.deanonymize(
        text=result.pseudonymized_text,
        entity_map=result.entity_map,
    )
    assert deanonymized == text


def test_deanonymization_multiple_entities(
    inconnu, multiple_entities_text, structured_output
):
    result = inconnu.process_data(text=multiple_entities_text)

    deanonymized = inconnu.pseudonymizer.deanonymize(
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


def test_prompt_processing_time(inconnu, en_prompt):
    result = inconnu.process_data(text=en_prompt)

    # Processing time should be less than 150ms
    assert 0 < result.processing_time_ms < 150


def test_en_prompt(inconnu, en_prompt):
    result = inconnu.process_data(text=en_prompt)

    deanonymized = inconnu.pseudonymizer.deanonymize(
        text=result.pseudonymized_text,
        entity_map=result.entity_map,
    )

    print(json.dumps(result.entity_map, indent=2))
    # Custom NER components
    assert result.entity_map.get("[EMAIL_0]") == "emma.schmidt@solartech.de"
    assert result.entity_map.get("[PHONE_NUMBER_0]") == "+49 30 9876543"
    assert result.entity_map.get("[PHONE_NUMBER_1]") == "+49 89 1234567"

    assert result.entity_map.get("[PERSON_2]") == "Max Mustermann"
    assert result.entity_map.get("[PERSON_0]") == "Emma Schmidt"
    assert result.entity_map.get("[PERSON_1]") == "Mustermann"

    assert en_prompt == deanonymized
