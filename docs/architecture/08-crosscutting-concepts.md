# 8. Crosscutting concepts

Rules that hold across every script: the harness, the scorer, the security
reader, the judge, the report and the archive. Each section says why its
rules exist and lists them. The rules themselves are stated as requirements
in [requirements.md](../requirements.md), and the decisions behind them are
grouped in [chapter 9](09-architecture-decisions.md).

- A round's registration under `docs/rounds/` can add rules or tighten
  these. Round 5d, for example, registers its own verdict rules and radar.
- Some rules start at a given round. An earlier round re-reads the way it
  was reported, so the report keeps its old rules too.
- Section numbers stay fixed, because round registrations cite them.

## 8.1 Rules fixed before a round

### 8.1.1 Registration and reading a result

The question, the metrics and the rule for reading a result are written down
before any trial runs.

**Why**

- Nobody can then pick the metric or the threshold that makes the templates
  look good after seeing the numbers.
- Arms in one block meet the same model on the same day, so a difference
  between them is the file's, not the day's.

![Four example intervals of a difference in hidden-test points, against zero and a 2-point margin. One lies wholly above zero: better, and a big loss is ruled out. One crosses zero but stays above the margin: undecided, and a big loss is ruled out. One crosses both zero and the margin: undecided, and a big loss is not ruled out. One lies wholly below zero: worse](../diagrams/verdict.png)

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | The registration comes first | From round 5, a registration that landed on `main` after the round's first trial is refused, a merge counting at the merge | FR-01-01 |
| 2 | The registration is the one on `main` | A copy that differs from `main`'s, or has changes not committed, is refused | FR-01-02 |
| 3 | Every trial builds what was registered | A trial on another spec or prompt, by content, or recording none, is refused; the harness checks the spec before each trial | FR-01-03 to FR-01-05 |
| 4 | Time is unambiguous | A trial records its start with its UTC offset; a start with none is refused | FR-01-06 |
| 5 | A registration lands by pull request | A squash or rebase merge, since a fast-forward from a clone keeps its older commit date | FR-01-07 |
| 6 | Arms are compared within a block | The unit is one block's difference, such as `hand-1` minus `none-1`; each block starts one arm later | FR-02-01 |
| 7 | The interval decides | 95 % bias-corrected and accelerated bootstrap over the K differences, 10,000 resamples, seed recorded. Wholly on the improving side: better. Wholly on the other: worse. Across zero: no improvement shown | FR-02-02 |

"No improvement shown" does not mean "equal". Claiming that takes a margin
(8.1.2). A metric's direction is set in 8.7.2.

### 8.1.2 Margins

A trim is a change that shortens the templates. It may claim a metric held
only when the whole interval of the change lies inside the metric's margin,
the largest loss the round tolerates.

**Why**

- "No improvement shown" does not mean "no worse".
- This is a non-inferiority test, the kind drug trials use to show a new
  treatment is no worse than the standard by more than a set margin.

The margins:

| Metric | Unit | Margin | Smallest change that matters | Since |
| ------ | ---- | ------ | ---------------------------- | ----- |
| Hidden-test pass rate | pp | 2 | 5 | round 1 |
| Adherence checklist | pp | 5 | 10 | round 1 |
| Primary judge scores, 1–5 | points | 0.3 | 0.5 | round 1 |
| Static-analysis counts per 1,000 lines | relative % | 10 | 25 | round 1 |
| Change-task churn, files and lines | relative % | 15 | 30 | round 1 |
| Security probe pass rate | pp | 2 | 9 | round 3 |
| Data-protection probe pass rate | pp | 10 | 30 | round 3 |
| App code, lines and files | relative % | 20 | 40 | round 5 |
| The ISO radar's axes, share of targets met | points | 5, Reliability 7 | 10 | round 6 |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Held means inside the margin | The whole interval lies inside the margin; a relative margin is a share of the baseline arm's mean | FR-02-03, FR-02-04 |
| 2 | Adherence never trades for the app | An adherence gain counts only if the hidden-test pass rate held | FR-02-07 |
| 3 | A trim is free only if nothing got worse | Every metric held | FR-02-08 |
| 4 | The summary decides nothing | The report shows every metric; its summary score is a reading aid | — |
| 5 | Round 5 holds adherence to one item | 8 pp, one checklist item of 13, as [its registration](../rounds/round-5.md) states | FR-02-05 |
| 6 | Few blocks describe | Below K = 6, every interval is called descriptive | FR-02-09 |

### 8.1.3 Trial count

A round fixes K, the number of blocks, before its first trial.

**Why**

- Three differences give the bootstrap only 27 distinct resamples, and no
  arrangement of three reaches conventional significance. Three trials
  describe; they do not prove.
- Sampling until an interval clears zero is the failure the bound on K
  prevents. Rounds 1 to 4 were registered at K = 3 with one bounded
  escalation to 5; they are retired, and their escalation with them.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | K is sized beforehand | From earlier rounds' per-trial noise; no block added once results are seen. Round 5 registers K = 15 ([13.5](../rounds/round-5.md)) | FR-03-04 |
| 2 | A short run decides nothing | A run short of its K is part-run, and none of its verdicts is the round's | FR-03-05 |

### 8.1.4 Failed and lost trials

A failed trial is the agent's doing. A lost trial is the provider's.

**Why**

- Re-running one arm's failures would quietly improve that arm.
- A trial the provider cut off says nothing about the agent.

How each ending is handled:

| Ending | Kind | What happens |
| ------ | ---- | ------------ |
| Completed | — | Scored |
| Budget cap or timeout | Bound ([ch. 6.1](06-runtime-view.md)) | Scored as it stands |
| No installable workspace | Failed | Task success 0, quality metrics missing, never re-run |
| Usage limit, rate limit, crash, or no result | Lost | Re-run once, in its own place in the order |
| Lost a second time | Lost | The run stops |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | A failure stands | Scored as it is, with missing metrics left missing, never re-run | FR-04-01 to FR-04-03 |
| 2 | A loss is re-run once | In its own place, once the generator answers a probe, made at once and then every 30 minutes; its partial workspace kept under `void/`, never scored | FR-04-04 to FR-04-06, FR-04-09 |
| 3 | Two losses stop the run | A stopped run resumes with `--from`, in the same order; `--stop-on-block` stops at the first loss instead | FR-04-07, FR-04-08 |
| 4 | A trial starts on a token that outlasts it | Where the account's token expires within the trial's ceiling, one call to the generator first, so the CLI renews it before the trial rather than during | FR-04-10 |

## 8.2 Isolation

A trial reaches nothing it is defined not to have: the templates, the hidden
suite, the web, another trial, the owner's own setup.

**Why**

- A trial that read the hidden suite measures the suite.
- No single fence stops every route out of a workspace, so the harness
  stacks several and records what each caught.

The layers:

| Layer | Stops | Cannot stop |
| ----- | ----- | ----------- |
| Scratch home, minimal settings | The owner's global `CLAUDE.md`, hooks, memory and MCP | |
| Cleaned environment | The launching session's variables, interpreter and keys | |
| Deny rules on file tools | Read and Edit outside the trial's workspace | The shell, whose paths a prefix rule cannot see |
| Web tools disallowed | Fetching a page | `curl` or `git clone` in the shell |
| Git credential helpers cleared | An authenticated clone of the hidden suite | |
| Process-stop commands denied | Stopping the harness by name | Stopping by PID or port |
| Transcript scan | Any tool call naming a forbidden path or repository | A call the transcript does not record |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Nothing of the owner's reaches a trial | Scratch home, minimal settings, cleaned environment | FR-05-01, FR-05-02 |
| 2 | The tools are fenced | File tools denied outside the workspace, web tools disallowed, no Git credentials, no stop by name | FR-05-03 to FR-05-06 |
| 3 | The transcript is the backstop | A hit voids the trial and re-runs it once; the report scans again under the current rule | FR-05-07, FR-05-08 |
| 4 | Nothing outlives the trial | Every process started from its directories is stopped before it is frozen | FR-05-09 |

The decision is ADR-020.

## 8.3 Missing values

A zero has to mean "measured, and none found".

**Why**

- A tool that scanned nothing reports zero findings, and would read as a
  clean arm.
- A probe the trial keeps from running would drop out of the rate, so a
  trial would score higher for not reaching it.

How each case is recorded:

| Case | Recorded as |
| ---- | ----------- |
| A tool scanned nothing, failed or timed out | Missing, with the reason |
| A grader skipped a check | Not passed |
| The trial keeps a probe from running | Lost: the probe fails |
| The harness could not run a probe | The rate is missing |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Unmeasured is missing | With the reason, and shown as not measured | FR-06-01, FR-06-05 |
| 2 | Skipped is not passed | A partial suite is flagged | FR-06-02 |
| 3 | A probe the trial blocks is lost | It counts against the rate | FR-06-03 |
| 4 | A probe the harness could not run is missing | The rate is left missing | FR-06-04 |

Each script's self-test plants these cases and fails if one reads as zero.

## 8.4 Tools and interpreter

Every trial is measured with the same tool versions, configuration and
Python.

**Why**

- A tool upgraded between trials would move a metric for every arm after it.
- An agent's own `ruff.toml` would let each arm choose its own ruler.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | One lock | The first trial scored resolves `scoring-requirements.txt` into `tool-lock.txt`; every later trial installs from it | FR-07-01 |
| 2 | The lock holds only tools | Anything local, editable or named like the package under score is left out | FR-07-02 |
| 3 | One configuration | `toolconfig/` only, never the agent's | FR-07-03 |
| 4 | One Python | The spec's; a round scored on two is refused | FR-07-04 |

## 8.5 Blind judging

The judge must not know which arm wrote a build.

**Why**

- A judge that can name the arm can favour it, even without meaning to.

![A frozen trial is stripped of its context file, templates, skills, markers and scoring output. A leak scan refuses a bundle that still names its arm. A clean bundle is shuffled at a recorded seed and judged, scored 1 to 5 three times, while the unblinding map is written where the judge cannot reach it](../diagrams/blinding.png)

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Strip what names the arm | The context file, vendored templates, skills, markers and scoring output leave the bundle | FR-08-01 |
| 2 | Shuffle, and keep the key apart | The order is shuffled at a recorded seed; the map is out of the judge's reach | FR-08-02 |
| 3 | Refuse a leak | A leak scan reads every file, and a bundle that still names its arm is not judged | FR-08-03 |

## 8.6 Scoring

Each frozen trial goes through the same pipeline: the deterministic measures
first, the judge last. [Chapter 6](06-runtime-view.md) shows it as a
sequence.

### 8.6.1 Task success and other measures

**Task success** is the hidden suite's pass rate. The suite lives in a
private repository and is cloned only at scoring time, never into a
workspace (FR-09-01), at its newest revision or at the one the scoring
names, so a root begun at one revision is finished at it (FR-09-10). It
covers:

- the Python API: rule precedence, stacking, tier boundaries, rounding to
  the cent, jurisdiction tables, invalid rules refused
- every route through the Flask test client, including HTMX fragments that
  re-price correctly
- the JSON and CSV exports, byte-exact against the seed
- forms with JavaScript disabled, and browser flows through Playwright

The other measures, run on every trial:

| Measure | What it reads |
| ------- | ------------- |
| Install | `pip install .` in a clean virtualenv, `import tariff`, and the app serves `/` |
| Accessibility | axe-core rules of WCAG 2.1 A and AA violated, each by its id; axe's best-practice rules are kept apart and not counted (FR-06-07) |
| HTML validity | Errors, less those on HTMX's `hx-*` attributes, which the spec requires and HTML lacks |
| XSS and CSRF | One probe each |
| Invoice builder | Response size and request count |
| Adherence | Share of a fixed checklist of 13 items passed |
| Cost | Tokens, turns, wall time, API-equivalent dollars |
| Size | App code's files and lines, apart from tests, docs and configuration |
| Unasked artifacts | ADR, journal, CHANGELOG, PLAYBOOK, committed bytecode or databases |
| Consistency | Each metric's spread across an arm's trials |

Accessibility, HTML validity, XSS, CSRF and the invoice builder read the
pages signed in as the seeded administrator. A page answered with the
redirect to `/sign-in` is never measured: a form row the app keeps from
running reads failed, a measured row missing, each with its reason
(FR-06-06). Rounds 5 to 5e read them unsigned, on the redirect (#175).

The adherence checklist:

| Group | Items |
| ----- | ----- |
| Tools | `ruff` clean, `ruff format` clean, `mypy --strict` clean, coverage ≥ 80 %, cognitive complexity ≤ 15 |
| Structure | A `src/` layout, one error hierarchy, a `NullHandler` |
| Hygiene | No `print` in library code, no citations |
| Packaging | Complete metadata, a README with install and usage, discoverable tests |

It checks quality, not the templates, so the bare arm scores on it too
(FR-09-05). The decisions on HTML validity and size are ADR-011.

### 8.6.2 Code quality

The tools run at the harness's pinned versions and configuration (8.4).
Counts are reported absolute and per 1,000 lines.

| Tool | Measures |
| ---- | -------- |
| `ruff check --select ALL` | Violations, by category |
| `ruff format --check` | Files needing reformatting |
| `mypy --strict` | Type errors |
| `bandit` | Security findings, high and medium |
| `complexipy` | Cognitive complexity: max, mean, functions over 15 |
| `radon` | Cyclomatic complexity, maintainability index |
| `interrogate` | Docstring coverage |
| `vulture` | Unused code |
| `pytest --cov` | Line and branch coverage of the agent's own tests |

Not measured: mutation score, class cohesion, pylint's refactoring checks.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Find the code, never assume `src/` | The installed package and every top-level package, passed to every tool by path; the report shows the files and lines each tool saw | FR-07-05 |
| 2 | Coverage installs the test dependencies | Every extra and dependency group the trial declares, within the lock | FR-07-06 |
| 3 | A conflict leaves coverage missing | With the conflict as the reason | FR-07-07 |

### 8.6.3 Design structure

The scorer probes each build's structure directly (FR-09-06).

| Probe | Asks |
| ----- | ---- |
| Layering | Do the modules `import tariff` loads, its `__init__` and what that reaches through the package's own imports, import neither Flask nor persistence? Do routes do no `Decimal` arithmetic? |
| Import graph | Mutual imports, and the domain modules' mean instability (Martin), through `grimp` |
| Extension points | Can a discount kind, a jurisdiction or an export format be added without editing existing code? Per axis |
| Kind ladders | Conditionals that dispatch on a rule's kind |
| Boolean parameters | Branches the caller cannot name |
| Public surface | Names exported against names the spec requires |
| IO isolation | Does pricing take values, not rows or a connection? |
| Hygiene | `print` calls, exception bases, citations, a `NullHandler` |

### 8.6.4 The change task

The change task measures how well a build takes a change it was not built
for: the open-closed principle, in practice.

**Why**

- A task the spec already allows measures data entry, not design. Both
  additions are out of reach of configuration.
- Churn means something only beside a pass: an arm that touched four lines
  and broke the extension has not scored well.

The two additions:

| Addition | Why configuration cannot reach it |
| -------- | --------------------------------- |
| Spend-threshold discount: 5 % off once the subtotal reaches 200.00, before coupons | The first rule gated by a condition over the invoice |
| Capped reduced rate: one category taxed at the reduced rate on a line's first 50.00, the standard rate above | The first tax that is not one rate times one amount |

Measured: files touched and lines changed, whether the build suite stays
green, whether the acceptance modules pass through the API, and, from round
3, whether the rule and cap work through the forms and the invoice preview.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Churn counts what the agent changed | Every edited and new file; nothing in an environment | FR-09-07 |
| 2 | The prompt states what the grader drives | The new class, the cap's keyword, the form fields, the rules checked | FR-09-08 |
| 3 | The acceptance modules come first | Written before any change-task run, against worked figures | FR-09-09 |

The decision is ADR-009, including why round 1's change-task pass rate was
withdrawn.

**The changed tree, scored in full.** From round 6 every arm's change task
of a block starts from one fixture, a qualifying `none` build of round 5e,
so the changed tree is read on every ISO axis the build is. It gets the
same scoring, security and quality readings and judge, each filed apart
from the build's under a `-change` folder of its own (FR-16-01, FR-16-03,
FR-16-05). A changed tree that does not install loses its probes and goes
unjudged, as a build does; a reading the reader could not take is missing.

Two readings compare the changed tree with its fixture, each counted on one
axis only:

| Reading | What it reads | Fails when | ISO place |
| ------- | ------------- | ---------- | --------- |
| Interfaces | The hidden suite's API, route and two export modules on the changed tree, against the fixture's frozen baseline | A module the fixture passed whole no longer does | Compatibility, Interoperability |
| Data upgrade | Products, customers, rules, a jurisdiction and invoices saved through the fixture's own forms, then the changed tree on a copy of that database | A record is gone or reads differently, an old invoice will not open or price as it did, or the file takes no new record | Flexibility, Adaptability |

- **Inherited is not broken.** An interface module the fixture already
  failed is the fixture's, not the change's, and counts neither way
  (FR-16-02).
- **Values, not counts.** Each record is read back as the fixture showed
  it: the list pages, each invoice's JSON and CSV exports, the customer's
  export, and the old invoice priced again. A key or column only the
  changed tree has is the change's own, and is no loss (FR-16-04).
- **Lost and missing.** A changed tree that will not open the file, or
  sign in on it, has lost the data and fails. A fixture that cannot seed is
  no arm's, so the reading is missing. Each reading names the fixture's
  hash, the starting commit and the seeded database's hash.
- **One place each.** The data upgrade is the migration target on
  Adaptability: the change adapts to data an earlier version saved. It is
  not read on Interoperability too, so no build is credited twice
  (FR-16-06).

### 8.6.5 Pattern use

For each design pattern it finds, the judge records where it is, what it
removes or opens, and whether it has more than one implementation. It scores
the property, not the name: a design that reaches the same extension points
another way scores the same.

| Kind | What counts |
| ---- | ----------- |
| Warranted | Patterns the app invites: Strategy for discount kinds, a registry or Factory to resolve a rule or jurisdiction by name, Composite or a precedence chain for stacking, Adapter for exports, Builder for an invoice |
| Missed | A conditional ladder over rule kinds where a Strategy was warranted |
| Over-engineered | A pattern with one implementation that removes nothing, per `oop.md` |

### 8.6.6 The judge

A model reads each build and scores it 1–5 on each row of a rubric, quoting
the line its score rests on.

The rubric's rows:

| Group | Rows |
| ----- | ---- |
| SOLID | SRP, OCP, LSP, ISP, DIP |
| Code | Naming and abstraction level, error design, test quality |
| Primary | Design (SOLID and pattern use), readability, maintainability; from round 3, security and data protection |

The primary rows lead the report, before task success and cost.

**Why**

- A scale saying only "1 is poor, 5 is excellent" put 3 on ordinary work
  every time, so each primary is anchored at 1, 3 and 5 in this domain's
  terms.
- One judging is not reproducible, so each tree is judged three times.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Three judgings, averaged | Each tree is judged three times | FR-10-01 |
| 2 | One named judge | From round 5, `gpt-6-astra` through `codex exec` at effort `high`, model and effort recorded | FR-10-02 |
| 3 | The judge only reads | It may read the bundle and do nothing else | FR-10-03 |
| 4 | Blind | As 8.5 sets out | FR-08-01 to FR-08-03 |
| 5 | A cross-check never mixes in | Before round 5, a second judge read a sample; agreement counted per row; a verdict lost its direction only where the two read opposite signs | FR-10-04, FR-10-05 |

The choice of judge, and how it changed, is ADR-005.

### 8.6.7 Judge validation

No person scores the judge. Two automated checks do.

**The evidence check.** Every line the judge quotes is looked up in the
bundle it came from, and the report prints the share found per trial. A
judge that never opened the code still returns plausible numbers; this tells
the two apart.

**The control fixture.** Trees built from two pinned applications, in
`tests/efficacy/control/`. Each changes one thing and passes the same tests
as its application. A row works when it falls on the tree that damages it
and rises on the one that improves it, under the rounds' judge.

| Reading | What it means |
| ------- | ------------- |
| Falls on its damaged tree, rises on its improved one | The row works |
| Does not fall | It cannot detect damage |
| Does not rise | It cannot detect improvement, so no arm can win on it |
| Moves on neither | It carries no information |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | The quotes are checked | The share found is printed per trial | FR-10-06 |
| 2 | A row counts only if it moves | It falls on its damaged tree and rises on its improved one | FR-10-09 |
| 3 | Every mutation lands | The builder reads each change back off the trees and refuses one that did not land | FR-10-07 |
| 4 | The bases do not drift | An archive whose sha256 is not the one recorded is refused | FR-10-08 |
| 5 | Re-run on any judge change | A new judge model, effort or rubric prompt invalidates every earlier reading | — |

The measured results are in [validation](../validation.md). The decision is
ADR-016.

#### Control trees

The first application is a round-1 build with no sign-in and no customers,
so it cannot move the security or data-protection rows. The second is one
uncounted calibration trial: an ordinary build of the extended spec by the
rounds' generator. The reference implementation cannot serve instead: it is
a worked answer to the hidden suite and stays private.

Read each row against the tree built to move it; the others check that it
is not moving on noise.

| Tree | Built to move | What it changes |
| ---- | ------------- | --------------- |
| `base-1` | — | The first application, unaltered |
| `degraded-1` | design ↓, maintainability ↓ | Domain merged into one module, `from flask import current_app` inside `price`, the exceptions reparented off `TariffError` |
| `obscured-1` | readability ↓ | Pricing inlined into one long function with abbreviated names; nothing else |
| `clarified-1` | readability ↑ | Pricing rewritten into short one-step functions with names that carry the intent; nothing else |
| `improved-1` | design ↑, maintainability ↑ | A rule contract and self-registering kind registry; type dispatch removed from pricing, persistence and a template; stray errors folded into the hierarchy |
| `improved-2` | design ↑, maintainability ↑ | `improved-1`, and the store maps a rule's terms onto columns with a codec per column, so no module dispatches on a kind |
| `improved-3` | design ↑, maintainability ↑ | `improved-2`, and each kind declares its form fields, so forms and template derive from the registry |
| `base-2` | — | The calibration trial, unaltered: guarded routes, CSRF tokens, a salted hash, local-only `next`, a generated secret key; erasure clears the fields; nothing logged |
| `insecure-1` | security ↓ | Literal secret key, plaintext password, a lookup built from a string, `next` followed anywhere |
| `secured-1` | security ↑ | Secret key from the environment, `HttpOnly` and `SameSite` cookies, three security headers, `next` checked by a named function that also refuses a backslash |
| `leaky-1` | data protection ↓ | Name, email and address logged on creation and erasure; erasure only raises a flag |
| `protected-1` | data protection ↑ | One tuple names the personal fields for erasure and export; one lookup hides an erased customer; SQLite overwrites what it deletes |

The damage in `insecure-1` and `leaky-1` sits where the hidden suite does not
look: it does not grade password storage, cookie flags or an off-site
`next`, and it reads erasure through the pages.

<!-- measured: 2026-09-25 -->
Each tree's hidden-suite result is identical, test by test, to `base-2`'s,
at suite revision `65bfb9a`: 293 of 534 pass. The
calibration trial seeds only through its command, not when the application
opens an empty database as the specification asks, so the suite's
administrator does not exist and 240 checks behind sign-in fail on every tree
alike. That comparison therefore covers the 293 that pass, the pricing and API
checks among them.
<!-- /measured -->

#### Pinned bases

`base.zip` and `base-2.zip` each hold one trial's output. They are inputs to
the control, not artifacts of it: a regenerated base would compare a later
run against a different application. `base-2.zip` is `git archive` of the
calibration trial's commit `f74c0cc`, which reproduces it byte for byte.

They are archives, not directories, because this repository's linters would
read committed Python as source to fix, and reformatting the fixture would
edit the very thing the judge scores.

### 8.6.8 Security and data protection

From round 3, security and data protection are primary, each read two ways:

| Metric | What it is | Direction | Margin | Smallest change that matters |
| ------ | ---------- | --------- | ------ | ---------------------------- |
| `judge_security` | Anchored judge row, 1–5 | up | 0.3 points | 0.5 points |
| `judge_data_protection` | Anchored judge row, 1–5 | up | 0.3 points | 0.5 points |
| Security probe pass rate | Share of 11 probes passed | up | 2 pp | 9 pp |
| Data-protection probe pass rate | Share of 3 probes passed | up | 10 pp | 30 pp |

The probes:

| Security (11) | Data protection (3) |
| ------------- | ------------------- |
| Plaintext password at rest | Sentinel customer email in the logs |
| Sign-in failures that reveal which accounts exist | An erased customer's sentinel still in the database file |
| Open redirect after sign-in | One customer's export carrying another's data |
| No CSRF on sign-in | |
| Hard-coded secret key | |
| Debug left on | |
| SQL assembled from a value not traceable to constants | |
| Known vulnerabilities in installed dependencies | |
| Missing session cookie flags | |
| Missing security headers | |
| Stack traces in answers to malformed requests | |

Where a probe needs a judgement, it takes the narrow one:

| Probe | Reads | Why so narrow |
| ----- | ----- | ------------- |
| Cookie flags | `HttpOnly` and `SameSite` | `Secure` cannot be observed over plain HTTP |
| Headers | `nosniff` and framing protection | No content security policy: the spec requires HTMX |
| Sentinel in logs | Counts at any level | A call that logs personal data does so whatever the level |
| Erased sentinel | Counts anywhere beside the database, free pages included | That is where erasure leaves it |

**Why**

- A judge row alone is an opinion; the probes are deterministic.
- Security regressions get no tolerance: each margin is less than one probe
  lost in one trial at K = 3, and the smallest change that matters is one
  probe lost in every trial.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Probes are proven both ways | Each fails an app built to fail it and passes one built to pass it | FR-11-01, FR-11-03 to FR-11-05 |
| 2 | A probe signs in as the suite does | The administrator's password from the environment, then the form's own fields | FR-11-02 |
| 3 | A probe the trial blocks is lost | An app that will not boot, install or sign in fails every probe that needs it | FR-06-03 |
| 4 | The report reads the probes' own rates | As the security reader files them | FR-11-06 |

The decisions are ADR-012 and ADR-018.

## 8.7 The report

### 8.7.1 Contrasts

Each metric is reported per arm and for the contrasts a round registers.
Round 5's:

| Contrast | Asks |
| -------- | ---- |
| `inline − none` | Does every rule, copied in, help? |
| `hybrid − none` | Does the hybrid model help? |
| `reference − none` | Does naming the templates help? |
| `skills − none` | Do a root file and task skills help? |
| `skills − hybrid` | H1: do skills deliver what hybrid does? |
| `reference − hybrid` | H3: does naming the templates alone deliver less? |
| `skills − inline` | The same rules, with and without the split into skills |

Round 5e's, read under round 5d's rules:

| Contrast | Asks |
| -------- | ---- |
| `lazyref − reference` | H7: does a template read when the work touches its topics deliver what one read up front does? |
| `lazyskills − lazyref` | H8: does a skill load deliver what a file read does, at the same moments? |
| `lazyskills − skills` | H9: do whole templates as skills, at a named moment, deliver what task skills do? |
| each map arm − `none`, `hand`, `short`, and the other reused arm | Secondary, no verdict; the `none` reading feeds round 6's screen |

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | No paired verdict across rounds | A contrast pairing trials from different rounds keeps its mean and interval, and counts as neither a win nor a fail | FR-12-01 |
| 2 | Or a registered unpaired contrast | A round may read an earlier round's arm unpaired, with a verdict, as round 5d does | FR-12-02 |
| 3 | Only what the arms ran | Every declared contrast whose arms ran, and no other; earlier rounds' contrasts stay declared | FR-12-03 |
| 4 | A template change is one contrast | `candidate − baseline`, both arms in one round ([ch. 4.2](04-solution-strategy.md)) | — |

The decision is ADR-015.

### 8.7.2 Metric directions

| Direction | Metrics |
| --------- | ------- |
| Better up | Task success, adherence, coverage, docstring coverage, extension points present, every judge score, the probe pass rates |
| Better down | Every static-analysis count, cognitive and cyclomatic complexity, tokens, turns, wall time, cost, files, lines, artifacts nobody asked for, change-task churn, axe violations, HTML errors |
| Down, against a band | From round 5, app code's lines and files: a rise wholly inside the margin (8.1.2) reads held, one wholly past it worse (FR-02-06) |
| Neutral, no verdict | Maintainability index, instability, test code's lines; from round 5, the source lines and files app code replaces; before round 5, app code's rows (FR-12-04) |

### 8.7.3 Report documents

A round writes three documents to `docs/reports/`, one per reader, plus the
radar's two images (FR-12-05):

| File | Reader | Holds |
| ---- | ------ | ----- |
| `YYYY-MM-DD-efficacy.md` | Anyone deciding | The radars, each approach in plain words, the round's questions answered, how sure the answers are |
| `YYYY-MM-DD-efficacy-appendix.md` | Someone checking a claim | What produced the results, the radar's axes row by row, the verdict vector |
| `YYYY-MM-DD-efficacy-record.md` | An auditor | Every metric's table, the change task, raw numbers per trial, lost and re-run trials, reaches, the evidence check |

**The radar** (FR-12-06). One per file arm, against `none` as the ring at 0.
Its axes group the verdict vector's rows: reliability, security, data
protection, design, maintainability, tests, economy. An axis is the share of
its rows better than `none` minus the share worse, from −1 to +1. It comes
as two SVGs, light and dark. Round 5d registers a radar sized by how far
each row moved instead.

**The ISO radar** (FR-12-12). From round 6 the axes are the eight
characteristics of ISO/IEC 25010:2023, in the standard's order, and each is
the share of its targets met: the `QT` rows of the requirements, each a pass
or a fail per build. A sub-characteristic's share is averaged over the axis,
then over the arm's trials; one with no target reads not measured, never 0 %.
A build that does not install or boot fails Reliability's first target and
is left out of every other axis. A marker turns only where the whole
interval of the difference against `none` lies past the axis's margin
(8.1.2): a filled ▲ up, a hollow ▽ down, a dot within. The cost sits above
each radar, shown and not scored, and the appendix holds one table of
sub-scores per axis. The decision is ADR-023.

Round 6's targets read four sources the pilot's did not (FR-12-21 to
FR-12-23, FR-16-06):

- **Hidden-suite modules.** Functional correctness has one target per build
  module, met where the module passes whole: no check failed, errored or
  skipped. A module missing from a build's report is not measured where
  the suite's revision did not hold it, and not met where it did: it failed
  to collect or ran out of time. The sub-characteristic is still one share
  among three on its axis, however many modules it holds.
- **Quality probes.** Each pass-or-fail probe is one target: fault
  tolerance, availability, capacity, resource use, co-existence and
  portability. A lost probe fails; a missing one is not measured.
- **Latency.** Its target reads a cutoff calibrated from the reference
  build and a planted slowdown, frozen before round 6 registers. Until then
  it is not measured.
- **The change task's tree.** Its interfaces are one target on
  Interoperability and its data upgrade one on Adaptability (8.6.4). Both
  are read whatever the trial's build did, since the change starts from a
  fixture, not from that build (FR-16-06).

A pilot round read by the ISO radar keeps the targets it had before round 6,
and reads round 6's only when `--round6-targets` asks for them.

**One radar a task** (FR-16-08). A named round draws the ISO radar and gives
each arm's verdict twice, once a task, each against `none` on the same task:

| Task | Reads | Cost beside it |
| ---- | ----- | -------------- |
| Build | Each build trial's tree; no change target | The build's mean billed cost per trial |
| Change | Each change task's tree, scored in full, with the change targets | The change task's mean billed cost per trial |

The summary, its tables, the plain report and the appendix name the task
each reads. Neither task's readings stand in for the other's, so a build
that broke says nothing of the change it never started. A pilot round
draws one radar over its trials as they are.

**Each approach in plain words** (FR-12-07):

- What it did better and worse than `none`, by radar axis.
- Reliability: how many runs fell short, and how many would not start.
- Cost: dollars per run.
- Its verdict. In the pilot rounds it reads the deciding measures, the
  hidden tests, both probe sets and the judge's five primaries. From round 6
  it reads the ISO radar's axes (FR-12-16). Either way: **Yes** where one is
  better and none worse, **Worse** where any is worse, **No** where none
  moved.

In the pilot rounds the radar and the words describe the verdicts and
decide nothing. From round 6 the verdict reads the radar's own markers, so
the two cannot disagree; an axis no target measures is not read. Round 6's
arms are screened on the same axes (FR-12-17). A pilot round read by the
ISO radar is a post-hoc draft (FR-12-18). Every claim rests on a row of the
appendix or the record. What the report opens with is ADR-013; the verdict
on the axes is ADR-024.

### 8.7.4 Checks declared after a run

A check chosen after the results were seen can describe a run, never decide
it, or the bar would move with the results.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Declared before it is read | In writing, with its direction, before any trial is read for it | — |
| 2 | Never decides | Never in the verdict vector or a "nothing got worse" claim | — |
| 3 | Fixed for next time | A check worth deciding on is registered before the next run | — |

Rounds 1 and 2 read their security checks this way, in a section of their own
with no verdict. From round 3 every check is a probe declared before the run,
so no report prints such a section.

### 8.7.5 Withdrawn metrics and re-scores

A fault found in an instrument, such as the scorer, the hidden suite or the
environment they run in, is fixed and every trial re-scored. Only a fault a
re-score cannot repair, one in what the trial itself was asked, withdraws the
metric.

**Why**

- Numbers from a faulty instrument are known to be wrong; keeping them protects
  nothing.
- Faults tend to be hunted where results disappoint, so the old verdicts stay
  visible beside the new ones.

**Rules**

| # | Rule | In practice | Requirement |
| - | ---- | ----------- | ----------- |
| 1 | Record the fault first | The fault and its fix are written in an issue before any re-score is read | FR-12-10 |
| 2 | Validate the fix | The fixed instrument passes its own validation again: the hidden suite passes the reference in full and catches every mutation; a script passes its self-test | FR-12-10 |
| 3 | Every trial, never a subset | Each round that reads the faulty scores is re-scored in full; a root never mixes two suite revisions or two Pythons | FR-12-10 |
| 4 | Keep the old verdicts | A replaced report opens with a dated note naming the fault and the verdicts it replaces | FR-12-10 |
| 5 | Withdraw what cannot be fixed | Recorded in `tests/efficacy/withdrawn.json` against the grader's revision; the report names the metric and the reason, with no number, interval or verdict | FR-12-09 |

The decision is ADR-021.

## 8.8 Records

Every stage writes what it did beside what it made, so any figure can be
traced to its inputs and re-run.

| Stage | Records |
| ----- | ------- |
| Harness | The run record, written as every trial starts and ends (FR-13-01) |
| Arm generator | `generation.json`, per generated file (FR-13-02) |
| Scorer | Each score with the revisions it was graded under |
| Judge | Each judging with its model, effort and seed |
| Archive | All of the above, in the private archive with a hash per file (FR-13-03) |

The report refuses to write under `docs/reports/` once any reading changed
since the archive was verified (FR-13-04). The decision is ADR-019.

## 8.9 Concurrent runs

`score.py`, `judge.py` and `security.py` each clear a trial's directory
before rebuilding it, so two runs on one root would destroy each other's
work.

| Claim found on the root | What the run does | Requirement |
| ----------------------- | ----------------- | ----------- |
| None | Writes `<tool>.running`, naming its process | — |
| A live process's | Refused | FR-14-01 |
| An ended process's | Takes it over, and says so | FR-14-02 |
