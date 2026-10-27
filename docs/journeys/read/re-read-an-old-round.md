# Re-read an old round

The owner wants another vendor's judge to read a finished round, to see
whether the round's judge favoured the templates' own style.

Target:

- The other judge's readings of the round, and the report's agreement per
  judge row ([ch. 8.6.6](../../architecture/08-crosscutting-concepts.md))

Assumptions:

- The round is archived and verified in `braboj/tariff-runs`
- The other judge's plan allows the round's judgings this week
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Owner | Restores the archive into a fresh root | 10 min | Transcripts get back their original times |
| 2 | Owner | Removes `<root>-scoring/judge` | 1 min | The restored judgings would otherwise count as done and read as the other judge's |
| 3 | Owner | Rescores, to extract the trees the judge reads | 75 min | The archive keeps tarballs, not trees |
| 4 | Judge | Reads the round once per trial, with the other vendor's CLI | 60 min | Whole blocks, so every contrast it reads is paired |
| 5 | Owner | Writes the report with the cross-check | 2 min | Agreement per row, and a verdict withheld where the two judges read opposite directions |
| | | Total | about 2.5 hours | |

## Commands

```bash
py tests/efficacy/archive.py --restore --from <the round's archive> --into <a fresh root>
rm -r <that root>-scoring/judge
py tests/efficacy/score.py --root <that root> --rescore
py tests/efficacy/judge.py --root <that root> --cli codex --repeat 1
py tests/efficacy/report.py --root <the run root> --cross-check <that root>
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | The report refuses a cross-check root that holds no judging of the round's trials, since an empty one would print as agreement | Settled in [ch. 6.4](../../architecture/06-runtime-view.md) |
| 2 | Round 4 ran without the cross-check to keep the other vendor's plan free | Settled in [chapter 9](../../architecture/09-architecture-decisions.md), 2026-10-15 |
| 3 | Round 3's raw data was lost, so it cannot be re-read | Settled in [chapter 9](../../architecture/09-architecture-decisions.md), 2026-10-15 |
