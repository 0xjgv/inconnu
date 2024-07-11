import hashlib
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from spacy import load
from spacy.language import Language
from spacy.tokens import Doc, Span

from inconnu.nlp.patterns import EMAIL_ADDRESS_PATTERN_RE


# NER labels to randomize
class EntityLabel(StrEnum):
    PHONE_NUMBER = "PHONE_NUMBER"  # custom ner component
    WORK_OF_ART = "WORK_OF_ART"
    LANGUAGE = "LANGUAGE"
    PRODUCT = "PRODUCT"
    PERSON = "PERSON"
    EMAIL = "EMAIL"  # custom ner component
    EVENT = "EVENT"
    TIME = "TIME"
    DATE = "DATE"
    NORP = "NORP"
    LAW = "LAW"
    LOC = "LOC"
    ORG = "ORG"
    GPE = "GPE"
    FAC = "FAC"


@dataclass
class PrivacyConfig:
    anonymize_entities: bool = True
    data_retention_days: int = 30
    max_text_length: int = 1000


phone_number_pattern = re.compile(r"\+\d{1,3} \d{1,4} \d{1,4}(\d{1,4})*")


def filter_overlapping_spans(spans):
    filtered_spans = []
    current_end = -1

    # Sort spans by start index
    for span in sorted(spans, key=lambda span: span.start):
        if span.start >= current_end:
            filtered_spans.append(span)
            current_end = span.end

    return filtered_spans


def create_ner_component(pattern: re.Pattern, label: EntityLabel) -> str:
    custom_ner_component_name = f"{label.lower()}_ner_component"

    @Language.component(custom_ner_component_name)
    def custom_ner_component(doc: Doc) -> Doc:
        spans = []
        for match in pattern.finditer(doc.text):
            start, end = match.span()
            span = doc.char_span(start, end)
            if span:
                spans.append(Span(doc, span.start, span.end, label=label))

        doc.ents = filter_overlapping_spans(list(doc.ents) + spans)
        return doc

    return custom_ner_component_name


patterns_and_labels = [
    (phone_number_pattern, EntityLabel.PHONE_NUMBER),
    (EMAIL_ADDRESS_PATTERN_RE, EntityLabel.EMAIL),
]


class EntityAnonymizer:
    __slots__ = ["nlp"]

    def __init__(self):
        self.nlp = load("en_core_web_sm")

        for pattern, label in patterns_and_labels:
            custom_ner_component_name = create_ner_component(pattern, label)
            self.nlp.add_pipe(custom_ner_component_name, after="ner")

    def anonymize(self, text: str) -> tuple[str, dict[str, str]]:
        anonymized_text = text
        doc = self.nlp(text)
        entity_map = {}

        filtered_ents = filter(
            lambda ent: ent.label_ in EntityLabel.__members__, doc.ents
        )
        # Process in reverse to avoid index issues
        for ent in reversed(list(filtered_ents)):
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
