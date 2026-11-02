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

![An example radar with made-up values. Eight axes in ISO order, each scored as the share of its targets met: Functionality 95 %, Performance 70 %, Compatibility 85 %, Usability 60 %, Reliability 75 %, Security 90 %, Maintainability 80 % and Flexibility 55 %. A dashed green ring marks every target met, and a thin grey outline shows none, the build with no rules file. Each axis carries a filled triangle where it is better than none, a hollow downward triangle where it is worse, and a grey dot where no difference is shown; Security reads 90 % up 30, Reliability 75 % down 10. The top right corner reads $9.30/run, 2.2x none](../diagrams/iso-radar-example.png)

- **Cost** sits in the top right corner of each panel, as dollars per run and
  as a multiple of the baseline: `$9.30/run, 2.2x none`. It is shown, not
  scored: it is not an axis.
- **No verdict on the chart.** The verdict word that panels carried before is
  dropped; the report's text gives it.
- **The target ring** marks where each axis meets its targets.
- **`none`** is drawn as a thin grey outline with no fill, the reference the
  cost corner is measured against too.

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

## Open

| Item | Proposal |
| ---- | -------- |
| Scoring per axis | Each row has measurable targets, written as quality requirements (`QG` rows) with a target and a motivation. An axis scores the share of its targets met, so the target ring is 100 % |
| Target values per axis | Set per system, before it is scored |
| Mapping today's rows | Each metric the benchmark reads is placed under one row: hidden tests under functional correctness, probes under security's rows, coverage and test quality under testability, judge rows under their characteristics |
| A first re-score | The current system on the new axes; the old chart read Tests high, Reliability and Economy low |
