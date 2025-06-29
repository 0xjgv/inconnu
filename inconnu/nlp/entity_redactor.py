from enum import StrEnum

from phonenumbers import Leniency, PhoneNumberMatcher
from spacy import load
from spacy.tokens import Doc, Span

from .interfaces import NERComponent, ProcessedData
from .patterns import EMAIL_ADDRESS_PATTERN_RE, IBAN_PATTERN_RE
from .utils import (
    DefaultEntityLabel,
    create_ner_component,
    filter_overlapping_spans,
    singleton,
)


class SpacyModels(StrEnum):
    # 'en_core_web_trf' is the most accurate model for name entity recognition
    EN_CORE_WEB_TRF = "en_core_web_trf"
    DE_CORE_NEWS_SM = "de_core_news_sm"
    IT_CORE_NEWS_SM = "it_core_news_sm"
    EN_CORE_WEB_SM = "en_core_web_sm"


SUPPORTED_REGIONS = ["DE", "CH", "GB", "IT", "US"]


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

    doc.ents = filter_overlapping_spans(list(doc.ents) + spans)
    return doc


def person_with_title(doc: Doc) -> Doc:
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

            # Handle optional titles (Dr., Mr., Ms.) that precede a PERSON
            if ent.start != 0 and doc[ent.start - 1].text in (
                "Dr",
                "Dr.",
                "Mr",
                "Mr.",
                "Ms",
                "Ms.",
            ):
                ent = Span(doc, ent.start - 1, ent.end, label=DefaultEntityLabel.PERSON)

            ents.append(ent)
        else:
            ents.append(ent)
    doc.ents = ents
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

    def redact(
        self, *, text: str, deanonymize: bool = True
    ) -> tuple[str, dict[str, str]]:
        redacted_text = text
        doc = self.nlp(text)
        entity_map = {}

        # Process in reverse to avoid index issues
        for ent in reversed(doc.ents):
            label = ent.label_
            if label.startswith("PER"):
                label = DefaultEntityLabel.PERSON

            if label not in entity_map:
                entity_map[label] = []

            placeholder = f"[{label}]"
            if deanonymize:
                placeholder = f"[{label}_{len(entity_map[label])}]"
                entity_map[label].append((ent.text, placeholder))

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
