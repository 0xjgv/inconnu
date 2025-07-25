# https://github.com/Unstructured-IO/unstructured/blob/c27e0d0062a662ca377f4df9db3a9d9de26bfa55/unstructured/nlp/patterns.py
import re
from typing import Final

US_PHONE_NUMBERS_PATTERN = (
    r"(?:\+?(\d{1,3}))?[-. (]*(\d{3})?[-. )]*(\d{3})[-. ]*(\d{4})(?: *x(\d+))?\s*$"
)
US_PHONE_NUMBERS_RE = re.compile(US_PHONE_NUMBERS_PATTERN)

PHONE_NUMBER_PATTERN = r"\+\d{1,3} \d{1,4} \d{1,4}(\d{1,4})*"
PHONE_NUMBER_PATTERN_RE = re.compile(PHONE_NUMBER_PATTERN)

# NOTE(robinson) - Based on this regex from regex101. Regex was updated to run fast
# and avoid catastrophic backtracking
# ref: https://regex101.com/library/oR3jU1?page=673
US_CITY_STATE_ZIP_PATTERN = (
    r"(?i)\b(?:[A-Z][a-z.-]{1,15}[ ]?){1,5},\s?"
    r"(?:{Alabama|Alaska|Arizona|Arkansas|California|Colorado|Connecticut|Delaware|Florida"
    r"|Georgia|Hawaii|Idaho|Illinois|Indiana|Iowa|Kansas|Kentucky|Louisiana|Maine|Maryland"
    r"|Massachusetts|Michigan|Minnesota|Mississippi|Missouri|Montana|Nebraska|Nevada|"
    r"New[ ]Hampshire|New[ ]Jersey|New[ ]Mexico|New[ ]York|North[ ]Carolina|North[ ]Dakota"
    r"|Ohio|Oklahoma|Oregon|Pennsylvania|Rhode[ ]Island|South[ ]Carolina|South[ ]Dakota"
    r"|Tennessee|Texas|Utah|Vermont|Virginia|Washington|West[ ]Virginia|Wisconsin|Wyoming}"
    r"|{AL|AK|AS|AZ|AR|CA|CO|CT|DE|DC|FM|FL|GA|GU|HI|ID|IL|IN|IA|KS|KY|LA|ME|MH|MD|MA|MI|MN"
    r"|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|MP|OH|OK|OR|PW|PA|PR|RI|SC|SD|TN|TX|UT|VT|VI|VA|"
    r"WA|WV|WI|WY})(, |\s)?(?:\b\d{5}(?:-\d{4})?\b)"
)
US_CITY_STATE_ZIP_RE = re.compile(US_CITY_STATE_ZIP_PATTERN)

UNICODE_BULLETS: Final[list[str]] = [
    "\u0095",
    "\u2022",
    "\u2023",
    "\u2043",
    "\u3164",
    "\u204c",
    "\u204d",
    "\u2219",
    "\u25cb",
    "\u25cf",
    "\u25d8",
    "\u25e6",
    "\u2619",
    "\u2765",
    "\u2767",
    "\u29be",
    "\u29bf",
    "\u002d",
    "",
    r"\*",
    "\x95",
    "·",
]
BULLETS_PATTERN = "|".join(UNICODE_BULLETS)
UNICODE_BULLETS_RE = re.compile(f"(?:{BULLETS_PATTERN})(?!{BULLETS_PATTERN})")
# zero-width positive lookahead so bullet characters will not be removed when using .split()
UNICODE_BULLETS_RE_0W = re.compile(f"(?={BULLETS_PATTERN})(?<!{BULLETS_PATTERN})")
E_BULLET_PATTERN = re.compile(r"^e(?=\s)", re.MULTILINE)

# NOTE(klaijan) - Captures reference of format [1] or [i] or [a] at any point in the line.
REFERENCE_PATTERN = r"\[(?:[\d]+|[a-z]|[ivxlcdm])\]"
REFERENCE_PATTERN_RE = re.compile(REFERENCE_PATTERN)

ENUMERATED_BULLETS_RE = re.compile(r"(?:(?:\d{1,3}|[a-z][A-Z])\.?){1,3}")

EMAIL_HEAD_PATTERN = (
    r"(MIME-Version: 1.0(.*)?\n)?Date:.*\nMessage-ID:.*\nSubject:.*\nFrom:.*\nTo:.*"
)
EMAIL_HEAD_RE = re.compile(EMAIL_HEAD_PATTERN)

IBAN_PATTERN = r"\b[A-Z]{2}\d{2}(?:[ -]?[A-Z0-9]{1,4}){1,7}\b"
IBAN_PATTERN_RE = re.compile(IBAN_PATTERN)

# Helps split text by paragraphs. There must be one newline, with potential whitespace
# (incluing \r and \n chars) on either side
PARAGRAPH_PATTERN = r"\s*\n\s*"

PARAGRAPH_PATTERN_RE = re.compile(
    f"((?:{BULLETS_PATTERN})|{PARAGRAPH_PATTERN})(?!{BULLETS_PATTERN}|$)",
)
DOUBLE_PARAGRAPH_PATTERN_RE = re.compile("(" + PARAGRAPH_PATTERN + "){2}")

# Captures all new line \n and keeps the \n as its own element,
# considers \n\n as two separate elements
LINE_BREAK = r"(?<=\n)"
LINE_BREAK_RE = re.compile(LINE_BREAK)

# NOTE(klaijan) - captures a line that does not ends with period (.)
ONE_LINE_BREAK_PARAGRAPH_PATTERN = r"^(?:(?!\.\s*$).)*$"
ONE_LINE_BREAK_PARAGRAPH_PATTERN_RE = re.compile(ONE_LINE_BREAK_PARAGRAPH_PATTERN)

# IP Address examples: ba23::58b5:2236:45g2:88h2 or 10.0.2.01
IP_ADDRESS_PATTERN = (
    r"[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}",
    "[a-z0-9]{4}::[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}:[a-z0-9]{4}%?[0-9]*",
)
IP_ADDRESS_PATTERN_RE = re.compile(f"({'|'.join(IP_ADDRESS_PATTERN)})")

IP_ADDRESS_NAME_PATTERN = r"[a-zA-Z0-9-]*\.[a-zA-Z]*\.[a-zA-Z]*"

# Mapi ID example: 32.88.5467.123
MAPI_ID_PATTERN = r"[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*;"

# Date, time, timezone example: Fri, 26 Mar 2021 11:04:09 +1200
EMAIL_DATETIMETZ_PATTERN = (
    r"[A-Za-z]{3},\s\d{1,2}\s[A-Za-z]{3}\s\d{4}\s\d{2}:\d{2}:\d{2}\s[+-]\d{4}"
)
EMAIL_DATETIMETZ_PATTERN_RE = re.compile(EMAIL_DATETIMETZ_PATTERN)

EMAIL_ADDRESS_PATTERN = r"[a-z0-9\.\-+_]+@[a-z0-9\.\-+_]+\.[a-z]+"
EMAIL_ADDRESS_PATTERN_RE = re.compile(EMAIL_ADDRESS_PATTERN)

ENDS_IN_PUNCT_PATTERN = r"[^\w\s]\Z"
ENDS_IN_PUNCT_RE = re.compile(ENDS_IN_PUNCT_PATTERN)

# NOTE(robinson) - Used to detect if text is in the expected "list of dicts"
# format for document elements
LIST_OF_DICTS_PATTERN = r"\A\s*\[\s*{?"

# (?s) dot all (including newline characters)
# \{(?=.*:) opening brace and at least one colon
# .*? any characters (non-greedy)
# (?:\}|$) non-capturing group that matches either the closing brace } or the end of
# the string to handle cases where the JSON is cut off
# | or
# \[(?s:.*?)\] matches the opening bracket [ in a JSON array and any characters inside the array
# (?:$|,|\]) non-capturing group that matches either the end of the string, a comma,
# or the closing bracket to handle cases where the JSON array is cut off
JSON_PATTERN = r"(?s)\{(?=.*:).*?(?:\}|$)|\[(?s:.*?)\](?:$|,|\])"

# taken from https://stackoverflow.com/a/3845829/12406158
VALID_JSON_CHARACTERS = r"[,:{}\[\]0-9.\-+Eaeflnr-u \n\r\t]"

IMAGE_URL_PATTERN = (
    r"(?i)https?://"
    r"(?:[a-z0-9$_@.&+!*\\(\\),%-])+"
    r"(?:/[a-z0-9$_@.&+!*\\(\\),%-]*)*"
    r"\.(?:jpg|jpeg|png|gif|bmp|heic)"
)

# NOTE(klaijan) - only supports one level numbered list for now
# e.g. 1. 2. 3. or 1) 2) 3), not 1.1 1.2 1.3
NUMBERED_LIST_PATTERN = r"^\d+(\.|\))\s(.+)"
NUMBERED_LIST_RE = re.compile(NUMBERED_LIST_PATTERN)

# ===========================================================================
# HEALTHCARE PATTERNS
# ===========================================================================

# Social Security Number (SSN) - US Format: XXX-XX-XXXX
SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
SSN_PATTERN_RE = re.compile(SSN_PATTERN)

# Medical Record Number (MRN) - Common formats: MRN: XXXXXX to XXXXXXXXXX
MRN_PATTERN = r"\b(?:MRN:?\s*)?\d{6,10}\b"
MRN_PATTERN_RE = re.compile(MRN_PATTERN)

# National Provider Identifier (NPI) - 10 digits
NPI_PATTERN = r"\b\d{10}\b(?!\-|\d)"
NPI_PATTERN_RE = re.compile(NPI_PATTERN)

# DEA Number - Format: 2 letters followed by 7 digits
DEA_NUMBER_PATTERN = r"\b[A-Z]{2}\d{7}\b"
DEA_NUMBER_PATTERN_RE = re.compile(DEA_NUMBER_PATTERN)

# ICD Codes - ICD-10 format: Letter followed by digits with optional decimal
ICD_CODE_PATTERN = r"\b[A-Z]\d{2}\.?\d{0,3}\b"
ICD_CODE_PATTERN_RE = re.compile(ICD_CODE_PATTERN)

# Clinical Trial IDs - NCT followed by 8 digits
TRIAL_ID_PATTERN = r"\bNCT\d{8}\b"
TRIAL_ID_PATTERN_RE = re.compile(TRIAL_ID_PATTERN)

# Participant/Subject IDs
PARTICIPANT_ID_PATTERN = r"\b[P][-_]?\d{4}[-_]?\d{3}\b"
PARTICIPANT_ID_PATTERN_RE = re.compile(PARTICIPANT_ID_PATTERN)

# Study IDs
STUDY_ID_PATTERN = r"\b(?:Study\s*ID\s*)?\d{4}-[A-Z]-\d{3}\b"
STUDY_ID_PATTERN_RE = re.compile(STUDY_ID_PATTERN)

# ===========================================================================
# LEGAL PATTERNS
# ===========================================================================

# Case Numbers - Format: YYYY-XX-XXXXXX
CASE_NUMBER_PATTERN = r"\b\d{4}-[A-Z]{2}-\d{4,6}\b"
CASE_NUMBER_PATTERN_RE = re.compile(CASE_NUMBER_PATTERN)

# Bar Numbers - State Bar Numbers
BAR_NUMBER_PATTERN = r"\b(?:Bar No\.|State Bar No:?)\s*[A-Z]{2}-?\d{5,6}\b"
BAR_NUMBER_PATTERN_RE = re.compile(BAR_NUMBER_PATTERN)

# Legal Citations - US Code and CFR
LEGAL_CITATION_PATTERN = (
    r"\b\d+\s+(?:U\.S\.C\.|C\.F\.R\.)\s+[§\u00A7]?\s*\d+[a-z]?(?:\.\d+)?(?:\([a-z]\))?"
)
LEGAL_CITATION_PATTERN_RE = re.compile(LEGAL_CITATION_PATTERN)

# ===========================================================================
# FINANCIAL PATTERNS
# ===========================================================================

# Credit Card Numbers - 16 digits with optional separators
CREDIT_CARD_PATTERN = r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"
CREDIT_CARD_PATTERN_RE = re.compile(CREDIT_CARD_PATTERN)

# SWIFT Codes - 8 or 11 characters
SWIFT_CODE_PATTERN = r"\b[A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?\b"
SWIFT_CODE_PATTERN_RE = re.compile(SWIFT_CODE_PATTERN)

# Routing Numbers - 9 digits
ROUTING_NUMBER_PATTERN = r"\b\d{9}\b(?!-|\d)"
ROUTING_NUMBER_PATTERN_RE = re.compile(ROUTING_NUMBER_PATTERN)

# Bitcoin Addresses
BITCOIN_ADDRESS_PATTERN = r"\b(?:bc1|[13])[a-zA-HJ-NP-Z0-9]{25,62}\b"
BITCOIN_ADDRESS_PATTERN_RE = re.compile(BITCOIN_ADDRESS_PATTERN)

# Ethereum Addresses
ETHEREUM_ADDRESS_PATTERN = r"\b0x[a-fA-F0-9]{40}\b"
ETHEREUM_ADDRESS_PATTERN_RE = re.compile(ETHEREUM_ADDRESS_PATTERN)

# Crypto Wallet (generic)
CRYPTO_WALLET_PATTERN = f"({BITCOIN_ADDRESS_PATTERN}|{ETHEREUM_ADDRESS_PATTERN})"
CRYPTO_WALLET_PATTERN_RE = re.compile(CRYPTO_WALLET_PATTERN)

# ===========================================================================
# HR/EMPLOYMENT PATTERNS
# ===========================================================================

# Employee IDs
EMPLOYEE_ID_PATTERN = r"\b(?:EMP-|EMPLOYEE\s*ID:?\s*)\d{5,8}\b"
EMPLOYEE_ID_PATTERN_RE = re.compile(EMPLOYEE_ID_PATTERN)

# Salary Patterns - with currency symbols and suffixes
SALARY_PATTERN = r"\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?[kKmM]?\b"
SALARY_PATTERN_RE = re.compile(SALARY_PATTERN)

# Department Codes
DEPARTMENT_CODE_PATTERN = r"\b(?:DEPT|Department)[-_]?[A-Z]{2,4}\b"
DEPARTMENT_CODE_PATTERN_RE = re.compile(DEPARTMENT_CODE_PATTERN)

# LinkedIn URLs
LINKEDIN_URL_PATTERN = r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+"
LINKEDIN_URL_PATTERN_RE = re.compile(LINKEDIN_URL_PATTERN)

# ===========================================================================
# CUSTOMER SUPPORT PATTERNS
# ===========================================================================

# Ticket Numbers - Format: #YYYY-MM-DD-XXXX
TICKET_NUMBER_PATTERN = r"#\d{4}-\d{2}-\d{2}-\d{4}\b"
TICKET_NUMBER_PATTERN_RE = re.compile(TICKET_NUMBER_PATTERN)

# Order Numbers
ORDER_NUMBER_PATTERN = r"\b(?:ORD|ORDER)[-_]?\d{4}[-_]?\d{4,6}\b"
ORDER_NUMBER_PATTERN_RE = re.compile(ORDER_NUMBER_PATTERN)

# Customer IDs
CUSTOMER_ID_PATTERN = r"\b(?:CUST|Customer\s*ID:?\s*)\d{6,10}\b"
CUSTOMER_ID_PATTERN_RE = re.compile(CUSTOMER_ID_PATTERN)

# Social Media Handles - Twitter/Instagram/etc @username
SOCIAL_MEDIA_HANDLE_PATTERN = r"@[a-zA-Z0-9_]{1,15}\b"
SOCIAL_MEDIA_HANDLE_PATTERN_RE = re.compile(SOCIAL_MEDIA_HANDLE_PATTERN)

# ===========================================================================
# EDUCATION PATTERNS
# ===========================================================================

# Student IDs
STUDENT_ID_PATTERN = r"\b[A-Z]{2,3}-\d{4}-\d{4}\b"
STUDENT_ID_PATTERN_RE = re.compile(STUDENT_ID_PATTERN)

# Course Codes
COURSE_CODE_PATTERN = r"\b[A-Z]{2,4}\s?\d{3}[A-Z]?\b"
COURSE_CODE_PATTERN_RE = re.compile(COURSE_CODE_PATTERN)

# GPA Patterns
GPA_PATTERN = r"\b\d\.\d{1,2}(?:/4\.0)?\b"
GPA_PATTERN_RE = re.compile(GPA_PATTERN)

# ===========================================================================
# RESEARCH PATTERNS
# ===========================================================================

# IRB Numbers
IRB_NUMBER_PATTERN = r"#?\d{4}-[A-Z]{3}-\d{3}\b"
IRB_NUMBER_PATTERN_RE = re.compile(IRB_NUMBER_PATTERN)

# Interview Timestamps
INTERVIEW_TIMESTAMP_PATTERN = r"\[\d{2}:\d{2}\]\b"
INTERVIEW_TIMESTAMP_PATTERN_RE = re.compile(INTERVIEW_TIMESTAMP_PATTERN)

# ===========================================================================
# GOVERNMENT PATTERNS
# ===========================================================================

# Passport Numbers - 1 letter followed by 8 digits (simplified)
PASSPORT_PATTERN = r"\b[A-Z]\d{8}\b"
PASSPORT_PATTERN_RE = re.compile(PASSPORT_PATTERN)

# Driver's License - State specific formats (simplified)
DRIVER_LICENSE_PATTERN = r"\b[A-Z]{1,2}\d{6,8}\b"
DRIVER_LICENSE_PATTERN_RE = re.compile(DRIVER_LICENSE_PATTERN)

# VIN Numbers - 17 characters
VIN_PATTERN = r"\b[A-HJ-NPR-Z0-9]{17}\b"
VIN_PATTERN_RE = re.compile(VIN_PATTERN)

# License Plates - Various formats
LICENSE_PLATE_PATTERN = r"\b[A-Z]{2,3}[-\s]?\d{3,4}[-\s]?[A-Z]{0,2}\b"
LICENSE_PLATE_PATTERN_RE = re.compile(LICENSE_PLATE_PATTERN)

# EIN (Employer Identification Number)
EIN_PATTERN = r"\b\d{2}-\d{7}\b"
EIN_PATTERN_RE = re.compile(EIN_PATTERN)

# ===========================================================================
# TECHNOLOGY PATTERNS
# ===========================================================================

# UUIDs
UUID_PATTERN = (
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b"
)
UUID_PATTERN_RE = re.compile(UUID_PATTERN, re.IGNORECASE)

# API Keys - Generic pattern
API_KEY_PATTERN = r"\b(?:api[_-]?key|apikey|access[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9]{32,})['\"]?\b"
API_KEY_PATTERN_RE = re.compile(API_KEY_PATTERN, re.IGNORECASE)

# MAC Addresses
MAC_ADDRESS_PATTERN = r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b"
MAC_ADDRESS_PATTERN_RE = re.compile(MAC_ADDRESS_PATTERN)

# Badge Numbers
BADGE_NUMBER_PATTERN = r"\b(?:Badge\s*#?\s*)\d{3,6}\b"
BADGE_NUMBER_PATTERN_RE = re.compile(BADGE_NUMBER_PATTERN)

# ===========================================================================
# PATTERN METADATA
# ===========================================================================

# Map patterns to their default priorities (used by entity resolution)
PATTERN_PRIORITIES = {
    "SSN": 9,
    "BADGE_NUMBER": 8,
    "TICKET_NUMBER": 7,
    "SWIFT_CODE": 7,
    "PASSPORT": 8,
    "DRIVER_LICENSE": 8,
    "VIN": 7,
    "CREDIT_CARD": 8,
    "ROUTING_NUMBER": 7,
    "CRYPTO_WALLET": 6,
    "STUDENT_ID": 6,
    "EMPLOYEE_ID": 6,
    "CASE_NUMBER": 7,
    "BAR_NUMBER": 7,
    "MRN": 8,
    "NPI": 8,
    "DEA_NUMBER": 8,
    "ICD_CODE": 6,
    "PARTICIPANT_ID": 6,
    "STUDY_ID": 6,
    "ORDER_NUMBER": 6,
    "CUSTOMER_ID": 5,
}

# Map patterns to their domains
PATTERN_DOMAINS = {
    "SSN": "healthcare",
    "MRN": "healthcare",
    "NPI": "healthcare",
    "DEA_NUMBER": "healthcare",
    "ICD_CODE": "healthcare",
    "TRIAL_ID": "healthcare",
    "PARTICIPANT_ID": "research",
    "STUDY_ID": "research",
    "CASE_NUMBER": "legal",
    "BAR_NUMBER": "legal",
    "LEGAL_CITATION": "legal",
    "CREDIT_CARD": "financial",
    "SWIFT_CODE": "financial",
    "ROUTING_NUMBER": "financial",
    "CRYPTO_WALLET": "financial",
    "EMPLOYEE_ID": "hr",
    "SALARY": "hr",
    "DEPARTMENT_CODE": "hr",
    "LINKEDIN_URL": "hr",
    "TICKET_NUMBER": "support",
    "ORDER_NUMBER": "support",
    "CUSTOMER_ID": "support",
    "SOCIAL_MEDIA_HANDLE": "support",
    "STUDENT_ID": "education",
    "COURSE_CODE": "education",
    "GPA": "education",
    "IRB_NUMBER": "research",
    "INTERVIEW_TIMESTAMP": "research",
    "PASSPORT": "government",
    "DRIVER_LICENSE": "government",
    "VIN": "government",
    "LICENSE_PLATE": "government",
    "EIN": "government",
    "UUID": "technology",
    "API_KEY": "technology",
    "MAC_ADDRESS": "technology",
    "BADGE_NUMBER": "technology",
}
