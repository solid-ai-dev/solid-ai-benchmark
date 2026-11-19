# Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

## CI signals

- Read the log of a red check before calling the pull request green or red
- Separate an infrastructure failure (the check could not run) from a diff
  failure (it ran and found something), and say which in the merge decision
- File a separate task for an infrastructure failure, and note it in the
  merge decision
- Never retry until green without saying so (MUST NOT)
- Never bypass a failing check by skipping hooks or by an admin merge
  unless the maintainer explicitly accepts the risk (MUST NOT)
