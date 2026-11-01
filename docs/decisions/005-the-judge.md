---
id: "005"
status: Accepted
date: 2026-09-12
category: judge
supersedes: []
superseded_by: []
---

# ADR-005: The judge

## Context

A judge model scores each blind bundle on the rubric's rows. Its vendor
matters: a judge sharing a vendor with the builder could favour the templates'
style in every arm. Its plan matters too: a round needs three judgings per
trial, and a plan that allows fewer cannot judge a round.

## Decision

The rounds' judge is `gpt-6-astra` through `codex exec` at effort `high`,
alone, three times per trial, with no cross-check.

## Rationale

- A judge from another vendor than the builder answers the self-preference
  concern; with a judge from another vendor than every round-5 builder
  ([ADR-004](004-the-builder-models.md)), that concern is gone.
- The owner's OpenAI plan is raised to cover a round's judgings, which in
  rounds 3 and 4 it could not.
- A second judge could only withhold verdicts.

## Design

The cross-check that ran in round 3 and is dropped from round 5, kept for
reading the rounds that used it:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Never averaged | A second judge's scores are never averaged with the rounds' judge |
| 2 | Whole blocks | The cross-check reads whole blocks and reports agreement per judge row |
| 3 | Opposite directions | It withholds a verdict only where the two judges read opposite directions |

## History

Every change to this decision, oldest first. The 2026-09-12 row is the judge
half of that day's decision on models; its builder half is in
[ADR-004](004-the-builder-models.md):

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | Judge `gpt-6-astra` through `codex exec`, effort set explicitly | A different vendor judges | solid-ai-templates#1711 |
| 2026-09-19 | A second judge, Claude, reads the control fixture only | A second vendor's reading of the same trees; never averaged with the rounds' judge | solid-ai-templates#1831 |
| 2026-09-25 | The rounds' judge is `claude-opus-5-5`; `gpt-6-astra` reads a sample as a cross-check | gpt-6-astra's plan allows about thirty judgings a week and a round needs three times as many; Opus 5.5 runs on capacity the owner already pays for | solid-ai-templates#1767 |
| 2026-10-15 | Round 4 is judged by `claude-opus-5-5` alone, without the cross-check | The owner keeps `gpt-6-astra`'s weekly plan free; round 4's thirty build trials would take all of it. The same-vendor caveat round 3 carried stands for round 4 | solid-ai-templates#1903 |
| 2026-10-15 | The cross-check reads whole blocks, reports agreement per judge row, and withholds a verdict only where the two judges read opposite directions | A shared vendor could favour the templates' style in every arm; opposite signs is the disagreement a verdict cannot survive, and a missed confirmation is what the interval already weighs | solid-ai-templates#1903 |
| 2026-10-27 | Round 5 is judged by `gpt-6-astra` through `codex exec` at effort `high` alone, three times per trial, with no cross-check | The owner's OpenAI plan is raised to cover a round's judgings. With a judge from another vendor than every round-5 builder, the same-vendor concern the cross-check answered is gone, and a second judge could only withhold verdicts | — |
