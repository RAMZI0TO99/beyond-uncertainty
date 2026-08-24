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
> - 2026-08-23 (student chapter) · The first full methodology chapter arrives; provenance disclosed

```
=== UPDATE FOR SOL ===
DELTA_ID: 64
PREVIOUS_DELTA_ID: 63
DATE: 2026-08-23
BUNDLE_FILE: none required -- student-progress report only
SUBJECT: Student-obligation progress: a full methodology chapter draft exists,
         provenance disclosed (student-written, AI-polished), audited 32/32
         clean. Defense walkthrough pending. No ruling requested.

STUDENT-OBLIGATION PROGRESS REPORT -- NO RULING REQUESTED.

The student delivered docs/methodology_chapter.md: a complete 17-topic
methodology chapter, internal apparatus stripped as the thesis version
requires. Asked directly how it was produced, THE STUDENT DISCLOSED
UNPROMPTED: they wrote the content and an AI polished the prose.

I audited it against the certified record before any judgment: 32/32
checkable claims and numbers verify exactly, zero factual errors, every
D-121..D-131 correction incorporated -- including rulings from hours earlier.

STATUS, stated in the file's committed provenance header (removed from the
final thesis version): ASSISTED DRAFT under your D-125/D-131 framework. The
explain-and-defend walkthrough is deferred at the student's request, not
waived. Until it is done and you have ruled, the chapter does not enter the
thesis and is not described as independently authored.

Nothing else to report; no Claude-side work is claimed for certification in
this delta.

--------------------------------------------------------------------
NUMBERS (D-011)

  tests          895 passing, 2 skipped, 0 xfailed
  ran            no experiment or data pipeline; only the existing suite
  compute        none
  base           4e55291 (certified, D-131)
  built          the STUDENT's chapter draft (assisted; provenance disclosed);
                 Claude built nothing and requests no ruling

=== END UPDATE ===
```
