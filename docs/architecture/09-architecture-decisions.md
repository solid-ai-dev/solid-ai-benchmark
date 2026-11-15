# 9. Architecture decisions

The decisions the benchmark has taken, grouped by the part of the benchmark each
one shapes. A record under [`docs/decisions/`](../decisions/) holds one topic:
the decision as it holds today, its context and its reasons, and a History
table with every dated change to it, the superseded ones included. Each row
here gives a record's decision in one line.

- Status "Accepted" means the decision holds. "Superseded" means a later record
  replaced it, and both name each other in `supersedes` and `superseded_by`.
- A change to a topic adds a row to its record's History and updates its
  decision; a new topic gets a record of its own, from
  [`TEMPLATE.md`](../decisions/TEMPLATE.md).
- An issue `solid-ai-templates#N` is in `solid-ai-dev/solid-ai-templates`,
  where the benchmark lived until the split; `#N` is in this repository.
- Each record sits in one group. The rows run in record order.

## 9.1 The app, the arms and their inputs

What every trial builds, which context files it builds with, and what it is
told.

| Record | Decision | Status |
| ------ | -------- | ------ |
| [ADR-001](../decisions/001-the-app-under-test.md) | The app every trial builds is `tariff`, a small invoicing app on Flask, rendered on the server with Jinja and HTMX | Accepted |
| [ADR-002](../decisions/002-the-arms.md) | The arms have included a hand-written file and a `short` file at the same length, and `short`'s instruction asks the model to measure every line against the width | Accepted |
| [ADR-004](../decisions/004-the-builder-models.md) | Each round names its builder models in its registration, and none comes from the vendor of the rounds' judge | Accepted |
| [ADR-007](../decisions/007-the-baseline.md) | The baseline runs against `v2.90.0`, and a template change runs baseline and candidate head to head in one round | Accepted |
| [ADR-008](../decisions/008-the-brief-and-the-build-prompt.md) | The brief names the extension axes and the personal data, and the prompt tells every arm the spec is the approved plan and nobody will answer | Accepted |

## 9.2 What a trial is measured on

The tests, tasks, metrics and probes that score a trial without a judge.

| Record | Decision | Status |
| ------ | -------- | ------ |
| [ADR-006](../decisions/006-the-hidden-suite.md) | The hidden suite lives in a private repository and is written and validated before any trial | Accepted |
| [ADR-009](../decisions/009-the-change-task.md) | The change task adds a spend threshold and a capped rate, and its prompt states everything its grader checks | Accepted |
| [ADR-011](../decisions/011-html-validity-and-size.md) | HTML validity sets aside `hx-*` errors, and size reads app code against a band of 20 % | Accepted |
| [ADR-012](../decisions/012-security-and-data-protection.md) | Security and data protection are primary, each read by an anchored judge row and a probe pass rate | Accepted |
| [ADR-018](../decisions/018-the-security-probes.md) | A probe the trial keeps from running is lost, SQL counts only untraced values, and sign-in is read beside an anonymous client | Accepted |

## 9.3 The judge

Which model judges, how its rows are anchored, and who else may score.

| Record | Decision | Status |
| ------ | -------- | ------ |
| [ADR-005](../decisions/005-the-judge.md) | The rounds' judge is `gpt-6-astra` through `codex exec` at effort `high`, alone, three times per trial | Accepted |
| [ADR-014](../decisions/014-no-human-holdout.md) | No implementation is scored by a person | Accepted |
| [ADR-016](../decisions/016-anchors-control-fixture-and-repeats.md) | The primary rows are anchored and checked by the control fixture, and each tree is judged three times | Accepted |

## 9.4 Blocks, contrasts and the report

How many blocks a round runs, when a contrast gets a verdict, and what the
report shows first.

| Record | Decision | Status |
| ------ | -------- | ------ |
| [ADR-003](../decisions/003-k-blocks-and-escalation.md) | A round fixes K before its first trial, 15 from round 5, and no run goes past it; the escalation of rounds registered at K = 3 retired with them | Accepted |
| [ADR-013](../decisions/013-what-the-report-opens-with.md) | The report opens with the finding table, and keeps the score table only for contrasts between two files | Accepted |
| [ADR-015](../decisions/015-contrasts-and-verdicts.md) | A contrast gets a verdict only when both its arms run in the same round | Accepted |
| [ADR-023](../decisions/023-the-iso-radar.md) | From round 6 the radar reads ISO/IEC 25010:2023: eight axes, each the share of its targets met against `none`, a marker only past the axis's margin, the cost shown above | Accepted |
| [ADR-024](../decisions/024-verdicts-read-the-iso-radar.md) | From round 6 an arm's verdict and round 6's screen read the ISO radar's axes; a pilot round read by them is a post-hoc draft | Accepted |
| [ADR-025](../decisions/025-every-arm-is-built-by-a-script.md) | From round 6 every arm is built by a script with no model call, `inline` by the emitter's `--inline-skills`; `hybrid`, `short` and `hand` run no more | Accepted |

## 9.5 Running and keeping a round

How a trial is bounded and fenced, how a round is registered, and how it is
kept.

| Record | Decision | Status |
| ------ | -------- | ------ |
| [ADR-010](../decisions/010-trial-bounds.md) | Trials are bounded by `--max-budget-usd` and a timeout | Accepted |
| [ADR-017](../decisions/017-a-rounds-registration.md) | A round registers its spec by content, and the harness and the report refuse a trial built from other content | Accepted |
| [ADR-019](../decisions/019-archive-before-the-report.md) | A round is archived to `braboj/tariff-runs` and verified by restoring it before its report is written | Accepted |
| [ADR-020](../decisions/020-trial-isolation.md) | A trial is fenced by deny rules and excluded by its transcript, in a pen of its own; a reach voids it | Accepted |
| [ADR-021](../decisions/021-rescore-after-an-instrument-fault.md) | An instrument fault is fixed, validated and every reading round re-scored in full, its report replaced with a dated note keeping the old verdicts | Accepted |
| [ADR-022](../decisions/022-round-names.md) | From round 6 a round is named by the knob it turns, `C`, `S`, `M` or `T`, and the count of rounds of that knob, as `C1`; trials keep their names | Accepted |

## 9.6 Decisions about the templates

The decisions about the templates themselves, such as ADR-052 (hybrid is the
delivery floor) and ADR-058 (task procedures load on demand), live in
`solid-ai-templates` under `docs/decisions/`, numbered in that repository's own
series. A round's hypotheses name the record they decide.
