# 10. Quality requirements

The quality goals of chapter 1, each made testable by scenarios. A
scenario names a stimulus, the response the benchmark must give, and what
checks it.

## 10.1 Q1, fairness

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q1-1 | The model's behaviour drifts during a round | The drift lands across every arm of a block, not on one arm | Interleaved blocks, `harness.py` |
| Q1-2 | An agent writes its own `ruff.toml` | Every arm is still measured under `toolconfig/` | `score.py` |
| Q1-3 | A trial packages its tests in an extra | Coverage still runs, from the trial's declared groups within the lock | `score.py` |
| Q1-4 | The spec requires HTMX, whose attributes HTML lacks | HTML validity sets aside `hx-*` errors and records how many | `score.py` |

## 10.2 Q2, pre-registration

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q2-1 | A primary's interval contains zero while its mean exceeds the smallest change that matters | The report names the rows that owe K = 5 and the command that settles it | `report.py --self-test` |
| Q2-2 | Someone asks for K = 6 | The harness refuses, and the report refuses a run past 5 | `harness.py`, `report.py` |
| Q2-3 | A check is added after the results were seen | It prints in its own section with no verdict | `report.py` |
| Q2-4 | A grader is found to measure something else | Every run that revision graded loses the metric, named with its reason | `withdrawn.json`, `report.py --self-test` |

## 10.3 Q3, isolation

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q3-1 | The owner has a global `CLAUDE.md` | The bare arm never sees it, and the harness refuses a root a context file above it would reach | `harness.py` |
| Q3-2 | A trial runs `git clone` of the hidden suite in its shell | The clone has no credentials, the transcript scan flags it, and the trial is voided and re-run once | `harness.py --self-test` |
| Q3-3 | An agent stops its dev server by process name | The command is denied. One that ran voids the trial | Deny rules, transcript scan |
| Q3-4 | A background server outlives the CLI | Every process from the trial's directories is stopped before the freeze | `harness.py --self-test` |

## 10.4 Q4, honest measurement

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q4-1 | A tool is pointed at an empty `src/` | The metric is missing, not zero, and the report shows the files and lines each tool saw | `score.py --self-test` |
| Q4-2 | The judge returns scores without reading the code | The evidence check finds its quotes missing from the bundle | `judge.py`, the report's evidence line |
| Q4-3 | A judge row cannot move | The control fixture shows it fail to fall on a damaged tree or rise on an improved one | `control/control.py`, `judge.py` |
| Q4-4 | An app will not sign in its administrator | Every probe that needs it fails with the reason, so the rate cannot rise by not reaching it | `security.py` |

## 10.5 Q5, reproducibility

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q5-1 | The run root is deleted after a round | The archive restores it, and scoring and judging run on the restored root | `archive.py --restore` |
| Q5-2 | A reading changes after the archive was verified | The report refuses to write under `docs/audits/` | `archive.py`, `report.py` |
| Q5-3 | A run stops part way | The run record holds every trial it finished, and `--from` resumes at the next | `harness.py` |
| Q5-4 | A later template revision is to be measured | The same harness runs it as a candidate against the recorded baseline | Design [ch. 4.2](04-solution-strategy.md) |

## 10.6 The numbers behind the rules

**Why three trials cannot reach significance.** Three paired differences
give a bootstrap 27 distinct resamples and an exact sign test a minimum
two-sided p of 0.25.

**Why the judge reads each tree three times.**

- **Measured:** six judgings of one unchanged bundle returned readability
  4, 4, 4, 3, 4, 4. Mean 3.83, sample SD 0.41.
- **Effect:** about 0.33 standard error on a difference of two arm means at
  K = 3.
- **Why it mattered:** readability was the only primary that moved in
  rounds 1 and 2, so every verdict rested on the row that was not
  reproducible.
- **The fix:** three judgings cut that standard error by about 40 %.
- **Rows that did not need it:** eight of the eleven returned the same
  score on all six calls.

**Why the budget is $100 and the timeout two hours.** The CLI prices
`claude-sonnet-5` at $5 per million input tokens and $25 per million output.
It checks the budget between turns, so a trial can pass it by one turn's
cost. The agent that built the hidden suite's reference implementation, on
a stronger model, spent about $13 at that rate in 26 minutes. At that pace a
two-hour trial stays under the cap.

**How the hidden suite was validated.**

<!-- measured: 2026-09-24 -->
534 build checks across 18 modules and 74 change checks in
`braboj/tariff-hidden-suite`, validated before round 3's first trial.
<!-- /measured -->

- A reference implementation written from the spec alone passes every
  build check, so a correct implementation is not marked wrong.
- A second agent made the change task on that reference from the change
  prompt alone. It passes every change check, and the build suite still.
- A mutation control plants twelve spec violations one at a time, and the
  suite catches all twelve.
- The pre-round-3 reference, which has no sign-in, fails the sign-in
  module, so its checks cannot pass without a gate.
