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
  ([ADR-026](../../decisions/026-every-arm-is-built-by-a-script.md)):
  `reference`, `lazyref` and `lazyskills` as fixed text, `inline` and
  `skills` from the templates' emitter, `lazysections` from its sections
  mode, and `lazyrefold` as `lazyref` at the parent of the templates commit
  that cuts the check loop to one check command
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Operator | Runs the generator's self test | 2 min | Proves the scans and the fact filling can fail, rebuilds every committed arm, and checks the on-demand arms: no read of everything at the start, `lazyrefold` against `lazyref`, the section files against the inline root |
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
py tests/efficacy/generate_arm.py --arm lazysections --ref <ref> --root <outside this repository>
py tests/efficacy/generate_arm.py --arm lazyrefold --ref <the check-loop commit>^ --root <outside this repository>
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | A written arm changes with every writing: round 5e's `hybrid` was 511 lines, the one regenerated for round 6 was 221 | Settled in [ADR-026](../../decisions/026-every-arm-is-built-by-a-script.md), 2026-11-15 |
| 2 | The emitted `skills` root lacked the brief's paragraphs on personal data and on boundaries, and no check read an emitted root | Settled in [ADR-026](../../decisions/026-every-arm-is-built-by-a-script.md), rule 4 |
| 3 | The emitter builds no hybrid file, and the templates' rules forbid one that names template files | Settled in [ADR-026](../../decisions/026-every-arm-is-built-by-a-script.md); `hybrid` runs no more |
| 4 | #169 names the check-loop control `lazyref-old`, but an arm's word carries no hyphen: trial names, voided-workspace names and hypothesis labels split on it | Open, 2026-11-15: built as `lazyrefold`; rename only with those readers |
| 5 | `lazysections`, `lazyref` and `lazyrefold` are built at the open templates branch (`d6da8f33`; `a8079352`, the check-loop commit; `4e1de818`, its parent) while the other arms stay at `9abed019` | Open: every arm is re-pinned at one ref once templates #2495, #2496 and #2498 merge |
