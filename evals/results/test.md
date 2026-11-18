## test: PII (n = gold spans)

| type | n | precision | recall | F1 | covered | 0.1.1 precision | 0.1.1 recall |
|---|---|---|---|---|---|---|---|
| EMAIL | 300 | 0.997 | 1.000 | 0.998 | 1.000 | 0.865 | 1.000 |
| PHONE | 300 | 0.996 | 0.937 | 0.966 | 0.937 | 0.651 | 0.927 |
| IBAN | 150 | 1.000 | 1.000 | 1.000 | 1.000 | 0.993 | 1.000 |
| CARD | 150 | 0.986 | 0.973 | 0.980 | 0.973 | - | 0.000 |
| SSN | 150 | 1.000 | 1.000 | 1.000 | 1.000 | - | 0.000 |
| IP | 150 | 1.000 | 1.000 | 1.000 | 1.000 | - | 0.000 |
| PERSON | 400 | 0.933 | 0.762 | 0.839 | 0.750 | 0.395 | 0.725 |
| PERSON (spaCy en_core_web_sm, raw) | 400 | 0.381 | 0.730 | 0.501 | 0.690 | | |
| PHONE (regex only, no phonenumbers) | 300 | 1.000 | 0.497 | 0.664 | 0.487 | | |

## test: secrets by gold kind (recall = any SECRET prediction overlaps)

| kind | n | recall | covered | detect-secrets recall | 0.1.1 covered |
|---|---|---|---|---|---|
| anthropic-key | 50 | 1.000 | 1.000 | 0.240 | 0.080 |
| aws-access-key | 50 | 1.000 | 1.000 | 1.000 | 0.280 |
| basic-auth | 40 | 1.000 | 1.000 | 0.000 | 0.000 |
| bearer | 40 | 1.000 | 1.000 | 0.000 | 0.225 |
| discord-webhook | 50 | 1.000 | 1.000 | 0.100 | 0.180 |
| entropy | 240 | 0.954 | 0.954 | 0.075 | 0.304 |
| generic | 240 | 0.988 | 0.983 | 0.196 | 0.342 |
| github-token | 50 | 1.000 | 1.000 | 0.840 | 0.220 |
| gitlab-token | 50 | 1.000 | 1.000 | 1.000 | 0.140 |
| google-api-key | 50 | 1.000 | 1.000 | 0.280 | 0.200 |
| jwt | 50 | 1.000 | 1.000 | 1.000 | 0.200 |
| npm-token | 50 | 1.000 | 1.000 | 0.220 | 0.260 |
| openai-key | 50 | 1.000 | 1.000 | 0.720 | 0.060 |
| password-hash | 50 | 1.000 | 1.000 | 0.020 | 0.280 |
| private-key | 20 | 1.000 | 1.000 | 1.000 | 0.000 |
| pypi-token | 50 | 1.000 | 1.000 | 1.000 | 0.100 |
| sendgrid-key | 50 | 1.000 | 1.000 | 1.000 | 0.320 |
| slack-token | 50 | 1.000 | 1.000 | 1.000 | 0.380 |
| slack-webhook | 50 | 1.000 | 1.000 | 1.000 | 0.220 |
| stripe-key | 50 | 1.000 | 1.000 | 0.700 | 0.240 |
| url-password | 40 | 1.000 | 1.000 | 0.775 | 0.150 |

SECRET precision (all kinds): inconnu 0.984, detect-secrets 0.695

| predicted secret kind | n | precision |
|---|---|---|
| SECRET:anthropic-key | 50 | 1.000 |
| SECRET:aws-access-key | 50 | 1.000 |
| SECRET:basic-auth | 35 | 1.000 |
| SECRET:bearer | 40 | 1.000 |
| SECRET:discord-webhook | 50 | 1.000 |
| SECRET:entropy | 272 | 0.919 |
| SECRET:generic | 222 | 1.000 |
| SECRET:github-token | 50 | 1.000 |
| SECRET:gitlab-token | 50 | 1.000 |
| SECRET:google-api-key | 50 | 1.000 |
| SECRET:jwt | 50 | 1.000 |
| SECRET:npm-token | 50 | 1.000 |
| SECRET:openai-key | 49 | 1.000 |
| SECRET:password-hash | 50 | 1.000 |
| SECRET:private-key | 20 | 1.000 |
| SECRET:pypi-token | 50 | 1.000 |
| SECRET:sendgrid-key | 50 | 1.000 |
| SECRET:slack-token | 50 | 1.000 |
| SECRET:slack-webhook | 50 | 1.000 |
| SECRET:stripe-key | 50 | 1.000 |
| SECRET:url-password | 40 | 1.000 |

## test: false-redaction rate on negatives (share of records with any redaction)

| category | inconnu | detect-secrets | 0.1.1 |
|---|---|---|---|
| neg:base64-in-code | 0.000 | 0.450 | 0.280 |
| neg:code | 0.000 | 0.000 | 0.395 |
| neg:company | 0.095 | 0.000 | 0.890 |
| neg:corgea-issue-field | 0.000 | 0.000 | 0.418 |
| neg:corgea-issue-json | 0.000 | 1.000 | 1.000 |
| neg:git-sha | 0.000 | 0.000 | 0.620 |
| neg:hash | 0.000 | 0.105 | 0.440 |
| neg:identifier | 0.000 | 0.000 | 0.110 |
| neg:log | 0.000 | 0.000 | 0.915 |
| neg:numeric-id | 0.010 | 0.000 | 0.970 |
| neg:path | 0.000 | 0.000 | 0.075 |
| neg:prose | 0.000 | 0.000 | 0.665 |
| neg:random-id | 0.110 | 0.030 | 0.360 |
| neg:real-stdlib-line | 0.003 | 0.000 | 0.269 |
| neg:real-uv-lock-line | 0.000 | 0.000 | 0.884 |
| neg:scan-row | 0.000 | 0.975 | 1.000 |
| neg:timestamp | 0.000 | 0.000 | 1.000 |
| neg:url | 0.000 | 0.000 | 0.405 |
| neg:uuid | 0.000 | 0.000 | 0.265 |
| neg:version | 0.000 | 0.000 | 0.575 |
| neg:vuln-id | 0.000 | 0.000 | 0.455 |
| **all negatives** | 0.009 | 0.065 | 0.519 |

inconnu FRR by detector: entropy 0.0045, luhn 0.0004, names 0.0043, phonenumbers 0.0002, regex 0.0002

## latency (Python 3.14.10, arm64)

- per cell (<200 chars, n=7256): p50 12.1 µs, p99 79.6 µs, max 198.0 µs
- per KB (texts >= 64 chars, n=2100): p50 363.9 µs, p99 1055.7 µs
- 10k-cell batch: 0.18 s, 55673 cells/s, 2.49 MB/s
- inconnu 0.1.1 on the same records: inconnu-0.1.1 1.33 ms/record, spacy-sm-person 2.13 ms/record
