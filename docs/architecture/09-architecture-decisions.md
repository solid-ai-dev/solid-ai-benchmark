# 9. Architecture decisions

Every decision the benchmark has taken is dated, with its reason and its
issue, in the design's [decisions table](../design/efficacy-benchmark.md#10-decisions).
That table is the record. This chapter lists the ones that shaped the
architecture, so a reader can see why the parts are built as they are.

| Decision | Shapes | Date |
| -------- | ------ | ---- |
| The app is `tariff`: a natural object model, two extension axes, sharp decimal tests | Every input, the hidden suite, the change task | 2026-09-12 |
| A hand-written arm runs beside the generated ones | `arms/hand/`, the `hand` contrasts | 2026-09-12 |
| K = 3, with one bounded escalation to 5 | `report.py`'s escalation rule, `harness.py`'s refusal above 5 | 2026-09-12 |
| The hidden suite lives in a private repository | Scoring clones it into the scoring area only | 2026-09-12 |
| Trials are bounded by budget and timeout, since the CLI has no turn cap | The harness's process-tree handling | 2026-09-12 |
| No human holdout | Every stage is a script, and the judge is checked by a control fixture instead | 2026-09-17 |
| A contrast crossing rounds gets no verdict | `report.py` | 2026-09-18 |
| The primaries are anchored and checked by the control fixture | `control/`, the rubric | 2026-09-19 |
| Each tree is judged three times | `judge.py --repeat 3` | 2026-09-19 |
| The brief and the change prompt live in files of their own | `brief.txt`, `change-prompt.txt` | 2026-09-24 |
| A probe the trial keeps from running is lost, not missing | `security.py` | 2026-09-25 |
| The rounds' judge is `claude-opus-5-5`, with `gpt-6-astra` as a sampled cross-check | `judge.py --cli`, the cross-check root | 2026-09-25 |
| A round is archived and verified before it is reported | `archive.py`, the `archived.json` stamp, `report.py`'s refusal | 2026-10-15 |
| A trial is both fenced and excluded | The deny rules and the transcript scan | 2026-10-15 |
| A trial may not stop processes by name | The deny rules, and voiding a trial whose harness died | 2026-10-16 |

The decisions about the templates themselves, such as ADR-052 (hybrid is
the delivery floor) and ADR-058 (task procedures load on demand), live in
`solid-ai-templates` under `docs/decisions/`. A round's hypotheses name the
record they decide.
