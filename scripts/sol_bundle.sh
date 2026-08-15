#!/usr/bin/env bash
# Build a pasteable verification bundle for Sol.
#
# Sol has no filesystem, no shell and no git client, so it cannot check a claim
# like "28 tests pass at commit abc123" -- it can only take Claude's word for
# it. That is a real gap in an adversarial-review arrangement: the reviewer is
# reviewing a description of the work rather than the work.
#
# This produces the evidence in one block the student can paste. It is
# deliberately generated rather than hand-written, so it cannot flatter.
#
# Usage:
#   scripts/sol_bundle.sh                        # default: identity-critical files
#   scripts/sol_bundle.sh src/bu/env/gridworld.py
#   scripts/sol_bundle.sh > bundle.txt

set -euo pipefail
cd "$(dirname "$0")/.."

FILES=("$@")
if [ ${#FILES[@]} -eq 0 ]; then
    FILES=(src/bu/constants.py src/bu/config.py)
fi

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

echo "=== VERIFICATION BUNDLE FOR SOL ==="
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
