# Archive and report

Every trial of the round is scored. The operator judges them, archives the
round and writes its report.

Target:

- A verified archive in `braboj/tariff-runs`, then the dated report under
  `docs/reports/` in this repository
  ([ch. 6.4](../../architecture/06-runtime-view.md))

Assumptions:

- A clone of `braboj/tariff-runs` with room for the round
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Judge | Reads every trial three times | 7.5 to 15 hours | 225 readings for round 5's 75 trials, over several days where the plan's weekly limit binds. A run cut short by a usage limit resumes when started again |
| 2 | Operator | Archives the round | 15 min | Copies, restores into a temporary root, recomputes the report's figures from both, and writes `archived.json` only when they match |
| 3 | Operator | Commits and pushes the archive | 5 min | Before the report's pull request |
| 4 | Operator | Writes the report into `docs/reports/` | 2 min | Refuses without the stamp, or once a reading changed since |
| 5 | Operator | Opens the report's pull request in this repository | 10 min | The report and, for a registered hypothesis, its verdicts |
| | | Total | 8 to 16 hours | |

## Commands

```bash
py tests/efficacy/judge.py --root <run root> --repeat 3
py tests/efficacy/archive.py --root <run root> --into <a fresh directory in braboj/tariff-runs>
py tests/efficacy/archive.py --verify --root <run root> --from <the archive>
py tests/efficacy/report.py --root <run root>
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Round 3's run root and scoring area were deleted with nothing kept, so none of its readings can be re-run. Rounds are now archived before they are reported | Settled in [ADR-019](../../decisions/019-archive-before-the-report.md), 2026-10-15 |
| 2 | A file over 50 MB is refused, because a push would be | Settled in [ch. 6.4.2](../../architecture/06-runtime-view.md) |
| 3 | The report lands in another repository, so this one holds no results | Settled: reports land in this repository's `docs/reports/` (#170), and [the rounds index](../../rounds/README.md#reports) links every report |
