# Check the judge

The rubric's anchors have changed before a round. The owner must show
every primary judge row still moves the right way before the round reads
it. Target: each primary row falls on its damaged tree and rises on its
improved one, under the rounds' judge.

Assumptions: the control's two pinned bases are unchanged, so the builder
accepts their hashes. Minutes are estimated.

| # | Step | Minutes | Notes |
| - | ---- | ------- | ----- |
| 1 | `control/control.py --self-test` | 2 | Builds in a temporary directory and checks every mutation landed |
| 2 | `control.py --root C:/efficacy/control-<date>` | 2 | Prints one line per entity it changed, read back off the trees |
| 3 | `py -m pytest -q` in each built tree | 10 | Every tree passes, so only structure separates them |
| 4 | `judge.py --root` on the control root | 30 to 60 | Eleven trees, three readings each |
| 5 | Reads each primary row: down on `degraded-1`, `obscured-1`, `insecure-1`, `leaky-1`, up on `improved-*`, `secured-1`, `protected-1` | 15 | A row that does not move cannot decide a round |
| | Total | about 1.5 hours | |

## Findings

| # | Finding | Status |
| - | ------- | ------ |
| 1 | The control guide says its self test runs in CI. This repository has no CI since the split from the templates | Open, #16 |
| 2 | A mutation that silently did nothing would read as the judge holding. The builder refuses any mutation that did not land | Settled in the control guide |
| 3 | The cross-check judge reads the same trees in a root of its own, never averaged with the rounds' judge | Settled in design §5.7 |
| 4 | The security and data-protection rows cannot move on the first base, which has no sign-in. Their trees come from a second base, one uncounted calibration trial | Settled in design §5.7 |
