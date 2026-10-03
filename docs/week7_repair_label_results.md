# Week-7 Experiment-1 repair labels — verified results
Sol2, 2026-08-31. All 30 Experiment-1 configuration-conditions have completed,
independently source-reverified repair labels. This is an E1 label report, not
whole-Week-7 completion or external Sol certification. Overall execution and
remaining human obligations are recorded separately in `week7_execution_results.md`.

## Counts and scope

| E1 outcome | Units |
| --- | ---: |
| Estimation failure, observed 0 | 29 |
| Hypothesis-class failure, observed 1 | 0 |
| Ambiguous | 0 |
| Undiagnosed | 1 |
| Labelled total | 30 |
| Pending / blocked | 0 / 0 |
| Decidable 0/1 units | 29 |
| min(N0, N1) | 0 |

These are 30 units in five comparison groups, not 576 independent units.
The minimum is E1-only, not a whole-design or held-out adequacy assessment.
No Week-8 exclusion rate, reserve trigger, replacement or design expansion is
computed. The historical smoke and first-sweep outcomes stay separate.

The six shape/uniform conditions use seeds 1000–1019 (20; df=19). The other
24 conditions use seeds 1000–1002 (three; df=2). D-157 advances six already-owed
validation ladders without adding overall replications. The historical
five-seed H1 report is unchanged; its additional seeds are not silently added
to these three-seed label tests or combined with the new validation baselines.

## Method and complete per-unit results

Both repairs use each baseline seed's original strict failure set:
normalized movement error > 0.610702633857727, never equality. Data repair uses
the fixed 10x budget. Every model repair here is the distinct width 256→512
`capacity_extension_repair`; it does not add data. Baselines are five-member
ensembles; repairs are single models. Statistical replication is by seed,
not model member, episode, transition, copied file or execution role.

Effect is repaired minus baseline error, averaged within each seed and then
equally across seeds. Each displayed CI is the two-sided 95% t interval on those
seed means (method `paired_seed_cluster`), not a bootstrap, pooled-transition
or simultaneous interval. Acceptance requires ALL of effect < 0, CI upper < 0 and
relative reduction > 0.20. Exactly 20% or an interval touching zero does not pass.
Reduction is -effect / the equal-seed baseline mean; negative values indicate
a point-estimated increase in error.

All 60 arm intervals formed (`converged=true`); undefined/null intervals: 0.
Here `converged` concerns interval formation, not neural optimizer convergence.
Values below are rounded only for display (six decimals; percent two decimals).
Stored full-precision values and original reason strings are retained in the
hash-bound VERIFY receipt and labels. Verdicts are not recomputed from rounding.
Observed 0 means data passed and model failed; undiagnosed means neither passed.

| Unit ID | Configuration | N | Seeds | Observed label | Data effect [95% CI] | Data reduction % | Model effect [95% CI] | Model reduction % |
| --- | --- | ---: | ---: | --- | --- | ---: | --- | ---: |
| acc42cb149c7 | shape/uniform | 100 | 20 | 0 | -0.912113 [-0.940240, -0.883987] | 64.45 | -0.064780 [-0.181689, 0.052130] | 4.58 |
| de450aa09962 | shape/uniform | 250 | 20 | 0 | -0.738945 [-0.823253, -0.654637] | 66.85 | -0.118903 [-0.244142, 0.006336] | 10.76 |
| 89aa103104e5 | shape/uniform | 500 | 20 | 0 | -0.485239 [-0.505731, -0.464746] | 57.33 | 0.017900 [-0.010902, 0.046701] | -2.11 |
| 4713db8689d2 | shape/uniform | 1000 | 20 | 0 | -0.366478 [-0.385630, -0.347326] | 46.91 | 0.035013 [0.001198, 0.068829] | -4.48 |
| 835e1b5de74e | shape/uniform | 2500 | 20 | 0 | -0.220345 [-0.233319, -0.207370] | 30.99 | 0.004675 [-0.016840, 0.026189] | -0.66 |
| 8d3643edf353 | shape/uniform | 5000 | 20 | 0 | -0.204136 [-0.220469, -0.187803] | 29.90 | 0.007284 [-0.018891, 0.033458] | -1.07 |
| 9a5de26e672e | shape/sparse | 100 | 3 | 0 | -1.011508 [-1.116374, -0.906642] | 69.97 | -0.069127 [-0.647021, 0.508767] | 4.78 |
| 805e29ef457e | shape/sparse | 250 | 3 | 0 | -0.859991 [-1.368052, -0.351930] | 75.04 | -0.250454 [-1.048206, 0.547297] | 21.85 |
| e63cd4216508 | shape/sparse | 500 | 3 | 0 | -0.524820 [-0.564361, -0.485279] | 65.04 | 0.060488 [-0.153667, 0.274643] | -7.50 |
| 2d22cee3c2fd | shape/sparse | 1000 | 3 | 0 | -0.394211 [-0.447818, -0.340605] | 53.01 | 0.047620 [0.015352, 0.079888] | -6.40 |
| 999a120de9bb | shape/sparse | 2500 | 3 | 0 | -0.316781 [-0.418022, -0.215541] | 46.23 | -0.019664 [-0.164025, 0.124696] | 2.87 |
| d0de22a1dedf | shape/sparse | 5000 | 3 | undiagnosed | -0.336981 [-0.985570, 0.311608] | 51.87 | -0.041851 [-0.095122, 0.011420] | 6.44 |
| a868dc602b1a | colour/uniform | 100 | 3 | 0 | -0.839342 [-1.208887, -0.469796] | 62.66 | -0.077327 [-0.568954, 0.414300] | 5.77 |
| ba6ef0c75746 | colour/uniform | 250 | 3 | 0 | -0.828932 [-1.346155, -0.311708] | 69.81 | 0.072032 [0.038400, 0.105663] | -6.07 |
| 89eddbe2121a | colour/uniform | 500 | 3 | 0 | -0.567463 [-0.653460, -0.481466] | 63.99 | 0.016956 [-0.190399, 0.224312] | -1.91 |
| dfcac7080a9b | colour/uniform | 1000 | 3 | 0 | -0.431336 [-0.484300, -0.378372] | 54.11 | -0.007995 [-0.144857, 0.128868] | 1.00 |
| 0134c5669ed3 | colour/uniform | 2500 | 3 | 0 | -0.195866 [-0.324319, -0.067413] | 27.92 | -0.006320 [-0.190882, 0.178243] | 0.90 |
| 8dd1c7918310 | colour/uniform | 5000 | 3 | 0 | -0.143665 [-0.224576, -0.062754] | 21.46 | -0.014761 [-0.143354, 0.113831] | 2.21 |
| 92380c22dbdb | colour/clustered | 100 | 3 | 0 | -0.958946 [-1.057288, -0.860604] | 66.54 | -0.078271 [-0.621791, 0.465249] | 5.43 |
| e26546bd7cfa | colour/clustered | 250 | 3 | 0 | -0.775807 [-1.231560, -0.320055] | 67.13 | -0.096999 [-0.395297, 0.201299] | 8.39 |
| e7c7ebbf665d | colour/clustered | 500 | 3 | 0 | -0.418411 [-0.482649, -0.354173] | 50.22 | 0.039847 [-0.069607, 0.149301] | -4.78 |
| b5785fa36eab | colour/clustered | 1000 | 3 | 0 | -0.324985 [-0.398275, -0.251695] | 41.06 | -0.010668 [-0.215816, 0.194480] | 1.35 |
| 5e6bb0bb288d | colour/clustered | 2500 | 3 | 0 | -0.226531 [-0.285191, -0.167870] | 31.59 | 0.014106 [-0.136286, 0.164497] | -1.97 |
| 572f08ad126f | colour/clustered | 5000 | 3 | 0 | -0.287517 [-0.553004, -0.022030] | 41.26 | 0.004709 [-0.099781, 0.109199] | -0.68 |
| c3ba5c14c970 | shape/clustered | 100 | 3 | 0 | -0.825914 [-0.891578, -0.760251] | 59.86 | 0.046024 [-0.013709, 0.105757] | -3.34 |
| 0bdb3331fb85 | shape/clustered | 250 | 3 | 0 | -0.812004 [-1.167745, -0.456263] | 67.99 | 0.101215 [-1.006840, 1.209270] | -8.47 |
| 781608ef0f61 | shape/clustered | 500 | 3 | 0 | -0.469554 [-0.508919, -0.430189] | 53.49 | 0.067106 [-0.056146, 0.190358] | -7.65 |
| e5f44b0e1b5c | shape/clustered | 1000 | 3 | 0 | -0.355104 [-0.367001, -0.343208] | 43.54 | -0.024849 [-0.104425, 0.054726] | 3.05 |
| 6a0525a362a6 | shape/clustered | 2500 | 3 | 0 | -0.238950 [-0.344888, -0.133011] | 32.57 | 0.000922 [-0.026808, 0.028653] | -0.13 |
| 87f89a612937 | shape/clustered | 5000 | 3 | 0 | -0.320826 [-0.484713, -0.156939] | 45.74 | 0.012060 [-0.105284, 0.129404] | -1.72 |

## The undiagnosed condition

Unit `d0de22a1dedf` is shape/sparse at N5000, using three seeds. Data repair
has effect -0.3369810867433747 and CI
[-0.9855698736886995,0.31160770020195017], with relative reduction
0.5186640119016979. Its substantial point improvement is not sufficient:
the seed-level interval crosses zero. Model repair has effect
-0.04185124039649963, CI[-0.09512235074259584,0.011419869949596574],
relative reduction0.06441528353085732; it fails both the interval and practical
criteria. This is not proof that either intervention can never work.

The acceptance records contain 7 seed-scoped represented episodes and 32
long-form rows from the two arms (16 matched transition pairs). These are not
additional independent replications. No fallback method, wider budget, added
seed, new threshold, relabelling or preferred subset follows this outcome.

## Reason-text corrigendum — original evidence preserved

The existing `acceptance.py` failure explanation uses “includes zero” whenever
the interval is not wholly below zero. That phrase is inaccurate for three
model-repair intervals that are entirely positive:

| Unit | Actual model-repair 95% interval | Correct description |
| --- | --- | --- |
| 2d22cee3c2fd | [0.01535236149483478,0.07988776813443615] | Entirely above zero; fails the negative-interval criterion. |
| 4713db8689d2 | [0.001197936604504117,0.06882866142885954] | Entirely above zero; fails the negative-interval criterion. |
| ba6ef0c75746 | [0.0384003042054459,0.10566277365132962] | Entirely above zero; fails the negative-interval criterion. |

Their effects are positive and acceptance is correctly false. No numerical
estimate, bound, boolean or observed label changes. This report corrects the
description; it does not rewrite immutable reason strings. A future global
message change needs explicit compatibility treatment because strict label
readers compare source-rederived documents. That maintenance issue is flagged
for Sol; original-source replay continues to use the genuine frozen revision.

## Provenance and readback

- Historical E1 fit commit: `f036fe02c4c9fe2fb756d65480186c8e10f7d48e`.
- New E1 execution and both finalizer modes: clean `master` at
  `1f302d1a05425827229e6ba3f41010a2b003c6f1`.
- 150 historical baselines preserved; 102 label-required historical pairs,
  90 new baseline ensembles and 384 single-model repairs give 576 verified
  source/copy pairs. Each label export root contains 576 copied fit trees.
- New E1 production: 474 physical fits /834 member models, 474 executed and
  copied, 0 resumed, no launch/release failure. Launch report SHA256:
  `e7c526bda8dcd9d8ae6f94caa79f32e03021503261aeefd5e93b50a3f9ec4c26`.
- Driver `exp1_label_finalization_driver.py` SHA256:
  `040614a2486348559a87024d7a0ffb318485e6b088817881df37e77993a7e340`.
- Manifest SHA256:
  `f5a186b930c202355343c88fec4a4199c5cc6391a1a05a304ea76d990e7aef92`.
- Semantic manifest digest:
  `42afcb8f3c74920b46fe12cc6937004dc2db3115f4bce714f627c000f694e628`.
- CREATE receipt SHA256:
  `9fba98b2628b17bd7af1826e492473c215655ce6c65c4946fd0cb7b537c252f2`.
- Independent VERIFY receipt SHA256:
  `cedcaa3a08ff329d55096519095747aa23b29b48573140cc88486aa50cffcb10`.
- CREATE and VERIFY each exited 0; call times 4070.2925336000044 s and
  3138.0629666000023 s, respectively. These are bookkeeping/readback wall times,
  not training or GPU hours. Both modes executed/retrained 0 models.
- The reader processes had stopped, the common lease was absent, and the
  original checkout was still clean when main pinned both VERIFY copies.

Preparation/receipts:
`D:/Aenv/pro/pro/week7-execution-preparation-2026-08-31-attempt-001`.
Exports:
`D:/Aenv/pro/pro/week7-exp1-labels-2026-08-31-attempt-001` and its
`-project-evidence` counterpart. Each label is
`<export>/<unit_id>/label_evidence.json`. Original and independent copies
are separate files on the same D volume, not off-device backups. A metadata
packet alone does not replace the raw source and copied trees for replay.

| Unit ID | Immutable label file SHA256 |
| --- | --- |
| acc42cb149c7 | af0fb516856171ac9e39ba136c19d061a5c337b6c276194fe184dd6724608ce3 |
| de450aa09962 | 259357cf63d6b05d8a11336aa69477f814040e4c65371cc3674ddceee83d1d84 |
| 89aa103104e5 | 174afe303391a723b70529666e729131c35a2c5e902b1fb6276541e83aba8154 |
| 4713db8689d2 | b2bdc9b21b9e6741115dcf3e2b57a557e28d1ba0115348ac2c70000f0e4b9124 |
| 835e1b5de74e | c16028725f307af02fc0fe711710ebbc3a0a6e01cd6bf1db06d8e1070fc8aec8 |
| 8d3643edf353 | 15a3db11d05b3b1028dfbd0410b48669912a2df5a844cac100cf3b7d943a4dd8 |
| 9a5de26e672e | 3868a86ff24a3c5d70f64c638fd60ffe753dece4d407e20034fb72d5df8b4daa |
| 805e29ef457e | 32ea11227c25d3ad4b4ae86140d2f8079f20fa6bcae216af6dfcd311da13961c |
| e63cd4216508 | c61f7270f0403b0d097cfa173022a9587a334c757324bb2e249261e2e53b2c4c |
| 2d22cee3c2fd | b97eeb69f95f8930bae7136dbc1410cc6a8e60a33d10c25429cd2041b3232083 |
| 999a120de9bb | e215457b1d92e2f5112dcd20666b5bc35942396eaa40142a4a7cdb8a615ff8fb |
| d0de22a1dedf | afb02ed5668de5ee6516287c785afd8b35f9c8ba54b5913d4a9474c5e2c512be |
| a868dc602b1a | 1c53be7eeb4b989e878faa7f89a79352b82208d70d372dbd88f45db40ff084d1 |
| ba6ef0c75746 | 76a152c80f4fa052078b1b666e91c10e8b7100021242c74ac1556f6d0b1cccc1 |
| 89eddbe2121a | 3d999a43a286e050b00afaf0348f87150ec0d9dd9bc621f478a62217ef7adad3 |
| dfcac7080a9b | fd568ff70cb5a7b60d383db93a892f187f6598eec683da1515d9fb1a97208205 |
| 0134c5669ed3 | 8d8e6c202bcd54432cfc79ebb79e59aeca5914a100b32413b3b2b5c2bd8f426a |
| 8dd1c7918310 | ca59fa784e9ea786f98b7342bee4fd31db0b2200e8ba879fe3b9e9a68b0acbc7 |
| 92380c22dbdb | bc4b0d23eaf66a5f28003d1b29386311fad59c241513a39e7d258ef164f99684 |
| e26546bd7cfa | 1a93f0d1f98d3f4899332a02430f6083736b588ce1fc94898529c1cbcee69abf |
| e7c7ebbf665d | d543daa6891efe051808dadff8d13e08bc7d21e567c7f9ab04aa26a7fae9371c |
| b5785fa36eab | feec3514439932b3c351a9118f0cafeae748b24bbc1aae4cc21a9c1cb777cddc |
| 5e6bb0bb288d | fe26a678b9dc73fdf519d0631b7423038dbba57e1a44471c40bef0bebbbc034d |
| 572f08ad126f | d99bf7a0b02775b35dc0c04dc3c19cf8ae0451a459edcfa669ef8f7f9f91b3fc |
| c3ba5c14c970 | e18b373fce27dd78522ca3bd49a4ba7cde8c8ef99b319f5170d553099cc5c8ac |
| 0bdb3331fb85 | 1c3fa682df1193c56bd6fb07796bb0773177a01e1d384f812cbdde7e284ee349 |
| 781608ef0f61 | 3eeca90477831957a8bc75c75f85aed73c1d08e090afbb5ed2545d52b6c43aac |
| e5f44b0e1b5c | 72effe6500c7d0103bf85b960e07d16618e2f09187e653bf8569cb3469b76219 |
| 6a0525a362a6 | ba885a4af52dfe0bf871470bc296746f26ddb079c1e133681f1a8d9bf8472127 |
| 87f89a612937 | 22d034cd2b8457f7ac5daf79f7fff7510201d2cabcc7a6debd6bb922b93474d9 |

## Interpretation limits

D-154's capacity extension and H1 reporting amendment were post-collection and
partially exposed, not pristine preregistration. D-159/DEV-021's earlier
untrained-fixture input exposure remains disclosed; later development-only
fixture RNGs do not erase it. Fixed jobs and seeds were retained without
outcome-driven replacement, tuning or threshold recalibration.

D-156's existing five-configuration trend report and figures are reused unchanged,
including their discrete-bootstrap support/mass table. The label t intervals
above are a different procedure. No additional H1/H2/H3 test or full H1 verdict
is produced here; Week 10 interprets the same immutable trend report with the
repair evidence. Gate 1 remains FAIL on power, and local CPU timings do not
adjudicate the GPU-hour gate. Student own-voice prose and external Sol review
remain separate obligations.
