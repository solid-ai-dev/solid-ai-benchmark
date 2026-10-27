# Read a report

A team lead is deciding whether the team should adopt a generated context
file. They do not write code daily and have read the
[primer](../../primer.md). Target: a yes or no, with its main caveat, in
15 minutes.

Assumptions: the latest round's report, read on a laptop. Minutes are
estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | Finds the latest report under `docs/audits/` in `solid-ai-templates` | 3 | Nothing in this repository links to it |
| 2 | Reads the finding table's first row, "Improves the code?", per file | 2 | Yes, Worse or No, against no file |
| 3 | Reads "Hidden tests passed" against the no-file arm | 2 | A file that breaks the app is not an improvement, whatever else it gains |
| 4 | Reads code size and cost | 2 | Signed shares of the bare agent's, shown only where the interval separated them |
| 5 | Reads the caveats line: K, the escalation, lost trials, reach | 3 | Every interval is descriptive at K = 3 |
| 6 | Reads the assessment's claims table for the view across rounds | 3 | One round's verdict can flip in the next |
| | Total | about 15 minutes | |

The answer today, from round 4 and the assessment: a generated file gets
its conventions followed more, does not break a working build with a
strong model, and costs more. It has not made a strong model's code
clearly better. With a weaker model, every template file lowered the
tests passed.

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | No index of reports in this repository, so a reader must know to look in the templates source | Open |
| 2 | Round 4 has a one-page plain summary beside its generated reports. Earlier rounds do not | Open |
| 3 | Reports use terms such as "verdict vector" and "no improvement shown" without defining them | Settled in the [glossary](../../architecture/12-glossary.md) and the primer |
