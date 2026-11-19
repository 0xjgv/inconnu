"""Generate labeled eval data: synthetic positives for every type and negatives shaped like Corgea data.

No real customer data. Secret values are random strings in each provider's documented format; formats follow the
gitleaks rule set (https://github.com/gitleaks/gitleaks/blob/master/config/gitleaks.toml) and the detect-secrets
plugins (https://github.com/Yelp/detect-secrets/tree/master/detect_secrets/plugins). Values are generated at run
time and never committed, so no secret-shaped string lands in git.

Usage: python evals/generate.py  (writes evals/data/{dev,test}.jsonl; dev tunes thresholds, test reports them)
"""

from __future__ import annotations

import base64
import json
import random
import string
import sysconfig
import uuid
from datetime import datetime
from pathlib import Path

from faker import Faker

ROOT = Path(__file__).parent
LOCALES = [
    "en_US",
    "en_GB",
    "de_DE",
    "fr_FR",
    "es_ES",
    "it_IT",
    "nl_NL",
    "pt_BR",
    "pl_PL",
    "en_IN",
]
B62 = string.ascii_letters + string.digits
B64 = B62 + "+/"
B64URL = B62 + "-_"
HEXD = "0123456789abcdef"
UPPER32 = string.ascii_uppercase + "234567"
WORDS = (
    "user account token auth session fetch handler request response config settings client server cache "
    "scan issue project branch commit report rule finding severity webhook payload event queue worker job "
    "retry timeout limit page count total item list map filter parse render update delete create get set "
    "validate login logout password secret key value id name email phone address file path line column"
).split()


def jwt_segment(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


class Gen:
    def __init__(self, seed: int):
        self.r = random.Random(seed)
        self.fakers = {loc: Faker(loc) for loc in LOCALES}
        for i, f in enumerate(self.fakers.values()):
            f.seed_instance(seed * 100 + i)
        self.en = self.fakers["en_US"]
        self.records: list[dict] = []

    def s(self, alphabet: str, n: int) -> str:
        return "".join(self.r.choice(alphabet) for _ in range(n))

    def when(self) -> datetime:
        """Faker's own dates end at now, which would make the data differ from day to day."""
        return self.en.date_time_between(datetime(2015, 1, 1), datetime(2026, 1, 1))

    def faker(self) -> Faker:
        return self.fakers[self.r.choice(LOCALES)]

    def add(
        self,
        category: str,
        template: str,
        value: str = "",
        label: str | None = None,
        kind: str | None = None,
        key: str | None = None,
        inner: tuple[int, int] | None = None,
    ):
        """template holds {v} once; inner limits the gold span to value[inner[0]:inner[1]]."""
        start = template.find("{v}")
        text = template.replace("{v}", value) if start >= 0 else template
        spans = []
        if label and start >= 0:
            a, b = inner or (0, len(value))
            spans.append(
                {
                    "type": label,
                    "kind": kind or label,
                    "start": start + a,
                    "end": start + b,
                }
            )
        self.records.append(
            {"category": category, "text": text, "key": key, "spans": spans}
        )

    # ---------- PII positives ----------

    def pii(self, n: int):
        cell = ["{v}", " {v} "]
        prose = [
            "Contact {v} for access.",
            "Escalated by {v} at 10:42 UTC.",
            "{v}",
            "owner: {v}",
            '{"reporter": "{v}", "severity": "high"}',
            "2024-11-02T10:22:31Z INFO notified {v} (scan finished)",
            "Please reach out to {v} about the SSO setup.",
            "| 42 | {v} | active |",
        ]
        for _ in range(n):
            f = self.faker()
            self.add("pos:EMAIL", self.r.choice(prose + cell), f.email(), "EMAIL")
            self.add(
                "pos:EMAIL",
                self.r.choice(prose),
                f.user_name() + "@" + f.domain_name(),
                "EMAIL",
            )
            self.add(
                "pos:PHONE", self.r.choice(prose + cell), f.phone_number(), "PHONE"
            )
            raw = f.phone_number().split("x")[0]
            digits = ("+" if raw.startswith("+") else "") + "".join(
                c for c in raw if c.isdigit()
            )
            self.add(
                "pos:PHONE",
                "{v}",
                digits,
                "PHONE",
                key=self.r.choice(["phone", "phone_number", "mobile"]),
            )
            iban = f.iban()
            if self.r.random() < 0.5:
                iban = " ".join(iban[i : i + 4] for i in range(0, len(iban), 4))
            self.add(
                "pos:IBAN",
                self.r.choice(
                    ["IBAN: {v}", "{v}", "Refund to {v} by Friday", "iban={v}"]
                ),
                iban,
                "IBAN",
            )
            card = self.en.credit_card_number()
            if self.r.random() < 0.5 and len(card) == 16:
                card = self.r.choice([" ", "-"]).join(
                    card[i : i + 4] for i in range(0, 16, 4)
                )
            self.add(
                "pos:CARD",
                self.r.choice(
                    ["card {v} exp 12/29", "{v}", "Paid with {v}.", "pan={v}"]
                ),
                card,
                "CARD",
                key=self.r.choice([None, "card_number"]),
            )
            self.add(
                "pos:SSN",
                self.r.choice(["SSN {v}", "{v}", "ssn: {v}", "Employee SSN is {v}."]),
                self.en.ssn(),
                "SSN",
            )
            ip = self.r.choice(
                [self.en.ipv4_public(), self.en.ipv4_private(), self.en.ipv6()]
            )
            self.add(
                "pos:IP",
                self.r.choice(
                    [
                        "from {v}",
                        "{v}",
                        "client_ip={v} status=200",
                        "Login from {v} blocked",
                    ]
                ),
                ip,
                "IP",
            )

    def persons(self, n: int):
        prose = [
            "Assigned to {v} yesterday.",
            "{v} approved the fix.",
            "Reviewed by {v} on 2024-10-11.",
            "Hi {v}, your scan finished.",
            "The triage was done by {v} and closed.",
            "cc {v}",
            "Thanks {v} for the report!",
            "{v} (Security Lead) asked for an export.",
            "Owner: {v}",
            "Meeting notes: {v} will rotate the keys.",
        ]
        for _ in range(n):
            f = self.faker()
            name = (
                f"{f.first_name()} {f.last_name()}"
                if self.r.random() < 0.8
                else f.name()
            )
            self.add("pos:PERSON", self.r.choice(prose), name, "PERSON")
        for _ in range(n // 3):
            f = self.faker()
            self.add(
                "pos:PERSON",
                "{v}",
                f"{f.first_name()} {f.last_name()}",
                "PERSON",
                key=self.r.choice(["full_name", "author", "name", "assignee"]),
            )

    # ---------- secret positives ----------

    def jwt(self) -> str:
        def enc(d):
            return (
                base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
            )

        head = enc({"alg": "HS256", "typ": "JWT"})
        body = enc(
            {
                "sub": str(self.r.randint(1, 10**6)),
                "iat": self.r.randint(16 * 10**8, 18 * 10**8),
                "role": "user",
            }
        )
        return f"{head}.{body}.{self.s(B64URL, 43)}"

    def pem(self) -> str:
        label = self.r.choice(
            ["RSA PRIVATE KEY", "PRIVATE KEY", "EC PRIVATE KEY", "OPENSSH PRIVATE KEY"]
        )
        body = "\n".join(self.s(B64, 64) for _ in range(self.r.randint(4, 12)))
        return f"-----BEGIN {label}-----\n{body}\n-----END {label}-----"

    def secrets(self, n: int):
        r, s = self.r, self.s
        kinds = {
            "aws-access-key": lambda: r.choice(["AKIA", "ASIA"]) + s(UPPER32, 16),
            "github-token": lambda: (
                r.choice(["ghp_", "gho_", "ghu_", "ghs_", "ghr_"]) + s(B62, 36)
                if r.random() < 0.7
                else "github_pat_" + s(B62, 22) + "_" + s(B62, 59)
            ),
            "gitlab-token": lambda: "glpat-" + s(B62 + "-_", 20),
            "anthropic-key": lambda: "sk-ant-api03-" + s(B64URL, 93) + "AA",
            "openai-key": lambda: (
                "sk-proj-" + s(B64URL, 74) + "T3BlbkFJ" + s(B64URL, 74)
                if r.random() < 0.6
                else "sk-" + s(B62, 20) + "T3BlbkFJ" + s(B62, 20)
            ),
            "slack-token": lambda: (
                r.choice(["xoxb-", "xoxp-"])
                + f"{r.randint(10**9, 10**12)}-{r.randint(10**9, 10**12)}-"
                + s(B62, 24)
            ),
            "slack-webhook": lambda: (
                "https://hooks.slack.com/services/T"
                + s(UPPER32, 8)
                + "/B"
                + s(UPPER32, 10)
                + "/"
                + s(B62, 24)
            ),
            "discord-webhook": lambda: (
                f"https://discord.com/api/webhooks/{r.randint(10**17, 10**18)}/"
                + s(B64URL, 68)
            ),
            "stripe-key": lambda: (
                r.choice(["sk_live_", "sk_test_", "rk_live_"])
                + s(B62, r.choice([24, 99]))
            ),
            "google-api-key": lambda: "AIza" + s(B64URL, 35),
            "npm-token": lambda: "npm_" + s(B62, 36),
            "pypi-token": lambda: "pypi-AgEIcHlwaS5vcmc" + s(B64URL, 70),
            "sendgrid-key": lambda: "SG." + s(B64URL, 22) + "." + s(B64URL, 43),
            "jwt": self.jwt,
            "password-hash": lambda: r.choice(
                [
                    "$2b$12$" + s(B62 + "./", 53),
                    "pbkdf2_sha256$600000$" + s(B62, 22) + "$" + s(B64, 43) + "=",
                    "$argon2id$v=19$m=65536,t=3,p=4$" + s(B64, 22) + "$" + s(B64, 43),
                ]
            ),
        }
        code = [
            'API_KEY = "{v}"',
            "export SERVICE_KEY={v}",
            "token: {v}",
            '{"credential": "{v}"}',
            "{v}",
            "Rotated {v} after the incident.",
            'curl -H "X-Api-Key: {v}" https://api.example.com/v1/items',
            "2024-11-02 10:22:31 DEBUG using key {v}",
            "config.set('auth', '{v}')",
        ]
        for kind, make in kinds.items():
            for _ in range(n):
                self.add(f"pos:SECRET:{kind}", r.choice(code), make(), "SECRET", kind)
            for _ in range(n // 4):
                self.add(
                    f"pos:SECRET:{kind}",
                    "{v}",
                    make(),
                    "SECRET",
                    kind,
                    key=r.choice(["value", "data", "notes"]),
                )
        for _ in range(n // 2):
            self.add(
                "pos:SECRET:private-key",
                r.choice(["{v}", "key_material = '''{v}'''", "{v}\n"]),
                self.pem(),
                "SECRET",
                "private-key",
            )
        # Credentials inside URLs: only the password is gold.
        for _ in range(n):
            f = self.faker()
            user, pw = (
                f.user_name(),
                f.password(length=r.randint(10, 20), special_chars=r.random() < 0.3),
            )
            scheme = r.choice(
                [
                    "postgres",
                    "postgresql",
                    "mysql",
                    "mongodb+srv",
                    "redis",
                    "amqp",
                    "https",
                ]
            )
            host = (
                f.domain_word()
                + "."
                + r.choice(["internal", "rds.amazonaws.com", "example.net"])
            )
            url = f"{scheme}://{user}:{pw}@{host}:{r.randint(1000, 9999)}/{f.word()}"
            a = len(scheme) + 3 + len(user) + 1
            self.add(
                "pos:SECRET:url-password",
                r.choice(["DATABASE_URL={v}", "{v}", "connecting to {v}"]),
                url,
                "SECRET",
                "url-password",
                inner=(a, a + len(pw)),
            )
        # Opaque bearer and basic credentials in headers: the token is gold.
        for _ in range(n):
            self.add(
                "pos:SECRET:bearer",
                "Authorization: Bearer {v}",
                s(B64URL, r.randint(24, 64)),
                "SECRET",
                "bearer",
            )
            basic = base64.b64encode(
                f"{self.en.user_name()}:{self.en.password()}".encode()
            ).decode()
            self.add(
                "pos:SECRET:basic-auth",
                "Authorization: Basic {v}",
                basic,
                "SECRET",
                "basic-auth",
            )
        # Passwords and secrets under secret-like keys, in code, env files, YAML and table cells.
        for _ in range(n * 3):
            f = self.faker()
            value = r.choice(
                [
                    f.password(length=r.randint(8, 20)),
                    s(B64, 40),
                    s(HEXD, 32),
                    f.password(length=12, special_chars=False),
                ]
            )
            key = r.choice(
                [
                    "password",
                    "DB_PASSWORD",
                    "client_secret",
                    "aws_secret_access_key",
                    "apiKey",
                    "auth_token",
                    "SECRET_KEY",
                    "smtp_pass",
                    "privateKey",
                    "webhook_secret",
                ]
            )
            template = r.choice(
                [
                    key + ' = "{v}"',
                    key + "={v}",
                    key + ": {v}",
                    '"' + key + '": "{v}"',
                    key + " := '{v}'",
                ]
            )
            self.add("pos:SECRET:generic", template, value, "SECRET", "generic")
            self.add("pos:SECRET:generic", "{v}", value, "SECRET", "generic", key=key)
        # Unknown secrets with no provider prefix and no key: the entropy detector's job.
        for _ in range(n * 3):
            value = r.choice(
                [
                    s(B62, r.randint(24, 48)),
                    s(B64, r.randint(28, 64)),
                    s(B64URL, r.randint(24, 48)),
                ]
            )
            self.add(
                "pos:SECRET:entropy",
                r.choice(
                    [
                        "{v}",
                        "Rotated {v} after the incident.",
                        "X-Internal-Auth: {v}",
                        '{"value": "{v}"}',
                        "use {v} for the staging tenant",
                    ]
                ),
                value,
                "SECRET",
                "entropy",
            )
            self.add(
                "pos:SECRET:entropy",
                r.choice(["the api key is {v}", "secret {v}", "token={v}"]),
                s(HEXD, r.choice([32, 40, 64])),
                "SECRET",
                "entropy",
            )

    def context_jwe(self, n: int):
        def encode(data: bytes) -> str:
            return base64.urlsafe_b64encode(data).decode().rstrip("=")

        for i in range(n):
            alg = "dir" if i % 2 else "RSA-OAEP"
            header = encode(json.dumps({"alg": alg, "enc": "A256GCM"}).encode())
            segments = [
                encode(self.r.randbytes(length))
                for length in (0 if alg == "dir" else 64, 12, 80, 16)
            ]
            self.add(
                "pos:context:jwe-direct"
                if alg == "dir"
                else "pos:context:jwe-wrapped-key",
                self.r.choice(["{v}", "received ({v})", "ciphertext: {v}."]),
                ".".join([header, *segments]),
                "SECRET",
                "jwe",
            )
            self.add("neg:context:jwe-version", f"build.2.{i}.1.7")
            self.add("neg:context:jwe-host", f"node-{i}.eu.prod.example.net")
            self.add("neg:context:jwe-id", f"tenant-{i}.repo.scan.finding.item")
            # Public binary fixture with the same segment lengths as the positive.
            public_header = encode(f"public fixture {i}".encode())
            self.add("neg:context:jwe-nonjson", ".".join([public_header, *segments]))

    # ---------- negatives ----------

    def context_urls(self, n: int):
        for i in range(n):
            value = self.s(B62, 8) + "%2Btail%3D"
            param = self.r.choice(
                ["token", "key", "sig", "access_token", "X-Amz-Signature", "api%5Fkey"]
            )
            self.add(
                "pos:context:url-query",
                f"https://service.example/hook?{param}={{v}}&page=2",
                value,
                "SECRET",
                "url-query",
            )
            self.add(
                "neg:context:url-query",
                f"https://github.com/acme/repo?ref=release-{i}&page=2&sort=updated&utm_source=mail",
            )
            scheme = self.r.choice(
                ["postgres", "postgresql", "mysql", "mongodb+srv", "redis", "amqp"]
            )
            # Password-only userinfo is common for Redis; >128-byte passwords expose the old regex cap.
            password = self.s(B62, 140) if i % 2 else "short-pass!"
            user = "" if i % 2 == 0 else "service"
            self.add(
                "pos:context:url-password",
                f"{scheme}://{user}:{{v}}@db.internal:5432/prod",
                password,
                "SECRET",
                "url-password",
            )
            self.add("neg:context:url-password", f"{scheme}://db.internal:5432/prod")
            self.add("neg:context:clone-url", "https://git.example/acme/repo.git")

    def context_cookies(self, n: int):
        for i in range(n):
            cookie = self.r.choice(
                [
                    "session",
                    "connect.sid",
                    "JSESSIONID",
                    "PHPSESSID",
                    "__Host-session",
                    "sessionid",
                ]
            )
            self.add(
                "pos:context:cookie",
                self.r.choice(
                    [
                        f"Cookie: theme=dark; {cookie}={{v}}; locale=en",
                        f"Set-Cookie: {cookie}={{v}}; Path=/; HttpOnly; Secure",
                    ]
                ),
                self.s(HEXD, 32),
                "SECRET",
                "cookie",
            )
            self.add(
                "neg:context:cookie",
                self.r.choice(
                    [
                        "Cookie: theme=dark; locale=en",
                        "Set-Cookie: theme=dark; Path=/; SameSite=Lax",
                        "session_count=42",
                        "cookie_policy=required",
                    ]
                ),
            )
            self.add(
                "pos:context:session-column",
                "{v}",
                self.s(HEXD, 32),
                "SECRET",
                "generic",
                key=self.r.choice(
                    [
                        "session",
                        "session_id",
                        "sessionId",
                        "connect.sid",
                        "users.session_token",
                    ]
                ),
            )
            self.add(
                "neg:context:session-column",
                "active",
                key=self.r.choice(["session_status", "session_type", "session_count"]),
            )

    def dev_json_envelopes(self, n: int):
        for i in range(n):
            public = self.r.choice(
                ['{"format":"json"}', '{"format": "json"}', '{ "format": "json" }']
            )
            self.add(
                "neg:limits:public-envelope",
                f"{jwt_segment(public)}.{jwt_segment('[]' if i % 2 else '{}')}.release_notes",
            )
            private = self.r.choice(
                [
                    json.dumps({"password": "violet47"}),
                    json.dumps({"format": "json", "v": [self.s(B64URL, 22)]}),
                    json.dumps({"\u5f20\u4f1f": 123456789}, ensure_ascii=False),
                    '{"pin":9}',
                    "  [123456789]",
                ]
            )
            self.add(
                "pos:limits:private-envelope",
                self.r.choice(["{v}", jwt_segment(public) + ".{v}.release_notes"]),
                jwt_segment(private),
                "SECRET",
                "entropy",
            )

    def context_jwt(self, n: int):
        for i in range(n):
            # Legal JSON whitespace changes the encoded prefix; a short payload is still a JWT.
            jwt = (
                jwt_segment('{ "alg": "HS256", "typ": "JWT" }')
                + "."
                + jwt_segment("{}")
                + "."
                + self.s(B64URL, 43)
            )
            self.add("pos:context:jwt", "{v}", jwt, "SECRET", "jwt")
            self.add(
                "neg:context:jwt",
                jwt_segment('{ "format": "json" }')
                + "."
                + jwt_segment("{}")
                + "."
                + "release_notes",
            )

    def dev_unicode_names(self, n: int):
        names = [
            "张伟",
            "佐藤 花子",
            "Мария Иванова",
            "محمد عبد الله",
            "अनन्या शर्मा",
            "ณัฐธิดา ศรีสวัสดิ์",
            "Νικόλαος Παπαδόπουλος",
        ]
        for i in range(n):
            name = names[i % len(names)]
            self.add(
                "pos:limits:unicode-name-column",
                "{v}",
                name,
                "PERSON",
                key=self.r.choice(["people.full_name", "reporterName", "assignee"]),
            )
            self.add(
                "pos:limits:unicode-mention",
                self.r.choice(
                    [
                        "Assigned to {v}.",
                        "Reviewed by {v}.",
                        "Contact: {v}, please review.",
                    ]
                ),
                name,
                "PERSON",
            )
            self.add(
                "neg:limits:unicode-company",
                self.r.choice(["株式会社", "सुरक्षा टीम", "Мария Иванова"]),
                key=self.r.choice(["company_name", "organizations.name"]),
            )
            self.add(
                "neg:limits:unicode-contextless",
                self.r.choice(["安全审查", "नया संदेश", "Москва", "مرحبا بالعالم"]),
            )
            self.add(
                "neg:limits:unicode-team-mention",
                "Assigned to {v}.",
                self.r.choice(["安全团队", "सुरक्षा टीम", "Служба Поддержки"]),
            )
        latin_teams = (
            ("Assigned to {v} yesterday.", "Security Team"),
            ("Reviewed by {v} today.", "Build System"),
            ("Hi {v}, your scan finished.", "@platform-team"),
            ("Reviewed by {v}.", "SRE Group"),
            ("Contact: {v}.", "SRE"),
            ("Assigned to {v}.", "sec/infra"),
            ("Assigned to {v} yesterday.", "the delivery guild"),
            ("Reviewed by {v}.", "Observability Squads"),
            ("Contact: {v}.", "platform-team"),
            ("Assigned to {v}.", "Equipo de seguridad"),
        )
        other_teams = (
            ("Contact: {v}。", "平台團隊"),
            ("Reviewed by {v}。", "運用チーム"),
            ("Assigned to {v}.", "Команда платформы"),
            ("Reviewed by {v}.", "فريق المراجعة"),
            ("Assigned to {v}.", "अनुसंधान विभाग"),
            ("Contact: {v}.", "보안 팀"),
        )
        surname_controls = (
            ("Assigned to {v} yesterday.", "Maya Group"),
            ("Reviewed by {v} today.", "Jordan Crew"),
            ("Hi {v}, your scan finished.", "Nora Team"),
            ("Contact: {v}.", "Juan Williams"),
            ("Reviewed by {v} today.", "ALICE CREW"),
            ("Reviewed by {v} today.", "JON Crew"),
            ("Contact: {v}.", "Morgan-Crew"),
            ("Assigned to {v}.", "Алина Группа"),
            ("Reviewed by {v}.", "Ольга Команда"),
            ("Reviewed by Dr. {v} today.", "Maya Crew"),
        )
        for i in range(n):
            template, name = latin_teams[i % len(latin_teams)]
            self.add("neg:limits:latin-team-mention", template, name)
            template, name = other_teams[i % len(other_teams)]
            self.add("neg:limits:additional-unicode-team-mention", template, name)
            template, name = surname_controls[i % len(surname_controls)]
            self.add("pos:limits:team-like-surname", template, name, "PERSON")

    def context_person(self, n: int):
        for i in range(n):
            name = self.faker().first_name() + " " + self.faker().last_name()
            self.add(
                "pos:context:person",
                "{v}",
                name.lower(),
                "PERSON",
                key=self.r.choice(
                    ["users.full_name", "fullName", "firstName", "author_name"]
                ),
            )
            self.add(
                "pos:context:person-prose",
                self.r.choice(
                    [
                        "Assigned to {v} yesterday.",
                        "Reviewed by {v} today.",
                        "Hi {v}, your scan finished.",
                    ]
                ),
                name,
                "PERSON",
            )
            self.add(
                "neg:context:company",
                self.r.choice(["Morgan Stanley", "Charles Schwab", "Ralph Lauren"]),
                key=self.r.choice(
                    [
                        "companyName",
                        "companies.name",
                        "company_name",
                        "users.company_name",
                    ]
                ),
            )
            self.add(
                "neg:context:person-prose",
                self.r.choice(
                    [
                        "Assigned to Security Team yesterday.",
                        "Reviewed by Build System today.",
                        "Hi Support Team, your scan finished.",
                    ]
                ),
            )

    def dev_random_segments(self, n: int):
        for i in range(n):
            nbytes = 16 + i % 25
            encode = self.r.choice([base64.b64encode, base64.urlsafe_b64encode])
            token = encode(self.r.randbytes(nbytes)).decode()
            if i % 2:
                token = token.rstrip("=")
            self.add(
                "pos:limits:random-segment",
                self.r.choice(["{v}", "meta-v1.{v}.data-v1", " {v} "]),
                token,
                "SECRET",
                "entropy",
            )
            self.add("neg:limits:typed-random-id", "{v}", token, key="objectId")
            identifier = self.r.choice(
                [
                    f"cp314-win_arm64-asset_{i:05d}",
                    f"GetScanIssueActionForProject{i:03d}",
                    f"rhel9-x86_64-clang-build_{i:06d}",
                    f"SHA256:{token}",
                ]
            )
            self.add("neg:limits:build-identifier", identifier)

    def context_ids(self, n: int):
        for i in range(n):
            token = self.s(B62, 32)
            self.add(
                "neg:context:identifier",
                "{v}",
                token,
                key=self.r.choice(["requestId", "objectId", "orderId", "traceId"]),
            )
            self.add("pos:context:identifier-secret", "{v}", token, "SECRET", "entropy")
            self.add(
                "pos:context:secret-over-id",
                "token={v}",
                token,
                "SECRET",
                "generic",
                key="requestId",
            )
            object_key, prefix = self.r.choice(
                [
                    ("payment_intent", "pi_"),
                    ("customer", "cus_"),
                    ("request", "req_"),
                    ("event", "evt_"),
                ]
            )
            self.add("neg:context:object-id", "{v}", prefix + token, key=object_key)
            self.add(
                "pos:context:object-secret",
                "{v}",
                self.r.choice(["sk_live_", "rk_live_", "whsec_"]) + token,
                "SECRET",
                "stripe-key",
                key=object_key,
            )

    def heldout_urls(self, n: int):
        for i in range(n):
            self.add(
                "pos:holdout:url-query",
                'fetch("https://service.example/api?ref=main&X-Goog-Signature={v}#view")',
                self.s(HEXD, 40),
                "SECRET",
                "url-query",
            )
            self.add(
                "pos:holdout:url-password",
                'connect("redis://:{v}@cache.internal/0")',
                "pw-" + self.s(B62, 9),
                "SECRET",
                "url-password",
            )
            self.add(
                "neg:holdout:url",
                'fetch("https://git.example/team/repo.git?ref=release&sort=desc#readme")',
            )
            self.add(
                "neg:holdout:url-password", 'connect("redis://cache.internal:6379/0")'
            )
            self.add(
                "neg:holdout:clone-url",
                f"origin: ssh://git@code.internal/team/repo-{i}.git",
            )

    def heldout_cookies(self, n: int):
        for i in range(n):
            self.add(
                "pos:holdout:cookie",
                'custom_login="{v}"; Path=/private; SameSite=Strict',
                self.s(HEXD, 32),
                "SECRET",
                "cookie",
                key="set_cookie",
            )
            self.add(
                "pos:holdout:session-column",
                "{v}",
                self.s(HEXD, 32),
                "SECRET",
                "generic",
                key="accounts.sessionId",
            )
            self.add(
                "neg:holdout:cookie",
                "language=es; Max-Age=3600; SameSite=Strict",
                key="Set-Cookie",
            )
            self.add(
                "neg:holdout:session-column", "expired", key="accounts.sessionStatus"
            )

    def heldout_jwt(self, n: int):
        for i in range(n):
            value = (
                jwt_segment('{\n "typ": "JWT", "alg": "HS256"\n}')
                + "."
                + jwt_segment(
                    json.dumps({"sub": self.s(B62, 12), "email": self.en.email()})
                )
                + "."
                + self.s(B64URL, 43)
            )
            self.add(
                "pos:holdout:jwt", "claims: {v}\nstatus: active", value, "SECRET", "jwt"
            )
            self.add("neg:holdout:jwt", "artifact version: release.2026.preview")

    def heldout_person(self, n: int):
        for i in range(n):
            name = self.faker().first_name() + " " + self.faker().last_name()
            self.add(
                "pos:holdout:person",
                "The alert was triaged by {v} today.",
                name,
                "PERSON",
            )
            self.add(
                "pos:holdout:name-column",
                "{v}",
                name.lower(),
                "PERSON",
                key="profile.givenName",
            )
            self.add("neg:holdout:company", "Morgan Stanley", key="organizations.name")
            self.add(
                "neg:holdout:person-prose",
                "The alert was triaged by Security Team today.",
            )

    def heldout_ids(self, n: int):
        for i in range(n):
            key, prefix = self.r.choice(
                [
                    ("billing.paymentIntent", "pi_"),
                    ("accounts.customer", "cus_"),
                    ("logs.request", "req_"),
                    ("hooks.event", "evt_"),
                ]
            )
            token = self.s(B62, 32)
            self.add("neg:holdout:object-id", "{v}", prefix + token, key=key)
            self.add(
                "pos:holdout:object-secret",
                "{v}",
                self.r.choice(["sk_live_", "rk_live_", "whsec_"]) + token,
                "SECRET",
                "stripe-key",
                key=key,
            )
            self.add(
                "neg:holdout:identifier", "job ref: {v}", token, key="jobs.traceId"
            )
            self.add(
                "pos:holdout:identifier-secret",
                "output was ({v})",
                token,
                "SECRET",
                "entropy",
            )
            self.add(
                "pos:holdout:secret-over-id",
                'secret = "{v}"',
                token,
                "SECRET",
                "generic",
                key="jobs.traceId",
            )

    def identifier(self) -> str:
        words = [self.r.choice(WORDS) for _ in range(self.r.randint(2, 5))]
        style = self.r.choice(["snake", "camel", "pascal", "kebab", "const"])
        suffix = self.r.choice(["", "", "2", "_v2", "V3", "_401", "Id", "_test"])
        if style == "snake":
            return "_".join(words) + suffix
        if style == "kebab":
            return "-".join(words) + suffix.lower()
        if style == "const":
            return "_".join(words).upper() + suffix.upper()
        out = "".join(w.capitalize() for w in words) + suffix
        return out[0].lower() + out[1:] if style == "camel" else out

    def path(self) -> str:
        r = self.r
        parts = [
            r.choice(
                [
                    "src",
                    "app",
                    "lib",
                    "pkg",
                    "internal",
                    "services",
                    "frontend/src",
                    "backend",
                ]
            )
        ]
        parts += [self.identifier() for _ in range(r.randint(1, 3))]
        name = self.identifier() + r.choice(
            [".py", ".ts", ".tsx", ".go", ".java", ".rb", ".js", ".yaml", ".json"]
        )
        p = "/".join(parts + [name])
        return r.choice(
            [
                p,
                "/" + p,
                "./" + p,
                "C:\\Users\\dev\\" + p.replace("/", "\\"),
                "dist/assets/index-" + self.s(B64URL, 8) + ".js",
                "static/js/main." + self.s(HEXD, 8) + ".chunk.js",
            ]
        )

    def negatives(self, n: int):
        r, s, en = self.r, self.s, self.en
        corgea = json.loads((ROOT / "fixtures" / "corgea_issues.json").read_text())
        leaves = []

        def walk(node, key=None):
            if isinstance(node, dict):
                for k, v in node.items():
                    walk(v, k)
            elif isinstance(node, list):
                for v in node:
                    walk(v, key)
            elif isinstance(node, (str, int)) and not isinstance(node, bool):
                leaves.append((key, str(node)))

        walk(corgea)
        for key, value in leaves:
            self.add("neg:corgea-issue-field", value, key=key)
        for item in corgea["results"]:
            self.add("neg:corgea-issue-json", json.dumps(item))
        cwe = [
            "Path Traversal",
            "Cross-site Scripting",
            "SQL Injection",
            "Open Redirect",
            "Server-Side Request Forgery",
            "Hard-coded Credentials",
            "Missing Authorization",
            "Insecure Deserialization",
            "Command Injection",
            "Use of Weak Hash",
            "Permissive Regular Expression",
            "Cleartext Storage of Sensitive Information",
            "Improper Certificate Validation",
            "Exposure of Sensitive Information to an Unauthorized Actor",
        ]
        companies = [
            "Acme Corp",
            "Globex",
            "Initech",
            "Morgan Stanley",
            "Charles Schwab",
            "Wells Fargo",
            "Johnson & Johnson",
            "Ernst & Young",
            "Ford Motor Company",
            "Dell Technologies",
            "Tommy Hilfiger",
            "Ralph Lauren",
            "Goldman Sachs",
            "Jack Henry & Associates",
            "Lincoln Financial",
            "Grant Thornton",
            "Edward Jones",
        ]
        code = [
            "token_count = len(tokens)",
            "def get_api_key(self):\n    return os.environ['API_KEY']",
            "const password = req.body.password;",
            "if (!token) throw new Error('missing token')",
            "password_hash = make_password(raw_password)",
            "TOKEN_EXPIRY_SECONDS = 3600",
            "api_key: str = Field(..., description='API key')",
            "headers = {'Authorization': f'Bearer {token}'}",
            "password = getpass.getpass()",
            "secret = settings.SECRET_KEY",
            "auth_token = request.headers.get('X-Auth-Token')",
            "self.assertEqual(response.status_code, 200)",
            "import { useAuthToken } from '@/hooks/useAuthToken';",
            "max_tokens: 4096",
            "password: $" + "{DB_PASSWORD}",
            "client_secret: <your-client-secret>",
            "token = None",
            "export GITHUB_TOKEN=$(gh auth token)",
            "if user.check_password(password):",
            "passwordInput.value = ''",
            "for token in tokenizer(text):",
            "SESSION_COOKIE_SECURE = True",
            "secret_name = f'{env}-db-password'",
            "kubectl create secret generic db --from-literal=password=$PASSWORD",
            "jwt.decode(token, key, algorithms=['HS256'])",
            "SELECT id, email, created_at FROM users WHERE created_at > '2024-01-01' LIMIT 50",
            "logger.info('Processed %d tokens in %.2fs', count, elapsed)",
            "password_reset_token_ttl = timedelta(hours=1)",
            "uses: actions/checkout@v4",
            "image: ghcr.io/corgea/worker@sha256:" + s(HEXD, 64),
        ]
        for _ in range(n):
            u = str(uuid.UUID(int=r.getrandbits(128), version=4))
            sha = s(HEXD, 40)
            self.add(
                "neg:uuid",
                r.choice(["{v}", "scan_id={v}", "/api/v1/issues/{v}"]).replace(
                    "{v}", u
                ),
            )
            self.add(
                "neg:git-sha",
                r.choice(
                    [
                        sha,
                        "commit " + sha,
                        sha[:7],
                        "git_sha: " + sha,
                        "merge " + sha[:12] + " into main",
                    ]
                ),
            )
            self.add(
                "neg:hash",
                r.choice(
                    [
                        s(HEXD, 32),
                        s(HEXD, 64),
                        s(HEXD, 128),
                        "sha256:" + s(HEXD, 64),
                        "sha512-" + base64.b64encode(r.randbytes(64)).decode(),
                        "SHA256:"
                        + base64.b64encode(r.randbytes(32)).decode().rstrip("="),
                        ":".join(s(HEXD, 2) for _ in range(16)),
                        'etag: "' + s(HEXD, 32) + '"',
                        "fingerprint=" + s(HEXD, 64),
                    ]
                ),
            )
            self.add(
                "neg:timestamp",
                r.choice(
                    [
                        self.when().isoformat(),
                        self.when().isoformat() + "Z",
                        str(r.randint(16 * 10**8, 18 * 10**8)),
                        str(r.randint(16 * 10**11, 18 * 10**11)),
                        self.when().strftime("%a, %d %b %Y %H:%M:%S GMT"),
                        self.when().strftime("%Y-%m-%d %H:%M:%S.%f+00:00"),
                        self.when().date().isoformat(),
                    ]
                ),
            )
            self.add(
                "neg:numeric-id",
                str(
                    r.choice(
                        [
                            r.randint(1, 10**6),
                            r.randint(10**9, 10**12),
                            r.randint(10**17, 10**19),
                        ]
                    )
                ),
                key=r.choice(["id", "row_count", "line_number", "project_id", None]),
            )
            self.add("neg:path", self.path())
            self.add(
                "neg:vuln-id",
                r.choice(
                    [
                        f"CWE-{r.randint(1, 1400)}",
                        f"CVE-{r.randint(1999, 2026)}-{r.randint(1000, 99999)}",
                        "GHSA-"
                        + "-".join(s("23456789cfghjmpqrvwx", 4) for _ in range(3)),
                        f"CWE-{r.randint(1, 1400)}: {r.choice(cwe)}",
                    ]
                ),
            )
            self.add(
                "neg:url",
                r.choice(
                    [
                        f"https://github.com/{en.user_name()}/{self.identifier()}/pull/{r.randint(1, 9999)}",
                        f"https://app.corgea.com/project/{r.randint(1, 999)}/issue/{uuid.UUID(int=r.getrandbits(128))}",
                        f"https://api.{en.domain_name()}/v2/{self.identifier()}?page={r.randint(1, 9)}&per_page=50",
                        f"git@github.com:{en.user_name()}/{self.identifier()}.git",
                    ]
                ),
            )
            self.add("neg:code", r.choice(code))
            self.add("neg:identifier", self.identifier())
            self.add(
                "neg:version",
                r.choice(
                    [
                        f"{r.randint(0, 20)}.{r.randint(0, 30)}.{r.randint(0, 99)}",
                        f"v{r.randint(0, 9)}.{r.randint(0, 30)}.{r.randint(0, 9)}-rc.{r.randint(1, 5)}",
                        f"python {r.choice(['3.10', '3.11', '3.12', '3.13'])}",
                        f"lodash@4.17.{r.randint(1, 21)}",
                    ]
                ),
            )
            blob = base64.b64encode(r.randbytes(r.randint(60, 300))).decode()
            self.add(
                "neg:base64-in-code",
                r.choice(
                    [
                        f'src="data:image/png;base64,{blob}"',
                        f'integrity="sha384-{base64.b64encode(r.randbytes(48)).decode()}"',
                        f"ssh-ed25519 {base64.b64encode(r.randbytes(51)).decode()} dev@laptop",
                        f"FIXTURE = '{base64.b64encode(en.sentence().encode()).decode()}'",
                    ]
                ),
            )
            self.add(
                "neg:company",
                r.choice(companies + [self.faker().company() for _ in range(3)]),
                key=r.choice([None, "company_name", "organization"]),
            )
            self.add(
                "neg:prose",
                r.choice(
                    [
                        f"{r.choice(cwe)} in {self.path()} at line {r.randint(1, 900)}",
                        f"Hardcoded password detected in {self.path()}; rotate the credential and load it from the environment.",
                        f"User-controlled input flows into {self.identifier()}() without sanitization.",
                        "The product uses a regular expression that does not sufficiently restrict the set of allowed values.",
                        f"Scan {uuid.UUID(int=r.getrandbits(128))} finished with {r.randint(0, 99)} findings on branch main.",
                        f"Will Update the {r.choice(cwe)} rule after the Code Review.",
                        "Mark As Resolved",
                        "Grant Access to Admins",
                        f"Upgrade {self.identifier()} to {r.randint(1, 9)}.{r.randint(0, 9)}.{r.randint(0, 9)} to fix {r.choice(cwe)}.",
                    ]
                ),
            )
            self.add(
                "neg:scan-row",
                json.dumps(
                    {
                        "id": str(uuid.UUID(int=r.getrandbits(128))),
                        "project": self.identifier(),
                        "branch": r.choice(
                            ["main", "develop", "feature/" + self.identifier()]
                        ),
                        "git_sha": s(HEXD, 40),
                        "created_at": self.when().isoformat() + "Z",
                        "status": r.choice(["open", "fixed", "accepted_risk"]),
                        "urgency": r.choice(["LO", "ME", "HI", "CR"]),
                        "file": self.path(),
                        "line_number": r.randint(1, 2000),
                        "cwe": f"CWE-{r.randint(1, 1400)}",
                        "token_count": r.randint(100, 9000),
                    }
                ),
            )
            rid = r.choice(
                [
                    s(B62, 24),
                    "cus_" + s(B62, 14),
                    "pi_" + s(B62, 24),
                    s(B64, 64),
                    "i-0" + s(HEXD, 16),
                    s(B64URL, 22),
                ]
            )
            rkey = r.choice(
                [
                    "request_id",
                    "version_id",
                    "object_id",
                    "trace_id",
                    "external_id",
                    "etag",
                    "checksum",
                    "payment_intent",
                ]
            )
            self.add(
                "neg:random-id",
                r.choice(
                    ["{v}", f'"{rkey}": "{{v}}"', f"{rkey}={{v}} status=200"]
                ).replace("{v}", rid),
                key=r.choice([rkey, None]),
            )
            self.add(
                "neg:log",
                r.choice(
                    [
                        f"GET /api/v1/issues?page={r.randint(1, 9)} 200 {r.randint(2, 900)}ms",
                        f"worker-{r.randint(1, 9)} processed job {s(HEXD, 24)} in {r.randint(10, 999)}ms",
                        f"{self.when().isoformat()} WARN retrying request_id={uuid.UUID(int=r.getrandbits(128))} attempt={r.randint(1, 5)}",
                        f"listening on 0.0.0.0:{r.randint(1000, 9999)}",
                        f"connected to 127.0.0.1:{r.randint(1000, 9999)}",
                    ]
                ),
            )

    def real_negatives(self, n: int):
        """Real text with no secrets or PII planted: lines of the standard library and this repo's uv.lock.
        Unlabeled, so every redaction counts as false; docstrings do name real people (authors)."""
        stdlib = Path(sysconfig.get_paths()["stdlib"])
        lines = []
        for path in sorted(stdlib.glob("*.py")):
            lines += [
                line.strip()
                for line in path.read_text(errors="ignore").splitlines()
                if len(line.strip()) >= 20
            ]
        for line in self.r.sample(lines, n):
            self.add("neg:real-stdlib-line", line)
        lock = [
            line.strip()
            for line in (ROOT.parent / "uv.lock").read_text().splitlines()
            if len(line.strip()) >= 20
        ]
        for line in self.r.sample(lock, min(n, len(lock))):
            self.add("neg:real-uv-lock-line", line)

    def write(self, file: Path):
        self.r.shuffle(self.records)
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("w") as out:
            for i, record in enumerate(self.records):
                out.write(json.dumps({"id": i, **record}) + "\n")


def main(splits=(("dev", 1), ("test", 2)), output_dir=ROOT / "data"):
    for split, seed in splits:
        g = Gen(seed)
        g.pii(150)
        g.persons(300)
        g.secrets(40)
        g.negatives(200)
        g.real_negatives(1000)
        extra = Gen(seed + 1000)
        extra.context_urls(80)
        g.records.extend(extra.records)
        if split == "test":
            heldout = Gen(seed + 11000)
            heldout.heldout_urls(12)
            g.records.extend(heldout.records)
        extra = Gen(seed + 2000)
        extra.context_cookies(80)
        g.records.extend(extra.records)
        if split == "test":
            heldout = Gen(seed + 12000)
            heldout.heldout_cookies(12)
            g.records.extend(heldout.records)
        extra = Gen(seed + 3000)
        extra.context_jwt(80)
        g.records.extend(extra.records)
        if split == "dev":
            extra = Gen(seed + 23000)
            extra.dev_json_envelopes(100)
            g.records.extend(extra.records)
        if split == "test":
            heldout = Gen(seed + 13000)
            heldout.heldout_jwt(12)
            g.records.extend(heldout.records)
        extra = Gen(seed + 4000)
        extra.context_person(80)
        g.records.extend(extra.records)
        if split == "dev":
            extra = Gen(seed + 24000)
            extra.dev_unicode_names(70)
            g.records.extend(extra.records)
        if split == "test":
            heldout = Gen(seed + 14000)
            heldout.heldout_person(12)
            g.records.extend(heldout.records)
        extra = Gen(seed + 5000)
        extra.context_ids(80)
        g.records.extend(extra.records)
        if split == "dev":
            extra = Gen(seed + 25000)
            extra.dev_random_segments(400)
            g.records.extend(extra.records)
        if split == "test":
            heldout = Gen(seed + 15000)
            heldout.heldout_ids(12)
            g.records.extend(heldout.records)
        extra = Gen(seed + 6000)
        extra.context_jwe(80)
        g.records.extend(extra.records)
        g.write(output_dir / f"{split}.jsonl")
        print(f"{split}: {len(g.records)} records")


if __name__ == "__main__":
    main()
