# Re-read an old round

The owner wants another vendor's judge to read a finished round, to see
whether the rounds' judge favours the templates' own style. Target: the
cross-check judge's readings of the round, and the report's agreement per
judge row.

Assumptions: the round is archived and verified in `braboj/tariff-runs`.
The cross-check's weekly limit allows about thirty judgings. Minutes are
estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | `archive.py --restore --from <archive> --into <fresh root>` | 10 | Transcripts get back their original times |
| 2 | Removes `<root>-scoring/judge` | 1 | The restored judgings would otherwise count as done and read as the other vendor's |
| 3 | `score.py --root <root> --rescore` | 75 | Extracts the trees the judge reads. The archive keeps tarballs, not trees |
| 4 | `judge.py --root <root> --cli codex --repeat 1` | 60 | Whole blocks, so every contrast it reads is paired |
| 5 | `report.py --root <run root> --cross-check <root>` | 2 | Agreement per row, and a verdict withheld where the two judges read opposite directions |
| | Total | about 2.5 hours | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | The report refuses a cross-check root that holds no judging of the round's trials, since an empty one would print as agreement | Settled in the harness guide |
| 2 | Round 4 ran without the cross-check to keep the other vendor's plan free | Settled in design §10, 2026-10-15 |
| 3 | Round 3's raw data was lost, so it cannot be re-read | Settled in design §10, 2026-10-15 |
