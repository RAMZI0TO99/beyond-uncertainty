#!/usr/bin/env bash
# Build a pasteable verification bundle for Sol.
#
# Sol has no filesystem, no shell and no git client, so it cannot check a claim
# like "28 tests pass at commit abc123" -- it can only take Claude's word for
# it. That is a real gap in an adversarial-review arrangement: the reviewer is
# reviewing a description of the work rather than the work.
#
# This produces the evidence in one block the student can paste.
#
# It is generated rather than hand-written, but that alone does NOT make it
# unable to flatter: a clean commit can still be represented by an incomplete
# file selection, which is how the delta-12 bundle shipped two files and left
# nine claims uncertified. So it also prints the review base, the exact
# arguments it was called with, and the complete manifest and diff of what
# changed since that base -- none of which the caller chooses.
#
# Usage:
#   scripts/sol_bundle.sh                        # default: identity-critical files
#   scripts/sol_bundle.sh src/bu/env/gridworld.py
#   BASE=e1a8bad scripts/sol_bundle.sh           # review base for the diff
#   scripts/sol_bundle.sh > bundle.txt

set -euo pipefail
cd "$(dirname "$0")/.."

FILES=("$@")
if [ ${#FILES[@]} -eq 0 ]; then
    FILES=(src/bu/constants.py src/bu/config.py)
fi

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

# The base the diff is taken against: the last commit Sol reviewed. Override
# with BASE=<rev>; defaults to the previous commit.
BASE="${BASE:-HEAD~1}"

echo "=== VERIFICATION BUNDLE FOR SOL ==="
echo "commit:  $(git rev-parse HEAD)"
echo "tree:    $([ -z "$(git status --porcelain)" ] && echo clean || echo DIRTY)"
echo "review base: $BASE ($(git rev-parse --short "$BASE" 2>/dev/null || echo UNKNOWN))"
echo "invoked as:  sol_bundle.sh ${*:-<defaults>}"
echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo

echo "--- git ---"
echo "commit:  $(git rev-parse HEAD)"
echo "branch:  $(git rev-parse --abbrev-ref HEAD)"
if [ -n "$(git status --porcelain)" ]; then
    echo "tree:    DIRTY -- the files below are not the files at that commit"
    git status --short | sed 's/^/         /'
else
    echo "tree:    clean"
fi
echo "remote:  $(git remote get-url origin 2>/dev/null || echo none)"
echo
echo "recent commits:"
git log --oneline -8 | sed 's/^/  /'
echo

echo "--- tests ---"
# Never let a failing suite abort the bundle: a red result is exactly the thing
# Sol most needs to see.
"$PY" -m pytest -q 2>&1 | tail -15 || true
echo

echo "--- changed since $BASE (manifest; not chosen by the caller) ---"
if git rev-parse --verify --quiet "$BASE" >/dev/null; then
    git diff --stat "$BASE"..HEAD | sed 's/^/  /'
else
    echo "  BASE $BASE does not resolve -- no manifest, and no diff below."
fi
echo

echo "--- complete diff since $BASE ---"
if git rev-parse --verify --quiet "$BASE" >/dev/null; then
    git diff "$BASE"..HEAD
fi
echo

echo "--- files ---"
for f in "${FILES[@]}"; do
    if [ ! -f "$f" ]; then
        echo "MISSING: $f"
        continue
    fi
    echo
    echo "########## $f ($(wc -l < "$f") lines, sha256 $(sha256sum "$f" | cut -c1-12)) ##########"
    cat -- "$f"
done

echo
echo "=== END BUNDLE ==="
