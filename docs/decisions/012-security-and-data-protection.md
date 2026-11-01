---
id: "012"
status: Accepted
date: 2026-09-16
category: measurement
supersedes: []
superseded_by: []
---

# ADR-012: Security and data protection

## Context

Round 1 measured security with fixed checks that every trial passed, so they
separated nothing. A judge row alone is an opinion, and the control fixture's
first application has no sign-in and no customers to calibrate such a row on.

## Decision

Security and data protection are primary dimensions from round 3, each read by
an anchored judge row and a probe pass rate, and their probe margins let no
probe be lost.

## Rationale

- An owner decision after reading round 1's report.
- A judge row alone is an opinion; the probes are deterministic.
- Security regressions get no tolerance.
- Anchored first at a level the calibration application already met, both rows
  fell on damage and could not rise, so their 3 and their 5 were moved.

## Design

The rules the two dimensions follow:

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Four primaries | An anchored judge row and a probe pass rate for each of security and data protection |
| 2 | No probe lost | The probe margins mean no probe lost |
| 3 | The 3 | Each row's 3 describes the common defences and nothing more |
| 4 | The 5 | Each row's 5 asks for an explicitly configured deployment and one declaration of what is personal |
| 5 | Calibration | The control's application for these rows is one uncounted calibration trial on the extended spec; the reference implementation is a worked answer and stays private |

## Consequences

What the change did to the round before it:

| Consequence | Effect |
| ----------- | ------ |
| Round 1 | Read for security with checks declared after the run |

## History

Every change to this decision, oldest first:

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-09-16 | Security and data protection become primary dimensions from round 3 | Owner decision after reading round 1's report | solid-ai-templates#1767 |
| 2026-09-16 | Round 1 is read for security with checks declared after the run | Its fixed security checks passed on every trial and separated nothing | solid-ai-templates#1766 |
| 2026-09-24 | Security and data protection: an anchored judge row and a probe pass rate each, all primary; probe margins mean no probe lost | A judge row alone is an opinion; the probes are deterministic. Security regressions get no tolerance | solid-ai-templates#1767 |
| 2026-09-24 | The control's application for the security and data-protection rows is one uncounted calibration trial on the extended spec | The first application has no sign-in or customers; the reference implementation is a worked answer and stays private | solid-ai-templates#1767 |
| 2026-09-25 | The security and data-protection rows' 3 describes the common defences and nothing more; their 5 asks for an explicitly configured deployment and one declaration of what is personal | Anchored first at a level the calibration application already met, both rows fell on damage and could not rise | solid-ai-templates#1767 |
