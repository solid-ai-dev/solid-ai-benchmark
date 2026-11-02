# Spike: a quality radar on ISO/IEC 25010:2023

Written 2026-11-02, from the owner's handoff and a review of it.

The idea: one radar that assesses any backend's product quality against ISO/IEC
25010:2023, lean enough to read at a glance, with the evidence in tables below
it. It replaces radar axes built from what the benchmark happens to measure,
such as Tests or Economy, with the standard's own characteristics.

## The axes

Eight axes, in the standard's own order, one word each. Safety, the ninth
characteristic, is left out: it does not apply to this backend.

| # | Axis | ISO/IEC 25010:2023 characteristic |
| - | ---- | -------------------------------- |
| 1 | Functionality | Functional suitability |
| 2 | Performance | Performance efficiency |
| 3 | Compatibility | Compatibility |
| 4 | Usability | Interaction capability |
| 5 | Reliability | Reliability |
| 6 | Security | Security |
| 7 | Maintainability | Maintainability |
| 8 | Flexibility | Flexibility |

- The order is the standard's, so radars from different systems and rounds
  can be laid side by side.
- No axis is placed opposite another on purpose. A radar does not show
  opposition, and only two pairs are real trade-offs (Security with Usability,
  Performance with Maintainability); a report names a trade-off in its text.
- Tests and design are evidence, not qualities: they feed Maintainability's
  testability and modularity.

## The chart

Lean: the eight axes, the target ring, the system's shape, `none`'s outline
for reference, and one figure.

![An example radar with made-up values. Eight axes in ISO order, each scored as the share of its targets met: Functionality 95 %, Performance 70 %, Compatibility 85 %, Usability 60 %, Reliability 75 %, Security 90 %, Maintainability 80 % and Flexibility 55 %. A dashed green ring marks every target met, and a thin grey outline shows none, the build with no rules file. Each axis carries a filled triangle where it is better than none, a hollow downward triangle where it is worse, and a grey dot where no difference is shown; Security reads 90 % up 30, Reliability 75 % down 10. Centred above the chart, the cost reads $9.30/run, 2.2x none](../diagrams/iso-radar-example.png)

- **Cost** sits centred above each panel, over Functionality, as dollars per
  run and as a multiple of the baseline: `$9.30/run, 2.2x none`. It is shown, not
  scored: it is not an axis.
- **No verdict on the chart.** The verdict word that panels carried before is
  dropped; the report's text gives it.
- **The target ring** marks where each axis meets its targets.
- **`none`** is drawn as a thin grey outline with no fill, the reference the
  cost is measured against too.

How to read better, worse and lacking:

| Element | Shown as | Says |
| ------- | -------- | ---- |
| The system's area | One light fill, always the same | Its shape; area carries no meaning |
| Better than `none` | Filled ▲ on the axis, green, and "▲ +30" by the label | Past the margin, in the improving direction |
| Worse than `none` | Hollow ▽ on the axis, red, and "▽ −10" by the label | Past the margin, in the worsening direction |
| No difference shown | Small grey ● | Within the margin |
| Lacking | The white gap between the shape and the target ring | How far each axis is from every target met |

- A marker turns ▲ or ▽ only past the axis's margin, so noise stays a grey dot.
- Shape carries the meaning as well as colour: filled up, hollow down, a dot.
  The chart reads the same printed in black and white, or by a reader who does
  not see red and green apart.

## The tables below the chart

One table per axis, one row per ISO sub-characteristic. A row that does not
apply to a backend API is left out. Three rows are added, each named where it
comes from.

| Axis | Rows |
| ---- | ---- |
| Functionality | Functional completeness, functional correctness, functional appropriateness |
| Performance | Time behaviour, resource utilisation, capacity |
| Compatibility | Co-existence, interoperability |
| Usability | Appropriateness recognisability, learnability, operability, user error protection, user assistance, self-descriptiveness |
| Reliability | Faultlessness, availability, fault tolerance, recoverability |
| Security | Confidentiality, integrity, non-repudiation, accountability, authenticity, resistance; **data protection** (GDPR, ISO/IEC 27701) |
| Maintainability | Modularity, reusability, analysability, modifiability, testability; **observability** |
| Flexibility | Adaptability, scalability, installability, replaceability; **deploy and rollback** |

- **Usability** means the API's and the operator's: error clarity, consistent
  naming, documentation. There is no user interface. ISO's user engagement and
  inclusivity rows are left out.
- **Data protection** is not one of ISO's security sub-characteristics. It is a
  row of its own, so a weak data-protection result is not hidden inside a strong
  security one.
- **Operability** keeps ISO's meaning, how easy the API is to operate, and stays
  under Usability. Running the system is split into **observability** (logs,
  metrics, health, under analysability) and **deploy and rollback** (under
  installability and replaceability).

## Scoring

Each sub-characteristic has measurable targets, each a pass or a fail, written
as quality requirements (`QG` rows) with a target and a motivation.

| Step | Rule | Why |
| ---- | ---- | --- |
| Target | Pass or fail, such as "hidden tests ≥ 98 % pass" | Every axis lands on one scale, 0 to 100 % |
| Sub-score | The share of its targets one trial meets | |
| Axis, per trial | The mean of its sub-scores | Each sub-characteristic weighs the same, however many targets it has; a median of so few would hide the weakest one |
| Axis, per arm | The mean over its trials | A median would hide a few broken builds |
| ▲ or ▽ against `none` | Only where the whole interval of the difference lies past the axis's margin | Two means a few points apart stay a grey dot |

- **At least three targets** per sub-characteristic; one with fewer is marked
  in its table, since a single target swings it between 0 and 100 %.
- **A broken build counts once.** A build that will not install or start counts
  against Reliability only; every other axis reads the working builds.
- **Faults are fixed, not averaged away.** A score the instrument got wrong is
  re-scored (ADR-021); the mean keeps real failures in view.
- **The margin** is sized per axis from earlier rounds' trial-to-trial noise,
  before the round runs. The example's 5 points is a placeholder.

## Targets

- **Fixed per system, not per round.** They come from the spec and the quality
  requirements, such as "hidden tests ≥ 98 % pass" or "every security probe
  passes".
- **Set once, before the first round scores the system,** so no target moves
  after its results are seen.
- **Changed only by a new registration,** like any other rule.

## Mapping today's metrics

A draft for review. Each metric the benchmark reads today sits under one row.
The app under test serves pages as well as an API, so Usability keeps its
accessibility and form rows here.

| Axis | Sub-characteristic | Today's metrics |
| ---- | ------------------ | --------------- |
| Functionality | Functional correctness | Hidden-test pass rate, on working builds |
| Functionality | Functional completeness | Public surface: names exported against names the spec requires |
| Performance | Resource utilisation | Invoice builder's response size and request count |
| Compatibility | Interoperability | JSON and CSV exports, byte-exact against the seed |
| Usability | Inclusivity | axe-core WCAG 2.1 AA violations, forms with JavaScript disabled |
| Usability | User assistance | A README with install and usage |
| Usability | Operability | HTML validity, less `hx-*` |
| Reliability | Faultlessness | Installs and boots; `mypy --strict` type errors |
| Reliability | Fault tolerance | Stack traces in answers to malformed requests |
| Security | Confidentiality | Plaintext password, account enumeration, hard-coded secret, cookie flags |
| Security | Integrity | CSRF on sign-in and on forms, open redirect, assembled SQL, stored XSS |
| Security | Resistance | Debug left on, security headers, vulnerable dependencies, `bandit` findings |
| Security | Data protection | The three data-protection probes |
| Maintainability | Modularity | Layering, import cycles, instability, one error hierarchy |
| Maintainability | Analysability | `ruff`, `ruff format`, cognitive and cyclomatic complexity, docstrings, a `NullHandler` |
| Maintainability | Modifiability | Change-task churn and pass, extension points, kind ladders, unused code |
| Maintainability | Testability | Coverage of the agent's own tests, discoverable tests |
| Flexibility | Installability | `pip install .` in a clean environment, complete packaging metadata |

- **The judge's rows** sit beside the probes and tools under the same
  sub-characteristics: security and data protection under Security, design
  under modularity, readability under analysability, maintainability under
  modifiability, test quality under testability.
- **Thin axes:** Performance, Compatibility and Flexibility rest on one or two
  metrics, and Reliability's availability and recoverability on none. An empty
  sub-characteristic reads "not measured", never 0 %.
- **Off the radar:** cost, turns and tokens go to the cost line; code size
  stays a neutral row in the tables.

## Open

| Item | Proposal |
| ---- | -------- |
| A first re-score | The current system on the new axes; the old chart read Tests high, Reliability and Economy low |
