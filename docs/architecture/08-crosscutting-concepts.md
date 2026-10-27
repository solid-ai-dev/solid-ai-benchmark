# 8. Crosscutting concepts

The ideas that more than one building block applies. Each states the rule
and where it lives in the code.

## 8.1 The registered rules

Fixed before the first run, so no metric or threshold can be chosen after
the numbers are seen.

### 8.1.1 Rules, fixed before the first run

The question, the metrics and the rule for reading a result are written down
before any trial runs. Nobody can then pick the metric or the threshold that
makes the templates look good after seeing the numbers.

| Setting | Value | Why |
|---|---|---|
| Unit compared | The difference between two arms' trials in the same block: `full-1` minus `none-1` | The arms in a block meet the same model on the same day |
| Result | The mean of the K differences, per metric, per contrast | — |
| Interval | Bias-corrected and accelerated bootstrap over the K differences: 10,000 resamples, 95 %, seed recorded | Shows how steady the effect is |
| Direction | Declared per metric (section 8.7.2) | Half the metrics improve downward |
| Verdict | **Better**: interval wholly on the improving side of zero. **Worse**: wholly on the other side. **No improvement shown**: contains zero | "No improvement shown" does not mean "equal"; section 8.1.2 covers that |

### 8.1.2 Rules for claiming "nothing got worse"

A trim is a change that shortens the templates. A trim may claim a metric
held only when the whole interval of its change lies inside the margin
below. "No improvement shown" does not mean "no worse".

| Metric | Unit | Margin: largest tolerated loss | Smallest change that matters |
|---|---|---|---|
| Hidden-test pass rate | percentage points | 2 | 5 |
| Adherence checklist | percentage points | 5 | 10 |
| Primary judge scores, 1–5 | scale points | 0.3 | 0.5 |
| Static-analysis counts per 1,000 lines | relative % | 10 | 25 |
| Change-task churn, files and lines | relative % | 15 | 30 |
| Security probe pass rate (from round 3) | percentage points | 2 | 9 |
| Data-protection probe pass rate (from round 3) | percentage points | 10 | 30 |

- An adherence gain counts only if pass rate held. Following rules while
  breaking the app is not an improvement.
- A trim is free only if every metric held.
- The report shows every metric. Its summary score decides nothing.

This is a non-inferiority test, as used in drug trials to show a new
treatment is no worse than the standard one by more than a set margin. With
K = 3 it describes the result; it does not prove it.

### 8.1.3 Few trials, and the one escalation

**Three trials are a description, not proof.**

- Three differences give the bootstrap only 27 distinct resamples.
- No arrangement of three trials reaches conventional significance.
- The report says so beside every interval, not in a footnote.

**One escalation to K = 5 is allowed, once, under fixed conditions.**

- It is owed where a primary dimension's interval contains zero while its
  mean difference exceeds the smallest change that matters (section 8.1.2).
- Any contrast can trigger it, and the effect counts in either direction.
- One further block runs. The report prints the K = 3 and K = 5 results side
  by side.
- K never exceeds 5. A second inconclusive result is reported as
  inconclusive.
- The report computes whether the escalation is owed.

Why: sampling until an interval clears zero is the failure this bound
prevents.

### 8.1.4 Failed and lost trials

**A failed trial is scored as it stands and never re-run.**

- A trial that produced no installable workspace scores zero on task
  success.
- Its quality metrics are recorded as missing, never filled in.

Why: re-running one arm's failures quietly improves that arm.

**A lost trial is re-run once, in its own place in the order.**

- A trial is lost when the CLI ends it with any error other than the budget
  cap: a usage limit, a rate limit, a crash, or no result at all.
- Its partial workspace is kept under the run's `void/` directory and never
  scored.
- A second loss of the same trial stops the run.
- A trial ended by the budget cap or the timeout is not lost. Both are
  bounds [ch. 6.1](06-runtime-view.md) sets, and the trial is scored as it stands.

Why: the provider cut it, not the agent.

## 8.2 Isolation in layers

No single fence stops every route out of a workspace, so the harness
stacks them and records what each caught.

| Layer | Stops | Cannot stop |
| ----- | ----- | ----------- |
| Scratch home and minimal settings | The owner's global `CLAUDE.md`, hooks, memory and MCP | |
| Cleaned environment | The launching session's variables, interpreter and keys | |
| Deny rules on the file tools | Read and Edit outside the trial's own workspace | The shell, whose paths a prefix rule cannot see |
| Web tools disallowed | Fetching a page | `curl` or `git clone` in the shell |
| Git credential helpers cleared | An authenticated clone of the hidden suite | |
| Process-stop commands denied | Stopping the harness by name | Stopping by PID or port |
| Transcript scan | Any tool call that names a forbidden path or repository, after the fact | A call the transcript does not record |

The scan is the backstop: a hit voids the trial and re-runs it once, and
the report scans again under the current rule.

## 8.3 Missing is not zero

A tool that scanned nothing, failed or timed out records its metric as
missing, with the reason. A grader's skipped check is not a passed one. A
probe the trial keeps from running is lost. A probe the harness could not
run leaves the rate missing. Each script's self test plants the case and
fails if it reads as zero.

## 8.4 One ruler

The first trial scored resolves `scoring-requirements.txt` and freezes it
to `tool-lock.txt`. Every later trial installs from that lock. The lock
leaves out anything local, editable or named like the package under score,
so one trial's code never installs over another's. `toolconfig/` holds the
only configuration the tools run under.

## 8.5 Blindness

The judge reads a bundle with the context file, the vendored templates,
condition markers and scoring's own output removed, in an order shuffled
at a recorded seed. The unblinding map is written where the judge cannot
reach it. A leak scan reads every file in the bundle, and a bundle that
still names its arm is refused.

## 8.6 Scoring

Each frozen trial goes through the same pipeline:

### 8.6.1 Task success and the backbone

These run on every trial, deterministically.

**Task success** is the hidden suite's pass rate. The suite lives in a
private repository and is cloned only at scoring time, never into a
workspace. It covers:

- the Python API: rule precedence, stacking, tier boundaries, rounding to
  the cent, jurisdiction tables, invalid rules refused
- every route through the Flask test client, including HTMX fragments that
  re-price correctly
- the JSON and CSV exports, byte-exact against the seed
- forms with JavaScript disabled, and browser flows through Playwright

The rest of the backbone:

- **Install:** `pip install .` in a clean virtualenv, `import tariff`, and
  the app boots and serves `/`.
- **Web quality:**
  - accessibility: axe-core WCAG 2.1 AA violations
  - HTML validity, less errors on HTMX's `hx-*` attributes, which the spec
    requires and the HTML standard lacks
  - an XSS probe and a CSRF probe
  - the invoice builder's response size and request count
- **Adherence:** the share of a fixed checklist passed.
  - Tools: `ruff` clean, `mypy --strict` clean, coverage ≥ 80 %, cognitive
    complexity ≤ 15.
  - Structure: a `src/` layout, an error-contract test, a `NullHandler`.
  - Hygiene: no `print` in library code, no citations.
  - Packaging: complete metadata, a README with install and usage,
    discoverable tests.
- **Cost:** tokens, turns, wall time, API-equivalent dollars.
- **Scope:** files and lines, and artifacts nobody asked for (ADR, journal,
  CHANGELOG, PLAYBOOK).
- **Consistency:** the spread of every metric across an arm's trials.

Adherence runs on every arm. It is a quality checklist, not a template
checklist, so the bare arm can score on it.

### 8.6.2 Code quality

**One ruler for every arm.** The tools run at the harness's pinned versions
and configuration, never the configuration the agent wrote. Counts are
reported absolute and per 1,000 lines.

**Finding the code.** Each arm picks its own layout, so the tools never
assume `src/`.

- The harness imports the installed package and takes its directory.
- It adds every top-level package directory in the workspace.
- It passes those paths to every tool explicitly.

Why: a tool pointed at an empty `src/` reports zero findings, and "zero
findings" must never mean "nothing scanned".

**A tool that scanned nothing records the metric as missing, never zero.**
The same holds for a tool that failed or timed out. The report shows how
many files and lines each tool saw. A clean arm can then be told from an
unmeasured one.

| Tool | Measures |
|---|---|
| `ruff check --select ALL` | violations, by category |
| `ruff format --check` | files needing reformatting |
| `mypy --strict` | type errors |
| `bandit` | security findings, high and medium |
| `complexipy` | cognitive complexity: max, mean, functions over 15 |
| `radon` | cyclomatic complexity and maintainability index |
| `interrogate` | docstring coverage |
| `vulture` | unused code |
| `pytest --cov` | line and branch coverage of the agent's own tests |

Not measured: mutation score, class cohesion, and pylint's refactoring
checks.

The coverage run first installs what the trial declares for its tests —
every extra and every dependency group in its `pyproject.toml` — constrained
to the tool lock. The clean install leaves them out, and a suite that fails
on an import would record a trial that packaged its test dependencies
correctly as unmeasured. A declared dependency that conflicts with the lock
records coverage as missing, with the conflict as the reason.

### 8.6.3 Design structure

The harness probes each tree's structure directly:

- **Layering:** the domain imports neither Flask nor the persistence
  module, and routes do no `Decimal` arithmetic.
- **Import graph:** mutual imports, and the mean instability of domain
  modules (Martin), through `grimp`.
- **Extension points:** can a new discount kind, jurisdiction or export
  format be added without editing existing code? Present or absent, per
  axis.
- **Kind ladders:** conditionals that dispatch on a rule's kind.
- **Boolean parameters:** a branch the caller cannot name.
- **Public surface:** names exported against names the spec requires.
- **IO isolation:** pricing takes values, not database rows or a
  connection.
- **Hygiene:** `print` calls, exception bases, citations, logging set up
  with a `NullHandler`.

### 8.6.4 The change task: the open-closed measure

**The task must lie outside what the spec already allows.** Otherwise it
measures data entry, not design. It adds two things:

- a **spend-threshold discount**: 5 % off once the subtotal reaches 200.00,
  applied before coupons
- a **capped reduced rate**: one tax category taxed at the reduced rate on
  the first 50.00 of a line and at the standard rate above it

Neither is reachable by configuration:

- The threshold rule is the first invoice rule that depends on a condition
  over the invoice. Every existing kind is unconditional or gated only by a
  coupon code.
- The capped rate is the first tax that is not one rate times one amount,
  so it changes the shape of the tax step, not its inputs.

**Measured:**

- files touched and lines changed
- whether the build suite is still green
- whether the change-task acceptance modules pass, through the API
- from round 3, whether the new rule and cap work through the forms and
  the invoice preview

A new rule class plus a registry entry scores low churn. Editing the
pricing function, the tax step, three routes and two templates scores high.

**The prompt states everything the grader drives.** It names the new
class, the cap's keyword, the form fields and the rules the acceptance
modules check.

Why: round 1's grader constructed the new behaviours through names the
prompt never gave, so it graded which trials guessed them, and its pass
rate was withdrawn (section 8.7.5).

**The acceptance modules are written before any change-task run.** They
test the two new behaviours against worked figures.

Why: churn means something only beside a pass. An arm that touched four
lines and broke the extension has not scored well.

### 8.6.5 Pattern use

For each design pattern found, the judge records where it is, what it
removes or opens, and whether it has more than one implementation.

- **Invited by the app:** Strategy for the discount kinds, a registry or
  Factory to resolve a rule or jurisdiction by name, Composite or a
  precedence chain for stacking, Adapter for the exports, Builder for an
  invoice.
- **Scored on the property, not the name:** a design that reaches the same
  extension points another way scores the same.
- **Over-engineering:** a pattern with one implementation that removes
  nothing, per `oop.md`.
- **Missed:** a conditional ladder over rule kinds where a Strategy was
  warranted.

Reported as warranted, missed and over-engineered counts.

### 8.6.6 The model judge

**The rubric.** Each row is scored 1–5 with a quoted evidence line: SRP,
OCP, LSP, ISP, DIP, naming and abstraction level, error design,
readability, maintainability, and test quality.

**Primary dimensions:** design (SOLID and pattern use), readability and
maintainability. The report leads with them; task success and cost follow.
Security and data protection join them from round 3 (section 8.6.8).

**How it judges:**

- **Anchored:** each primary describes its 1, 3 and 5 in terms of this
  domain. A scale saying only "1 is poor, 5 is excellent" put 3 on ordinary
  work every time.
- **Three times:** each tree is judged three times and the scores are
  averaged. One judging is not reproducible.
- **Blind:** the context file and any condition marker are stripped, the
  order is shuffled at a recorded seed, and a bundle that still names its
  arm is not judged.
- **Claude, cross-checked by another vendor:** `claude-opus-5-5` through
  the `claude` CLI at effort `high`, with the model id and effort recorded.
  It shares a vendor with the generator, so a judge that favours its own
  family could favour every arm. Every arm is written by the same generator,
  so a contrast between arms cancels most of that; what it would not cancel
  is a preference for the templates' own style, which were largely written
  with Claude. `gpt-6-astra` through `codex exec` therefore judges a sample
  of each round, and the report states how often the two agree. The two are
  never averaged.

From round 5, `gpt-6-astra` judges every trial and no cross-check runs
([round 5's registration, 13.1](../rounds/round-5.md)).

**The cross-check's rule**, registered before the first round it covers:

- **Sample:** whole blocks, so every contrast it reads is paired. It reads
  every build trial once where the plan's weekly limit allows, which a round
  of five arms does up to K = 5 (25 judgings of about 30). Where it does not,
  blocks are drawn in a shuffled order at the round's recorded seed until the
  limit is reached.
- **Agreement:** per judge row, over the trials both judges read, the mean
  difference (the other judge's score minus the rounds' judge's mean) and the
  share of trials whose two scores lie within one point, which is half the
  distance between two anchors.
- **Direction:** a judge-row contrast the rounds' judge calls better or worse
  loses its verdict when the other judge's mean paired difference on the
  same pairs has the opposite sign. A contrast the other judge reads as zero,
  or did not read, keeps its verdict.
- **Reading:** the other judge's scores never replace or join the rounds'
  judge's, and its own intervals decide nothing.

### 8.6.7 How the judge is checked

No person scores the judge. Two automated checks do:

- **The evidence check:** every line the judge quotes is looked up in the
  bundle it was quoted from, and the report prints the share found per
  trial. A judge that never opened the code still returns plausible
  numbers; this is what tells the two apart.
- **The control fixture:** eleven trees built from two pinned applications
  (`tests/efficacy/control/`). Every tree passes the same tests as its
  application, so only what was changed separates them. Some are damaged,
  some improved. A primary dimension counts only if it falls on the damaged
  trees and rises on the improved ones.

**Where the control's application comes from.** A row can only fall or
rise on code that has what it measures. The first pinned application is a
round-1 tree with no sign-in and no customers, so the security and
data-protection rows can be neither damaged nor improved on it. Those rows
get a second pinned application: the output of one calibration trial, an
ordinary build of the extended specification by the rounds' generator. The
trial is uncounted, so no report reads it; it exists only to be the base
the new rows' trees are built from.

The reference implementation cannot serve instead. It is a worked answer to
the hidden suite and stays private, and a trial keeps the base
agent-written, like everything else the judge scores.

The control fixture is read by both judges, each in a root of its own, and
a primary counts only if it falls and rises under the rounds' judge.

#### The control's trees

The control lives in `tests/efficacy/control/`. Its builder prints one line per
entity it claims to change, read back off the trees, and refuses when any
mutation did not land: a mutation that silently did nothing would read as the
judge holding when it was never exercised. Every built tree passes its
application's tests.

| Tree | What it is |
|---|---|
| `base-1` | the application as one trial generated it, unaltered |
| `degraded-1` | the domain merged into one module, `from flask import current_app` used inside `price`, and the package's exceptions reparented off `TariffError` |
| `obscured-1` | the pricing algorithm inlined into one long function with abbreviated names, and nothing else: the module boundaries, the error hierarchy and the dispatch are the base's |
| `improved-1` | a rule contract and self-registering kind registry, dispatch on concrete type removed from pricing and persistence, the hardcoded kinds tuple replaced by the registry, a `__class__.__name__` ladder removed from a template, and two stray error classes folded into the package hierarchy |
| `improved-2` | `improved-1`, and the store maps a rule's own terms onto its columns with a codec per column, so no module dispatches on a kind |
| `improved-3` | `improved-2`, and each kind declares the fields it asks a form for, so the form-building code and the template are derived from the registry and no layer names a kind |

The second application's trees:

| Tree | What it is |
|---|---|
| `base-2` | the calibration trial's application, unaltered: one guard before every route but sign-in, a CSRF token on every form, a salted password hash, `next` followed only to a local path, a secret key generated into a file; erasure clears the customer's fields, and nothing is logged |
| `insecure-1` | the secret key a literal, the password stored and compared as typed, the user lookup built from a string, and `next` followed wherever it points |
| `secured-1` | the secret key read from the environment first, the session cookie marked `HttpOnly` and `SameSite`, three security headers on every answer, and the check on `next` a named function that also refuses a backslash |
| `leaky-1` | the customer's name, email and address written to the log on creation and erasure, and erasure only raising the flag, leaving every field in the database |
| `protected-1` | one tuple names the personal fields, which erasure clears and the export returns; one lookup answers None for an erased customer, so no view or template reads the flag for itself; SQLite overwrites what it deletes |

The damage in `insecure-1` and `leaky-1` sits where the hidden suite does not
look: it states that password storage, cookie flags and an off-site `next` are
not graded, and it reads erasure through the pages.

<!-- measured: 2026-09-25 -->
Each tree's hidden-suite result is identical, test by test, to `base-2`'s,
at suite revision `65bfb9a`: 293 of 534 pass. The
calibration trial seeds only through its command, not when the application
opens an empty database as the specification asks, so the suite's
administrator does not exist and 240 checks behind sign-in fail on every tree
alike. That comparison therefore covers the 293 that pass, the pricing and API
checks among them.
<!-- /measured -->

#### Reading a control result

A row is doing its job when it falls on the tree that damages what it
measures and rises on the tree that improves it. Anything else is a finding
about the instrument:

- a row that does not fall cannot detect damage
- a row that does not rise cannot detect improvement, so no arm can ever win
  on it
- a row that moves on neither is carrying no information at all

Which tree tests which row matters. `degraded-1` damages structure and leaves
every function body alone, so a flat `readability` there says nothing about
the row — that is what `obscured-1` is for. Read each row against the tree
built to move it, and treat the others as a check that it is not moving on
noise.

Re-run the control whenever the judge model, its effort, or the rubric prompt
changes. Each of those silently invalidates every reading below.

The measured results of every control run are in
[ch. 10.7](10-quality-requirements.md).

#### Why the bases are pinned archives

`base.zip` and `base-2.zip` each hold one trial's output: the application its
trees are built from. `base-2.zip` is `git archive` of the calibration trial's
commit `f74c0cc`, which reproduces it byte for byte. Each is an input to this
control, not an artifact of it: regenerating one would compare a later run
against a different application, and every number above would silently stop
meaning what it says.

Two things hold them still. The builder refuses any archive whose sha256 is not
the one recorded in `control.py`, so a changed base stops the control instead
of quietly shifting what it measures. And every edit the builder makes is an
exact-text swap that refuses when its target is absent, so a base that drifts
stops the control rather than mutating less than it claims.

It is an archive rather than a directory of files because this repository's
own checks read committed Python as source to be brought into line — the
comment-layout rule flags a trailing comment in the application's test suite.
Reformatting the fixture would edit the thing the judge scores, which is the
one change this control cannot survive.

### 8.6.8 Security and data protection

**From round 3, security and data protection are primary dimensions.**
Each is read two ways, and both readings are primary:

| Metric | What it is | Direction | Margin | Smallest change that matters |
|---|---|---|---|---|
| `judge_security` | anchored judge row, 1–5 | up | 0.3 points | 0.5 points |
| `judge_data_protection` | anchored judge row, 1–5 | up | 0.3 points | 0.5 points |
| Security probe pass rate | share of the security probes a trial passes | up | 2 pp | 9 pp |
| Data-protection probe pass rate | share of the data-protection probes a trial passes | up | 10 pp | 30 pp |

**Security probes (11):**

- a plaintext password at rest
- sign-in failures that reveal which accounts exist
- an open redirect after sign-in
- no CSRF on sign-in
- a hard-coded secret key
- debug left on
- SQL assembled from a value the module cannot trace to its constants
- known vulnerabilities in the installed dependencies
- missing session cookie flags
- missing security headers
- stack traces in answers to malformed requests

**Data-protection probes (3):**

- a sentinel customer email found in the logs
- an erased customer's sentinel still in the database file
- one customer's export carrying another customer's data

**How a probe reads the application.** It seeds and signs in the way the
hidden suite does: the administrator's password from the environment, then
the sign-in form's own fields. Where a probe needs a judgement, it takes the
narrow one:

- the cookie flags pass on `HttpOnly` and `SameSite`; `Secure` cannot be
  observed over plain HTTP, so it is not asked
- the headers pass on `nosniff` and framing protection; a content security
  policy is not asked, because the specification requires HTMX
- a sentinel in the logs counts at every level, since a call that logs
  personal data does so whatever the level is set to
- an erased sentinel counts anywhere in the files beside the database,
  free pages included, since that is where erasure leaves it

**A probe the trial keeps from running is lost.** An application that will
not boot, install or sign in its administrator fails every probe that needs
it, with the reason recorded. Counted as missing instead, those probes would
drop out of the rate, and a trial would score higher for not reaching them.
A probe the harness itself could not run leaves the rate missing.

**How the probe margins are set.** Both follow one rule, so the figures
change only if a probe count does:

- The margin is less than one probe lost in one trial. With K = 3 that is
  under 3.0 pp for security (1 of 11) and under 11.1 pp for data
  protection (1 of 3). No probe may be lost.
- The smallest change that matters is one probe lost in every trial: 9.1 pp
  and 33.3 pp, rounded down to 9 and 30.

**Before round 3's first trial:**

- Each judge row is anchored at 1, 3 and 5 in terms of this domain.
- Each passes the control fixture: it falls on a tree that damages it and
  rises on one that improves it, both built from the calibration trial's
  application (section 8.6.7).

The last seven security probes are `tests/efficacy/security.py`'s checks.
They were declared after round 1, so they described that round and decided
nothing (section 8.7.4). Fixed here before round 3, they decide it.

## 8.7 The report

### 8.7.1 Contrasts

Each metric is reported per arm and for eight paired contrasts:

| Contrast | Asks |
|---|---|
| `full − none` | do the templates help as shipped |
| `short − none` | does a short generated file help |
| `hybrid − none` | does the hybrid model help |
| `hand − none` | does any file help |
| `full − hand` | do the templates beat forty hand-written lines |
| `short − hand` | at equal length, can the templates pick the right forty lines |
| `hybrid − full` | does the hybrid model beat the same content inline |
| `short − full` | does length matter |

`full − hand` is the question an adopter asks. A large `full − none` beside
an equally large `hand − none` is not a result for the templates.

**Reading `short − hand`:**

- `short` ≈ `hand` (no improvement shown, every quality metric held): the
  templates' content is sound, and the interview emits too much.
- `short` worse than `hand` on a primary dimension: the content itself is
  the defect.

**A contrast pairing trials from different rounds gets no verdict.** It keeps
its mean and interval and counts as neither a win nor a fail.

### 8.7.2 Metric directions

- **Better upward:** task success, adherence, coverage, docstring coverage,
  extension points present, every judge score, the security and
  data-protection probe pass rates.
- **Better downward:** every static-analysis count, cognitive and cyclomatic
  complexity, tokens, turns, wall time, cost, files, lines, artifacts nobody
  asked for, change-task churn, axe violations, HTML errors.
- **Neutral, reported without a verdict:** maintainability index,
  instability.

### 8.7.3 What the report prints

The report is `docs/audits/YYYY-MM-DD-efficacy.md`.

**It opens with the finding table.** One column per context file against
`none`, headed by the file's line count:

- **Improves the code?** Yes where a primary dimension or task success is
  better and none worse; Worse where any is worse; No where none is better.
- the primary dimensions that moved
- the hidden-suite pass rate against `none`, naming any run below it by more
  than the smallest change that matters
- code size and cost, as signed shares of `none`'s, where the interval
  separated them
- a one-phrase reading

Under the table:

- one line per file on why it scored so, in words
- one line reading the columns together
- one line scoring the contrasts between two files, 1 to 10:
  1 + 9 × wins ÷ (wins + fails). A win or fail is a metric better or worse;
  "no improvement shown" counts neither way.
- one line of caveats: the escalation, withdrawn metrics, lost trials,
  reaches past a workspace, and the judge's evidence check

The table and the score describe the verdicts and decide nothing. Every cell
rests on a verdict or record below it.

**Then the record:**

- model ids, CLI versions and the template revision
- each generated arm's brief and token scan
- K and the bootstrap seed
- every trial's raw numbers
- every trial that failed or was re-run, and why
- the judge's evidence check
- the verdict vector

### 8.7.4 Checks declared after a run

**A check chosen after the results were seen can describe a run but never
decide it.**

- It is declared in writing, with its direction, before any trial is read
  for it.
- The report prints it in its own section, with means and intervals and no
  verdict.
- It never enters the verdict vector, a "nothing got worse" claim or the
  escalation.
- A check worth deciding on is fixed before the next run instead.

Why: otherwise the bar moves with the results.

### 8.7.5 Withdrawn measurements

**A metric whose grader turns out to measure something else is withdrawn,
not reported.**

- The withdrawal is recorded in `tests/efficacy/withdrawn.json` against the
  grader's revision.
- Every run that revision graded loses the metric; a run graded by a
  corrected revision keeps it.
- The report names the metric and the reason, with no number, interval or
  verdict.
- A corrected grader never re-grades the same trials. The correction is
  fixed before the next run.

## 8.8 Records

Every stage writes what it did beside what it made: the run record per
invocation, `generation.json` per generated file, each score with the
revisions it was graded under, each judging with its model, effort and
seed. `archive.py` carries all of it to the private archive with a hash per
file, and a report refuses to write once any reading changed since the
archive was verified.

## 8.9 One run at a time

`score.py`, `judge.py` and `security.py` each clear a trial's directory
before rebuilding it. A run writes `<tool>.running` naming its process. A
second run that finds a live claim is refused. A claim naming a process
that has ended is taken over, and the run says so.
