from enum import StrEnum
from re import Pattern

from spacy.language import Language
from spacy.tokens import Doc, Span


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


def filter_overlapping_spans(spans):
    filtered_spans = []
    current_end = -1

    # Sort spans by start index
    for span in sorted(spans, key=lambda span: span.start):
        if span.start >= current_end:
            filtered_spans.append(span)
            current_end = span.end

    return filtered_spans


def create_ner_component(pattern: Pattern, label: EntityLabel) -> str:
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
