from spacy import load

from inconnu.config import Language, get_spacy_model
from inconnu.nlp.utils import (
    CUSTOM_NER_COMPONENTS,
    EntityLabel,
    create_ner_component,
    singleton,
)


# Spacy pipeline for entity pseudonymization
@singleton
class EntityPseudonymizer:
    def __init__(self, language: Language):
        # Disable everything except for NER
        self.nlp = load(
            get_spacy_model(language),
            disable=[
                "attribute_ruler",
                "lemmatizer",
                "tok2vec",
                "tagger",
                "parser",
            ],
        )

        for custom_ner_component in CUSTOM_NER_COMPONENTS:
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
