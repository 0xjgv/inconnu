#!/bin/sh
# make release [BUMP=patch|minor|major]
# Tag the next version on main (or pyproject.toml's version when it was never tagged) and push it; the Release workflow publishes it.
# Idempotent: when HEAD already carries a release tag, rerunning only re-pushes
# that tag, so an interrupted release resumes instead of skipping a number.
set -eu

root=$(CDPATH='' cd -- "$(dirname "$0")/.." && pwd)
cd "$root"
remote=${RELEASE_REMOTE:-origin}
bump=${BUMP:-patch}

die() {
    echo "release: $*" >&2
    exit 1
}

case $bump in patch | minor | major) ;; *) die "BUMP must be patch, minor, or major" ;; esac
[ "$(git rev-parse --abbrev-ref HEAD)" = main ] || die "run from the main branch"
[ -z "$(git status --porcelain)" ] || die "the working tree has uncommitted changes"
git fetch --quiet --tags "$remote" main
git merge-base --is-ancestor "$remote/main" HEAD || die "main is behind $remote/main; pull first"

project_version() {
    sed -n 's/^version = "\(.*\)"$/\1/p' pyproject.toml
}

package_version() {
    sed -n 's/^__version__ = "\(.*\)"$/\1/p' inconnu/__init__.py
}

next_version() {
    echo "$1" | awk -F. -v bump="$2" '
        bump == "major" {print $1 + 1 ".0.0"; exit}
        bump == "minor" {print $1 "." $2 + 1 ".0"; exit}
        {print $1 "." $2 "." $3 + 1}'
}

release_tags() {
    grep -E '^v[0-9]+\.[0-9]+\.[0-9]+$' || true  # skip prerelease and malformed tags
}

tag=$(git tag --points-at HEAD | release_tags | sort -V | tail -n 1)
if [ -n "$tag" ]; then
    echo "HEAD is already $tag; resuming its release."
else
    latest=$(git tag | release_tags | sed 's/^v//' | sort -V | tail -n 1)
    current=$(project_version)
    echo "$current" | grep -Eq '^[0-9]+\.[0-9]+\.[0-9]+$' || die "pyproject.toml version '$current' is not X.Y.Z"
    newest=$(printf '%s\n%s\n' "$latest" "$current" | sed '/^$/d' | sort -V | tail -n 1)
    if [ "$current" = "$newest" ] && [ "$current" != "$latest" ]; then
        version=$current  # pyproject.toml holds a version that was never tagged: release it as is
    else
        version=$(next_version "$newest" "$bump")
    fi
    tag=v$version
    git rev-parse -q --verify "refs/tags/$tag" >/dev/null && die "$tag already exists on another commit"
    if [ "$version" != "$(project_version)" ]; then
        sed "s/^version = \".*\"$/version = \"$version\"/" pyproject.toml > pyproject.toml.tmp
        mv pyproject.toml.tmp pyproject.toml
        sed "s/^__version__ = \".*\"$/__version__ = \"$version\"/" inconnu/__init__.py > inconnu/__init__.py.tmp
        mv inconnu/__init__.py.tmp inconnu/__init__.py
        uv lock --quiet
        git commit --quiet -m "chore(release): $tag" -- pyproject.toml inconnu/__init__.py uv.lock
    fi
    git tag -a "$tag" -m "inconnu $tag"
    echo "Tagged $tag (latest tag: ${latest:-none})."
fi

[ "$(project_version)" = "${tag#v}" ] || die "pyproject.toml version does not match $tag"
[ "$(package_version)" = "${tag#v}" ] || die "inconnu/__init__.py version does not match $tag"
git push --quiet --atomic "$remote" HEAD:refs/heads/main "refs/tags/$tag"
echo "Pushed $tag. The Release workflow publishes https://github.com/0xjgv/inconnu/releases/tag/$tag"
