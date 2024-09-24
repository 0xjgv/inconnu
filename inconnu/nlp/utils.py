from collections import defaultdict
from enum import StrEnum
from re import Pattern

from spacy.language import Language, PipeCallable
from spacy.tokens import Doc, Span


def singleton(cls):
    instances = defaultdict(dict)

    def get_instance_by_language(*args, **kwargs):
        language = kwargs.get("language")
        if language not in instances[cls]:
            instances[cls][language] = cls(*args, **kwargs)
        return instances[cls][language]

    return get_instance_by_language


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
    MISC = "MISC"  # misc for DE language“
    IBAN = "IBAN"  # custom ner component
    LAW = "LAW"
    LOC = "LOC"
    ORG = "ORG"
    GPE = "GPE"
    FAC = "FAC"
    PER = "PER"  # person for DE language


def filter_overlapping_spans(spans):
    filtered_spans = []
    current_end = -1

    # Sort spans by start index
    for span in sorted(spans, key=lambda span: span.start):
        if span.start >= current_end:
            filtered_spans.append(span)
            current_end = span.end

    return filtered_spans


def create_ner_component(
    *,
    processing_func: PipeCallable | None = None,
    pattern: Pattern | None = None,
    label: EntityLabel,
) -> str:
    custom_ner_component_name = f"{label.lower()}_ner_component"

    @Language.component(custom_ner_component_name)
    def custom_ner_component(doc: Doc) -> Doc:
        if processing_func:
            return processing_func(doc)
        if not pattern:
            raise ValueError("Pattern is required if processing_func is not provided.")

        spans = []
        for match in pattern.finditer(doc.text):
            start, end = match.span()
            span = doc.char_span(start, end)
            if span:
                spans.append(Span(doc, span.start, span.end, label=label))

        doc.ents = filter_overlapping_spans(list(doc.ents) + spans)
        return doc

    return custom_ner_component_name
