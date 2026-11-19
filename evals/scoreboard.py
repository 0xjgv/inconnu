"""Score a detector on a fixed dev corpus. Run from the repo with python -m evals.scoreboard."""

import argparse
import hashlib
import html
import io
import json
import os
import re
import secrets
import shutil
import statistics
import subprocess
import sys
import tarfile
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10: tomli is locked there through pytest
    import tomli as tomllib

SECRET_WEIGHT = 20  # A surviving secret costs twenty false redactions.
IDENTIFIER_WEIGHT = 10  # SSN, CARD and IBAN expose durable financial or identity data.
OTHER_PII_WEIGHT = 3  # EMAIL, PHONE, PERSON and IP still carry a privacy cost.
FALSE_REDACTION_WEIGHT = 1  # One unnecessarily redacted negative row is the cost unit.

TIMING_LIMITS = {"batch": 1.15, "p99": 1.25}
TIMING_PAIRS = 5

ROOT = Path(__file__).resolve().parents[1]
# Rows are measured with the working evaluator, even for --revision, so it must match Git.
EVALUATOR = (
    "evals/generate.py",
    "evals/run.py",
    "evals/scoreboard.py",
    "evals/fixtures",
)
BOARD = ROOT / "evals/SCOREBOARD.md"
GIT = shutil.which("git") or "git"
TABLE = (
    "| Date | Commit | Change | Score ↑ | Cost ↓ | Leaks S/P | Original FRR | Added FRR | Batch / p99 ratios² | Gates¹ |\n"
    "|---|---|---|---:|---:|---:|---:|---:|---:|---|\n"
)
# These are the original negative categories. New adversarial groups get distinct names.
ORIGINAL_NEGATIVES = {
    "neg:" + name
    for name in (
        "base64-in-code code company corgea-issue-field corgea-issue-json git-sha hash "
        "identifier log numeric-id path prose random-id real-stdlib-line real-uv-lock-line "
        "scan-row timestamp url uuid version vuln-id"
    ).split()
}
PII_WEIGHTS = dict.fromkeys(("SSN", "CARD", "IBAN"), IDENTIFIER_WEIGHT) | dict.fromkeys(
    ("EMAIL", "PHONE", "PERSON", "IP"), OTHER_PII_WEIGHT
)


def git(*args):
    return subprocess.check_output([GIT, *args], cwd=ROOT)


def measure(records):
    from evals import run

    predictions = run.predict_inconnu(records)
    result = run.score(records, predictions)
    gold = result["gold"]
    leaks = {k: n - result["fully_covered_counts"][k] for k, n in gold.items()}
    negatives = {"original": [0, 0], "added": [0, 0]}
    for row, spans in zip(records, predictions, strict=True):
        category = row["category"]
        if category.startswith("neg:"):
            bucket = negatives[
                "original" if category in ORIGINAL_NEGATIVES else "added"
            ]
            bucket[0] += bool(spans)
            bucket[1] += 1
    if any(
        g["type"] not in {"SECRET", *PII_WEIGHTS} for r in records for g in r["spans"]
    ):
        raise ValueError("assign an explicit weight to the new PII type")
    return {"gold": gold, "leaks": leaks, **negatives}


def totals(m):
    weights = {k: PII_WEIGHTS.get(k, SECRET_WEIGHT) for k in m["gold"]}
    cost = sum(n * weights[k] for k, n in m["leaks"].items())
    cost += FALSE_REDACTION_WEIGHT * (m["original"][0] + m["added"][0])
    nothing = sum(n * weights[k] for k, n in m["gold"].items())
    pii = sum(n for k, n in m["leaks"].items() if k in PII_WEIGHTS)
    return cost, 100 * (1 - cost / nothing), sum(m["leaks"].values()) - pii, pii


def gates(m, baseline, parent):
    if parent["gold"] != m["gold"] or baseline["original"][1] != m["original"][1]:
        raise ValueError("gate inputs have different corpus denominators")
    drops = [
        k
        for k, n in m["gold"].items()
        if 100 * (m["leaks"][k] - parent["leaks"][k]) > n
    ]
    new_deps = sorted(set(m["deps"]) - set(baseline["deps"]))
    return {
        "original FRR": (
            m["original"][0] <= baseline["original"][0],
            f"{m['original'][0]} vs baseline {baseline['original'][0]} / {m['original'][1]}",
        ),
        "kind coverage": (
            not drops,
            "declines over 1 percentage point: " + (", ".join(drops) or "none"),
        ),
        "latency": latency_gate(m["timing"]),
        "dependencies": (
            not new_deps,
            "added distributions: " + (", ".join(new_deps) or "none"),
        ),
    }


def dependencies(manifest):
    requirements = tomllib.loads(manifest)["project"]["dependencies"]
    return sorted(
        {
            re.sub(r"[-_.]+", "-", re.match(r"[\w.-]+", r.strip())[0]).lower()
            for r in requirements
        }
    )


@contextmanager
def detector_tree(revision, working=False):
    if working:
        yield ROOT
        return
    with tempfile.TemporaryDirectory() as folder:
        source = Path(folder).resolve()
        with tarfile.open(
            fileobj=io.BytesIO(git("archive", revision, "inconnu/"))
        ) as archive:
            archive.extractall(source, filter="data")
        yield source


def worker(task, corpus, source):
    # Historical imports and detector caches must not come from the active editable install.
    return json.loads(
        subprocess.check_output(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                task,
                str(corpus),
                str(source),
            ],
            cwd=source,
            env={
                **os.environ,
                "PYTHONHASHSEED": "0",
                "PYTHONPATH": os.pathsep.join(map(str, (source, ROOT))),
            },
        )
    )


def snapshot(corpus, revision, *, working=False):
    with detector_tree(revision, working) as source:
        data = worker("_measure", corpus, source)
    manifest = (
        (ROOT / "pyproject.toml").read_text()
        if working
        else git("show", f"{revision}:pyproject.toml").decode()
    )
    return {**data, "commit": revision, "deps": dependencies(manifest)}


def paired_timing(corpus, revision, baseline, *, working=False):
    samples = []
    with detector_tree(baseline) as base, detector_tree(revision, working) as candidate:
        sources = {"base": base, "candidate": candidate}
        for i in range(TIMING_PAIRS):
            order = ("base", "candidate") if i % 2 == 0 else ("candidate", "base")
            samples.append(
                {name: worker("_latency", corpus, sources[name]) for name in order}
            )
    return samples


def ratio_summary(samples, metric):
    ratios = [pair["candidate"][metric] / pair["base"][metric] for pair in samples]
    return statistics.median(ratios), min(ratios), max(ratios)


def timing_text(samples, metric):
    median, low, high = ratio_summary(samples, metric)
    return f"{median:.3f} [{low:.3f}–{high:.3f}]"


def latency_gate(samples):
    unstable = False
    within = True
    for metric, limit in TIMING_LIMITS.items():
        median, low, high = ratio_summary(samples, metric)
        # Compare unrounded ratios, tolerating floating point error at the equality boundary.
        unstable |= high - low > limit - 1 + 1e-12
        within &= median <= limit + 1e-12
    detail = ", ".join(
        f"{metric} {timing_text(samples, metric)} (limit {limit:.2f}×)"
        for metric, limit in TIMING_LIMITS.items()
    )
    return (None if unstable else within), detail


def verdict(flag):
    return "UNSTABLE" if flag is None else "PASS" if flag else "FAIL"


def history(text):
    return [json.loads(data) for data in re.findall(r"<!-- score-row (.+?) -->", text)]


def nearest(rows, revision, *, include_self, passing_only=False):
    recorded = {row["commit"]: row for row in rows if not passing_only or row["passed"]}
    if not include_self:
        recorded.pop(revision, None)
    if recorded:
        for sha in git("rev-list", "--topo-order", revision).decode().splitlines():
            if sha in recorded:
                return recorded[sha]
    return None


def ratio(pair):
    hits, total = pair
    return f"{hits / total:.4f}" if total else "—"


def render(row, label, checks, reason=""):
    cost, score, secret, pii = totals(row)
    flags = "/".join(verdict(passed) for passed, _ in checks.values())
    change = html.escape(
        " ".join((label + (f" — {reason}" if reason else "")).split())
    ).replace("|", "&#124;")
    meta = json.dumps(row, separators=(",", ":"))
    return (
        f"| {date.today()} | `{row['commit'][:9]}` | {change} | {score:.3f} | {cost} | {secret}/{pii} | "
        f"{ratio(row['original'])} | {ratio(row['added'])} | {timing_text(row['timing'], 'batch')} / {timing_text(row['timing'], 'p99')} | {flags} <!-- score-row {meta} --> |\n"
    )


def report(row, label, checks):
    cost, score, _, _ = totals(row)
    print(f"{label}: cost {cost}, score {score:.3f}, corpus {row['corpus']}")
    for name, (passed, detail) in checks.items():
        print(f"{verdict(passed)} {name}: {detail}")
    print("Leaked / gold spans by kind:")
    print(
        "  " + ", ".join(f"{k} {v}/{row['gold'][k]}" for k, v in row["leaks"].items())
    )


def append(text, addition):
    import fcntl

    lock_dir = ROOT / "evals/data"
    lock_dir.mkdir(exist_ok=True)
    with (lock_dir / ".scoreboard.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if BOARD.read_text() != text:
            raise SystemExit(
                "Scoreboard changed during measurement. Rerun against its new parent."
            )
        with tempfile.NamedTemporaryFile(mode="w", dir=BOARD.parent, delete=False) as f:
            f.write(text.rstrip() + "\n" + addition)
        os.chmod(f.name, BOARD.stat().st_mode)
        os.replace(f.name, BOARD)


def evaluate(
    mode,
    corpus,
    revision,
    label,
    reason="",
    *,
    working=False,
    holdout_seed=None,
    dev_digest=None,
):
    text = BOARD.read_text()
    rows = history(text)
    digest = hashlib.sha256(corpus.read_bytes()).hexdigest()
    start = len(rows)
    while start and rows[start - 1]["corpus"] == (dev_digest or digest):
        start -= 1
    epoch = rows[start:]
    dirty = working and bool(
        git("status", "--porcelain", "--", "inconnu", "pyproject.toml")
    )
    if mode == "append" and (dirty or git("status", "--porcelain", "--", *EVALUATOR)):
        raise SystemExit(
            "Commit detector, dependency and evaluator changes before recording their Git SHA. Use make score for working edits."
        )
    if mode == "append":
        previous = next((r for r in reversed(epoch) if r["commit"] == revision), None)
        if previous and latency_gate(previous["timing"])[0] is not None:
            raise SystemExit("This revision already has a row in the epoch.")
    prior = nearest(
        epoch or rows, revision, include_self=dirty or not epoch, passing_only=not epoch
    )
    # An append must reproduce the recorded commit even if a new edit lands during timing.
    working = working and mode != "append"
    current = snapshot(corpus, revision, working=working)
    current.update(corpus=digest)
    if mode == "holdout":
        # The baseline and parent must see the same fresh examples as the candidate.
        base_rev = (
            epoch[0]["commit"] if epoch else prior["commit"] if prior else revision
        )
        cache = {} if dirty else {revision: current}
        for rev in dict.fromkeys([base_rev, prior["commit"] if prior else base_rev]):
            if rev not in cache:
                cache[rev] = snapshot(corpus, rev)
        base, parent = cache[base_rev], cache[prior["commit"] if prior else base_rev]
    elif epoch:
        base, parent = epoch[0], prior or epoch[0]
    else:
        base_rev = prior["commit"] if prior else revision
        base = snapshot(corpus, base_rev) if base_rev != revision or dirty else current
        parent = base
    current["timing"] = paired_timing(corpus, revision, base["commit"], working=working)
    checks = gates(current, base, parent)
    current["passed"] = all(flag for flag, _ in checks.values())
    report(current, label, checks)
    if mode == "holdout":
        print(f"Sanity check only, seed {holdout_seed}")
        print(TABLE + render(current, label, checks).split(" <!--")[0] + " |")
    if mode == "append":
        worsened = (
            current["original"][0] > parent["original"][0]
            or totals(current)[2] > totals(parent)[2]
        )
        if not reason and (worsened or not current["passed"]):
            raise SystemExit("Supply REASON for a guarded regression or failed gate.")
        if not epoch:
            addition = f"\n## Dev epoch `{digest}`\n\n" + TABLE
            if base is not current:
                base_row = {
                    **base,
                    "corpus": digest,
                    "timing": paired_timing(corpus, base["commit"], base["commit"]),
                }
                base_checks = gates(base_row, base_row, base_row)
                base_row["passed"] = all(flag for flag, _ in base_checks.values())
                addition += render(base_row, "Epoch baseline", base_checks)
        else:
            addition = ""
        append(text, addition + render(current, label, checks, reason))
    return 0 if current["passed"] else 1


def main():
    from evals import generate

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["score", "append", "holdout"])
    parser.add_argument(
        "--revision", help="measure the committed inconnu/ at this revision"
    )
    args = parser.parse_args()
    label = os.environ.get("LABEL", "").strip()
    if args.mode == "append" and not label:
        parser.error("set LABEL to describe the change")
    revision = (
        git("rev-parse", "--verify", (args.revision or "HEAD") + "^{commit}")
        .decode()
        .strip()
    )
    seed = 3 + secrets.randbelow(2**31) if args.mode == "holdout" else 1
    with tempfile.TemporaryDirectory() as folder:
        fixture = Path(folder) / "dev.jsonl"
        generate.main((("dev", 1),), Path(folder))
        dev_digest = hashlib.sha256(fixture.read_bytes()).hexdigest()
        if args.mode == "holdout":
            generate.main((("dev", seed),), Path(folder))
        return evaluate(
            args.mode,
            fixture,
            revision,
            label or args.mode,
            os.environ.get("REASON", "").strip(),
            working=not args.revision,
            holdout_seed=seed,
            dev_digest=dev_digest,
        )


if __name__ == "__main__":
    if sys.argv[1:2] in (["_measure"], ["_latency"]):
        import inconnu

        if (
            Path(inconnu.__file__).resolve().parent.parent
            != Path(sys.argv[3]).resolve()
        ):
            raise SystemExit(
                "The imported detector does not match the requested source tree"
            )
        records = [
            json.loads(line) for line in Path(sys.argv[2]).read_text().splitlines()
        ]
        if sys.argv[1] == "_measure":
            print(json.dumps(measure(records)))
        else:
            from evals.run import latency

            times = latency(records)
            print(
                json.dumps(
                    {
                        "p99": times["cell_us"]["p99"],
                        "batch": times["batch_10k"]["seconds_median_of_5"],
                    }
                )
            )
    else:
        sys.exit(main())
