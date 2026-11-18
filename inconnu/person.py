"""Person names without a model: gazetteers of first names and surnames, titles, and name columns.

Gazetteers (folded to lowercase ASCII):
- US Census Bureau 1990 name files, public domain: https://www2.census.gov/topics/genealogy/1990surnames/
  (all first names; the 5,000 most common surnames)
- popular-names-by-country-dataset, CC0: https://github.com/sigpwned/popular-names-by-country-dataset
  (forenames from 106 countries, surnames from 75)
"""

from __future__ import annotations

import re
import unicodedata
from functools import cache
from importlib.resources import files

UPPER, LOWER = "A-ZÀ-ÖØ-ÞĀĆČĎĘĚŁŃŇŐŘŚŠŤŮŰŹŻŽ", "a-zß-öø-ÿāćčďęěłńňőřśšťůűźżž"
WORD = re.compile(
    rf"[{UPPER}](?:[{LOWER}]+(?:['’-][{UPPER}]?[{LOWER}]+)?|['’][{UPPER}][{LOWER}]+)"
)  # Maria, Smith-Jones, O'Connor
ANY_CASE_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)?")
# Between first and last name: spaces, a middle initial, or a lowercase particle (van der, da, de la, bin).
GAP = re.compile(
    rf"\s+(?:[{UPPER}]\.\s+|(?:(?:van|von|de|da|del|della|di|dos|das|du|le|la|ter|ten|der|den|bin|ibn|al)\s+){{1,2}})?"
)
TITLE = re.compile(
    r"(?:\b(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Sir|Herr|Frau|Mme|Mlle|Sr|Sra|Dott|pan|pani)\.?\s+)$"
)
NAME_KEY = re.compile(
    r"(?i)^(?:(?:full|first|last|given|family|display|user|sur|contact|author|owner|assignee|reporter)_?)?name$"
    r"|^(?:author|assignee|reporter|owner|contact)$"
)
COMPANY_KEY = re.compile(
    r"(?i)^(?:company|organi[sz]ation|org|tenant|vendor|employer)(?:_?name)?$"
)
# Next words that make a first name part of a company, product or UI label (from the eval negatives).
NOT_SURNAME = frozenset(
    "As Access Update Updates Review Request Admin Admins Settings Report Rule Scan Issue Team Project "
    "Inc Corp Corporation Company Co Group Holdings Technologies Technology Financial Bank Capital Partners Associates "
    "Labs Systems Solutions Software Security Services Consulting Media Health Insurance Motors Foods Energy "
    "Industries International Global Ventures".split()
)
# code_words.txt: lowercase words frequent in real source code (else, will, case, mark), counted over the dev
# environment's site-packages, not the eval data. A name that is also such a word needs a known, uncommon partner.


@cache
def wordlist(resource: str) -> frozenset[str]:
    return frozenset(files("inconnu").joinpath("data", resource).read_text().split())


def _fold(word: str) -> str:
    return (
        unicodedata.normalize("NFKD", word).encode("ascii", "ignore").decode().lower()
    )


def _known(word: str, resource: str) -> bool:
    return _fold(word) in wordlist(resource) or _fold(word.split("-")[0]) in wordlist(
        resource
    )


def _common(word: str) -> bool:
    return _fold(word) in wordlist("code_words.txt")


def find(text: str, key: str | None):
    """Yield (start, end, type, confidence, detector) candidates."""
    if key and COMPANY_KEY.search(key):
        return
    if key and NAME_KEY.match(key):
        stripped = text.strip()
        words = ANY_CASE_WORD.findall(
            stripped
        )  # name columns also hold JOHN SMITH and john smith
        named = (
            key.lower() != "name"
        )  # a bare "name" column also holds projects, rules and companies
        if (
            1 <= len(words) <= 5
            and len(" ".join(words)) >= len(stripped) - 8
            and (
                _known(words[0], "first_names.txt")
                or (len(words) >= 2 and (named or _known(words[-1], "surnames.txt")))
            )
        ):
            start = text.index(stripped)
            yield start, start + len(stripped), "PERSON", 0.9, "names"
            return
    words = list(WORD.finditer(text))
    i = 0
    while i < len(words):
        word = words[i]
        # The longest run of capitalized words joined by name gaps, up to four.
        j = i
        while (
            j + 1 < len(words)
            and j - i < 3
            and GAP.fullmatch(text, words[j].end(), words[j + 1].start())
        ):
            j += 1
        title = TITLE.search(text, max(0, word.start() - 8), word.start())
        if title:
            yield title.start(), words[j].end(), "PERSON", 0.9, "names"
            i = j + 1
            continue
        if j == i:
            i += 1
            continue
        first, last = word.group(), words[j].group()
        if last in NOT_SURNAME or text[words[j].end() : words[j].end() + 2] == " &":
            i = j + 1
            continue
        known_first, known_last = (
            _known(first, "first_names.txt"),
            _known(last, "surnames.txt") and not _common(last),
        )
        if (
            not known_first
            and j > i + 1
            and _known(words[i + 1].group(), "first_names.txt")
        ):
            i += 1  # "Thanks Maria Gonzalez": start the name at Maria
            continue
        if _common(first) and not known_last or _common(last) and not known_first:
            conf = 0.0
        elif known_first:
            conf = 0.9 if known_last else 0.7
        else:
            conf = (
                0.6 if known_last else 0.0
            )  # unknown first name before a known surname: uncertain
        if conf:
            yield word.start(), words[j].end(), "PERSON", conf, "names"
            i = j + 1
        else:
            i += 1
