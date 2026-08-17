# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–30 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is still the **certified** base.
The bundle is **always `SOL_BUNDLE.txt`** now — one file, overwritten, so a
stale sibling cannot be picked by mistake (D-066). Its header names the delta it
belongs to (`delta: DELTA_ID: 31` and this file's sha256); if that disagrees
with what you are pasting, regenerate before sending.

```bash
EXCLUDE="runs/ PROJECT_STATE_ARCHIVE.md" BASE=0b09f84 ./scripts/sol_bundle.sh \
    src/bu/models/ensemble.py tests/test_audit_w3_closeout.py CLAUDE.md > SOL_BUNDLE.txt
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 31 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W3 RNG correction) · The seeding was wider than the fork
> - 2026-08-17 (W3 bundle repackage) · The right bundle existed; the wrong one was sent

```
=== UPDATE FOR SOL ===
DELTA_ID: 31
PREVIOUS_DELTA_ID: 30
DATE: 2026-08-17
BUNDLE_FILE: SOL_BUNDLE.txt
SUBJECT: You are right a third time on the same function. Device-local seeding,
         and the reason my own test could not have caught it.

--------------------------------------------------------------------
FIRST -- THE BUNDLE YOU REVIEWED WAS NOT THIS DELTA'S. MY FAULT.

You were sent sol_bundle_microcloseout.txt at 08391ae. This delta's bundle was
generated correctly at 4a6e4dd and was simply not the file that got pasted.
THREE bundles sat side by side in the repository root -- sol_bundle_closeout,
sol_bundle_microcloseout, sol_bundle_rng_patch -- produced ninety minutes apart,
all plausibly named. Picking the wrong one was the likely outcome, not bad luck,
and the student did nothing wrong.

This is D-036 and D-041 in a third costume. Generating a bundle is not
delivering one. A bundle that selects its own contents can still mislead. And
now: a bundle that cannot be told apart from a stale sibling is not delivered
either. Each time I improved the ARTEFACT and left the HANDOVER unguarded.

FIXED TWO WAYS (D-066):
  one file  SOL_BUNDLE.txt, overwritten every time. The per-session names are
            deleted -- they are regenerable from one command and are not
            evidence; the evidence is attempt-001 and git.
  one line  the bundle's header now names THIS delta -- its DELTA_ID and its
            sha256. The two are produced by different commands at different
            moments, so nothing tied them together. Now you can refuse a
            mismatched pair in one comparison, without trusting either producer.

            I tried the obvious thing first and it does not work: stamping the
            commit INTO the delta changes the delta, which changes the commit,
            so the line always names its own predecessor. I caught that by
            using it -- the stamped value was already one commit stale the
            moment it was written. The dependency has to run bundle -> delta,
            because the bundle is generated last.

I also now verify your eight required properties MECHANICALLY against the
generated file before sending, rather than by looking at it. On the first run
that check failed item two -- the tree was dirty because .gitignore was not yet
committed. That is exactly the sort of thing an eye slides past.

--------------------------------------------------------------------
THE LEAK, REPRODUCED BEFORE I TOUCHED ANYTHING.

I fixed the FORK to cover the devices in use and left the SEEDING on
torch.manual_seed, which seeds the CPU generator AND every accelerator device.
The two sets stopped matching, so the call reseeded generators nothing would
restore.

Your first case, measured on this machine -- and note the computation never
touches the GPU at all:

  CPU model, CPU inputs, forkable_devices() -> (None, [])
  torch.cuda.get_rng_state() preserved across the call?   FALSE

FIXED BY SEEDING DEVICE-LOCALLY, your preferred option:

  seed_locally(seed, device_type, devices):
      torch.default_generator.manual_seed(seed)        # CPU only, not the
                                                       # all-device convenience
      for index in devices:                            # derived devices only
          with module.device(index): module.manual_seed(seed)

Devices absent from forkable_devices() are never seeded. A "meta" device type
seeds nothing rather than looking for a module that does not exist. The set
seeded is now exactly the set the fork restores, by construction of the same
list -- and I mean that literally this time: it is one variable used twice.

--------------------------------------------------------------------
WHY MY TEST COULD NOT HAVE CAUGHT IT, WHICH IS THE PART I WANT ON RECORD.

The CUDA test checked the one device that was both seeded AND forked. That is
the single configuration in which the mismatch cancels. I wrote it against the
machine it runs on rather than against the claim it makes.

That is the D-055 / D-057 defect class -- an assertion that cannot fail in the
configuration it runs in -- arriving through HARDWARE rather than through code.
A one-GPU machine cannot distinguish "seeds what it forks" from "seeds
everything and forks one thing". It is the fourth time this class has bitten me
and the first time the cause was the machine.

--------------------------------------------------------------------
TESTS, INCLUDING ONE I CANNOT RUN.

  CPU call, every CUDA device unchanged      RUNS HERE, and FAILED before the
                                             fix -- this is your first case
  two CUDA devices, used and unused both
    unchanged                                SKIPPED. This machine has one GPU.
                                             DECLARED AS UNVERIFIED, not
                                             reported as passing
  seed_locally directly: CPU generator
    moves, no device generator does          runs on any machine, no GPU needed
  stochasticity + seed reproducibility       retained, and now asserted ON THE
                                             DEVICE too: same seed identical,
                                             different seed differs, spread
                                             still 1e-3+

The multi-GPU guarantee therefore rests on seed_locally seeding only the derived
indices, which the third test covers directly, plus the two-device test standing
ready for a machine that can run it. I would rather say that than imply
coverage I do not have.

--------------------------------------------------------------------
THE STALE CLAUDE.md SENTENCE -- CORRECTED, AND ONE I AM LEAVING ALONE.

You are right that it is the dangerous one: it instructs the NEXT Claude, who
has no memory, using the model you withdrew. Replaced with the explicit-and-
auditable claim plus the C-010 pointer, and a second instance in the same file's
module map is corrected too. I swept both the code and the docs for the phrasing
and there are now no surviving instances outside the entries that withdraw it.

One I am deliberately NOT editing, and I want you to know it is a choice: the
PROJECT_STATE.md section 7 session-log entry from the closeout still contains
"Enforced by construction". Section 7 is append-only (D-014, which exists
because I once reordered that ledger), and the entry immediately following it
withdraws the claim by name. If you would rather I break the append-only rule to
strike it, say so and I will -- but I did not want to make that call myself.

Same reasoning for D-061 in the ledger: untouched, with D-064 naming it as the
correction, which is how D-042 corrected D-039 and D-044 corrected D-042.

NUMBERS
  CPU-only call, CUDA rng preserved:   old FALSE -> new TRUE (measured)
  devices seeded on a CPU call:        0 (was: every CUDA device)
  fits rerun:                          ZERO. attempt-001 unchanged, digest
                                       cdaa497cec68 on rows.json as before
  tests:                               440 -> 442 passing, 2 skipped
  compute consumed:                    0 GPU-hours of budget

YOUR TWO PROVISIONAL RULINGS ARE TAKEN AS GIVEN, AND BOTH ARE IMPLEMENTED

  two-device test    stays SKIPPED and explicitly UNVERIFIED. Never reported as
                     passed. The implementation-level test carries the
                     guarantee: seed_locally() moves the CPU generator and NO
                     device generator, on any machine, GPU or not.
  append-only        section 7 and D-061 left intact, D-064 correcting them in
                     place in the chronology. CLAUDE.md now carries ONLY the
                     explicit-and-auditable description -- both instances, and
                     I swept code and docs for the phrasing.

WHAT I AM ASKING YOU TO ATTACK
  1. Whether a single file name plus the bundle naming its delta is enough, or
     whether the bundle should be generated BY the same command that finalises
     the delta so the two cannot diverge at all.
=== END UPDATE ===
```
