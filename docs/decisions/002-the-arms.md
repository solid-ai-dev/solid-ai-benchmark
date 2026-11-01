---
id: "002"
status: Accepted
date: 2026-09-12
category: design
supersedes: []
superseded_by: []
---

# ADR-002: The arms

## Context

An arm is one setting of the context-file knob. Comparing a generated file with
the bare agent alone cannot tell the templates' effect from the effect of
having any file at all. Round 1's reading added a second question: whether the
generated file is too long to add quality.

## Decision

Beside the bare agent and the generated file, the arms have included a
hand-written file and, from round 2, a `short` generated file held to the same
length and the hybrid model, and `short`'s instruction asks the model to
measure every line against the width before answering.

## Rationale

- Only the hand-written arm separates the templates from having any file.
- The owner read round 1 as saying the generated file is too long to add
  quality and that a short one can, so length is held fixed and the
  hybrid model added.
- Refusing a `short` generation over the width and retrying until one passes
  would select the tersest sample, and dropping the width lets a line carry a
  paragraph; asking the model to measure every line does neither.

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The hand-written arm runs | Only it separates the templates from having any file | solid-ai-templates#1705 |
| 2026-09-17 | Round 2 holds length fixed and adds the hybrid model | Owner's reading of round 1: the generated file is too long to add quality, and a short one can[^context] | solid-ai-templates#1795 |
| 2026-09-26 | `short`'s instruction asks the model to measure every line against the width before answering | On the round-3 brief two generations in a row were refused, with 1 and then 9 lines over 88 characters; retrying until one passed would select the tersest sample, and dropping the width lets a line carry a paragraph | solid-ai-templates#1767 |

[^context]: This agrees with Anthropic's guidance on context engineering, which
    asks for the smallest set of high-signal tokens: [Effective context
    engineering for AI
    agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents).
