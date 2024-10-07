from enum import StrEnum
from functools import wraps
from re import Pattern
from threading import Lock
from typing import Callable

from spacy.language import Language
from spacy.tokens import Doc, Span

# Global dictionaries to store global lock and instances
global_lock = Lock()
instances = {}


def singleton(cls):
    @wraps(cls)
    def get_instance_by_language(*args, **kwargs) -> "cls":
        language: str | None = kwargs.get("language")
        key = (cls, language)

        ## Double-checked locking pattern
        # Initial check without acquiring the lock (fast path)
        if key in instances:
            return instances[key]

        with global_lock:
            # Second check after acquiring the lock (slow path)
            if key not in instances:
                instances[key] = cls(*args, **kwargs)
        return instances[key]

    return get_instance_by_language


# https://github.com/explosion/spaCy/discussions/9147
# NER labels to identify entities
class DefaultEntityLabel(StrEnum):
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
    processing_func: Callable[[Doc], Doc] | None = None,
    pattern: Pattern | None = None,
    label: DefaultEntityLabel,
    **kwargs,
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
