## dev: PII (n = gold spans)

| type | n | precision | recall | F1 | covered | 0.1.1 precision | 0.1.1 recall |
|---|---|---|---|---|---|---|---|
| EMAIL | 300 | 0.980 | 1.000 | 0.990 | 1.000 | 0.865 | 1.000 |
| PHONE | 300 | 0.993 | 0.930 | 0.960 | 0.930 | 0.658 | 0.897 |
| IBAN | 150 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 | 1.000 |
| CARD | 150 | 0.966 | 0.933 | 0.949 | 0.947 | - | 0.000 |
| SSN | 150 | 1.000 | 1.000 | 1.000 | 1.000 | - | 0.000 |
| IP | 150 | 0.980 | 1.000 | 0.990 | 1.000 | - | 0.000 |
| PERSON | 400 | 0.931 | 0.775 | 0.846 | 0.760 | 0.427 | 0.792 |
| PERSON (spaCy en_core_web_sm, raw) | 400 | 0.418 | 0.792 | 0.547 | 0.745 | | |
| PHONE (regex only, no phonenumbers) | 300 | 1.000 | 0.520 | 0.684 | 0.510 | | |

## dev: secrets by gold kind (recall = any SECRET prediction overlaps)

| kind | n | recall | covered | detect-secrets recall | 0.1.1 covered |
|---|---|---|---|---|---|
| anthropic-key | 50 | 1.000 | 1.000 | 0.180 | 0.060 |
| aws-access-key | 50 | 1.000 | 1.000 | 1.000 | 0.120 |
| basic-auth | 40 | 1.000 | 1.000 | 0.000 | 0.075 |
| bearer | 40 | 1.000 | 1.000 | 0.000 | 0.275 |
| discord-webhook | 50 | 1.000 | 1.000 | 0.100 | 0.180 |
| entropy | 240 | 0.971 | 0.971 | 0.117 | 0.354 |
| generic | 240 | 0.983 | 0.967 | 0.212 | 0.308 |
| github-token | 50 | 1.000 | 1.000 | 0.800 | 0.220 |
| gitlab-token | 50 | 1.000 | 1.000 | 1.000 | 0.220 |
| google-api-key | 50 | 1.000 | 1.000 | 0.200 | 0.200 |
| jwt | 50 | 1.000 | 1.000 | 1.000 | 0.320 |
| npm-token | 50 | 1.000 | 1.000 | 0.280 | 0.300 |
| openai-key | 50 | 1.000 | 1.000 | 0.680 | 0.040 |
| password-hash | 50 | 1.000 | 1.000 | 0.020 | 0.340 |
| private-key | 20 | 1.000 | 1.000 | 1.000 | 0.000 |
| pypi-token | 50 | 1.000 | 1.000 | 1.000 | 0.060 |
| sendgrid-key | 50 | 1.000 | 1.000 | 1.000 | 0.140 |
| slack-token | 50 | 1.000 | 1.000 | 1.000 | 0.360 |
| slack-webhook | 50 | 1.000 | 1.000 | 1.000 | 0.280 |
| stripe-key | 50 | 1.000 | 1.000 | 0.720 | 0.120 |
| url-password | 40 | 1.000 | 1.000 | 0.750 | 0.175 |

SECRET precision (all kinds): inconnu 0.985, detect-secrets 0.706

| predicted secret kind | n | precision |
|---|---|---|
| SECRET:anthropic-key | 50 | 1.000 |
| SECRET:aws-access-key | 50 | 1.000 |
| SECRET:basic-auth | 28 | 1.000 |
| SECRET:bearer | 40 | 1.000 |
| SECRET:discord-webhook | 50 | 1.000 |
| SECRET:entropy | 263 | 0.920 |
| SECRET:generic | 242 | 1.000 |
| SECRET:github-token | 50 | 1.000 |
| SECRET:gitlab-token | 50 | 1.000 |
| SECRET:google-api-key | 50 | 1.000 |
| SECRET:jwt | 50 | 1.000 |
| SECRET:npm-token | 50 | 1.000 |
| SECRET:openai-key | 50 | 1.000 |
| SECRET:password-hash | 50 | 1.000 |
| SECRET:private-key | 20 | 1.000 |
| SECRET:pypi-token | 50 | 1.000 |
| SECRET:sendgrid-key | 48 | 1.000 |
| SECRET:slack-token | 50 | 1.000 |
| SECRET:slack-webhook | 50 | 1.000 |
| SECRET:stripe-key | 50 | 1.000 |
| SECRET:url-password | 40 | 1.000 |

## dev: false-redaction rate on negatives (share of records with any redaction)

| category | inconnu | detect-secrets | 0.1.1 |
|---|---|---|---|
| neg:base64-in-code | 0.000 | 0.405 | 0.360 |
| neg:code | 0.000 | 0.000 | 0.385 |
| neg:company | 0.110 | 0.000 | 0.920 |
| neg:corgea-issue-field | 0.000 | 0.000 | 0.418 |
| neg:corgea-issue-json | 0.000 | 1.000 | 1.000 |
| neg:git-sha | 0.000 | 0.000 | 0.550 |
| neg:hash | 0.000 | 0.130 | 0.380 |
| neg:identifier | 0.000 | 0.000 | 0.135 |
| neg:log | 0.000 | 0.000 | 0.950 |
| neg:numeric-id | 0.025 | 0.000 | 0.975 |
| neg:path | 0.000 | 0.000 | 0.075 |
| neg:prose | 0.005 | 0.000 | 0.710 |
| neg:random-id | 0.105 | 0.030 | 0.325 |
| neg:real-stdlib-line | 0.005 | 0.000 | 0.290 |
| neg:real-uv-lock-line | 0.000 | 0.000 | 0.884 |
| neg:scan-row | 0.000 | 0.985 | 1.000 |
| neg:timestamp | 0.000 | 0.000 | 1.000 |
| neg:url | 0.000 | 0.000 | 0.435 |
| neg:uuid | 0.000 | 0.000 | 0.275 |
| neg:version | 0.000 | 0.000 | 0.605 |
| neg:vuln-id | 0.000 | 0.000 | 0.460 |
| **all negatives** | 0.011 | 0.065 | 0.528 |

inconnu FRR by detector: entropy 0.0043, ipaddress 0.0004, luhn 0.0010, names 0.0047, regex 0.0006

## latency (Python 3.14.10, arm64)

- per cell (<200 chars, n=7238): p50 13.3 µs, p99 101.3 µs, max 250.2 µs
- per KB (texts >= 64 chars, n=2163): p50 406.0 µs, p99 1133.6 µs
- 10k-cell batch: 0.2 s, 50018 cells/s, 2.2 MB/s
- inconnu 0.1.1 on the same records: inconnu-0.1.1 0.84 ms/record, spacy-sm-person 1.47 ms/record
