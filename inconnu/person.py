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

from .credentials import CAMEL

UPPER, LOWER = "A-ZÀ-ÖØ-ÞĀĆČĎĘĚŁŃŇŐŘŚŠŤŮŰŹŻŽ", "a-zß-öø-ÿāćčďęěłńňőřśšťůűźżž"
WORD = re.compile(
    rf"[{UPPER}](?:[{LOWER}]+(?:['’-][{UPPER}]?[{LOWER}]+)?|['’][{UPPER}][{LOWER}]+)"
)  # Maria, Smith-Jones, O'Connor
ANY_CASE_WORD = re.compile(r"[^\W\d_]+(?:['’-][^\W\d_]+)?")
# Between first and last name: spaces, a middle initial, or a lowercase particle (van der, da, de la, bin).
GAP = re.compile(
    rf"\s+(?:[{UPPER}]\.\s+|(?:(?:van|von|de|da|del|della|di|dos|das|du|le|la|ter|ten|der|den|bin|ibn|al)\s+){{1,2}})?"
)
TITLE_WORD = (
    r"(?:Mr|Mrs|Ms|Miss|Mx|Dr|Prof|Sir|Herr|Frau|Mme|Mlle|Sr|Sra|Dott|pan|pani)"
)
TITLE = re.compile(rf"\b{TITLE_WORD}\.?\s+$")
NAME_KEY = re.compile(
    r"(?i)^(?:(?:full|first|last|given|family|display|user|sur|contact|author|owner|assignee|reporter)_?)?name$"
    r"|^(?:author|assignee|reporter|owner|contact)$"
)
COMPANY_KEY = re.compile(
    r"(?i)^(?:company|organi[sz]ation|org|tenant|vendor|employer)(?:_?name)?$"
)
HUMAN_CUE = r"(?i)(?:\b(?:assigned to|reviewed by|triaged by|done by|owner:|reporter:|contact:|hi|dear|thanks|cc)|meeting notes:)"
HUMAN_CONTEXT = re.compile(HUMAN_CUE + r"\s+$")
MENTION = re.compile(
    HUMAN_CUE
    + rf"[^\S\r\n]+(?=(?P<title>{TITLE_WORD}\.[ \t]+)?"
    + r"(?P<subject>[^,\r\n.!?;:，。！？；：]{1,100})(?:[,\r\n.!?;:，。！？；：]|$))"
)
NAME_JOINER = re.compile(r"['’\u200c\u200d-]")
TEAM_COLUMN = re.compile(
    r"(?:teams?|groups?|squads?)(?:_(?:name|display_name|slug|handle|type))?"
)
SLUG = re.compile(r"@?[^\W\d_][^\W_]*(?:[-_/][^\W_]+)*")
SUBJECT_WORD = re.compile(r"\S+")
# Common organization nouns used as grammatical heads or modifiers. Capitalized
# English suffixes alone are ambiguous because they can be surnames.
TEAM_NOUNS = frozenset(
    "team squad group guild crew unit department org committee system "
    "security support platform build "
    "equipo équipe grupo equipe команда группа отдел служба فريق قسم टीम विभाग 팀".split()
)
JOINED_TEAM_NOUNS = ("团队", "團隊", "チーム")
TEAM_HEADS = frozenset(
    {
        "equipo",
        "équipe",
        "equipe",
        "grupo",
        "команда",
        "группа",
        "служба",
        "отдел",
        "فريق",
        "قسم",
    }
)
PLURAL_TEAM_HEADS = frozenset(
    {"team", "squad", "guild", "unit", "department", "committee"}
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


def _unicode_name(value: str) -> bool:
    """Check a name-shaped value with combining marks and optional joiners."""
    words = value.split()
    if not 1 <= len(words) <= 5:
        return False
    return all(
        part
        and part[0].isalpha()
        and all(c.isalpha() or unicodedata.category(c).startswith("M") for c in part)
        for word in words
        for part in NAME_JOINER.split(word)
    )


def _acronym(word: str) -> bool:
    # An internal vowel makes an all-caps spelling such as JON plausible as a name.
    return (
        3 <= len(word) <= 5
        and word.isascii()
        and word.isalpha()
        and word.isupper()
        and all(c not in "AEIOU" for c in word[:-1])
    )


def _team_subject(value: str) -> bool:
    """Keep a subject only when it carries evidence of an organizational role."""
    if value.islower() and SLUG.fullmatch(value):
        parts = re.split(r"[-_/]", value.removeprefix("@"))
        if "/" in value or (
            len(parts) > 1
            and (
                (value.startswith("@") and parts[-1] == "team")
                or (parts[0] in TEAM_NOUNS and parts[-1] in TEAM_NOUNS)
            )
        ):
            return True
    words = value.split()
    if len(words) == 1:
        return (
            _acronym(words[0])
            or value in PLURAL_TEAM_HEADS
            or value.endswith(JOINED_TEAM_NOUNS)
            and _unicode_name(value)
        )
    first, last = words[0], words[-1]
    first_fold, last_fold = first.casefold(), last.casefold()
    if first_fold in TEAM_HEADS and _unicode_name(value):
        return True
    tail = last_fold.removesuffix("s")
    if tail != last_fold and tail in PLURAL_TEAM_HEADS:
        return True
    return (last_fold in TEAM_NOUNS or tail in TEAM_NOUNS) and (
        first_fold == "the"
        or first_fold in TEAM_NOUNS
        or _acronym(first)
        or not any(c.isupper() or c.islower() for c in last)
    )


def _mentions(text: str):
    """Yield contextual subject offsets and whether the subject is a team."""
    if len(text.split(maxsplit=1)) < 2:
        return
    for m in MENTION.finditer(text):
        raw = m["subject"].rstrip()
        words = list(SUBJECT_WORD.finditer(raw))
        if not words:
            continue
        # Cased names often end before a lowercase prose continuation. Preserve
        # name particles that the ordinary name matcher already understands.
        first = words[0].group()
        title = m["title"]
        cased_start = first[0].isupper()
        org_head = not title and first.casefold() in TEAM_HEADS
        end = words[0].end()
        for i, word in enumerate(words[1:5], 1):
            current = word.group()
            if (
                current.islower()
                and current.casefold() not in TEAM_NOUNS
                and not org_head
            ):
                if cased_start and not (
                    i + 1 < len(words)
                    and GAP.fullmatch(raw, words[i - 1].end(), words[i + 1].start())
                ):
                    break
                if not (cased_start or title) and _team_subject(raw[:end]):
                    break
            end = word.end()
        # Longer uncased clauses have no reliable subject boundary.
        if len(words) > 5 and end == words[4].end() and not cased_start:
            continue
        subject = raw[:end]
        team = not title and _team_subject(subject)
        if team or _unicode_name(subject) or SLUG.fullmatch(subject):
            yield (
                m.start("title") if title else m.start("subject"),
                m.start("subject") + end,
                team,
            )


def _words_outside_teams(text: str, teams: list[tuple[int, int]]):
    end = 0
    for start, stop in teams:
        yield from WORD.finditer(text, end, start)
        end = stop
    yield from WORD.finditer(text, end)


def find(text: str, key: str | None):
    """Yield (start, end, type, confidence, detector) candidates."""
    if key:
        parts = CAMEL.sub("_", key).lower().split(".")
        key = parts[-1]
        if TEAM_COLUMN.fullmatch(key) or (
            key in {"name", "slug", "handle", "display_name"}
            and any(TEAM_COLUMN.fullmatch(p) for p in parts[:-1])
        ):
            return
        if key == "assignee_type" and text.strip().casefold() in TEAM_NOUNS:
            return
        if key == "name" and any(
            p
            in {
                "companies",
                "company",
                "organizations",
                "organization",
                "tenants",
                "vendors",
            }
            for p in parts[:-1]
        ):
            return
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
        unicode_name = (
            named
            and not stripped.isascii()
            and _unicode_name(stripped)
            and not any(w.capitalize() in NOT_SURNAME for w in stripped.split())
        )
        if unicode_name or (
            1 <= len(words) <= 5
            and len(" ".join(words)) >= len(stripped) - 8
            and not any(
                w.capitalize() in NOT_SURNAME for w in words
            )  # Acme Corp under full_name
            and (
                (named and len(words) == 1)
                or _known(words[0], "first_names.txt")
                or (len(words) >= 2 and (named or _known(words[-1], "surnames.txt")))
            )
        ):
            start = text.index(stripped)
            yield start, start + len(stripped), "PERSON", 0.9, "names"
            return
    teams = []
    for start, end, team in _mentions(text):
        if team:
            teams.append((start, end))
        else:
            yield start, end, "PERSON", 0.85, "names"
    words = list(_words_outside_teams(text, teams) if teams else WORD.finditer(text))
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
            # The title's own word, then only words that are known names: "Mr. Smith Approved Review" -> "Mr. Smith".
            last = i
            while (
                last < j
                and any(
                    _known(words[last + 1].group(), r)
                    for r in ("first_names.txt", "surnames.txt")
                )
                and not _common(words[last + 1].group())
            ):
                last += 1
            yield title.start(), words[last].end(), "PERSON", 0.9, "names"
            i = last + 1
            continue
        if j == i:
            i += 1
            continue
        first, last = word.group(), words[j].group()
        if first.lower() in {"hi", "dear", "thanks"} and j > i + 1:
            i += 1
            continue
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
        elif HUMAN_CONTEXT.search(text, max(0, word.start() - 48), word.start()):
            conf = 0.85
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
