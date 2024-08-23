from enum import StrEnum
from re import Pattern

from phonenumbers import PhoneNumberMatcher
from spacy.language import Language, PipeCallable
from spacy.tokens import Doc, Span

from inconnu.config import SUPPORTED_REGIONS
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
    MISC = "MISC"  # misc for DE language“
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


def _process_phone_number(doc: Doc) -> Doc:
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


def _person_with_title(doc: Doc) -> Doc:
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


CUSTOM_NER_COMPONENTS = [
    {"processing_func": _person_with_title, "label": EntityLabel.PERSON},
    {"pattern": EMAIL_ADDRESS_PATTERN_RE, "label": EntityLabel.EMAIL},
    {
        "processing_func": _process_phone_number,
        "label": EntityLabel.PHONE_NUMBER,
    },
]
