---
id: "021"
status: Accepted
date: 2026-11-02
category: process
supersedes: []
superseded_by: []
---

# ADR-021: Re-score after an environment defect

## Context

Round 5c was scored on Python 3.14.8, though its spec names Python 3.12. The
scorer refused three builds that capped `requires-python` below 3.13, and the
registered report read them as builds that would not install.

Two kinds of scoring fault had to be told apart:

- **A grader that measures something else:** its logic is wrong, such as round
  1's change-task grader driving names the prompt never gave. The metric is
  withdrawn and the same trials are never re-graded (ADR-009).
- **A grader run outside the registered environment:** its logic is right, but
  it ran on another interpreter than the spec's. The trials and the rules are
  unchanged; only the ruler was the wrong one.

Re-scored on Python 3.12, with the three builds judged for the first time, the
verdicts moved:

| Question | Registered (3.14) | Re-scored (3.12) |
| -------- | ----------------- | ---------------- |
| `hybrid` against no file | Worse | Better |
| `inline` against no file | No clear gain | Better |
| H3, a reference alone delivers less | Not settled | Yes |

## Decision

A round scored outside its registered environment is re-scored in full in that
environment, and its report replaced, with a dated note that keeps the verdicts
it replaces.

## Rationale

- The environment is part of what a round registers: the spec names the Python
  every build is scored on. A build refused by another interpreter measures the
  scorer, not the agent.
- Every trial is re-scored, not only the refused ones, so no trial is picked
  for a second chance.
- The trials, the rules and the verdict rule stay as registered, so no result
  is chosen after seeing it; the old verdicts stay visible in the note.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Only an environment defect qualifies | Another interpreter or tool lock than the registered one; a grader whose logic is wrong is withdrawn instead |
| 2 | All or nothing | Every trial of the round is re-scored; the report refuses scores from two interpreters |
| 3 | Judge what was never judged | A build that installs only after the fix is judged as every other, at the round's judge and repeats |
| 4 | Archive again | The re-scored round is archived and verified before its report is replaced |
| 5 | Keep the old verdicts | The replaced report opens with a dated note naming the defect and the verdicts it replaces |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | Re-score in full and replace the report | Chosen |
| B | Keep the registered report, and add the re-score as a post-hoc reading beside it | Not chosen: the registered verdicts rest on three refusals the spec rules out |
| C | Withdraw install and task success for the round | Not chosen: it drops the round's deciding row over a fault in the scorer, not in the grader's logic |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| FR-12-11 | States the rule; FR-12-10 still forbids re-grading with a corrected grader |
| Round 5c | Its 2026-11-01 report is the Python 3.12 reading, archived as `rounds/2026-11-02-round-5c-py312b` |
| Round 5d | Reads round 5c's `none` from the re-scored root |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-02 | Round 5c is re-scored on Python 3.12 and its report replaced, keeping the old verdicts in a dated note | It was scored on Python 3.14, which refused three builds the spec's Python installs | #100, #101, #103 |
