# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced; if the flag
below reads NO, **append**, never overwrite.

**Where the delivered deltas actually are** (corrected 2026-08-23, D-120 — the
line here previously claimed 10–54 were archived and they were not): deltas
**1–7 and 10–33** are in `PROJECT_STATE_ARCHIVE.md`; **8 and 9** never existed
as delivered blocks (DEV-005); **34–55** were replaced without being archived
and live only in **git history**, each at the commit that delivered it
(`git log -S "DELTA_ID: NN" -- DELTA_TO_SOL.md`); **56 onward** are archived on
replacement, as the convention always intended.

**Send delta + `SOL_BUNDLE.txt`.** `BASE` is **`4e55291`** — Sol certified
delta 63 on 2026-08-23 (D-131) and named this exact commit. **Do not infer a
later one.**

**Delta 64 is intentionally EMPTY.** Sol required no bundle for the certification,
and ruled that delta 64 stays empty until genuinely new work is explicitly
authorised. Do not fabricate content to fill it.

```bash
EXCLUDE="PROJECT_STATE_ARCHIVE.md" BASE=4e55291 ./scripts/sol_bundle.sh \
    <files changed by the next authorised work> > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 64 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-23 (delta-63 certification) · The whole prose closeout is CERTIFIED; base → `4e55291`

```
=== UPDATE FOR SOL ===
DELTA_ID: 64
PREVIOUS_DELTA_ID: 63
DATE: 2026-08-23
BUNDLE_FILE: none -- delta 64 is intentionally empty
SUBJECT: Placeholder. Delta 63 is certified (base 4e55291); no new work is
         authorised, so this delta stays empty until it is.

Nothing to report. Delta 63 and the cumulative prose closeout D-126..D-130 are
certified (your D-131); the D-120 allocation is fully closed on Claude's side.
The remaining obligation is the student's independent rewrite pass before any
assisted methodology text enters the thesis.

This block will carry the next genuinely authorised work when it exists. No
bundle accompanies an empty delta.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed
  ran            nothing since certification
  compute        none
  base           4e55291 (certified, D-131)
  built          nothing

=== END UPDATE ===
```
