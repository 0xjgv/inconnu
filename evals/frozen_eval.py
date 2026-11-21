"""Compare two detector revisions against the trusted frozen CI corpus."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections import Counter, defaultdict
from importlib.metadata import version as distribution_version
from pathlib import Path

from evals.scoreboard import ORIGINAL_NEGATIVES, totals

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]
FROZEN = ROOT / "evals/frozen"
PREDICTOR = ROOT / "evals/frozen_predict.py"
PYTHON_IMAGE = "python:3.14.10-slim@sha256:9aaa474097d094040649f2162a627c0049b408f52138d980916788d80f04802f"
GIT = shutil.which("git") or "git"
DOCKER = shutil.which("docker") or "docker"


def git(*args: str) -> bytes:
    return subprocess.check_output([GIT, *args], cwd=ROOT)


def load_corpus(revision: str | None = None):
    def read(name):
        if revision:
            return git("show", f"{revision}:evals/frozen/{name}")
        return (FROZEN / name).read_bytes()

    manifest = json.loads(read("manifest.json"))
    version = manifest["version"]
    if type(version) is not int or version < 1:
        raise ValueError("Invalid frozen corpus version")
    with gzip.GzipFile(fileobj=io.BytesIO(read(f"v{version}.jsonl.gz"))) as stream:
        data = stream.read(16_000_001)
    cases = read(f"v{version}-cases.json")
    if len(data) > 16_000_000 or len(cases) > 128_000:
        raise ValueError("Frozen corpus exceeds the runner's input limit")
    digest = hashlib.sha256(data + cases).hexdigest()
    if digest != manifest["sha256"]:
        raise ValueError("Frozen corpus checksum does not match")
    records = [json.loads(line) for line in data.splitlines()]
    named = json.loads(cases)
    if not records or not named:
        raise ValueError("The frozen corpus and named regressions must both be present")
    combined = records + named
    if len({str(row["id"]) for row in combined}) != len(combined):
        raise ValueError("Frozen corpus IDs must be unique")
    return digest, combined


def runtime_requirement(revision: str) -> str:
    """Read the currently supported locked runtime dependency without running a build."""
    packages = tomllib.loads(git("show", f"{revision}:uv.lock").decode())["package"]
    (project,) = (p for p in packages if p["name"] == "inconnu")
    if [p["name"] for p in project.get("dependencies", [])] != ["phonenumberslite"]:
        raise ValueError("Update the frozen runner for the new runtime dependencies")
    manifest = tomllib.loads(git("show", f"{revision}:pyproject.toml").decode())
    (declared,) = project["metadata"]["requires-dist"]
    if manifest["project"]["dependencies"] != [
        declared["name"] + declared.get("specifier", "")
    ]:
        raise ValueError("The runtime dependency manifest differs from the lock")
    (phone,) = (p for p in packages if p["name"] == "phonenumberslite")
    (wheel,) = phone["wheels"]
    version, checksum = phone["version"], wheel["hash"]
    if phone["source"].get("registry") != "https://pypi.org/simple" or not (
        re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version)
        and re.fullmatch(r"sha256:[0-9a-f]{64}", checksum)
    ):
        raise ValueError("Unsupported phonenumberslite source, version or wheel hash")
    return f"phonenumberslite=={version} --hash={checksum}"


def detector_command(source: Path, requirement: str, images: dict, native: bool):
    if native:
        installed = distribution_version("phonenumberslite")
        if not requirement.startswith(f"phonenumberslite=={installed} "):
            raise ValueError(
                "The local phonenumberslite version differs from the revision's lock"
            )
        return [sys.executable, "-I", str(PREDICTOR), str(source)]
    if requirement not in images:
        digest = hashlib.sha256(requirement.encode()).hexdigest()[:16]
        image = f"inconnu-frozen-ci:{digest}"
        recipe = (
            f"FROM {PYTHON_IMAGE}\n"
            f"RUN printf '%s\\n' '{requirement}' > /tmp/frozen-requirements.txt"
            " && python -m pip --isolated install --no-cache-dir --only-binary=:all:"
            " --require-hashes --no-deps -r /tmp/frozen-requirements.txt\n"
        )
        subprocess.run(
            [DOCKER, "build", "--tag", image, "-"],
            input=recipe.encode(),
            stdout=sys.stderr,
            check=True,
        )
        images[requirement] = image
    return [
        DOCKER,
        "run",
        "--rm",
        "-i",
        "--network",
        "none",
        "--read-only",
        "--cap-drop",
        "ALL",
        "--security-opt",
        "no-new-privileges",
        "--pids-limit",
        "64",
        "--memory",
        "512m",
        "--cpus",
        "2",
        "--user",
        "65534:65534",
        "--mount",
        f"type=bind,source={source},target=/detector,readonly",
        "--mount",
        f"type=bind,source={PREDICTOR},target=/predict.py,readonly",
        images[requirement],
        "python",
        "-I",
        "-B",
        "/predict.py",
        "/detector",
    ]


def predictions(revision: str, records, images: dict, native: bool):
    request = "".join(
        json.dumps({"text": row["text"], "key": row["key"], "named": "expected" in row})
        + "\n"
        for row in records
    ).encode()
    requirement = runtime_requirement(revision)
    with tempfile.TemporaryDirectory() as directory:
        source = Path(directory) / "source"
        source.mkdir(mode=0o755)
        with tarfile.open(
            fileobj=io.BytesIO(git("archive", revision, "inconnu/"))
        ) as archive:
            archive.extractall(source, filter="data")
        command = detector_command(source, requirement, images, native)
        with tempfile.TemporaryFile() as stdout:
            # Cap the host file the Docker client can write. Detector stderr is untrusted.
            result = subprocess.run(
                [
                    "/bin/sh",
                    "-c",
                    'ulimit -f 8192 && exec "$@"',
                    "frozen-detector",
                    *command,
                ],
                input=request,
                stdout=stdout,
                stderr=subprocess.DEVNULL,
                timeout=90,
            )
            if result.returncode:
                raise ValueError(
                    f"Detector {revision} exited with status {result.returncode}"
                )
            stdout.seek(0)
            payload = stdout.read(4_000_001)
    if len(payload) > 4_000_000:
        raise ValueError(f"Detector {revision} returned too much output")
    return requirement, (json.loads(line) for line in payload.splitlines())


def measure(records, outputs):
    failures = defaultdict(set, {"original": set(), "added": set()})
    gold = Counter()
    negatives = Counter()
    named_failures = set()
    for row, output in zip(records, outputs, strict=True):
        identifier = str(row["id"])
        spans = output["spans"]
        previous = 0
        covered = set()
        for start, end in spans:
            if (
                type(start) is not int
                or type(end) is not int
                or not (previous <= start < end <= len(row["text"]))
            ):
                raise ValueError(f"Invalid prediction span on case {identifier}")
            covered.update(range(start, end))
            previous = end
        if "expected" in row:
            if output["output"] != row["expected"]:
                named_failures.add(identifier)
            continue
        if row["category"].startswith("neg:"):
            bucket = "original" if row["category"] in ORIGINAL_NEGATIVES else "added"
            negatives[bucket] += 1
            if spans:
                failures[bucket].add(identifier)
        for span in row["spans"]:
            kind = span["kind"] if span["type"] == "SECRET" else span["type"]
            gold[kind] += 1
            start, end = span["start"], span["end"]
            if not covered.issuperset(range(start, end)):
                failures[kind].add(f"{identifier}:{start}-{end}")

    leaks = {kind: len(failures[kind]) for kind in sorted(gold)}
    stats = {
        "gold": gold,
        "leaks": leaks,
        "original": [len(failures["original"]), negatives["original"]],
        "added": [len(failures["added"]), negatives["added"]],
    }
    cost, score, _, _ = totals(stats)
    return {
        "cost": cost,
        "score": round(score, 6),
        "leaks": leaks,
        "false_redactions": {bucket: stats[bucket] for bucket in ("original", "added")},
        "failures": dict(failures),
        "named_failures": named_failures,
    }


def compare(base, candidate):
    new, recovered, increases = {}, {}, {}
    for kind in sorted(base["failures"].keys() | candidate["failures"].keys()):
        old = base["failures"].get(kind, set())
        current = candidate["failures"].get(kind, set())
        if current - old:
            new[kind] = sorted(current - old)
        if old - current:
            recovered[kind] = sorted(old - current)
        if len(current) > len(old):
            increases[kind] = len(current) - len(old)
    return {
        "passed": not increases and not candidate["named_failures"],
        "count_increases": increases,
        "new_failures": new,
        "recovered": recovered,
        "named_failures": sorted(candidate["named_failures"]),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base")
    parser.add_argument("candidate")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--native", action="store_true", help="local trusted revisions only"
    )
    parser.add_argument("--validate-candidate-corpus", action="store_true")
    args = parser.parse_args()
    base_sha, candidate_sha = (
        git("rev-parse", "--verify", "--end-of-options", f"{rev}^{{commit}}")
        .decode()
        .strip()
        for rev in (args.base, args.candidate)
    )
    digest, records = load_corpus()
    stats = []
    images = {}
    if args.validate_candidate_corpus:
        candidate_digest, candidate_records = load_corpus(candidate_sha)
        if candidate_digest != digest:
            _, output = predictions(base_sha, candidate_records, images, args.native)
            bad_cases = measure(candidate_records, output)["named_failures"]
            if bad_cases:
                raise ValueError(
                    f"New frozen corpus fails named cases on main: {sorted(bad_cases)}"
                )
    for sha in (base_sha, candidate_sha):
        requirement, output = predictions(sha, records, images, args.native)
        stats.append({"sha": sha, "runtime": requirement, **measure(records, output)})
    base, candidate = stats
    result = compare(base, candidate)
    report = {
        "corpus_sha256": digest,
        "records": len(records),
        "evaluator_sha": git("rev-parse", "HEAD").decode().strip(),
        "base": base,
        "candidate": candidate,
        **result,
    }
    for item in stats:
        item.pop("failures")
        item["named_failures"] = sorted(item["named_failures"])
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(
        f"{base['sha'][:9]} -> {candidate['sha'][:9]}: "
        f"{base['score']:.6f} -> {candidate['score']:.6f} on {len(records)} frozen cases"
    )
    print(
        f"Count increases: {result['count_increases']}; "
        f"failed named cases: {result['named_failures']}"
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
