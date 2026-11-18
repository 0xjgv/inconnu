# Changelog

## 0.2.0 (unreleased)

A rewrite as a one-way PII and secrets redactor for query results that reach AI agents. Breaking.

Added
- `redact()`, `redact_batch()` and `redact_json()` with typed placeholders (`[EMAIL]`, `[PHONE]`, `[IBAN]`, `[CARD]`,
  `[SSN]`, `[IP]`, `[PERSON]`, `[SECRET:<kind>]`, `[SECRET:entropy]`) and findings without values.
- Secret rules for 19 provider and credential formats, secret-named key/value pairs, and an entropy detector for
  unknown secrets that leaves hashes, UUIDs, digests, paths and identifiers alone.
- Person names from first-name and surname gazetteers (US Census 1990, popular-names-by-country CC0) instead of spaCy.
- `inconnu` CLI: text or `--json` on stdin; fails closed with no stdout on error.
- Optional `Scorer` for the uncertain band (System One `noul` over TypeSafe, OpenRouter, Respan); off by default,
  fails closed, sends only masked shapes.
- `evals/`: labeled data generator, runner, baselines (inconnu 0.1.1, raw spaCy, detect-secrets) and results.

Removed
- `Inconnu`, `Config`, `ProcessedData`, `NERComponent`, the exceptions module, pseudonymization, `restore()` and
  `deanonymize()`: the redactor is one-way.
- spaCy and every language model, `inconnu-download`, custom NER components and multilingual pipelines: the
  gazetteer heuristic scored F1 0.84 on PERSON against 0.50 for spaCy `en_core_web_sm` (evals/results/test.md).
- Healthcare, legal, education, HR and support patterns (MRN, NPI, DEA, ICD, case and student numbers and more),
  text-structure regexes, async helpers, examples and the notebook.
- Bitbucket pipeline and its Corgea auto-fix script.

Changed
- `phonenumbers` replaced by `phonenumberslite` (same API, no geocoding data: 2.7 MB instead of 23 MB).
- Dependencies refreshed and locked with uv; development on Python 3.14, still supporting 3.10+.
