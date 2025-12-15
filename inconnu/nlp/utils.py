import logging
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


def clear_singleton_instances():
    """Clear all singleton instances.

    Useful for:
    - Testing (ensuring clean state between tests)
    - Memory management (releasing loaded spaCy models)
    - Configuration changes (forcing model reload)
    """
    global instances
    with global_lock:
        instances.clear()


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
    NORP = "NORP"  # nationality, religious or political groups
    MISC = "MISC"  # misc for DE language"
    IBAN = "IBAN"  # custom ner component
    LAW = "LAW"
    LOC = "LOC"
    ORG = "ORG"
    GPE = "GPE"
    FAC = "FAC"
    PER = "PER"  # person for DE language
    STUDENT_ID = "STUDENT_ID"  # custom ner component
    EMPLOYEE_ID = "EMPLOYEE_ID"  # custom ner component
    LEGAL_CITATION = "LEGAL_CITATION"  # custom ner component
    SSN = "SSN"  # custom ner component
    CREDIT_CARD = "CREDIT_CARD"  # custom ner component
    BADGE_NUMBER = "BADGE_NUMBER"  # custom ner component


def validate_entity_spans(spans, doc_length=None):
    """Validate entity spans for correctness before processing.

    Returns (valid_spans, errors) tuple where errors is a list of validation issues.
    """
    valid_spans = []
    errors = []

    for i, span in enumerate(spans):
        try:
            # Check basic span validity
            if not hasattr(span, "start") or not hasattr(span, "end"):
                errors.append(f"Span {i} missing start/end attributes")
                continue

            # Check for malformed spans
            if span.start < 0 or span.end < 0:
                errors.append(
                    f"Span {i} has negative indices: start={span.start}, end={span.end}"
                )
                continue

            if span.start >= span.end:
                errors.append(
                    f"Span {i} has invalid range: start={span.start} >= end={span.end}"
                )
                continue

            # Check bounds if doc_length is provided
            if doc_length and (span.start >= doc_length or span.end > doc_length):
                errors.append(
                    f"Span {i} out of bounds: [{span.start}, {span.end}) in doc of length {doc_length}"
                )
                continue

            valid_spans.append(span)

        except Exception as e:
            errors.append(f"Error validating span {i}: {str(e)}")

    return valid_spans, errors


def filter_overlapping_spans(spans, debug=False):
    """Filter overlapping spans with priority-based resolution.

    When spans overlap, this function:
    1. Prefers longer spans over shorter ones
    2. Uses entity type priority as a tiebreaker
    3. Falls back to first-come for equal priority
    4. Handles edge cases with identical positions using text content
    """
    if not spans:
        return []

    # Define entity priority (higher number = higher priority)
    # Expanded with all entity types from examples
    ENTITY_PRIORITY = {
        "PERSON": 10,
        "SSN": 9,
        "EMAIL": 9,
        "PHONE_NUMBER": 8,
        "BADGE_NUMBER": 8,
        "PASSPORT": 8,
        "DRIVER_LICENSE": 8,
        "CREDIT_CARD": 8,
        "MRN": 8,  # Medical Record Number
        "NPI": 8,  # National Provider Identifier
        "DEA_NUMBER": 8,
        "IBAN": 7,
        "TICKET_NUMBER": 7,
        "SWIFT_CODE": 7,
        "ROUTING_NUMBER": 7,
        "CASE_NUMBER": 7,
        "BAR_NUMBER": 7,
        "VIN": 7,
        "DATE": 6,
        "CRYPTO_WALLET": 6,
        "STUDENT_ID": 6,
        "EMPLOYEE_ID": 6,
        "ICD_CODE": 6,
        "PARTICIPANT_ID": 6,
        "STUDY_ID": 6,
        "ORDER_NUMBER": 6,
        "GPE": 5,
        "LOC": 5,
        "CUSTOMER_ID": 5,
        "ORG": 4,
        "MONEY": 3,
        "TIME": 2,
        "WORK_OF_ART": 1,
        "LANGUAGE": 1,
        "PRODUCT": 1,
        "EVENT": 1,
        "NORP": 1,
        "FAC": 1,
        "LAW": 1,
        "MISC": 0,
    }

    # Pre-compute priority lookups for performance
    priority_cache = {}
    for span in spans:
        if span.label_ not in priority_cache:
            priority_cache[span.label_] = ENTITY_PRIORITY.get(span.label_, 0)

    # Sort spans by start index, then by length (descending), then by priority, then by text content
    sorted_spans = sorted(
        spans,
        key=lambda span: (
            span.start,
            -(span.end - span.start),  # Negative for descending length
            -priority_cache.get(span.label_, 0),  # Negative for descending priority
            len(span.text)
            if hasattr(span, "text")
            else 0,  # Text length as additional tiebreaker
            span.text
            if hasattr(span, "text")
            else "",  # Alphabetical as final tiebreaker
        ),
    )

    filtered_spans = []
    covered_positions = set()

    if debug:
        conflict_log = []

    for span in sorted_spans:
        try:
            # Check if this span overlaps with any already selected span
            span_positions = set(range(span.start, span.end))
            if not span_positions & covered_positions:
                filtered_spans.append(span)
                covered_positions.update(span_positions)
            elif debug:
                # Log conflict for debugging
                overlapping = [
                    s
                    for s in filtered_spans
                    if set(range(s.start, s.end)) & span_positions
                ]
                conflict_log.append(
                    {
                        "rejected": span,
                        "label": span.label_,
                        "priority": priority_cache.get(span.label_, 0),
                        "overlaps_with": [
                            (s.label_, s.text if hasattr(s, "text") else "")
                            for s in overlapping
                        ],
                    }
                )
        except Exception as e:
            logging.warning(
                f"Error processing span [{span.start}, {span.end}): {str(e)}"
            )
            continue

    if debug and conflict_log:
        logging.debug(
            f"Entity conflict resolution: {len(conflict_log)} conflicts resolved"
        )
        for conflict in conflict_log[:5]:  # Log first 5 conflicts
            logging.debug(
                f"  Rejected {conflict['label']} (priority {conflict['priority']}) "
                f"overlapping with {conflict['overlaps_with']}"
            )

    # Sort filtered spans by start position for consistent output
    return sorted(filtered_spans, key=lambda span: span.start)


def merge_and_validate_spans(
    doc: Doc,
    new_spans: list[Span],
    error_prefix: str = "Entity",
    debug: bool = False,
) -> list[Span]:
    """Merge new spans with existing doc entities, validate, and filter overlaps.

    Args:
        doc: SpaCy Doc object
        new_spans: New spans to merge with doc.ents
        error_prefix: Prefix for error logging messages
        debug: Enable debug logging for conflict resolution

    Returns:
        Filtered list of valid, non-overlapping spans
    """
    all_spans = list(doc.ents) + new_spans
    valid_spans, errors = validate_entity_spans(all_spans, len(doc))

    if errors:
        for error in errors[:3]:
            logging.warning(f"{error_prefix} validation error: {error}")

    return filter_overlapping_spans(valid_spans, debug=debug)


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

        doc.ents = merge_and_validate_spans(doc, spans, "Entity")
        return doc

    return custom_ner_component_name
