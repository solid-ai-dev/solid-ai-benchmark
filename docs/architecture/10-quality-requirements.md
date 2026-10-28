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
| Q1-5 | The model drifts within one block | No arm always runs first or last: each block starts one arm later | `harness.py --self-test` |

## 10.2 Q2, pre-registration

| # | Stimulus | Response | Checked by |
| - | -------- | -------- | ---------- |
| Q2-1 | In a round registered at K = 3, a primary's interval contains zero while its mean exceeds the smallest change that matters | The report names the rows that owe K = 5 and the command that settles it | `report.py --self-test` |
| Q2-2 | Someone asks for more blocks than the round allows | The harness refuses past 5, or past 15 for a round-5 run, and the report refuses a run past them | `harness.py`, `report.py` |
| Q2-3 | A check is added after the results were seen | It prints in its own section with no verdict | `report.py` |
| Q2-4 | A grader is found to measure something else | Every run that revision graded loses the metric, named with its reason | `withdrawn.json`, `report.py --self-test` |
| Q2-5 | A round-5 run holds fewer than its 15 blocks | The report calls it part-run and names the blocks still owed | `report.py --self-test` |

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
| Q5-4 | A later template revision is to be measured | The same harness runs it as a candidate against the baseline, both in one round | Design [ch. 4.2](04-solution-strategy.md) |
| Q5-5 | A report is aimed at any `docs/audits/` before the round is archived | Refused, in the templates source as anywhere else | `report.py --self-test` |

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

## 10.7 Judge validation results

Each run of the control fixture, dated, with the judge and rubric it read
under. A row is trusted once it falls and rises on its target trees under the
rounds' judge.

### Before the primaries were anchored, 2026-09-18

Judge `gpt-6-astra` at effort `high`, evidence found 100 % on every judging.
Three trees; the rubric said only that 1 was poor and 5 excellent.

| Dimension | base-1 | degraded-1 | improved-1 |
|---|---|---|---|
| design | 3 | **2** | 3 |
| maintainability | 3 | **2** | 3 |
| readability | 4 | **3** | 4 |
| dip | 5 | **1** | 5 |
| srp | 3 | **2** | 3 |
| error_design | 2 | **1** | **3** |
| ocp | 2 | 2 | **3** |
| lsp | 2 | 2 | **3** |
| isp | 4 | 4 | 4 |
| naming_and_abstraction | 4 | 4 | 4 |
| test_quality | 4 | 3 | 3 |

`design` and `maintainability` fell on damage and did not rise on improvement.
On the improved tree the evidence line the judge quoted *for* `design` was
`class Rule(ABC):` — it cited the improvement and scored it 3 anyway. The
component rows moved in both directions.

Six judgings of one byte-identical `base-1` bundle returned readability 4, 4,
4, 3, 4, 4 — mean 3.83, SD 0.41 — while eight of the eleven rows returned the
same integer every time. That is why a round judges each trial several times
and means them.

### After anchoring, 2026-09-19

Six trees, one judging each unless stated, evidence 100 % on every judging
counted. A bold cell differs from `base-1` in the same run.

#### gpt-6-astra at effort `high`, the judge the rounds use

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| **design** | 3 | **2** | 3 | 3 | **3.5** | **4** |
| **readability** | 3 | 3 | **1** | 3 | 3 | 3 |
| **maintainability** | 3 | 3 | 3 | 3 | 3 | **4** |
| dip | 5 | **1** | 5 | 5 | 5 | 5 |
| srp | 3 | **2** | 3 | 3 | 3 | 3 |
| error_design | 2 | **1** | 2 | **3** | **3** | **3** |
| ocp | 2 | 2 | 2 | **3** | **3** | **3** |
| lsp | 3 | **2** | **2** | 3 | 3 | 3 |
| isp | 4 | 4 | 4 | 4 | 4 | 4 |
| naming_and_abstraction | 4 | **3** | **2** | 4 | 4 | 4 |
| test_quality | 3 | 3 | **4** | **4** | **4** | **4** |

`improved-2` holds two judgings, meaned. The top-up to three per tree stopped
on the judge plan's usage limit after one call; the next section completes it.

#### Opus 5 through the claude backend, a cross-check on the rubric

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| **design** | 3 | **2** | 3 | **4** | **4** | **4** |
| **readability** | 4 | **3** | **2** | 4 | 4 | 4 |
| **maintainability** | 3 | **2** | 3 | **4** | **4** | **4** |
| dip | 4 | **1** | **5** | **5** | **5** | **5** |
| srp | 3 | 3 | 3 | **4** | **4** | **4** |
| error_design | 3 | **1** | 3 | **4** | 3 | **4** |
| ocp | 2 | 2 | 2 | **3** | **3** | **4** |
| lsp | 3 | **2** | 3 | **4** | **4** | **4** |
| isp | 4 | 4 | 4 | **3** | 4 | **3** |
| naming_and_abstraction | 4 | **3** | **2** | 4 | 4 | 4 |
| test_quality | 4 | **3** | 4 | 4 | 4 | 4 |

Opus 5 shares a vendor with the generator, so it cannot judge a round. It is
here to ask whether the rubric's behaviour belongs to the rubric or to one
model.

#### What the two say together

Under both judges, every primary falls on the tree built to damage it and
rises on a tree built to improve it:

- `design` falls to 2 on `degraded-1` and reaches 4 on the improved trees
- `readability` falls on `obscured-1`, to 1 under gpt-6-astra and to 2 under
  Opus 5
- `maintainability` reaches 4 once no layer names a kind, which is the tree
  `improved-3` was built to be

The judges differ in threshold, not in direction. Opus 5 credits the
improvement already at `improved-1`; gpt-6-astra waits for `improved-3`. An
arm has to improve more to register under the rounds' judge than under this
one.

Single judgings vary between runs of the same prompt. `design` on
`improved-1` read 4 in three earlier anchored runs and 3 in this one, and
`maintainability` on `degraded-1` read 2 in two earlier runs and 3 in this
one. Those are the flips repeat judging exists to average out, and why a row
is read against its target tree across more than one run before it is
trusted.

The repair is tracked in solid-ai-templates#1827.

### Three judgings per tree, 2026-09-25

gpt-6-astra at effort `high`, the same root as the single judgings above,
topped up with `--repeat 3`. Evidence found 100 % on every judging. Each
cell is the mean, followed by the three scores; a bold cell differs from
`base-1`.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| **design** | 3.00 (333) | **2.00** (222) | 3.00 (333) | **3.67** (344) | **3.67** (434) | **4.00** (444) |
| **readability** | 3.00 (333) | 3.00 (333) | **1.00** (111) | 3.00 (333) | 3.00 (333) | **3.33** (343) |
| **maintainability** | 3.00 (333) | **2.33** (223) | 3.00 (333) | 3.00 (333) | 3.00 (333) | **4.00** (444) |

Averaged over three, every primary falls on the tree built to damage it and
rises on a tree built to improve it. `design` and `maintainability` fall on
`degraded-1`, `readability` falls on `obscured-1`, and all three rise on
`improved-3`. The one-point flips of single judgings remain inside each
triple, which is what the mean is there to absorb.

### Five primaries, and a new judge, 2026-09-25

Every run below judges each tree three times; a cell is the mean. Evidence
was found 100 % on every judging.

#### gpt-6-astra, security and data protection as first anchored

The second application's trees, the only ones built to move these two rows:

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 4.00 | **2.00** | 4.00 | 4.00 | 4.00 |
| data_protection | 5.00 | 5.00 | 5.00 | **2.00** | 5.00 |

Both rows fell on the tree that damages them and rose on neither. `base-2`
already met most of what the 5s described, so no improvement had room to
register. The 3s were rewritten to describe the common defences and nothing
more, and the 5s to ask for what only the improved trees have.

The re-run under those anchors stopped on the judge plan's weekly limit
after 16 of 33 judgings, with `secured-1` not yet judged. What it had read
put `base-2` at 3 on both rows, `insecure-1` and `leaky-1` at 1 on theirs,
and `protected-1` at 5. The plan allows about thirty judgings a week and a
round needs three times as many, so the rounds' judge became
`claude-opus-5-5` ([ch. 8.6.6](../architecture/08-crosscutting-concepts.md)).

A first run through the claude backend recorded effort `high` but never
passed it, so the CLI ran at its own default. Its readings are not counted;
the backend now passes the effort, and a self-test check fails without it.

#### claude-opus-5-5 at effort `high`

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 2.00 | 2.00 | 2.33 | 3.00 | 3.00 | **4.00** |
| readability | 3.00 | 2.67 | **1.67** | 3.33 | 3.33 | **3.67** |
| maintainability | 3.00 | **2.00** | 3.00 | 3.00 | 3.00 | **4.00** |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 | **1.00** | **4.67** | 3.00 | 3.00 |
| data_protection | 3.00 | 3.00 | 3.00 | **1.00** | **4.00** |

Four rows fall and rise. `design` rises but does not fall: the judge quoted
the same concrete-class dispatch for `base-1` and `degraded-1` and scored
both 2, reading the 3's description of that dispatch as a fault below it.
The damage `degraded-1` adds, the domain merged and importing Flask, moved
`maintainability` instead. The 1 now names that damage, and the 3 says the
dispatch alone, with the layers kept apart, is not lower.

#### claude-opus-5-5 at effort `high`, design re-anchored

The rounds' judge and rubric as they stand.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 2.67 | **1.00** | 3.00 | **3.67** | **4.00** | **4.00** |
| readability | 3.00 | 2.00 | **1.67** | 3.33 | 3.00 | 3.33 |
| maintainability | 3.00 | **2.00** | 3.00 | 3.00 | 3.00 | **4.00** |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 | **1.00** | **5.00** | 3.00 | 3.00 |
| data_protection | 3.00 | 3.00 | 3.00 | **1.00** | **4.00** |

Every primary falls on the tree built to damage it and rises on one built to
improve it, and each row of the second application holds still on the trees
built to move another. The 33 judgings used about 1 % of the owner's weekly
plan.

### gpt-6-astra as round 5 registers it, 2026-10-28

The judge round 5 registers: `gpt-6-astra` through `codex exec` at effort
`high`, three judgings per tree, under the rubric as it stands. All 33
judgings took, with evidence found 100 % on every one. Each cell is the mean,
followed by the three scores; a bold cell differs from its application's base
tree.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 3.00 (333) | **1.00** (111) | 3.00 (333) | **4.00** (444) | **4.00** (444) | **4.00** (444) |
| readability | 3.00 (333) | 3.00 (333) | **1.00** (111) | 3.00 (333) | 3.00 (333) | 3.00 (333) |
| maintainability | 3.00 (333) | **1.33** (121) | 3.00 (333) | 3.33 (433) | 3.67 (434) | **4.00** (444) |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 (333) | **1.00** (111) | **5.00** (555) | 3.00 (333) | 3.00 (333) |
| data_protection | 3.00 (333) | 3.00 (333) | 3.00 (333) | **1.00** (111) | **5.00** (555) |

Four primaries fall on the tree built to damage them and rise on one built
to improve them. `readability` falls on `obscured-1` but reads 3 on every
improved tree, none of which was built to improve it. So `clarified-1`, the
mirror of `obscured-1`, was added to the control and judged in the same root,
three times:

| Dimension | base-1 | clarified-1 |
|---|---|---|
| design | 3.00 (333) | 3.00 (333) |
| readability | 3.00 (333) | **3.67** (434) |
| maintainability | 3.00 (333) | 3.00 (333) |

`readability` rises on the tree built to improve it, and the other two rows
hold still there. With that, every primary falls on the tree built to damage
it and rises on one built to improve it. The rise is the smallest in the
run: one of the three judgings read 3, so a single judging would have missed
it. The second application's rows hold still on the trees built to move
another.

The re-anchored rubric reads the same under gpt-6-astra as under
claude-opus-5-5, with sharper steps: `design` reaches 4 from `improved-1`, and
the four rows of the second application read 1 or 5 on all three judgings.

`security` is also read on the first application, where no tree is built to
move it. There its triples spread from 2 to 4, a one-point flip between
judgings of the same bundle, which the three judgings per trial are there to
absorb.

The first 33 judgings took 70 minutes and used about 11 % of the OpenAI
plan's weekly limit: it read 3 % used before and 14 % after. A block of 75
trials at three judgings each would take about 75 %. The three judgings of
`clarified-1` came after.
