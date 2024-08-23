from enum import StrEnum

from phonenumbers import PhoneNumberMatcher
from spacy import load
from spacy.tokens import Doc, Span

from inconnu.nlp.patterns import EMAIL_ADDRESS_PATTERN_RE
from inconnu.nlp.utils import (
    EntityLabel,
    create_ner_component,
    filter_overlapping_spans,
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


custom_ner_components = [
    {"processing_func": person_with_title, "label": EntityLabel.PERSON},
    {"pattern": EMAIL_ADDRESS_PATTERN_RE, "label": EntityLabel.EMAIL},
    {
        "processing_func": process_phone_number,
        "label": EntityLabel.PHONE_NUMBER,
    },
]


# Spacy pipeline for entity pseudonymization
class EntityAnonymizer:
    __slots__ = ["nlp"]

    def __init__(self, language: str = "en"):
        # Disable everything except for NER
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
            ],
        )

        for custom_ner_component in custom_ner_components:
            custom_ner_component_name = create_ner_component(**custom_ner_component)
            self.nlp.add_pipe(custom_ner_component_name, after="ner")

    def __call__(self, text: str) -> tuple[str, dict[str, str]]:
        pseudonymized_text = text
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

            pseudonymized_text = (
                pseudonymized_text[: ent.start_char]
                + placeholder
                + pseudonymized_text[ent.end_char :]
            )
        return pseudonymized_text, {
            v[1]: v[0] for values in entity_map.values() for v in values
        }

    def deanonymize(self, *, text: str, entity_map: dict[str, str]) -> str:
        for placeholder, original in entity_map.items():
            text = text.replace(placeholder, original)
        return text
