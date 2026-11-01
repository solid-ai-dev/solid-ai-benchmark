---
id: "014"
status: Accepted
date: 2026-09-17
category: judge
supersedes: []
superseded_by: []
---

# ADR-014: No human holdout

## Context

A human holdout would score a share of the implementations by hand, as a check
on the judge. Every round produces many implementations, and the benchmark runs
with no person in the loop
([ch. 4.3](../architecture/04-solution-strategy.md)).

## Decision

No implementation is scored by a person: there is no human holdout.

## Rationale

- Scoring many implementations by hand cannot be sustained.
- A person in the loop breaks
  [ch. 4.3](../architecture/04-solution-strategy.md).

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-17 | No human holdout | Scoring many implementations by hand cannot be sustained, and a person in the loop breaks [ch. 4.3](../architecture/04-solution-strategy.md) | solid-ai-templates#1774 |
