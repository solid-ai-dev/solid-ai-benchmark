# Run a round

The operator runs a round of five arms at K = 3 on the Windows
workstation: build trials, change tasks, then scoring. Target: every trial
built, changed and scored, with none lost to the setup.

Assumptions: the arms' files exist, the needs of [ch.
7](../../architecture/07-deployment-view.md) are installed, and 15 GB is free on the run
root's drive. Times and costs per trial are measured in rounds 1 and 2 at
`claude-sonnet-5`. Scoring times are estimated.

| # | Step | Minutes | Cost | Notes |
| - | ---- | ------- | ---- | ----- |
| 1 | Checks `claude`, `gh`, Python 3.12, Java and free disk | 10 | | A missing piece shows as a refusal or a missing metric |
| 2 | `harness.py --self-test` | 5 | | Estimate. Plants each thing the harness removes or catches |
| 3 | A dry run of the whole round | 5 | | Prepares every workspace in `<root>-dry-run`, calls no model |
| 4 | The build trials, 15 in interleaved order | 240 to 420 | about $195 | Measured: 16 to 28 minutes and $8.7 to $16.7 per trial |
| 5 | The change tasks, 15 in the same order | 120 to 240 | about $130 | Measured in round 1: $5 to $17 per task. Minutes estimated |
| 6 | `score.py`, build then change, with the security probes | 150 | | Estimate: about 5 minutes per trial |
| | Total | 9 to 14 hours | about $325 | Subscription quota, not invoice |

Commands:

```bash
py tests/efficacy/harness.py --self-test
py tests/efficacy/harness.py --root <run root> --arms none,inline,hybrid,reference,skills --k 3 --model <exact id> --dry-run
py tests/efficacy/harness.py --root <run root> --arms none,inline,hybrid,reference,skills --k 3 --model <exact id>
py tests/efficacy/harness.py --root <run root> --task change --arms none,inline,hybrid,reference,skills --resume-after-block
py tests/efficacy/score.py --root <run root>
py tests/efficacy/score.py --root <run root> --task change
```

The run record is rewritten after every trial, so the operator can leave a
round running overnight. A trial that was blocked is handled in
[Resume a blocked run](resume-a-blocked-run.md).

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | Each trial records the templates source's remote, ref and commit, and vendoring reads that ref with `git archive`, so the templates clone's HEAD may move during a run | Settled in [ch. 6.1.2](../../architecture/06-runtime-view.md) |
| 2 | A stray process-stop command in a trial once stopped the harness itself. Such commands are now denied, and a trial whose harness died is voided by the next run | Settled in [chapter 9](../../architecture/09-architecture-decisions.md), 2026-10-16 |
| 3 | A full disk ends a trial with `No space left on device`, and that trial is not a result | Settled in [ch. 7.2](../../architecture/07-deployment-view.md) |
| 4 | A trial that prints its result but does not exit is ended two minutes later | Settled in chapter 6.1 |
