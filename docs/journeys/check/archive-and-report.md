# Archive and report

Every trial of the round is scored. The operator judges them, archives the
round and writes its report. Target: a verified archive in
`braboj/tariff-runs`, then the dated report under `docs/audits/` in the
templates source.

Assumptions: a clone of `braboj/tariff-runs` with room for the round, and
a templates clone to write the report into. Minutes are estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | `judge.py --root <root> --repeat 3` | 90 to 180 | 45 readings for 15 trials. A run cut short by a usage limit resumes when started again |
| 2 | `archive.py --root <root> --into <a fresh directory>` | 15 | Copies, restores into a temporary root, recomputes the report's figures from both, and writes `archived.json` only when they match |
| 3 | Commits and pushes the archive | 5 | Before the report's pull request |
| 4 | `report.py --root <root>` | 2 | Refuses without the stamp, or once a reading changed since |
| 5 | Opens the report's pull request in the templates source | 10 | The report and, for a registered hypothesis, its verdicts |
| | Total | 2 to 3.5 hours | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Round 3's run root and scoring area were deleted with nothing kept, so none of its readings can be re-run. Rounds are now archived before they are reported | Settled in design §10, 2026-10-15 |
| 2 | A file over 50 MB is refused, because a push would be | Settled in the harness guide |
| 3 | The report lands in another repository, so this one holds no results | Open, #17, see [Read a report](../read/read-a-report.md) |
