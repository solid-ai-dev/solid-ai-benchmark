# Generate the arms

The operator prepares a round, whose context files are each built by
script, before block A, from one chain of the templates.

Target:

- Each arm's file built, with a clean leak scan and its `generation.json`
  committed beside it
  ([ch. 5.5.3](../../architecture/05-building-block-view.md))

Assumptions:

- A templates clone holding the round's registered ref, named with
  `--templates`
- The arms, all built with no model call
  ([ADR-025](../../decisions/025-every-arm-is-built-by-a-script.md)):
  `reference`, `lazyref` and `lazyskills` as fixed text, `inline` and
  `skills` from the templates' emitter
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Operator | Runs the generator's self test | 2 min | Proves the scans and the fact filling can fail, and rebuilds every committed arm |
| 2 | Operator | Dry-runs each arm at the round's ref | 1 min each | Builds and scans the files, writes nothing under `arms/` |
| 3 | Generator | Builds each arm, at a root outside this repository | 1 min each | The same ref gives the same bytes |
| 4 | Operator | Reads each `generation.json`: ref, chain, commit, how the file was built, its size, both scans | 5 min | The report reads it from there |
| 5 | Operator | Commits the files and their records | 5 min | An existing file is never overwritten without `--replace` |
| | | Total | about 20 min | |

## Commands

```bash
py tests/efficacy/generate_arm.py --self-test
py tests/efficacy/generate_arm.py --arm inline --ref <ref> --root <outside this repository> --dry-run
py tests/efficacy/generate_arm.py --arm inline --ref <ref> --root <outside this repository> --replace
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | A written arm changes with every writing: round 5e's `hybrid` was 511 lines, the one regenerated for round 6 was 221 | Settled in [ADR-025](../../decisions/025-every-arm-is-built-by-a-script.md), 2026-11-15 |
| 2 | The emitted `skills` root lacked the brief's paragraphs on personal data and on boundaries, and no check read an emitted root | Settled in [ADR-025](../../decisions/025-every-arm-is-built-by-a-script.md), rule 4 |
| 3 | The emitter builds no hybrid file, and the templates' rules forbid one that names template files | Settled in [ADR-025](../../decisions/025-every-arm-is-built-by-a-script.md); `hybrid` runs no more |
