# 8. Crosscutting concepts

The ideas that more than one building block applies. Each states the rule
and where it lives in the code.

## 8.1 Pairing and the verdict

A **contrast** compares two arms within each block. With K blocks it is K
paired differences, one per block, never the difference of two means.
`report.py` resamples the differences 10,000 times at a recorded seed and
takes a bias-corrected and accelerated 95 % interval. The verdict follows
from where the interval lies.

| Interval | Verdict |
| -------- | ------- |
| Wholly on the improving side of zero | Better |
| Wholly on the other side | Worse |
| Contains zero | No improvement shown |
| Contains zero, wholly inside the metric's margin | Held: nothing got worse |

Each metric declares its direction (design §6.2), since half improve
downward. A contrast that pairs trials from different rounds keeps its
mean and interval and gets no verdict.

## 8.2 Isolation in layers

No single fence stops every route out of a workspace, so the harness
stacks them and records what each caught.

| Layer | Stops | Cannot stop |
| ----- | ----- | ----------- |
| Scratch home and minimal settings | The owner's global `CLAUDE.md`, hooks, memory and MCP | |
| Cleaned environment | The launching session's variables, interpreter and keys | |
| Deny rules on the file tools | Read and Edit outside the trial's own workspace | The shell, whose paths a prefix rule cannot see |
| Web tools disallowed | Fetching a page | `curl` or `git clone` in the shell |
| Git credential helpers cleared | An authenticated clone of the hidden suite | |
| Process-stop commands denied | Stopping the harness by name | Stopping by PID or port |
| Transcript scan | Any tool call that names a forbidden path or repository, after the fact | A call the transcript does not record |

The scan is the backstop: a hit voids the trial and re-runs it once, and
the report scans again under the current rule.

## 8.3 Missing is not zero

A tool that scanned nothing, failed or timed out records its metric as
missing, with the reason. A grader's skipped check is not a passed one. A
probe the trial keeps from running is lost. A probe the harness could not
run leaves the rate missing. Each script's self test plants the case and
fails if it reads as zero.

## 8.4 One ruler

The first trial scored resolves `scoring-requirements.txt` and freezes it
to `tool-lock.txt`. Every later trial installs from that lock. The lock
leaves out anything local, editable or named like the package under score,
so one trial's code never installs over another's. `toolconfig/` holds the
only configuration the tools run under.

## 8.5 Blindness

The judge reads a bundle with the context file, the vendored templates,
condition markers and scoring's own output removed, in an order shuffled
at a recorded seed. The unblinding map is written where the judge cannot
reach it. A leak scan reads every file in the bundle, and a bundle that
still names its arm is refused.

## 8.6 Registration before results

| Kind of check | Decides | Printed |
| ------------- | ------- | ------- |
| Registered before the round's first trial | Yes | In the verdict vector and the finding table |
| Declared after a run, before any trial is read for it | No | In its own section, means and intervals only |
| Withdrawn, its grader measured something else | No | Named with its reason, no number |

## 8.7 Records

Every stage writes what it did beside what it made: the run record per
invocation, `generation.json` per generated file, each score with the
revisions it was graded under, each judging with its model, effort and
seed. `archive.py` carries all of it to the private archive with a hash per
file, and a report refuses to write once any reading changed since the
archive was verified.

## 8.8 One run at a time

`score.py`, `judge.py` and `security.py` each clear a trial's directory
before rebuilding it. A run writes `<tool>.running` naming its process. A
second run that finds a live claim is refused. A claim naming a process
that has ended is taken over, and the run says so.
