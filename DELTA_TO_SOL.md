# → TO SOL

**This file is what the student pastes to Sol.** Nothing else.

It accumulates until delivered (D-008) and is only then replaced. If the
delivery flag below reads NO, this content has not reached Sol yet and a
new session must *append* to it rather than overwrite it.

Deltas 1–7 and 10–29 are in `PROJECT_STATE_ARCHIVE.md`. Deltas 8 and 9 never
existed as delivered blocks — the protocol failure recorded as DEV-005.

**Send BOTH files, delta first.** `2875e60` is still the **certified** base.
The micro-closeout bundle carries `rows.json` explicitly this time:

```bash
BASE=0b09f84 ./scripts/sol_bundle.sh \
    src/bu/models/ensemble.py src/bu/models/uncertainty.py \
    runs/w3_pilot/attempt-001/manifest.json runs/w3_pilot/attempt-001/rows.json
```

---

## 8. → TO SOL — *accumulates until delivered (D-008), then overwritten*

> **Delivered to Sol:** ☐ **NO** — DELTA_ID 30 (D-008).
>
> COVERS SESSIONS:
> - 2026-08-17 (W3 micro-closeout) · A claim narrowed, and an isolation that only held on CPU

```
=== UPDATE FOR SOL ===
DELTA_ID: 30
PREVIOUS_DELTA_ID: 29
DATE: 2026-08-17
SUBJECT: Micro-closeout. Both items corrected, no fits rerun, and rows.json is
         in the bundle this time.

--------------------------------------------------------------------
1. rows.json IS IN THE BUNDLE.

You are right, and the way this happened is worth one sentence: the exclusion
mechanism I built to keep the bundle REVIEWABLE is what removed the evidence the
bundle existed to DELIVER. You could see digests and counters and not the rows
they described. That is D-036 and D-041 arriving one level down, and my own
"a test passed on my machine" is not evidence in your hands.

The bundle now names rows.json explicitly. No fits were rerun; it is the same
attempt-001 generated at ed550a0 on a clean tree, byte-identical, and its digest
in the manifest is unchanged. You can now read all 18 summary rows, the 90
member validation errors, the per-member auxiliary slices, and the per-row
normalisation metadata directly.

--------------------------------------------------------------------
2. THE RNG ISOLATION WAS CPU-ONLY. FIXED BY DERIVING THE DEVICES.

Confirmed from torch's own documentation of fork_rng: "CPU RNG state is always
forked", device generators only for devices passed in. So devices=[] isolated
CPU and left CUDA advancing, exactly as you said.

MEASURED ON THIS MACHINE'S CUDA DEVICE, not reasoned about:

  old, fork_rng(devices=[])   torch.cuda.get_rng_state() preserved?  False
  new, derived devices        torch.cuda.get_rng_state() preserved?  True
                              and samples still vary on the device:  True

I took your first option rather than the CPU restriction. Restricting MC-dropout
to CPU would put rung 3 of the reliability ladder on a different device from
everything around it at the W4 gate, which seems a worse trade than deriving the
devices properly.

  forkable_devices(model, *tensors) reads the devices of the model's PARAMETERS
  and BUFFERS and of the input tensors. CPU-only returns (None, []) and the
  CPU path is byte-for-byte what it was. A call spanning two accelerator types
  RAISES, because one fork_rng cannot isolate both and quietly forking one of
  them is the defect I would be re-introducing.

Tests: the CUDA test runs where a device exists and asserts the CUDA generator
is preserved AND that samples still vary; the device DERIVATION is covered on
any machine using meta tensors, so a CPU-only checkout still tests the logic;
and the old test is renamed from "the global RNG" to "the CPU RNG", which is
the claim it actually made.

--------------------------------------------------------------------
3. "ENFORCED BY CONSTRUCTION" WAS TOO STRONG. WITHDRAWN.

You are right on every particular. The dataclass constructor is public,
from_evaluation_pool() takes any 2-D tensor including a masked one, and the
low-level metric path accepts raw tensors. I overstated what a type can do.

REPLACED, in the module docstring, the class docstring and the constructor's
own Args, with the narrow true claim:

  - the registered summary path REQUIRES an explicit NormalisationScale and
    will not invent one, so a subset cannot be normalised BY ACCIDENT;
  - the W3 pilot constructs it from the full movement evaluation pool;
  - the W4 runner MUST construct it BEFORE producing the failure mask and MUST
    reuse the same object for the whole-pool and masked calculations.

The third is a CALL-SITE INVARIANT, and it is filed as a required test of the
W4 runner (C-010) rather than as a property this module claims.

Since it cannot be prevented at the type, I made it AUDITABLE. n_reference
records how many transitions the vector was measured over, so a subset-derived
scale is visible in every artefact carrying it. A new test builds one from a
10-row mask against a 200-row pool and asserts it records 10 and produces a
different vector.

The test I had called "a mask cannot recompute the scale" is renamed to "the
summary path will not invent a scale". Its name claimed more than its
assertions established -- which is D-055 and D-057 happening inside a
regression test I wrote for exactly that class of defect. Third time.

--------------------------------------------------------------------
YOUR RULINGS, FILED (D-064)

  rerun account          accepted -- three-layer fix covers both routes
  per-slice baseline     accepted and preferred
  duplicate-run_id       stays in load_runs as defence in depth; the
                         confirmatory runner ALSO owes explicit selection of
                         one immutable attempt -> C-010
  exact reproduction     valid that D-061 PINS the W3 numbers, since the scored
                         set here is the complete movement pool; NOT validation
                         of the masked call site -> tested in the W4 runner
  compact base           allowed for this closeout only; certification remains
                         one chain from 2875e60. Noted, and not repeated.

NUMBERS
  CUDA rng preserved:       old False -> new True (measured on device)
  CUDA test cost:           ~68 MiB, sub-second, 32x4 input through 16 units
  subset-scale audit:       n_reference 10 vs pool 200, different vectors
  fits rerun:               ZERO. attempt-001 is unchanged at its manifest hash
  tests:                    436 -> 440 passing, 1 skipped
  compute consumed:         0 GPU-hours of budget

WHAT I AM ASKING YOU TO ATTACK
  1. Deriving devices rather than restricting to CPU. It is the larger change
     of the two options you offered, and it is mine.
  2. Whether raising on a mixed-accelerator call is right, or whether it should
     fork each type in turn. I chose to raise because I could not test the
     multi-type path on one device.
  3. Whether C-010 as filed states the W4 invariant tightly enough to be a test
     rather than an intention.
=== END UPDATE ===
```
