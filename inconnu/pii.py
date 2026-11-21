"""PII detectors: regex candidates confirmed by validators (Luhn, IBAN mod-97, ipaddress, phonenumbers)."""

from __future__ import annotations

import ipaddress
import re
from functools import lru_cache

from phonenumbers import (
    NumberParseException,
    is_possible_number,
    is_valid_number,
    parse,
)

from .credentials import url_password_candidates

EMAIL = re.compile(
    r"(?<![\w.%+/-])[\w.%+-]{1,64}@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,24}\b"
)
# A plus or 00 prefix, then digit groups split by one separator each; contiguous runs only after a prefix.
PHONE = re.compile(
    r"(?<![\w+/.:-])(?:(?:\+|00)\d{1,4}[ .-]?(?:\(\d{1,5}\)[ .-]?)?\d{1,12}(?:[ .-]\d{1,10}){0,5}"
    r"|\(\d{1,5}\)[ .-]?\d{3,10}(?:[ .-]\d{1,10}){0,4}|\d{1,5}(?:[ .-]\d{1,10}){1,5}|0\d{8,11})"
    r"(?:\s?(?:x|ext\.?)\s?\d{1,6})?(?![\w/:-]|\.\d)"
)
EXTENSION = re.compile(r"\s?(?:x|ext\.?)\s?\d{1,6}$")
IBAN = re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]{4}){2,7}(?: ?[A-Z0-9]{1,4})?\b")
CARD = re.compile(r"(?<![\w.+-])\d(?:[ -]?\d){11,18}(?![\w-]|\.\d)")
SSN = re.compile(r"(?<![\d-])\d{3}-\d{2}-\d{4}(?![\d-])")
IPV4 = re.compile(r"(?<![\w.])(?:\d{1,3}\.){3}\d{1,3}(?![\w]|\.\d)")
IPV6 = re.compile(
    r"(?<![\w:.])(?:[0-9A-Fa-f]{0,4}:){2,7}(?:\d{1,3}(?:\.\d{1,3}){3}|[0-9A-Fa-f]{0,4})(?:%\w+)?(?![\w:]|\.\d)"
)
DIGITS = re.compile(r"\D")
DATE = re.compile(r"\d{4}([-./ ])\d{1,2}\1\d{1,2}|\d{1,2}([-./ ])\d{1,2}\2\d{2,4}")

PHONE_KEY = re.compile(r"(?i)(?:phone|mobile|cell|tel|fax|msisdn)")
_PHONE_FIELD = (
    r"(?:phone(?:[_ -]+number)?|mobile(?:[_ -]+(?:phone|number))?|"
    r"cell(?:[_ -]+phone)?|telephone|tel|fax|msisdn)"
)
PHONE_FIELD = re.compile(_PHONE_FIELD, re.IGNORECASE)
LABELED_PHONE = re.compile(
    rf"(?<![\w-]){_PHONE_FIELD}[ \t]*[:=][ \t]*"
    r"""["'`]?([0-9]{7,15})(?![\w-]|\.\d)""",
    re.IGNORECASE,
)
SSN_KEY = re.compile(r"(?i)(?:ssn|social_?security)")
CARD_KEY = re.compile(r"(?i)(?:card|ccn|\bpan\b|credit)")
# National formats that start with a trunk 0; US numbers are tried first.
NATIONAL_REGIONS = (
    "GB",
    "DE",
    "FR",
    "ES",
    "IT",
    "NL",
    "CH",
    "AT",
    "BE",
    "IE",
    "SE",
    "AU",
    "PL",
    "BR",
    "IN",
)
CARD_PREFIXES = (
    "4",
    "34",
    "37",
    "6011",
    "65",
    "35",
    "36",
    "38",
    "30",
    "62",
    "2131",
    "1800",
    "50",
    "56",
    "57",
    "58",
    "6304",
    "67",
)


def find(text: str, key: str | None):
    """Yield (start, end, type, confidence, detector) candidates."""
    digits = len(DIGITS.sub("", text))
    url_passwords = (
        [u.span("s") for u in url_password_candidates(text)] if "://" in text else []
    )
    for m in EMAIL.finditer(text) if "@" in text else ():
        local, domain = m.group().split("@", 1)
        remote = local == "git" and text[m.end() : m.end() + 1] == ":"
        if remote or re.match(r"\d+x\.", domain):  # git@host:org/repo, icon@2x.png
            continue
        if any(s < m.end() and m.start() < e for s, e in url_passwords):
            continue  # scheme://user:pass@host: the URL credential rule owns it
        yield m.start(), m.end(), "EMAIL", 0.95, "regex"
    for m in IPV4.finditer(text) if digits >= 4 and "." in text else ():
        conf = _ipv4(m.group())
        if conf:
            yield m.start(), m.end(), "IP", conf, "ipaddress"
    for m in IPV6.finditer(text) if text.count(":") >= 2 else ():
        groups = m.group().split("%")[0].split(":")
        if (len(groups) >= 4 or max(map(len, groups)) >= 3) and _ipv6(
            m.group()
        ):  # not slices like a[1::2]
            yield m.start(), m.end(), "IP", 0.9, "ipaddress"
    if digits < 7:  # every remaining type needs 7+ digits
        return
    for m in SSN.finditer(text):
        if _ssn(m.group()):
            yield m.start(), m.end(), "SSN", 0.9, "regex"
    for m in IBAN.finditer(text):
        if _iban(m.group()):
            yield m.start(), m.end(), "IBAN", 0.95, "mod97"
    card_key = bool(key and CARD_KEY.search(key))
    for m in CARD.finditer(text):
        conf = _card(m.group(), card_key)
        if conf:
            yield m.start(), m.end(), "CARD", conf, "luhn"
    phone_key = bool(key and PHONE_KEY.search(key))
    for m in PHONE.finditer(text):
        conf = _phone(m.group(), phone_key)
        if conf:
            yield m.start(), m.end(), "PHONE", conf, "phonenumbers"
    if ":" in text or "=" in text:
        for labeled in LABELED_PHONE.finditer(text):
            if conf := _phone(labeled.group(1), True):
                start, end = labeled.span(1)
                yield start, end, "PHONE", conf, "phonenumbers"
    stripped = text.strip()
    signed = stripped.startswith(("+", "-"))
    magnitude = stripped[1:] if signed else stripped
    if key and magnitude.isdigit():  # a bare number needs column context
        start = text.index(stripped)
        end = start + len(stripped)
        if phone_key and _phone(magnitude, True):
            yield start, end, "PHONE", 0.9, "phonenumbers"
        elif (
            len(magnitude) == 9
            and SSN_KEY.search(key)
            and _ssn(f"{magnitude[:3]}-{magnitude[3:5]}-{magnitude[5:]}")
        ):
            yield start, end, "SSN", 0.9, "regex"
        elif signed and card_key and (conf := _card(magnitude, True)):
            yield start, end, "CARD", conf, "luhn"


def _ipv4(value: str) -> float:
    try:
        ip = ipaddress.IPv4Address(value)
    except ValueError:
        return 0.0
    if (
        ip.is_loopback or ip.is_unspecified or value.startswith("255.")
    ):  # localhost, 0.0.0.0, netmasks
        return 0.0
    return 0.9


def _ipv6(value: str) -> bool:
    try:
        ip = ipaddress.IPv6Address(value)
    except ValueError:
        return False
    return not (ip.is_loopback or ip.is_unspecified)


def _ssn(value: str) -> bool:
    area, group, serial = value.split("-")
    return (
        area not in ("000", "666")
        and area[0] != "9"
        and group != "00"
        and serial != "0000"
    )


def _iban(value: str) -> bool:
    iban = value.replace(" ", "")
    if not 15 <= len(iban) <= 34:
        return False
    digits = "".join(str(int(c, 36)) for c in iban[4:] + iban[:4])
    return int(digits) % 97 == 1


def luhn(digits: str) -> bool:
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def _card(value: str, card_key: bool) -> float:
    digits = DIGITS.sub("", value)
    if not 12 <= len(digits) <= 19 or not luhn(digits) or len(set(digits)) < 2:
        return 0.0
    known = (
        digits.startswith(CARD_PREFIXES)
        or 51 <= int(digits[:2]) <= 55
        or 2221 <= int(digits[:4]) <= 2720
    )
    if not known:
        return 0.6 if card_key else 0.0
    grouped = value != digits  # 4111 1111 ... or 4111-1111-...
    if grouped or card_key:
        return 0.95
    return (
        0.6 if len(digits) <= 16 else 0.0
    )  # bare runs: uncertain; 17-19 digits are mostly snowflake IDs


@lru_cache(maxsize=4096)  # table columns repeat values
def _phone(value: str, phone_key: bool) -> float:
    value = EXTENSION.sub("", value)
    if DATE.fullmatch(value) or re.match(r"\(?\d(?:\D|$)", value):
        return (
            0.0  # dates, and ranges like 0-999999: national numbers open with 2+ digits
        )
    digits = DIGITS.sub("", value)
    if not 7 <= len(digits) <= 15:
        return 0.0
    if value.startswith(("+", "00")):
        try:
            number = parse("+" + value[2:] if value.startswith("00") else value, None)
        except NumberParseException:
            return 0.0
        if is_valid_number(number):
            return 0.95
        return 0.6 if is_possible_number(number) else 0.0
    if not phone_key and value.isdigit() and value[0] != "0":
        return 0.0  # bare digit runs are IDs, counts and timestamps; a trunk 0 marks a national number
    try:
        us = parse(value, "US")
    except NumberParseException:
        return 0.0
    if is_valid_number(us):
        return 0.9
    if digits[0] == "0" or not value.isdigit():
        for region in NATIONAL_REGIONS:
            try:
                if is_valid_number(parse(value, region)):
                    return 0.85
            except NumberParseException:
                continue
    if (
        len(digits) == 10
        and re.fullmatch(r"\(?\d{3}\)?[ .-]?\d{3}[ .-]\d{4}", value)
        and is_possible_number(us)
    ):
        return 0.6  # NANP shape outside allocated ranges (e.g. 555 numbers): uncertain
    return 0.7 if phone_key and is_possible_number(us) else 0.0
