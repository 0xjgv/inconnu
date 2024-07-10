import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime

import spacy


@dataclass
class PrivacyConfig:
    anonymize_entities: bool = True
    data_retention_days: int = 30
    max_text_length: int = 1000


class EntityAnonymizer:
    __slots__ = ["nlp"]

    def __init__(self):
        self.nlp = spacy.load("en_core_web_sm")

    def anonymize(self, text: str) -> tuple[str, dict[str, str]]:
        anonymized_text = text
        doc = self.nlp(text)
        entity_map = {}

        for ent in reversed(doc.ents):  # Process in reverse to avoid index issues
            if ent.label_ not in entity_map:
                entity_map[ent.label_] = []

            placeholder = f"[{ent.label_}_{len(entity_map[ent.label_])}]"
            entity_map[ent.label_].append((ent.text, placeholder))

            anonymized_text = (
                anonymized_text[: ent.start_char]
                + placeholder
                + anonymized_text[ent.end_char :]
            )
        return anonymized_text, {
            v[1]: v[0] for values in entity_map.values() for v in values
        }

    def deanonymize(self, *, text: str, entity_map: dict[str, str]) -> str:
        for placeholder, original in entity_map.items():
            text = text.replace(placeholder, original)
        return text


@dataclass
class ProcessedData:
    entity_map: dict[str, str]
    anonymized_text: str
    text_length: int
    anonymized: bool
    timestamp: str
    hashed_id: str
    text: str


class Inconnu:
    __slots__ = ["anonymizer", "config"]

    def __init__(self, *, config: PrivacyConfig, anonymizer: EntityAnonymizer):
        self.anonymizer = anonymizer
        self.config = config

    def process_data(self, *, text: str) -> ProcessedData:
        start_time = time.time()
        if len(text) > self.config.max_text_length:
            raise ValueError(
                f"Text exceeds maximum length of {self.config.max_text_length}"
            )

        hashed_id = self._hash_text(text)

        processed_data = ProcessedData(
            timestamp=datetime.now().isoformat(),
            text_length=len(text),
            anonymized_text=text,
            hashed_id=hashed_id,
            anonymized=False,
            entity_map={},
            text=text,
        )

        if self.config.anonymize_entities:
            anonymized_text, entity_map = self.anonymizer.anonymize(text)
            processed_data.anonymized_text = anonymized_text
            processed_data.entity_map = entity_map
            processed_data.anonymized = True

        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Processing time: {execution_time * 1000:.2f} ms")
        return processed_data

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()


if __name__ == "__main__":
    inconnu = Inconnu(
        anonymizer=EntityAnonymizer(),
        config=PrivacyConfig(
            anonymize_entities=True,
            data_retention_days=30,
            max_text_length=500,
        ),
    )
    try:
        initial_text = "John Doe from New York visited Paris last summer. Jane Smith from California attended a conference in Tokyo in March. Dr. Alice Johnson from Texas gave a lecture in London last week."

        processed_data = inconnu.process_data(text=initial_text)
        print(processed_data)
        print()

        deanonymized_text = inconnu.anonymizer.deanonymize(
            entity_map=processed_data.entity_map,
            text=processed_data.anonymized_text,
        )
        print("Anonymized Text:", processed_data.anonymized_text)
        print("Deanonymized Text:", deanonymized_text)
        print(initial_text == deanonymized_text)
        print()

        # Structured Output from OpenAI (anonymized text)
        structured_output = [
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
        print("Structured Output:", json.dumps(structured_output, indent=2))

        deanonymized_text = inconnu.anonymizer.deanonymize(
            entity_map=processed_data.entity_map,
            text=json.dumps(structured_output, indent=2),
        )
        print("Deanonymized Text:", deanonymized_text)

    except Exception as e:
        print(f"An error occurred: {str(e)}")
