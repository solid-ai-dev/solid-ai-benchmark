# Validation

The measurements behind the benchmark's instruments: the hidden suite, the
trial bounds, and every run of the judge's control fixture. The rules they
support are in [requirements.md](requirements.md); the reasons are in
[chapter 8](architecture/08-crosscutting-concepts.md).

## The hidden suite

<!-- measured: 2026-09-24 -->
534 build checks across 18 modules and 74 change checks in
`braboj/tariff-hidden-suite`, validated before round 3's first trial.
<!-- /measured -->

| Check | Result |
| ----- | ------ |
| A reference implementation written from the spec alone | Passes every build check |
| The change task made on it from the change prompt alone | Passes every change check, and the build suite still |
| Twelve spec violations, each planted alone | All twelve caught |
| The pre-round-3 reference, with no sign-in | Fails the sign-in module |

## Trial bounds

A trial is bounded by a budget of $100 and a timeout of two hours.

| Fact | Figure |
| ---- | ------ |
| The CLI's price for `claude-sonnet-5` | $5 per million input tokens, $25 per million output |
| When the CLI checks the budget | Between turns, so a trial can pass it by one turn's cost |
| The reference implementation's agent, on a stronger model | About $13 in 26 minutes at that rate |

At that pace, a two-hour trial stays under the cap.

## The ISO radar's margins

Sized on 2026-11-04, before round 6, from round 5c's 75 trials re-scored in
round 5d's root: each axis's per-trial score, in points, and the pooled
within-arm standard deviation over the five arms. The margin is half of it,
rounded up to a whole point, and never under 5 points, so an axis the pilot's
trials could not shake, or did not measure, still needs a visible move.

| Axis | Pooled within-arm SD, points | Margin, points |
| ---- | ---------------------------- | -------------- |
| Functionality | 5.5 | 5 |
| Performance | 0.0 | 5 |
| Compatibility | not measured | 5 |
| Usability | 0.0 | 5 |
| Reliability | 13.8 | 7 |
| Security | 5.4 | 5 |
| Maintainability | 7.8 | 5 |
| Flexibility | 0.0 | 5 |

Reliability's 7 points is one build of 15, the margin round 5d gave it.

## Why three trials cannot prove

| Test | With three paired differences |
| ---- | ----------------------------- |
| Bootstrap | 27 distinct resamples |
| Exact sign test | A two-sided p of at least 0.25 |

## The judge's control runs

Each run of the control fixture, newest first. A row is trusted once it
falls on the tree built to damage it and rises on the one built to improve
it, under the rounds' judge. The trees are described in
[ch. 8.6.7](architecture/08-crosscutting-concepts.md).

| Date | Judge | Rubric | Outcome |
| ---- | ----- | ------ | ------- |
| 2026-10-28 | `gpt-6-astra`, high, ×3 | As it stands | Every primary falls and rises; `readability` rises only on `clarified-1` |
| 2026-09-25 | `claude-opus-5-5`, high, ×3 | `design` re-anchored | Every primary falls and rises |
| 2026-09-25 | `claude-opus-5-5`, high, ×3 | Five primaries anchored | Four rows fall and rise; `design` does not fall |
| 2026-09-25 | `gpt-6-astra`, high, ×3 | Security and data protection first anchored | Both fall, neither rises |
| 2026-09-25 | `gpt-6-astra`, high, ×3 | Three primaries anchored | Every primary falls and rises |
| 2026-09-19 | `gpt-6-astra` and Opus 5, ×1 | Three primaries anchored | Every primary falls and rises under both |
| 2026-09-18 | `gpt-6-astra`, high, ×1 | Not anchored | `design` and `maintainability` do not rise |

In every table below, a bold cell differs from its application's base
tree. A cell with digits in brackets is the mean of three judgings,
followed by each score.

### 2026-10-28: `gpt-6-astra`, as round 5 registers it

`gpt-6-astra` through `codex exec` at effort `high`, three judgings per
tree, the rubric as it stands. All 33 judgings took, with evidence found
100 % on every one.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 3.00 (333) | **1.00** (111) | 3.00 (333) | **4.00** (444) | **4.00** (444) | **4.00** (444) |
| readability | 3.00 (333) | 3.00 (333) | **1.00** (111) | 3.00 (333) | 3.00 (333) | 3.00 (333) |
| maintainability | 3.00 (333) | **1.33** (121) | 3.00 (333) | 3.33 (433) | 3.67 (434) | **4.00** (444) |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 (333) | **1.00** (111) | **5.00** (555) | 3.00 (333) | 3.00 (333) |
| data_protection | 3.00 (333) | 3.00 (333) | 3.00 (333) | **1.00** (111) | **5.00** (555) |

`readability` fell on `obscured-1` but read 3 on every improved tree, none
of them built to improve it. So `clarified-1` was added and judged in the
same root:

| Dimension | base-1 | clarified-1 |
|---|---|---|
| design | 3.00 (333) | 3.00 (333) |
| readability | 3.00 (333) | **3.67** (434) |
| maintainability | 3.00 (333) | 3.00 (333) |

- Every primary now falls on its damaged tree and rises on an improved one.
- `readability`'s rise is the smallest: one judging of three read 3, so a
  single judging would have missed it.
- The second application's rows hold still on the trees built to move
  another.
- Under this rubric `gpt-6-astra` steps more sharply than
  `claude-opus-5-5`: `design` reaches 4 from `improved-1`, and the second
  application's rows read 1 or 5 on all three judgings.
- On the first application, where no tree is built to move it, `security`
  spread from 2 to 4 within a triple.
- The first 33 judgings took 70 minutes and about 11 % of the OpenAI plan's
  weekly limit (3 % before, 14 % after). A round of 75 trials at three
  judgings each would take about 75 %.

### 2026-09-25: `claude-opus-5-5`, `design` re-anchored

The rubric and judge the rounds used until round 5. Three judgings per tree;
a cell is the mean.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 2.67 | **1.00** | 3.00 | **3.67** | **4.00** | **4.00** |
| readability | 3.00 | 2.00 | **1.67** | 3.33 | 3.00 | 3.33 |
| maintainability | 3.00 | **2.00** | 3.00 | 3.00 | 3.00 | **4.00** |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 | **1.00** | **5.00** | 3.00 | 3.00 |
| data_protection | 3.00 | 3.00 | 3.00 | **1.00** | **4.00** |

- Every primary falls on its damaged tree and rises on an improved one.
- Each second-application row holds still on the trees built to move
  another.
- The 33 judgings used about 1 % of the owner's weekly plan.

### 2026-09-25: `claude-opus-5-5`, five primaries anchored

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 2.00 | 2.00 | 2.33 | 3.00 | 3.00 | **4.00** |
| readability | 3.00 | 2.67 | **1.67** | 3.33 | 3.33 | **3.67** |
| maintainability | 3.00 | **2.00** | 3.00 | 3.00 | 3.00 | **4.00** |

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 3.00 | **1.00** | **4.67** | 3.00 | 3.00 |
| data_protection | 3.00 | 3.00 | 3.00 | **1.00** | **4.00** |

- Four rows fall and rise. `design` rises but does not fall.
- The judge quoted the same concrete-class dispatch for `base-1` and
  `degraded-1`, and read the 3's description of it as a fault below it.
- What `degraded-1` adds, the domain merged and importing Flask, moved
  `maintainability` instead.
- **Fix:** `design`'s 1 now names that damage, and its 3 says the dispatch
  alone, with the layers kept apart, is not lower.
- A first run through the claude backend recorded effort `high` but never
  passed it. Its readings are not counted, and a self-test check now fails
  without the effort.

### 2026-09-25: `gpt-6-astra`, security and data protection first anchored

The second application's trees, the only ones built to move these rows.
Three judgings per tree; a cell is the mean.

| Dimension | base-2 | insecure-1 | secured-1 | leaky-1 | protected-1 |
|---|---|---|---|---|---|
| security | 4.00 | **2.00** | 4.00 | 4.00 | 4.00 |
| data_protection | 5.00 | 5.00 | 5.00 | **2.00** | 5.00 |

- Both rows fell on their damaged tree and rose on neither: `base-2`
  already met most of what the 5s described.
- **Fix:** the 3s describe the common defences and nothing more; the 5s ask
  for what only the improved trees have.
- The re-run under the new anchors stopped at the plan's weekly limit after
  16 of 33 judgings. What it read: `base-2` at 3 on both rows, `insecure-1`
  and `leaky-1` at 1, `protected-1` at 5.
- The plan allows about thirty judgings a week and a round needs three times
  as many, so the rounds' judge became `claude-opus-5-5` until round 5.

### 2026-09-25: `gpt-6-astra`, three judgings per tree

The root of the 2026-09-19 run, topped up with `--repeat 3`. Evidence found
100 % on every judging.

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 3.00 (333) | **2.00** (222) | 3.00 (333) | **3.67** (344) | **3.67** (434) | **4.00** (444) |
| readability | 3.00 (333) | 3.00 (333) | **1.00** (111) | 3.00 (333) | 3.00 (333) | **3.33** (343) |
| maintainability | 3.00 (333) | **2.33** (223) | 3.00 (333) | 3.00 (333) | 3.00 (333) | **4.00** (444) |

- Every primary falls on its damaged tree and rises on `improved-3`.
- The one-point flips of single judgings stay inside each triple, which the
  mean absorbs.

### 2026-09-19: after anchoring, two judges

Six trees, one judging each, evidence 100 % on every judging counted.
`improved-2` under `gpt-6-astra` holds two judgings, meaned: the third
stopped at the plan's usage limit.

`gpt-6-astra` at effort `high`:

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 3 | **2** | 3 | 3 | **3.5** | **4** |
| readability | 3 | 3 | **1** | 3 | 3 | 3 |
| maintainability | 3 | 3 | 3 | 3 | 3 | **4** |
| dip | 5 | **1** | 5 | 5 | 5 | 5 |
| srp | 3 | **2** | 3 | 3 | 3 | 3 |
| error_design | 2 | **1** | 2 | **3** | **3** | **3** |
| ocp | 2 | 2 | 2 | **3** | **3** | **3** |
| lsp | 3 | **2** | **2** | 3 | 3 | 3 |
| isp | 4 | 4 | 4 | 4 | 4 | 4 |
| naming_and_abstraction | 4 | **3** | **2** | 4 | 4 | 4 |
| test_quality | 3 | 3 | **4** | **4** | **4** | **4** |

Opus 5 through the claude backend, a cross-check on the rubric:

| Dimension | base-1 | degraded-1 | obscured-1 | improved-1 | improved-2 | improved-3 |
|---|---|---|---|---|---|---|
| design | 3 | **2** | 3 | **4** | **4** | **4** |
| readability | 4 | **3** | **2** | 4 | 4 | 4 |
| maintainability | 3 | **2** | 3 | **4** | **4** | **4** |
| dip | 4 | **1** | **5** | **5** | **5** | **5** |
| srp | 3 | 3 | 3 | **4** | **4** | **4** |
| error_design | 3 | **1** | 3 | **4** | 3 | **4** |
| ocp | 2 | 2 | 2 | **3** | **3** | **4** |
| lsp | 3 | **2** | 3 | **4** | **4** | **4** |
| isp | 4 | 4 | 4 | **3** | 4 | **3** |
| naming_and_abstraction | 4 | **3** | **2** | 4 | 4 | 4 |
| test_quality | 4 | **3** | 4 | 4 | 4 | 4 |

- Under both judges every primary falls on its damaged tree and rises on an
  improved one.
- The judges differ in threshold, not direction: Opus 5 credits the
  improvement at `improved-1`, `gpt-6-astra` waits for `improved-3`.
- Opus 5 shares a vendor with the generator, so it read the rubric, not a
  round.
- Single judgings flip between runs: `design` on `improved-1` read 4 in three
  earlier runs and 3 here. That is why a row is trusted only across runs.
- The repair is tracked in solid-ai-templates#1827.

### 2026-09-18: before the primaries were anchored

`gpt-6-astra` at effort `high`, one judging per tree, evidence found 100 %.
The rubric said only that 1 was poor and 5 excellent.

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

- `design` and `maintainability` fell on damage and did not rise on
  improvement.
- On the improved tree the judge quoted `class Rule(ABC):` for `design`,
  the improvement itself, and still scored it 3.

**One tree, judged six times.** Six judgings of one byte-identical `base-1`
bundle:

| Row | Scores | Mean | SD |
| --- | ------ | ---- | -- |
| readability | 4, 4, 4, 3, 4, 4 | 3.83 | 0.41 |
| Eight of the eleven rows | The same score all six times | — | 0 |

- That spread is about 0.33 standard error on a difference of two arm means
  at K = 3.
- Readability was the only primary that moved in rounds 1 and 2, so every
  verdict rested on the row that was not reproducible.
- Three judgings per tree cut that standard error by about 40 %.
