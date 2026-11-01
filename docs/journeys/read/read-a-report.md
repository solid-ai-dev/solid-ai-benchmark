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
| 2 | Team lead | Reads the radar: one shape per file, against the no-file ring | 1 min | Outside the ring is better; the axes cluster the verdicts |
| 3 | Team lead | Reads each approach: better, worse, and the verdict with its reason | 3 min | A file that breaks the app is not an improvement, whatever else it gains |
| 4 | Team lead | Reads the questions answered and how sure we are | 2 min | Plain words; the numbers are in the appendix |
| 5 | Team lead | Opens the appendix for a claim to check | 3 min | What produced the results, the radar's rows, the verdict vector |
| 6 | Team lead | Reads the assessment's claims table for the view across rounds | 3 min | One round's verdict can flip in the next |
| | | Total | about 15 min | |

The answer today, from round 4 and the assessment: a generated file gets
its conventions followed more, does not break a working build with a strong
model, and costs more. It has not made a strong model's code clearly
better. With a weaker model, every template file lowered the tests passed.

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | No index of reports in this repository, so a reader must know to look in the templates source | Settled: [the rounds index](../../rounds/README.md#reports) lists every report |
| 2 | Round 4 has a one-page plain summary beside its generated reports. Earlier rounds do not | Open |
| 3 | Reports use terms such as "verdict vector" and "no improvement shown" without defining them | Settled in the [glossary](../../architecture/12-glossary.md) and the primer |
