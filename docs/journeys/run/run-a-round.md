# Run a round

The operator runs round 5's block A on the Windows workstation: five arms at
K = 15, the build task alone, then scoring.

Target:

- Every trial built and scored, with none lost to the setup
  ([ch. 6.1](../../architecture/06-runtime-view.md))

Assumptions:

- The arms' files exist
- The needs of [ch. 7](../../architecture/07-deployment-view.md) are installed, with 40
  GB free on the run root's drive
- Times and costs per trial are round 3's, measured at `claude-sonnet-5`.
  Scoring times are estimates
- The cost is subscription quota, not invoice

## Steps

| # | Who | Step | Time | Notes |
| - | --- | ---- | ---- | ----- |
| 1 | Operator | Checks `claude`, `gh`, Python 3.12, Java and free disk | 10 min | A missing piece shows as a refusal or a missing metric |
| 2 | Operator | Runs the harness's self test | 5 min | Plants each thing the harness removes or catches |
| 3 | Operator | Dry-runs the whole round | 5 min | Prepares every workspace in `<root>-dry-run`, calls no model |
| 4 | Harness | Runs the 75 build trials, each block starting one arm later | about 21 hours | Measured in round 3: 10 to 29 min and $1.4 to $3.5 per trial, about $185 |
| 5 | Operator | Scores every trial, with the security probes | about 6 hours | About 5 min per trial |
| | | Total | about 27 hours, over several nights | about $185 |

The run record is rewritten after every trial, so the operator can leave a
round running overnight. A trial that was blocked is handled in
[Resume a blocked run](resume-a-blocked-run.md). A round with the change task
runs it after the build trials with `--task change`, and scores it with
`score.py --task change`.

## Commands

```bash
py tests/efficacy/harness.py --self-test --templates <the templates clone>
py tests/efficacy/harness.py --root <run root> --arms none,inline,hybrid,reference,skills --k 15 --model claude-sonnet-5 --dry-run
py tests/efficacy/harness.py --root <run root> --arms none,inline,hybrid,reference,skills --k 15 --model claude-sonnet-5
py tests/efficacy/score.py --root <run root>
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Each trial records the templates source's remote, ref and commit, and vendoring reads that ref with `git archive`, so the templates clone's HEAD may move during a run | Settled in [ch. 6.1.2](../../architecture/06-runtime-view.md) |
| 2 | A stray process-stop command in a trial once stopped the harness itself. Such commands are now denied, and a trial whose harness died is voided by the next run | Settled in [ADR-020](../../decisions/020-trial-isolation.md), 2026-10-16 |
| 3 | A full disk ends a trial with `No space left on device`, and that trial is not a result | Settled in [ch. 7.2](../../architecture/07-deployment-view.md) |
| 4 | A trial that prints its result but does not exit is ended two minutes later | Settled in chapter 6.1 |
