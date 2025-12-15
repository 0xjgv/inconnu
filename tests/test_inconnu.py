import json
from re import compile

import pytest

from inconnu import Inconnu
from inconnu.config import Config
from inconnu.nlp.interfaces import NERComponent


@pytest.fixture
def inconnu_en() -> Inconnu:
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=75_000,
        ),
        language="en",
    )


@pytest.fixture
def inconnu_de() -> Inconnu:
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=10_000,
        ),
        language="de",
    )


@pytest.fixture
def inconnu_it() -> Inconnu:
    return Inconnu(
        config=Config(
            data_retention_days=30,
            max_text_length=10_000,
        ),
        language="it",
    )


@pytest.fixture
def multiple_entities_text() -> str:
    return "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March. Dr. Alice Johnson from Texas gave a lecture in London last week."


@pytest.fixture
def structured_output() -> list[dict[str, str]]:
    # Given the anonymized text from `multiple_entities_text`, the following is the expected output
    # Updated to match actual entity extraction order
    return [
        {
            "Person": "[PERSON_0]",
            "Origin": "[GPE_0]",
            "Event": "Visit",
            "Location": "[GPE_1]",
            "Date": "[DATE_0]",
        },
        {
            "Person": "[PERSON_1]",
            "Origin": "[GPE_2]",
            "Event": "Conference Attendance",
            "Location": "[GPE_3]",
            "Date": "[DATE_1]",
        },
        {
            "Person": "[PERSON_2]",
            "Origin": "[GPE_4]",
            "Event": "Lecture",
            "Location": "[GPE_5]",
            "Date": "[DATE_2]",
        },
    ]


class TestInconnuPseudonymizer:
    def test_process_data_basic(self, inconnu_en):
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        assert processed_data.entity_map["[PERSON_0]"] == "John Doe"
        assert processed_data.entity_map["[GPE_0]"] == "New York"
        assert processed_data.text_length == len(text)
        assert len(processed_data.entity_map) == 2

    def test_process_data_no_entities(self, inconnu_en):
        text = "The quick brown fox jumps over the lazy dog."

        processed_data = inconnu_en(text=text)

        assert processed_data.redacted_text == text
        assert len(processed_data.entity_map) == 0

    def test_process_data_multiple_entities(self, inconnu_en):
        text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March."

        processed_data = inconnu_en(text=text)

        assert processed_data.entity_map["[DATE_0]"] == "last summer"
        assert processed_data.entity_map["[DATE_1]"] == "March"

        assert processed_data.entity_map["[PERSON_0]"] == "John Doe"
        assert processed_data.entity_map["[PERSON_1]"] == "Jane Smith"

        assert processed_data.entity_map["[GPE_0]"] == "New York"
        assert processed_data.entity_map["[GPE_1]"] == "Paris"
        assert processed_data.entity_map["[GPE_2]"] == "California"
        assert processed_data.entity_map["[GPE_3]"] == "Tokyo"
        assert len(processed_data.entity_map) == 8

    def test_process_data_hashing(self, inconnu_en):
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        assert processed_data.hashed_id.isalnum()  # Should be alphanumeric
        assert len(processed_data.hashed_id) == 64  # SHA-256 hash length

    def test_process_data_timestamp(self, inconnu_en):
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        assert processed_data.timestamp is not None
        assert len(processed_data.timestamp) > 0

    def test_deanonymization(self, inconnu_en):
        text = "John Doe visited New York last summer."

        processed_data = inconnu_en(text=text)

        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)
        assert deanonymized == text

    def test_deanonymization_multiple_entities(
        self, inconnu_en, multiple_entities_text, structured_output
    ):
        processed_data = inconnu_en(text=multiple_entities_text)

        processed_data.redacted_text = json.dumps(structured_output)
        deanonymized = inconnu_en.deanonymize(processed_data=processed_data)

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

    def test_prompt_processing_time(self, inconnu_en, en_prompt):
        processed_data = inconnu_en(text=en_prompt)

        # Processing time for ~7KB document should be under 500ms
        # (stricter per-document requirements tested in test_performance.py)
        assert 0 < processed_data.processing_time_ms < 500

    def test_de_prompt(self, inconnu_de, de_prompt):
        processed_data = inconnu_de(text=de_prompt)

        deanonymized_text = inconnu_de.deanonymize(processed_data=processed_data)

        # Custom NER components
        assert processed_data.entity_map.get("[EMAIL_0]") == "emma.schmidt@solartech.de"
        assert processed_data.entity_map.get("[PHONE_NUMBER_0]") == "+49 89 1234567"
        assert processed_data.entity_map.get("[PHONE_NUMBER_1]") == "+49 30 9876543"

        assert processed_data.entity_map.get("[PERSON_0]") == "Max Mustermann"
        assert processed_data.entity_map.get("[PERSON_3]") == "Emma Schmidt"
        assert processed_data.entity_map.get("[PERSON_2]") == "Herr Mustermann"
        assert processed_data.entity_map.get("[PERSON_1]") == "Re"

        assert de_prompt == deanonymized_text

    def test_us_555_phone_number(self, inconnu_en):
        """Ensure reserved US 555 numbers are still detected and redacted.

        The libphonenumber metadata marks most 555 numbers as *invalid* because they
        are reserved for fictional use. We relaxed the matcher to
        ``Leniency.POSSIBLE`` for the US region, so +1-555-123-4567 should now be
        picked up and replaced by a ``PHONE_NUMBER`` placeholder.
        """

        text = "John Doe called from +1-555-123-4567 regarding the incident."

        processed_data = inconnu_en(text=text)

        # Locate the phone-number placeholder dynamically (index may vary).
        phone_placeholders = [
            k for k in processed_data.entity_map if k.startswith("[PHONE_NUMBER")
        ]

        assert len(phone_placeholders) == 1, (
            "Exactly one phone number should be detected"
        )

        placeholder = phone_placeholders[0]

        # Mapping should point back to the original number (with hyphens preserved)
        assert processed_data.entity_map[placeholder] == "+1-555-123-4567"

        # Number must be absent from the redacted text, replaced by the placeholder
        assert "+1-555-123-4567" not in processed_data.redacted_text
        assert placeholder in processed_data.redacted_text


class TestInconnuAnonymizer:
    @pytest.mark.parametrize(
        "text, expected_anonymized_text",
        [
            (
                "John Doe visited New York last summer.",
                "[PERSON] visited [GPE] [DATE].",
            ),
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
    def test_basic_anonymization(self, inconnu_en, text, expected_anonymized_text):
        processed_data = inconnu_en(text=text, deanonymize=False)

        assert processed_data.redacted_text == expected_anonymized_text
        assert processed_data.text_length == len(text)

    def test_process_data_no_entities(self, inconnu_en):
        text = "The quick brown fox jumps over the lazy dog."

        result = inconnu_en(text=text)

        assert result.redacted_text == text

    def test_process_data_multiple_entities(self, inconnu_en):
        text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March."

        result = inconnu_en(text=text, deanonymize=False)

        # Date
        assert "last summer" not in result.redacted_text
        assert "March" not in result.redacted_text

        # Person
        assert "Jane Smith" not in result.redacted_text
        assert "John Doe" not in result.redacted_text

        # GPE (Location)
        assert "California" not in result.redacted_text
        assert "New York" not in result.redacted_text
        assert "Paris" not in result.redacted_text
        assert "Tokyo" not in result.redacted_text

    def test_process_data_hashing(self, inconnu_en):
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        assert processed_data.hashed_id.isalnum()  # Should be alphanumeric
        assert len(processed_data.hashed_id) == 64  # SHA-256 hash length

    def test_process_data_timestamp(self, inconnu_en):
        text = "John Doe visited New York."

        processed_data = inconnu_en(text=text)

        assert processed_data.timestamp is not None
        assert len(processed_data.timestamp) > 0

    def test_prompt_processing_time(self, inconnu_en, en_prompt):
        result = inconnu_en(text=en_prompt)

        # Processing time for ~7KB document should be under 500ms
        # (stricter per-document requirements tested in test_performance.py)
        assert 0 < result.processing_time_ms < 500

    def test_de_prompt(self, inconnu_de, de_prompt):
        processed_data = inconnu_de(text=de_prompt)

        # Custom NER components
        assert "emma.schmidt@solartech.de" not in processed_data.redacted_text
        assert "+49 30 9876543" not in processed_data.redacted_text
        assert "+49 89 1234567" not in processed_data.redacted_text

        assert "Reinhard Müller" not in processed_data.redacted_text
        assert "Max Mustermann" not in processed_data.redacted_text
        assert "Emma Schmidt" not in processed_data.redacted_text

    def test_iban_entities_en(self, inconnu_en):
        text = """
        Hi,

        I would like to update my SEPA bank details for future payments for my contract with the number 021948. Please update my account with the following information:

        Account Holder Name: Max Mustermann
        Bank: DEUTSCHE KREDITBANK BERLIN
        IBAN: DE02120300000000202051

        Kindly confirm once these details have been updated in your system. Should you need further information, please feel free to contact me.
        """

        processed_data = inconnu_en(text=text)

        assert processed_data.entity_map.get("[IBAN_0]") == "DE02120300000000202051"

    def test_iban_entities_it(self, inconnu_it):
        text = """
        Guten Tag!

        vorrei aggiornare i miei dettagli bancari SEPA per i pagamenti futuri per il mio contratto con il numero 021948. Per favore aggiornate il mio conto con le seguenti informazioni:

        Nome del titolare del conto: Max Mustermann
        Banca: DEUTSCHE KREDITBANK BERLIN
        IBAN: DE02120300000000202051

        Vi prego di confermare una volta che questi dettagli sono stati aggiornati nel vostro sistema. Se avete bisogno di ulteriori informazioni, non esitate a contattarmi.
        """

        processed_data = inconnu_it(text=text)

        assert processed_data.entity_map.get("[IBAN_0]") == "DE02120300000000202051"

    def test_entities_custom_component(self):
        text = """
        Ciao,

        vorrei aggiornare i miei dettagli bancari SEPA per i pagamenti futuri per il mio contratto con il numero 021948. Per favore aggiornate il mio conto con le seguenti informazioni:

        Nome del titolare del conto: Max Mustermann
        Banca: DEUTSCHE KREDITBANK BERLIN
        IBAN: DE02120300000000202051

        Vi prego di confermare una volta che questi dettagli sono stati aggiornati nel vostro sistema. Se avete bisogno di ulteriori informazioni, non esitate a contattarmi.
        """
        inconnu = Inconnu(
            config=Config(
                data_retention_days=30,
                max_text_length=5_000,
            ),
            language="it",
        )

        inconnu.add_custom_components(
            [
                NERComponent(
                    pattern=compile(r"SEPA[-\w]*"),
                    label="TRANSACTION_TYPE",
                    before_ner=True,
                ),
                NERComponent(
                    pattern=compile(r"numero[:]?\s*(?:\d+)"),
                    label="CONTRACT_NUMBER",
                    before_ner=True,
                ),
            ]
        )

        processed_data = inconnu(text=text)

        assert processed_data.entity_map.get("[CONTRACT_NUMBER_0]") == "numero 021948"
        assert processed_data.entity_map.get("[TRANSACTION_TYPE_0]") == "SEPA"
