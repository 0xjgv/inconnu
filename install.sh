#!/bin/sh
# Install or update the inconnu CLI from a checksummed GitHub release.
# INCONNU_VERSION        release version, e.g. v0.2.0 (default: latest)
# INCONNU_DOWNLOAD_BASE  release base URL, or an absolute directory holding
#                        checksums.txt and the wheel (local testing)
# INCONNU_HOME           where release wheels are kept (default: $HOME/.local/share/inconnu)
# INCONNU_LOCAL_BUILD=1  install unsigned assets you built in the local
#                        DOWNLOAD_BASE directory (`make install-cli`), even when
#                        that version is already installed
# When an anonymous download fails and the GitHub CLI is logged in, it downloads through `gh`.
# checksums.txt is verified against PUBLIC_KEY with minisign when it is installed, and always
# during `inconnu update`.
set -eu

REPO=0xjgv/inconnu
PUBLIC_KEY=RWRReGpZNrXT60bmrY0IQGD5vLPBmlNwGcfZzXYkLchaAogZNhEHAQ3/
NAME=inconnu

die() {
    echo "$NAME install: $*" >&2
    exit 1
}

command -v uv >/dev/null 2>&1 || die "uv is required: https://docs.astral.sh/uv/"

sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        die "sha256sum or shasum is required"
    fi
}

curl_get() {
    if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$1" -o "$2" 2>/dev/null
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$2" "$1"
    else
        return 1
    fi
}

version=${INCONNU_VERSION:-}
version=${version#v}
if [ -n "$version" ]; then
    printf '%s\n' "$version" | awk '/^[0-9]+\.[0-9]+\.[0-9]+$/ {valid=1} END {exit !valid}' ||
        die "INCONNU_VERSION must be a version such as v0.2.0"
fi

base=${INCONNU_DOWNLOAD_BASE:-https://github.com/$REPO/releases}
base=${base%/}
local_build=${INCONNU_LOCAL_BUILD:-}
if [ -n "$local_build" ]; then
    case $base in
    /*) ;;
    *) die "INCONNU_LOCAL_BUILD needs INCONNU_DOWNLOAD_BASE to be a local directory" ;;
    esac
fi
case $base in
/*) release=$base ;;
*) if [ -n "$version" ]; then release=$base/download/v$version; else release=$base/latest/download; fi ;;
esac

# fetch <file> <dest>: local directory, anonymous HTTPS, then the GitHub CLI.
fetch() {
    case $release in
    /*) cp "$release/$1" "$2" 2>/dev/null && return 0 ;;
    *)
        curl_get "$release/$1" "$2" && return 0
        if command -v gh >/dev/null 2>&1; then
            gh release download ${version:+"v$version"} -R "$REPO" -p "$1" -O "$2" --clobber >/dev/null 2>&1 && return 0
        fi
        ;;
    esac
    die "download failed: $release/$1"
}

verify_signature() {
    if [ -n "$local_build" ]; then
        echo "$NAME install: local build from $release; signature not checked" >&2
        return
    fi
    if [ -n "${INCONNU_VERIFIER:-}" ]; then
        fetch checksums.txt.minisig "$tmpdir/checksums.txt.minisig"
        "$INCONNU_VERIFIER" -m inconnu update --verify-signature "$PUBLIC_KEY" \
            "$tmpdir/checksums.txt" "$tmpdir/checksums.txt.minisig" ||
            die "invalid signature for $release/checksums.txt"
    elif command -v minisign >/dev/null 2>&1; then
        fetch checksums.txt.minisig "$tmpdir/checksums.txt.minisig"
        minisign -V -q -P "$PUBLIC_KEY" -m "$tmpdir/checksums.txt" -x "$tmpdir/checksums.txt.minisig" ||
            die "invalid signature for $release/checksums.txt"
    else
        echo "$NAME install: minisign not found; checksums.txt signature not verified" >&2
    fi
}

tmpdir=$(mktemp -d)
trap 'rm -rf "$tmpdir"' 0
trap 'exit 1' HUP INT TERM

fetch checksums.txt "$tmpdir/checksums.txt"
verify_signature
wheel=$(awk -v version="$version" '
    {sub(/^\*/, "", $2)}
    $2 ~ /^inconnu-[0-9]+[.][0-9]+[.][0-9]+-py3-none-any[.]whl$/ &&
        (version == "" || $2 == "inconnu-" version "-py3-none-any.whl") {
        found=$2; count++
    }
    END {if (count == 1) print found}
' "$tmpdir/checksums.txt")
[ -n "$wheel" ] || die "expected one $NAME wheel in $release/checksums.txt"
wheel_version=${wheel#inconnu-}
wheel_version=${wheel_version%-py3-none-any.whl}

bin_dir=$(uv tool dir --bin)
previous=
if [ -x "$bin_dir/$NAME" ]; then
    previous=$("$bin_dir/$NAME" version 2>/dev/null || true)
fi
if [ -z "$local_build" ] && [ "$previous" = "$wheel_version" ]; then
    echo "$bin_dir/$NAME is already up to date: $previous"
    exit 0
fi

expected=$(awk -v name="$wheel" '{sub(/^\*/, "", $2)} $2 == name {print $1}' "$tmpdir/checksums.txt")
fetch "$wheel" "$tmpdir/$wheel"
[ "$(sha256 "$tmpdir/$wheel")" = "$expected" ] || die "checksum mismatch for $wheel"

store=${INCONNU_HOME:-$HOME/.local/share/$NAME}/releases
mkdir -p "$store"
cp "$tmpdir/$wheel" "$store/$wheel"

uv tool install --quiet --force --python '>=3.10' "$store/$wheel" || die "uv tool install failed for $wheel"
current=$("$bin_dir/$NAME" version 2>/dev/null) || die "installed $NAME does not run"
[ "$current" = "$wheel_version" ] || die "installed $NAME reported an unexpected version: $current"

if [ -n "$previous" ] && [ "$previous" != "$current" ]; then
    echo "Updated $bin_dir/$NAME: $previous -> $current"
else
    echo "Installed $bin_dir/$NAME: $current"
fi
case :$PATH: in
*":$bin_dir:"*) ;;
*) echo "Add $bin_dir to PATH: export PATH=\"$bin_dir:\$PATH\"" ;;
esac
