# Read a report

A team lead is deciding whether the team should adopt a generated context
file. They do not write code daily and have read the
[primer](../../primer.md).

Target:

- A yes or no on adopting a generated file, with its main caveat, in
  15 minutes

Assumptions:

- The latest round's report, read on a laptop
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Team lead | Finds the latest report under `docs/audits/` in `solid-ai-templates` | 3 min | Nothing in this repository links to it |
| 2 | Team lead | Reads the finding table's first row, "Improves the code?", per file | 2 min | Yes, Worse or No, against no file |
| 3 | Team lead | Reads "Hidden tests passed" against the no-file arm | 2 min | A file that breaks the app is not an improvement, whatever else it gains |
| 4 | Team lead | Reads code size and cost | 2 min | Signed shares of the bare agent's, shown only where the interval separated them |
| 5 | Team lead | Reads the caveats line: K, the escalation, lost trials, reach | 3 min | Every interval is descriptive at K = 3 |
| 6 | Team lead | Reads the assessment's claims table for the view across rounds | 3 min | One round's verdict can flip in the next |
| | | Total | about 15 min | |

The answer today, from round 4 and the assessment: a generated file gets
its conventions followed more, does not break a working build with a strong
model, and costs more. It has not made a strong model's code clearly
better. With a weaker model, every template file lowered the tests passed.

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | No index of reports in this repository, so a reader must know to look in the templates source | Open, #17 |
| 2 | Round 4 has a one-page plain summary beside its generated reports. Earlier rounds do not | Open |
| 3 | Reports use terms such as "verdict vector" and "no improvement shown" without defining them | Settled in the [glossary](../../architecture/12-glossary.md) and the primer |
