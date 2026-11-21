#!/usr/bin/env bash
# Resolve identities in the trusted job. The request workflow supplies no scores or artifacts.
set -euo pipefail

if [ "$GITHUB_EVENT_NAME" = push ]; then
  base=$(jq -er '.before' "$GITHUB_EVENT_PATH")
  candidate=$GITHUB_SHA
  git merge-base --is-ancestor "$base" "$candidate"
  test "$(git rev-parse HEAD)" = "$candidate"
  test "$base" != "$candidate"
else
  owner=$(jq -er '.workflow_run.head_repository.owner.login' "$GITHUB_EVENT_PATH")
  branch=$(jq -er '.workflow_run.head_branch' "$GITHUB_EVENT_PATH")
  head=$(jq -er '.workflow_run.head_sha' "$GITHUB_EVENT_PATH")
  pr=$(gh api --method GET "repos/$GITHUB_REPOSITORY/pulls" \
    -f state=open -f base=main -f "head=$owner:$branch" |
    jq -ec --arg head "$head" '[.[] | select(.head.sha == $head)] | if length == 1 then .[0] else error("request no longer identifies a single current PR") end')
  number=$(jq -er '.number' <<< "$pr")
  base=$(jq -er '.base.sha' <<< "$pr")
  test "$(git rev-parse HEAD)" = "$base"
  for attempt in 1 2 3 4 5 6; do
    if git fetch --quiet --no-tags origin "refs/pull/$number/merge"; then
      candidate=$(git rev-parse FETCH_HEAD)
      if [ "$(git show -s --format=%P "$candidate")" = "$base $head" ]; then
        break
      fi
    fi
    test "$attempt" != 6
    sleep 5
  done
fi

printf 'base=%s\nsha=%s\n' "$base" "$candidate" >> "$GITHUB_OUTPUT"

if [ "$GITHUB_EVENT_NAME" != push ] &&
   ! git diff --quiet "$base" "$candidate" -- evals/frozen evals/frozen_eval.py evals/frozen_predict.py evals/frozen_ci.sh evals/scoreboard.py '.github/workflows/frozen-eval*.yml' &&
   ! git diff --quiet "$base" "$candidate" -- inconnu pyproject.toml uv.lock; then
  echo "Change the detector and the frozen evaluator in separate pull requests." >&2
  exit 1
fi
