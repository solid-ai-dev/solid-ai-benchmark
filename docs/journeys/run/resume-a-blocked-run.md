# Resume a blocked run

Part way through a round, the account hits its usage limit, and trial
`short-2` ends with no result. Target: the round finished, `short-2` re-run
once in its own place, and no trial counted twice.

Assumptions: the limit lifts within a few hours. Minutes are estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | The harness records `short-2` as blocked, moves its workspace and tarball under `void/`, and stops | 0 | The provider cut it, not the agent |
| 2 | The operator reads the run record: every trial before `short-2` is kept | 5 | The record is rewritten after every trial |
| 3 | Restarts with `--from short-2 --resume-after-block` | 1 | The same `--arms` and root |
| 4 | The harness probes the generator every 30 minutes until it answers | wait | `--probe-every`. It gives up after 12 hours, `--give-up-after` |
| 5 | `short-2` re-runs in its place, and the round carries on | per trial | A second block of the same trial stops the run |
| 6 | Scoring reads every run record in the root, so the resumed run scores whole | | A trial offered by two records is refused, not picked |
| | Total | about 10 minutes of attention | |

Commands:

```bash
py tests/efficacy/harness.py --root <run root> --arms none,inline,hybrid,reference,skills --from reference-2 --resume-after-block
```

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | A run started without `--resume-after-block` stops at the first block and waits for the operator | Settled in [ch. 6.1.2](../../architecture/06-runtime-view.md) |
| 2 | A reached trial is voided and re-run at once, with no wait. A second reach loses it, and the run goes on | Settled in chapter 6.1 |
| 3 | The report reads each transcript's time to tell a re-run's session from the blocked attempt before it | Settled in [ch. 6.4.2](../../architecture/06-runtime-view.md) |
