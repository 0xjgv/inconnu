# Inconnu

[![PyPI](https://img.shields.io/pypi/v/inconnu)](https://pypi.org/project/inconnu/)

Inconnu redacts PII and secrets from text and JSON, one way, fast enough to run on every query result an AI agent
sees. The core path is regular expressions, validators (Luhn, IBAN mod-97, `ipaddress`, `phonenumbers`) and the
standard library. It needs no model and no network.

```python
from inconnu import redact, redact_batch, redact_json

text, findings = redact(
    "Ping jane.doe@example.org or +1 415-555-2671 from 203.0.113.42"
)
# text     -> "Ping [EMAIL] or [PHONE] from [IP]"
# findings -> [{"type": "EMAIL", "start": 5, "end": 25, "confidence": 0.95, "detector": "regex"}, ...]
```

Findings carry the type, offsets into the input, a confidence and the detector. They never carry the value.

## Install

```bash
uv add inconnu        # or: pip install inconnu
```

Python 3.10 or newer. The only dependency is `phonenumberslite` (pure Python, 2.7 MB).

## API

- `redact(text, key=None, scorer=None) -> (redacted_text, findings)`. `key` is the column or JSON key the text came
  from; it lets a value be judged by its column (a `password` cell, a `phone` cell, a `request_id` cell).
- `redact_batch(cells, keys=None, scorer=None)` redacts many short texts, such as the cells of a query result, and
  asks the scorer (if any) once per distinct uncertain shape.
- `redact_json(data, scorer=None)` redacts every string, integer, integral float and dict key in a JSON value,
  keeping its structure. Dict keys are the context for their values. A dict with `rows` (lists) and `cols` or
  `columns` (names, or objects with a `name`) gives each cell its column name. Two keys that redact to the same
  placeholder become `[EMAIL]` and `[EMAIL] (2)`.

## CLI

```bash
echo "mail jane.doe@example.org" | inconnu            # text in, text out
inconnu --json < result.json > redacted.json          # JSON in, JSON out
```

Exit 0 on success, 2 when `--json` input is not JSON, 1 on any other error. On failure nothing is written to
stdout and the error message never quotes the input, so a caller that forwards stdout cannot leak unredacted data.
A stdlib-only caller can run it as a subprocess: `subprocess.run(["inconnu", "--json"], input=..., capture_output=True)`.

## Placeholders

| Placeholder | Detects |
|---|---|
| `[EMAIL]` | email addresses |
| `[PHONE]` | phone numbers: international (+ or 00), or national formats valid for the US and 15 other regions |
| `[IBAN]` | IBANs that pass mod-97 |
| `[CARD]` | payment card numbers that pass Luhn with a known issuer prefix |
| `[SSN]` | US Social Security numbers |
| `[IP]` | IPv4 and IPv6 addresses (not loopback, 0.0.0.0 or netmasks) |
| `[PERSON]` | person names: first-name and surname gazetteers, titles (Mr., Dr.), name columns |
| `[SECRET:<kind>]` | `aws-access-key`, `github-token`, `gitlab-token`, `anthropic-key`, `openai-key`, `slack-token`, `slack-webhook`, `discord-webhook`, `stripe-key`, `google-api-key`, `npm-token`, `pypi-token`, `sendgrid-key`, `jwt`, `private-key`, `password-hash`, `url-password`, `bearer`, `basic-auth`, and `generic` for values of secret-named keys (`password=`, `client_secret:`, `"apiKey": ...`) |
| `[SECRET:entropy]` | unknown secrets: long tokens that look random for their charset |

The entropy detector leaves alone UUIDs, git SHAs and other hex hashes (unless a secret-like key is next to them),
digests (`sha256:`, `sha512-`), data URIs, public SSH keys, base64-encoded sentences, identifiers, paths, wheel tags,
and values under ID-like keys (`request_id`, `etag`, `checksum`). Company names are not redacted on purpose; names of
companies that are also person names (Morgan Stanley) can be.

## Confidence and the optional scorer

Every candidate gets a confidence. Below 0.5 it is dropped; at 0.8 or above it is redacted. In between (a bare
word under `PASSWORD=`, a random token with no key nearby, a 16-digit run that passes Luhn, a name with an unknown
first name) it is redacted unless a `Scorer` says it may stay.

```python
from inconnu import Scorer, redact

redact(text, scorer=Scorer())  # or: INCONNU_SCORER=1 inconnu ...
```

The scorer is off by default. It asks a System One `noul` question over the provider chain used by
[s1r](https://github.com/0xjgv/s1r): TypeSafe Jev, then OpenRouter, then Respan (keys `TYPESAFE_API_KEY`,
`OPENROUTER_API_KEY`, `RESPAN_API_KEY`), 8 s per request and an 8 s budget per batch. It fails closed: an error, a
timeout, a missing key or a spent budget means redact. It never sends a value: only the type, length, character
classes, entropy, a masked shape (`(999) 999-9999`, or the first four characters as `Aa9-` for secrets) and the key
or column name.

## Evals

`make eval` generates labeled data (synthetic positives for every type; negatives shaped like Corgea data plus real
standard-library and `uv.lock` lines), scores inconnu, detect-secrets and a regex-only phone detector, prints the
tables and writes `evals/results/`. `make eval-baseline` adds inconnu 0.1.1 and raw spaCy `en_core_web_sm` PERSON
entities, run in their own venv. `make eval-scorer` checks the scorer live on the dev split (at most 120 calls).
Thresholds and allowlists were tuned on the dev split; the numbers below are the held-out test split
(`evals/results/test.md`).

| type | precision | recall | 0.1.1 precision | 0.1.1 recall |
|---|---|---|---|---|
| EMAIL | 0.997 | 1.000 | 0.865 | 1.000 |
| PHONE | 0.996 | 0.937 | 0.651 | 0.927 |
| IBAN | 1.000 | 1.000 | 0.993 | 1.000 |
| CARD | 0.986 | 0.973 | - | 0.000 |
| SSN | 1.000 | 1.000 | - | 0.000 |
| IP | 1.000 | 1.000 | - | 0.000 |
| PERSON | 0.933 | 0.762 | 0.395 | 0.725 |
| PERSON, raw spaCy en_core_web_sm | 0.381 | 0.730 | | |
| SECRET (21 kinds, n=1370) | 0.984 | 0.990 | - | 0.239 (any label) |
| SECRET, detect-secrets 1.5 | 0.695 | 0.454 | | |

Lowest secret recall: entropy 0.954. False-redaction rate (share of negative records with any redaction, 21 categories): 0.009 (0.1.1: 0.519); the entropy detector alone: 0.004. Below 0.95 precision or 0.90 recall: PERSON (precision 0.933, recall 0.762: first names outside the gazetteers, and companies named after people) and SECRET:entropy precision (0.919: random request and object IDs with no key nearby look exactly like secrets, so they land in the uncertain band and are redacted).

Scorer, live on 120 of 246 distinct dev-band descriptions (0.23 s per call, 0 failures): at the 0.5 threshold it cleared 3 of 24 false positives and 0 of 118 true positives (`evals/results/scorer.json`).

Latency on Python 3.14.10 (arm64): p50 21.6 µs and p99 157.9 µs per cell under 200 characters; p50 654.7 µs and p99 1904.3 µs per KB; a 10k-cell batch in 0.291 s (34391 cells/s). inconnu 0.1.1 took 1.33 ms per record on the same data.

## Migrating from 0.1

0.2.0 is a rewrite. `Inconnu`, `Config`, pseudonymization and `restore()`, the spaCy pipeline, custom NER components,
the healthcare, legal and education patterns, async helpers and `inconnu-download` are gone. Use
`redact()` / `redact_batch()` / `redact_json()`. See [CHANGELOG.md](CHANGELOG.md).

## License

MIT. Name gazetteers: US Census Bureau 1990 name files (public domain) and
[popular-names-by-country-dataset](https://github.com/sigpwned/popular-names-by-country-dataset) (CC0).
