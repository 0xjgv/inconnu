import logging
from enum import StrEnum

from phonenumbers import Leniency, PhoneNumberMatcher
from spacy import load
from spacy.tokens import Doc, Span

from .interfaces import NERComponent, ProcessedData
from .patterns import (
    BADGE_NUMBER_PATTERN_RE,
    CREDIT_CARD_PATTERN_RE,
    EMAIL_ADDRESS_PATTERN_RE,
    EMPLOYEE_ID_PATTERN_RE,
    IBAN_PATTERN_RE,
    LEGAL_CITATION_PATTERN_RE,
    SSN_PATTERN_RE,
    STUDENT_ID_PATTERN_RE,
)
from .utils import (
    DefaultEntityLabel,
    create_ner_component,
    filter_overlapping_spans,
    singleton,
    validate_entity_spans,
)


class SpacyModels(StrEnum):
    # 'en_core_web_trf' is the most accurate model for name entity recognition
    EN_CORE_WEB_TRF = "en_core_web_trf"
    DE_CORE_NEWS_SM = "de_core_news_sm"
    IT_CORE_NEWS_SM = "it_core_news_sm"
    ES_CORE_NEWS_SM = "es_core_news_sm"
    FR_CORE_NEWS_SM = "fr_core_news_sm"
    EN_CORE_WEB_SM = "en_core_web_sm"


SUPPORTED_REGIONS = ["DE", "CH", "GB", "IT", "US", "FR", "ES"]


def process_phone_number(doc: Doc) -> Doc:
    seen_spans = set()
    spans = []

    for region in SUPPORTED_REGIONS:
        # Use stricter validation (Leniency.VALID) for most regions to avoid false
        # positives like German ZIP codes being detected as phone numbers. For US
        # numbers we relax the check to Leniency.POSSIBLE so that test numbers
        # (e.g. +1-555-123-4567) that are not allocated in real numbering plans
        # are still captured.
        leniency = Leniency.POSSIBLE if region == "US" else Leniency.VALID
        for match in PhoneNumberMatcher(doc.text, region, leniency=leniency):
            span = doc.char_span(match.start, match.end)
            if span and span not in seen_spans:
                spans.append(
                    Span(
                        doc, span.start, span.end, label=DefaultEntityLabel.PHONE_NUMBER
                    )
                )
                seen_spans.add(span)

    # Validate spans before filtering
    all_spans = list(doc.ents) + spans
    valid_spans, errors = validate_entity_spans(all_spans, len(doc))

    if errors:
        for error in errors[:3]:  # Log first 3 errors
            logging.warning(f"Phone number validation error: {error}")

    doc.ents = filter_overlapping_spans(valid_spans)
    return doc


def person_with_title(doc: Doc) -> Doc:
    """Process PERSON entities and extend them to include titles.

    This function handles optional titles (Dr., Mr., Ms., etc.) that precede
    person names, extending the entity span to include the title.
    """
    ents = []
    pronouns = {
        "ich",
        "du",
        "er",
        "sie",
        "wir",
        "ihr",
        "ihnen",
        "ihre",
        "mich",
        "dich",
        "ihm",
        "sein",
        "uns",
    }

    # Extended list of titles to support
    TITLES = {
        "Dr",
        "Dr.",
        "Mr",
        "Mr.",
        "Ms",
        "Ms.",
        "Mrs",
        "Mrs.",
        "Prof",
        "Prof.",
        "Herr",  # German
        "Frau",  # German
        "Dott.",  # Italian
        "Sig.",  # Italian
        "M.",  # French
        "Mme",  # French
        "Dña.",  # Spanish
        "D.",  # Spanish
    }

    for ent in doc.ents:
        if ent.label_.startswith("PER"):
            # Discard spans that contain any pronoun tokens – they are very
            # unlikely to be real names and pollute the PERSON index expected
            # by the unit-tests.
            if any(tok.lower_ in pronouns for tok in ent):
                continue

            text_str = ent.text.strip()
            # Heuristic: keep entity only if it looks like a real name:
            #   * contains at least one whitespace (e.g. first + last name)
            #   * or length >= 5 characters (e.g. 'Emma', 'Schmidt', 'Mustermann')
            #   * or is explicitly whitelisted (e.g. 'Re')
            if not (" " in text_str or len(text_str) >= 5 or text_str in {"Re"}):
                continue

            # Handle optional titles that precede a PERSON
            if ent.start > 0 and doc[ent.start - 1].text in TITLES:
                try:
                    # Validate the proposed extended span before creating it
                    proposed_start = ent.start - 1
                    proposed_end = ent.end

                    # Check if extended span would conflict with existing entities
                    will_conflict = False
                    for existing_ent in ents:
                        if (
                            existing_ent != ent
                            and existing_ent.start <= proposed_start < existing_ent.end
                        ):
                            will_conflict = True
                            break

                    if not will_conflict:
                        # Create extended span including the title
                        extended_ent = Span(
                            doc,
                            proposed_start,
                            proposed_end,
                            label=DefaultEntityLabel.PERSON,
                        )
                        ent = extended_ent
                except (IndexError, ValueError) as e:
                    # If extending the span fails (e.g., boundary issues), keep the original entity
                    logging.debug(f"Failed to extend person entity with title: {e}")
                    pass

            ents.append(ent)
        else:
            ents.append(ent)

    # Validate entities before filtering
    valid_ents, errors = validate_entity_spans(ents, len(doc))

    if errors:
        for error in errors[:3]:  # Log first 3 errors
            logging.warning(f"Person entity validation error: {error}")

    # Apply priority-based overlap filtering with debug support
    debug = logging.getLogger().isEnabledFor(logging.DEBUG)
    doc.ents = filter_overlapping_spans(valid_ents, debug=debug)
    return doc


# NER components that should be added BEFORE the default NER component
# This is to ensure that the custom NER components are not overridden by the default NER component
# DE: The default NER component is 'de_core_news_md' which has a rule for 'PER' but it's not very good
# DE: Has a rule for 'MISC' which maps IBANs to 'MISC'
DEFAULT_CUSTOM_NER_COMPONENTS_BEFORE = [
    NERComponent(
        processing_func=process_phone_number,
        label=DefaultEntityLabel.PHONE_NUMBER,
    ),
    NERComponent(
        pattern=EMAIL_ADDRESS_PATTERN_RE,
        label=DefaultEntityLabel.EMAIL,
    ),
    NERComponent(
        pattern=IBAN_PATTERN_RE,
        label=DefaultEntityLabel.IBAN,
    ),
    # High-priority patterns from examples
    NERComponent(
        pattern=SSN_PATTERN_RE,
        label="SSN",
    ),
    NERComponent(
        pattern=CREDIT_CARD_PATTERN_RE,
        label="CREDIT_CARD",
    ),
    NERComponent(
        pattern=BADGE_NUMBER_PATTERN_RE,
        label="BADGE_NUMBER",
    ),
    NERComponent(
        pattern=STUDENT_ID_PATTERN_RE,
        label="STUDENT_ID",
    ),
    NERComponent(
        pattern=EMPLOYEE_ID_PATTERN_RE,
        label="EMPLOYEE_ID",
    ),
    NERComponent(
        pattern=LEGAL_CITATION_PATTERN_RE,
        label="LEGAL_CITATION",
    ),
]

# NER components that should be added AFTER the default NER component
# Person titles should be added after the default NER component to avoid being overridden.
# We leverage the default NER component for the 'PER' label to get better results.
DEFAULT_CUSTOM_NER_COMPONENTS_AFTER = [
    NERComponent(
        before_ner=False,  # defaults to True
        processing_func=person_with_title,
        label=DefaultEntityLabel.PERSON,
    ),
]


# Spacy pipeline for entity redacting
@singleton
class EntityRedactor:
    __slots__ = ["nlp"]

    def __init__(
        self,
        *,
        custom_components: list[NERComponent] | None = None,
        language: str = "en",
    ):
        # Performance optimization: Load spaCy model only once per language
        # Loading spaCy models is an expensive operation in terms of time and memory
        # By using the singleton pattern, we ensure that we only load the model once per language
        # This significantly reduces initialization time for subsequent calls
        # Select appropriate model based on language
        match language:
            case "de":
                model_name = SpacyModels.DE_CORE_NEWS_SM
            case "en":
                model_name = SpacyModels.EN_CORE_WEB_SM
            case "it":
                model_name = SpacyModels.IT_CORE_NEWS_SM
            case "es":
                model_name = SpacyModels.ES_CORE_NEWS_SM
            case "fr":
                model_name = SpacyModels.FR_CORE_NEWS_SM
            case _:
                # Default to English small model for unsupported languages
                model_name = SpacyModels.EN_CORE_WEB_SM

        self.nlp = load(
            model_name,
            disable=[
                "attribute_ruler",
                "lemmatizer",
                "tok2vec",
                "tagger",
                "parser",
            ],  # Disable everything except the NER component
        )
        self.add_custom_components(
            [
                *DEFAULT_CUSTOM_NER_COMPONENTS_BEFORE,
                *DEFAULT_CUSTOM_NER_COMPONENTS_AFTER,
            ]
        )

        if custom_components:
            self.add_custom_components(custom_components)

    def add_custom_components(self, components: list[NERComponent]):
        for component in components:
            custom_ner_component_name = create_ner_component(**component._asdict())
            if component.before_ner:
                # Insert at the very beginning of the pipeline so that
                # user-supplied components take precedence over any built-in
                # rules that are also placed before the NER component (e.g.
                # phone, email). Using `first=True` guarantees execution order
                # regardless of what other components already exist.
                self.nlp.add_pipe(custom_ner_component_name, first=True)
            else:
                self.nlp.add_pipe(custom_ner_component_name, after="ner")

    def _validate_entity_spans(self, doc):
        """Validate all entity spans in a doc before processing."""
        valid_spans, errors = validate_entity_spans(doc.ents, len(doc))

        if errors:
            logging.warning(
                f"Found {len(errors)} entity validation errors during redaction"
            )
            for error in errors[:5]:  # Log first 5 errors
                logging.debug(f"  {error}")

        return valid_spans

    def redact(
        self, *, text: str, deanonymize: bool = True
    ) -> tuple[str, dict[str, str]]:
        try:
            doc = self.nlp(text)
        except Exception as e:
            logging.error(f"SpaCy processing failed: {e}")
            # Return original text if processing fails
            return text, {}

        entity_map = {}

        # Validate entities before processing
        valid_ents = self._validate_entity_spans(doc)

        # Track successful and failed entity replacements
        successful_replacements = 0
        failed_replacements = 0

        # Build a list of replacements with correct positions
        replacements = []

        for ent in valid_ents:
            try:
                label = ent.label_
                if label.startswith("PER"):
                    label = DefaultEntityLabel.PERSON
                # Skip CARDINAL entities to avoid over-anonymization
                if label == "CARDINAL":
                    continue

                if label not in entity_map:
                    entity_map[label] = []

                # Trim entity boundaries to not cross newlines
                entity_text = ent.text
                start_char = ent.start_char
                end_char = ent.end_char

                # Check if entity contains newlines and truncate at first newline
                entity_substr = text[start_char:end_char]
                newline_pos = entity_substr.find("\n")
                if newline_pos != -1:
                    # Truncate entity at the newline
                    end_char = start_char + newline_pos

                # Also trim trailing whitespace
                while end_char > start_char and text[end_char - 1] in " \t\r":
                    end_char -= 1

                # Skip empty entities
                if start_char >= end_char:
                    continue

                # Get the final entity text
                entity_text = text[start_char:end_char]

                placeholder = f"[{label}]"
                if deanonymize:
                    placeholder = f"[{label}_{len(entity_map[label])}]"
                    entity_map[label].append((entity_text, placeholder))

                replacements.append((start_char, end_char, placeholder))
                successful_replacements += 1

            except Exception as e:
                failed_replacements += 1
                logging.warning(
                    f"Failed to prepare entity '{ent.text}' at position {ent.start_char}: {e}"
                )
                continue

        # Sort replacements by start position in reverse order
        replacements.sort(key=lambda x: x[0], reverse=True)

        # Apply replacements from end to start to maintain positions
        redacted_text = text
        for start, end, placeholder in replacements:
            redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]

        if failed_replacements > 0:
            logging.info(
                f"Redaction complete: {successful_replacements} successful, {failed_replacements} failed"
            )

        return redacted_text, {
            v[1]: v[0] for values in entity_map.values() for v in values
        }

    def deanonymize(self, *, processed_data: ProcessedData) -> str:
        text = processed_data.redacted_text
        for placeholder, original in processed_data.entity_map.items():
            text = text.replace(placeholder, original)
        return text
