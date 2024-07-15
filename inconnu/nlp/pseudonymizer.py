from enum import StrEnum

from spacy import load

from inconnu.nlp.patterns import EMAIL_ADDRESS_PATTERN_RE, PHONE_NUMBER_PATTERN_RE
from inconnu.nlp.utils import EntityLabel, create_ner_component


class SpacyModels(StrEnum):
    # 'en_core_web_trf' is the most accurate model for name entity recognition
    EN_CORE_WEB_TRF = "en_core_web_trf"
    EN_CORE_WEB_SM = "en_core_web_sm"


# Patterns and labels for custom NER components
custom_patterns_and_labels = [
    (PHONE_NUMBER_PATTERN_RE, EntityLabel.PHONE_NUMBER),
    (EMAIL_ADDRESS_PATTERN_RE, EntityLabel.EMAIL),
]


# Spacy pipeline for entity pseudonymization
class EntityPseudonymizer:
    __slots__ = ["nlp"]

    def __init__(self):
        # Disable everything except for NER
        self.nlp = load(
            SpacyModels.EN_CORE_WEB_SM,
            disable=[
                "attribute_ruler",
                "lemmatizer",
                "tok2vec",
                "tagger",
                "parser",
            ],
        )

        for pattern, label in custom_patterns_and_labels:
            custom_ner_component_name = create_ner_component(pattern, label)
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
