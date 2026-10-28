# Check the judge

The rubric's anchors have changed before a round, or the judge has. The
owner must show every primary judge row still moves the right way before
the round reads it.

Target:

- Each primary row falls on its damaged tree and rises on its improved one,
  under the rounds' judge ([ch. 8.6.7](../../architecture/08-crosscutting-concepts.md))

Assumptions:

- The control's two pinned bases are unchanged, so the builder accepts
  their hashes
- All times are estimates

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Owner | Runs the control's self test | 2 min | Builds in a temporary directory and checks every mutation landed |
| 2 | Owner | Builds the control root | 2 min | Prints one line per entity it changed, read back off the trees |
| 3 | Owner | Runs the tests in each built tree | 10 min | Every tree passes, so only structure separates them |
| 4 | Judge | Reads the control root, three times per tree | 30 to 60 min | Eleven trees, 33 judgings |
| 5 | Owner | Reads each primary row: down on `degraded-1`, `obscured-1`, `insecure-1`, `leaky-1`, up on `improved-*`, `clarified-1`, `secured-1`, `protected-1` | 15 min | A row that does not move cannot decide a round. Results go in [ch. 10.7](../../architecture/10-quality-requirements.md) |
| | | Total | about 1.5 hours | |

## Commands

```bash
py tests/efficacy/control/control.py --self-test
py tests/efficacy/control/control.py --root C:/efficacy/control-<date>
py -m pytest -q          # in each built tree; every tree passes
py tests/efficacy/judge.py --root C:/efficacy/control-<date> --repeat 3
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | No CI ran the control's self test after the split from the templates. The self-tests workflow now runs it on every push and pull request | Settled in `.github/workflows/self-tests.yml` |
| 2 | A mutation that silently did nothing would read as the judge holding. The builder refuses any mutation that did not land | Settled in [ch. 8.6.7](../../architecture/08-crosscutting-concepts.md) |
| 3 | The cross-check judge reads the same trees in a root of its own, never averaged with the rounds' judge | Settled in [ch. 8.6.7](../../architecture/08-crosscutting-concepts.md) |
| 4 | The security and data-protection rows cannot move on the first base, which has no sign-in. Their trees come from a second base, one uncounted calibration trial | Settled in [ch. 8.6.7](../../architecture/08-crosscutting-concepts.md) |
