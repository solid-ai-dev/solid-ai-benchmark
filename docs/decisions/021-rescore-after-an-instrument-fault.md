---
id: "021"
status: Accepted
date: 2026-11-02
category: process
supersedes: []
superseded_by: []
---

# ADR-021: Re-score after an instrument fault

## Context

Two faults in the instruments turned up in round 5c, both after its report:

| Fault | What it did | Builds hit |
| ----- | ----------- | ---------- |
| Scored on Python 3.14, though the spec names 3.12 | Refused builds capped below 3.13 as not installing | `hybrid-3`, `inline-5`, `skills-4` |
| The hidden suite ran every module in one process | A build's sign-in lockout, tripped by the suite's own wrong-password tests, failed every later test that signs in | `skills-4`, `skills-10`, `hybrid-2`, `reference-4` |

The rule then in force, FR-12-10, said a corrected grader never re-grades the
same trials, and the metric is withdrawn instead. It was written for round 1's
change-task grader, whose fault lay in what the trial was asked: no re-grade
could repair it. Applied to a fault in the instrument, it would keep numbers
known to be wrong, and stop round 5d from grading round 5c's arms with the
same suite as its own.

## Decision

A fault found in an instrument is fixed, the fix validated, and every round
that reads the faulty scores re-scored in full, its report replaced with a
dated note that keeps the verdicts it replaces; a fault a re-score cannot
repair still withdraws the metric.

## Rationale

- An instrument fault makes the numbers wrong, not the trials: re-scoring the
  same frozen trials under the same rules repairs them.
- Every trial is re-scored, so no trial or arm is picked for a second chance.
- Faults are found where results look wrong, and so far both helped the
  templates arms once fixed. Recording the fault before the re-score is read,
  validating the fix, and keeping the old verdicts in view guard against
  choosing an outcome.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Record the fault first | An issue names the fault and its fix before any re-score is read |
| 2 | Validate the fix | The hidden suite passes the reference in full and catches every mutation; a script passes its self-test |
| 3 | All or nothing | Each round reading the faulty scores is re-scored in full; a root never mixes two suite revisions or two Pythons |
| 4 | Judge what was never judged | A build that installs only after the fix is judged as every other |
| 5 | Archive again | The re-scored round is archived and verified before its report is replaced |
| 6 | Keep the old verdicts | The replaced report opens with a dated note naming the fault and the verdicts it replaces |
| 7 | Withdraw only the unfixable | A fault in what the trial was asked withdraws the metric, as round 1's change-task pass rate was (ADR-009) |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | Fix, validate, re-score in full, replace the report with a dated note | Chosen |
| B | Keep the registered report, and add the re-score as a post-hoc reading beside it | Not chosen: the registered verdicts rest on numbers the instrument got wrong |
| C | Withdraw the affected metrics, as FR-12-10 asked | Not chosen: it drops a round's deciding rows over a fault a re-score repairs |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| FR-12-10 | States this rule; FR-12-11 is merged into it |
| Round 5c | Its 2026-11-01 report is the Python 3.12 reading, archived as `rounds/2026-11-02-round-5c-py312b` |
| Round 5d | Re-scores round 5c's arms with the corrected hidden suite in its own root, so every contrast is graded by one suite (#116) |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-02 | Round 5c is re-scored on Python 3.12 and its report replaced, keeping the old verdicts in a dated note | It was scored on Python 3.14, which refused three builds the spec's Python installs | #100, #101, #103 |
| 2026-11-02 | The rule covers any instrument fault, and FR-12-11 merges into FR-12-10 | The hidden suite's shared process failed a locked-out build's later tests; the old FR-12-10 would have kept those numbers | #116 |
