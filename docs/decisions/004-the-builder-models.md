---
id: "004"
status: Accepted
date: 2026-09-12
category: design
supersedes: []
superseded_by: []
---

# ADR-004: The builder models

## Context

The model a trial's agent runs on sets the ceiling every arm works under. A
model far stronger than an adopter's would leave the context file little to
add, and a model from the judge's vendor could be favoured by that judge.

## Decision

Each round names its builder models in its registration, and none comes from
the vendor of the rounds' judge.

## Rationale

- The first choice was what a typical adopter runs, `claude-sonnet-5` at effort
  `high`, since a stronger model's ceiling would hide the effect.
- The models are a knob a round sets, not a fixed list.
- A builder from the judge's vendor would bring back the self-preference the
  cross-check once answered, and the cross-check no longer runs
  ([ADR-005](005-the-judge.md)).

## History

Every change to this decision, oldest first. The 2026-09-12 row is the builder
half of that day's decision on models; its judge half is in
[ADR-005](005-the-judge.md):

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | Generator `claude-sonnet-5` at effort `high` | What a typical adopter runs; a stronger model's ceiling would hide the effect | solid-ai-templates#1711 |
| 2026-10-27 | Each round names its builder models in its registration, and none comes from the vendor of the rounds' judge | The models are a knob a round sets, not a fixed list. A builder from the judge's vendor would bring back the self-preference the cross-check once answered, which no longer runs | — |
