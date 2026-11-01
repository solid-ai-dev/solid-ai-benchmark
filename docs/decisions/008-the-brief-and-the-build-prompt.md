---
id: "008"
status: Accepted
date: 2026-09-12
category: design
supersedes: []
superseded_by: []
---

# ADR-008: The brief and the build prompt

## Context

The brief is what an adopter would type to the generator, and the build prompt
is what every arm's agent is told with the spec. Both shape what a trial
builds, so each says what an adopter would say and nothing the hidden suite
checks. A headless trial gets no answer to any question it asks.

## Decision

The brief and the prompts live in files of their own; the brief names the two
extension axes, customers as personal data under the GDPR and one signing-in
administrator, and the build prompt tells every arm the spec is the approved
plan and nobody will answer.

## Rationale

- An adopter would name the extension axes;
  [ch. 5.5.4](../architecture/05-building-block-view.md) states what that
  costs.
- An adopter storing customers would say so.
- `hand`'s two added lines stay generic: lines mirroring the probes would hand
  it the answer key.
- The design's restructure would have broken the code that read the brief and
  the change prompt by heading.
- A trial waiting for an approval no headless trial gets stops after its plan,
  as `inline-1` did in round 5's first start.

## Design

The rules the brief and the prompt follow:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Files of their own | The brief and the change prompt are read from their own files, not by heading |
| 2 | Extension axes | The brief names the app's two extension axes |
| 3 | Personal data | The brief names customers as personal data under the GDPR, and one administrator who signs in |
| 4 | `hand`'s lines | `hand` carries two generic lines, OWASP ASVS level 1 and the GDPR, and nothing that mirrors a probe |
| 5 | No one answers | The prompt tells every arm the spec is the approved plan and nobody will answer; the report refuses a build trial on another prompt |

## Consequences

What the prompt change did to the round it arrived in:

| Consequence | Effect |
| ----------- | ------ |
| Round 5b | A registration is fixed once a trial has run, so round 5 stays as registered and runs again as round 5b |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-12 | The brief names the two extension axes | An adopter would; [ch. 5.5.4](../architecture/05-building-block-view.md) states what that costs | solid-ai-templates#1713 |
| 2026-09-24 | The brief and the change prompt live in files of their own | The design's restructure would have broken the code that read them by heading | solid-ai-templates#1843 |
| 2026-09-24 | The brief names customers as personal data under the GDPR and one signing-in administrator; `hand` gains two generic lines (OWASP ASVS level 1, GDPR) | An adopter storing customers would say so. `hand`'s lines stay generic: lines mirroring the probes would hand it the answer key | solid-ai-templates#1767 |
| 2026-10-29 | The prompt tells every arm the spec is the approved plan and nobody will answer, and the report refuses a build trial on another prompt. Round 5 stays as registered and runs again as round 5b | Round 5's first start: `inline-1` stopped after its plan, waiting for an approval no headless trial gets. A registration is fixed once a trial has run, so the change is a registration of its own | — |
