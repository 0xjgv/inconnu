from enum import StrEnum

from phonenumbers import PhoneNumberMatcher
from spacy import load
from spacy.tokens import Doc, Span

from inconnu.nlp.interfaces import ProcessedData
from inconnu.nlp.patterns import EMAIL_ADDRESS_PATTERN_RE, IBAN_PATTERN_RE
from inconnu.nlp.utils import (
    EntityLabel,
    create_ner_component,
    filter_overlapping_spans,
    singleton,
)


class SpacyModels(StrEnum):
    # 'en_core_web_trf' is the most accurate model for name entity recognition
    EN_CORE_WEB_TRF = "en_core_web_trf"
    DE_CORE_NEWS_MD = "de_core_news_md"
    EN_CORE_WEB_SM = "en_core_web_sm"


SUPPORTED_REGIONS = ["DE", "CH", "GB"]


def process_phone_number(doc: Doc) -> Doc:
    seen_spans = set()
    spans = []

    for region in SUPPORTED_REGIONS:
        for match in PhoneNumberMatcher(doc.text, region, leniency=1):
            span = doc.char_span(match.start, match.end)
            if span and span not in seen_spans:
                spans.append(
                    Span(doc, span.start, span.end, label=EntityLabel.PHONE_NUMBER)
                )
                seen_spans.add(span)

    doc.ents = filter_overlapping_spans(list(doc.ents) + spans)
    return doc


def person_with_title(doc: Doc) -> Doc:
    ents = []
    for ent in doc.ents:
        # Only check for title if it's a person and not the first token
        if ent.label_.startswith("PER") and ent.start != 0:
            prev_token = doc[ent.start - 1]
            if prev_token.text in ("Dr", "Dr.", "Mr", "Mr.", "Ms", "Ms."):
                person_ent = Span(doc, ent.start - 1, ent.end, label=EntityLabel.PERSON)
                ents.append(person_ent)
            else:
                person_ent = Span(doc, ent.start, ent.end, label=EntityLabel.PERSON)
                ents.append(person_ent)
        else:
            ents.append(ent)
    doc.ents = ents
    return doc


# NER components that should be added BEFORE the default NER component
# This is to ensure that the custom NER components are not overridden by the default NER component
# DE: The default NER component is 'de_core_news_md' which has a rule for 'PER' but it's not very good
# DE: Has a rule for 'MISC' which maps IBANs to 'MISC'
custom_ner_components_before = [
    {"pattern": EMAIL_ADDRESS_PATTERN_RE, "label": EntityLabel.EMAIL},
    {"pattern": IBAN_PATTERN_RE, "label": EntityLabel.IBAN},
    {
        "processing_func": process_phone_number,
        "label": EntityLabel.PHONE_NUMBER,
    },
]

# NER components that should be added AFTER the default NER component
# Person titles should be added after the default NER component to avoid being overridden.
# We leverage the default NER component for the 'PER' label to get better results.
custom_ner_components_after = [
    {"processing_func": person_with_title, "label": EntityLabel.PERSON},
]


# Spacy pipeline for entity redacting
@singleton
class EntityRedactor:
    __slots__ = ["nlp"]

    def __init__(self, language: str = "en"):
        # Performance optimization: Load spaCy model only once per language
        # Loading spaCy models is an expensive operation in terms of time and memory
        # By using the singleton pattern, we ensure that we only load the model once per language
        # This significantly reduces initialization time for subsequent calls
        self.nlp = load(
            SpacyModels.DE_CORE_NEWS_MD
            if language == "de"
            else SpacyModels.EN_CORE_WEB_SM,
            disable=[
                "attribute_ruler",
                "lemmatizer",
                "tok2vec",
                "tagger",
                "parser",
            ],  # Disable everything except the NER component
        )

        # Add custom NER components to the pipeline
        # These components are added only once per language, improving overall efficiency
        for custom_ner_component in custom_ner_components_before:
            custom_ner_component_name = create_ner_component(**custom_ner_component)
            self.nlp.add_pipe(custom_ner_component_name, before="ner")

        for custom_ner_component in custom_ner_components_after:
            custom_ner_component_name = create_ner_component(**custom_ner_component)
            self.nlp.add_pipe(custom_ner_component_name, after="ner")

    def redact(
        self, *, text: str, deanonymize: bool = True
    ) -> tuple[str, dict[str, str]]:
        redacted_text = text
        doc = self.nlp(text)
        entity_map = {}

        filtered_ents = filter(
            lambda ent: ent.label_ in EntityLabel.__members__, doc.ents
        )
        # Process in reverse to avoid index issues
        for ent in reversed(list(filtered_ents)):
            if ent.label_ not in entity_map:
                entity_map[ent.label_] = []

            placeholder = f"[{ent.label_}]"
            if deanonymize:
                placeholder = f"[{ent.label_}_{len(entity_map[ent.label_])}]"
                entity_map[ent.label_].append((ent.text, placeholder))

            redacted_text = (
                redacted_text[: ent.start_char]
                + placeholder
                + redacted_text[ent.end_char :]
            )
        return redacted_text, {
            v[1]: v[0] for values in entity_map.values() for v in values
        }

    def deanonymize(self, *, processed_data: ProcessedData) -> str:
        text = processed_data.redacted_text
        for placeholder, original in processed_data.entity_map.items():
            text = text.replace(placeholder, original)
        return text
