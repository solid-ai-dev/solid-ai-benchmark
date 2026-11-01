# Generate the arms

The operator prepares round 5, whose context files must each be made once,
before block A, from one chain of the templates.

Target:

- Each arm's file made once, with clean leak scans and its
  `generation.json` committed beside it
  ([ch. 5.5.3](../../architecture/05-building-block-view.md))

Assumptions:

- A templates clone at the round's registered ref, named with `--templates`
- Round 5's four context-file arms: `reference` as fixed text, `inline` and
  `hybrid` as one generation each, `skills` from the emitter
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Operator | Runs the generator's self test | 1 min | Proves the leak scan, the reference text and the fact filling can fail |
| 2 | Operator | Dry-runs each model arm: builds and scans the prompt without a model | 1 min each | The cheap check after any change to the brief or the chain |
| 3 | Generator | Makes each arm, at a root outside this repository | 5 to 10 min each | Nobody answers questions, and nobody trims a result |
| 4 | Operator | Reads each `generation.json`: ref, chain, commit, how the file was made, its size, both scans | 5 min | The report reads it from there |
| 5 | Operator | Commits the files and their records | 5 min | An existing file is never overwritten without `--replace` |
| | | Total | about 40 min | |

## Commands

```bash
py tests/efficacy/generate_arm.py --self-test
py tests/efficacy/generate_arm.py --arm inline --root <outside this repository> --dry-run
py tests/efficacy/generate_arm.py --arm inline --root <outside this repository>
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Retrying a refused generation until one passes would select the tersest sample. The instruction instead asks the model to measure every line before answering | Settled in [ADR-002](../../decisions/002-the-arms.md), 2026-09-26 |
| 2 | The prompt scan is broad and the output scan narrow: a spec-only token in the prompt means the wiring is wrong, and only data nobody could derive counts as an output leak | Settled in [ch. 5.5.4](../../architecture/05-building-block-view.md) |
| 3 | Round 5's `reference` and `skills` arms are made by other means: fixed text, and `resolve_chain.py --emit` | Open in [round 5's registration, 13.4](../../rounds/round-5.md) |
