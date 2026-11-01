---
id: "009"
status: Accepted
date: 2026-09-12
category: measurement
supersedes: []
superseded_by: []
---

# ADR-009: The change task

## Context

The change task is a second session that extends a copy of a frozen build. Its
churn shows how well the first build was laid out for change, so the task has
to need code, not configuration, and its grader has to check what the prompt
asked for and nothing it did not.

## Decision

The change task adds a spend threshold and a capped rate, and its prompt states
the API, the form fields and the rules its acceptance modules check, with the
UI graded by HTTP cases from round 3.

## Rationale

- Buy-one-get-one and a reduced rate, the first draft's items, were already
  expressible by configuration, so every arm would score zero churn.
- A grader driving names the prompt never gave grades guessing.
- The UI was asked for but never graded.

## Consequences

What the grading rule withdrew:

| Consequence | Effect |
| ----------- | ------ |
| Round 1's pass rate | Its change-task pass rate is withdrawn: its grader built the new rule and rate through names the prompt never gave |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The change task adds a spend threshold and a capped rate, replacing a first draft of buy-one-get-one and a reduced rate | Both first-draft items were already expressible by configuration, so every arm would score zero churn | solid-ai-templates#1717 |
| 2026-09-17 | Round 1's change-task pass rate is withdrawn | Its grader built the new rule and rate through names the prompt never gave | solid-ai-templates#1772 |
| 2026-09-24 | The change prompt states the API, the form fields and the rules its acceptance modules check; the UI is graded by HTTP cases from round 3 | A grader driving names the prompt never gave grades guessing; the UI was asked for but never graded | solid-ai-templates#1767 |
