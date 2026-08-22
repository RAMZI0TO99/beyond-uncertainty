#!/usr/bin/env bash
# Deliver a complete immutable evidence directory to Sol.
#
# WHY THIS EXISTS. Delta 49 shipped a bundle that LISTED the 136 W4 threshold
# artefacts with truncated digests and carried none of their bytes. Sol withheld
# the D-035 promotion, correctly: tracking evidence in git is not the same as
# DELIVERING it to the reviewer. That is the D-041 shape -- digests with no
# files -- arriving through the delivery layer instead of through file selection
# or .gitignore. D-104 mechanised the tracking half; this is the delivery half.
#
# WHY NOT THE TEXT BUNDLE. sol_bundle.sh produces a pasteable text file. The
# error arrays are binary NumPy; a text bundle cannot carry them faithfully.
# Sol offered an archive as the first of its two options and this is it.
#
# WHY `git archive` AND NOT `tar`. The bytes are taken from the COMMIT OBJECT,
# never from the working tree. So "exactly as tracked at <commit>" is a
# structural property of how the file was built, not a claim about the state of
# a filesystem at the moment someone ran tar. A dirty tree cannot leak in.
#
# The archive is deterministic -- `git archive` stamps mtimes from the commit
# and `gzip -n` records no name or timestamp -- so anyone with the repository
# can re-derive a byte-identical file and confirm the SHA-256 below.
#
# Usage:
#   scripts/sol_evidence_archive.sh                       # W4 threshold at 84cfdb9
#   COMMIT=<sha> SUBTREE=<path> scripts/sol_evidence_archive.sh

set -euo pipefail
cd "$(dirname "$0")/.."

COMMIT="${COMMIT:-84cfdb9}"
SUBTREE="${SUBTREE:-runs/w4_threshold/attempt-001}"
OUT="${OUT:-SOL_THRESHOLD_EVIDENCE.tar.gz}"

PY=".venv/bin/python"
[ -x "$PY" ] || PY="python3"

FULL_COMMIT=$(git rev-parse "$COMMIT")

# Refuse to build from a commit that does not carry the subtree at all, rather
# than shipping an empty archive whose digest looks just as authoritative.
COUNT=$(git ls-tree -r --name-only "$COMMIT" -- "$SUBTREE" | wc -l | tr -d ' ')
if [ "$COUNT" -eq 0 ]; then
    echo "REFUSING: $SUBTREE is empty at $COMMIT" >&2
    exit 1
fi

git archive --format=tar "$COMMIT" -- "$SUBTREE" | gzip -n -9 > "$OUT"

ARCHIVE_SHA=$(sha256sum "$OUT" | cut -d' ' -f1)
SIZE=$(wc -c < "$OUT" | tr -d ' ')

# Verify the DELIVERABLE, not the repository. Extract to a scratch directory and
# recompute the threshold from the extracted bytes alone: that is the property
# Sol actually needs -- that what was sent is sufficient on its own -- and it is
# not implied by the repository being correct.
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
tar -xzf "$OUT" -C "$TMP"

"$PY" - "$TMP/$SUBTREE" "$FULL_COMMIT" "$ARCHIVE_SHA" "$OUT" "$SIZE" "$COUNT" <<'PY'
import hashlib, json, pathlib, sys
sys.path.insert(0, "src")
from bu.experiments.w4_threshold import recompute_threshold

attempt, commit, archive_sha, out, size, count = sys.argv[1:7]
d = pathlib.Path(attempt)

files = sorted(p for p in d.rglob("*") if p.is_file())
j = d / "threshold_calibration.json"
json_sha = hashlib.sha256(j.read_bytes()).hexdigest()
rec = json.loads(j.read_text())

# digest-of-array-digests: sha256 over the concatenated RAW 32-byte digests of
# the error arrays, ordered by errors_file. Reported in delta 49 with no
# recorded definition; reconstructed and pinned here so it is reproducible.
cells = sorted(rec["cells"], key=lambda c: c["errors_file"])
composite = hashlib.sha256(
    b"".join(bytes.fromhex(c["errors_digest"]) for c in cells)
).hexdigest()

value = recompute_threshold(d)

print("=== SOL EVIDENCE ARCHIVE ===")
print(f"archive            : {out}  ({size} bytes)")
print(f"built from commit  : {commit}")
print(f"files in subtree   : {count} at that commit / {len(files)} extracted")
print()
print("FULL SHA-256 (untruncated)")
print(f"  archive                  : {archive_sha}")
print(f"  threshold_calibration.json: {json_sha}")
print(f"  digest-of-array-digests  : {composite}")
print()
print("RECOMPUTED FROM THE EXTRACTED ARCHIVE ALONE")
print(f"  threshold  : {value!r}")
print(f"  recorded   : {rec['threshold']!r}")
ok = repr(value) == repr(rec["threshold"]) == repr(0.610702633857727)
print(f"  bit-identical to the recorded value and to delta 49: {ok}")
print(f"  cells      : {len(rec['cells'])}")
if not ok:
    raise SystemExit("ARCHIVE DOES NOT REPRODUCE THE THRESHOLD")
PY
