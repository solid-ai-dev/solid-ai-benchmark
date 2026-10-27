# Generate the arms

The operator prepares a round whose generated arms must be made fresh.
Target: each generated arm's `CLAUDE.md` made once, in one non-interactive
call, with clean leak scans, within its budget, and its `generation.json`
committed beside it.

Assumptions: a templates clone at the round's fixed release, named with
`--templates`. Three generated arms, as in rounds 1 to 4. Minutes for the
model calls are estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | `generate_arm.py --self-test` | 1 | Proves the leak scan and the budget can fail |
| 2 | `--dry-run` per arm: builds and scans the prompt without a model | 1 each | The cheap check after any change to the brief or the chain |
| 3 | The real generation per arm, at a root outside this repository | 5 to 10 each | Estimate. A result over budget is refused and kept as rejected, never trimmed |
| 4 | Reads each `generation.json`: release, chain, model, both scans, the budget check | 5 | The report reads it from there |
| 5 | Commits the files and their records | 5 | An existing file is never overwritten without `--replace` |
| | Total | about 40 minutes | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Retrying a refused generation until one passes would select the tersest sample. The instruction instead asks the model to measure every line before answering | Settled in design §10, 2026-09-26 |
| 2 | The prompt scan is broad and the output scan narrow: a spec-only token in the prompt means the wiring is wrong, and only data nobody could derive counts as an output leak | Settled in design §3.4 |
| 3 | Round 5's `reference` and `skills` arms are made by other means: fixed text, and `resolve_chain.py --emit` | Open in design §13.4 |
