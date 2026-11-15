---
id: "025"
status: Accepted
date: 2026-11-15
category: arms
supersedes: []
superseded_by: []
---

# ADR-025: From round 6, every arm is built by a script

## Context

Through round 5e, three arms were written: `inline`, `hybrid` and `short`
were one model generation each, and `hand` was a person's file. A
generation run again gives a different file, so the arm under one name
changes: round 5e's `hybrid` was 511 lines, and the one regenerated for
round 6 was 221. A result then speaks for one draw of the method, not for
the method, and two rounds of one arm do not compare.

The templates' own emitter, `resolve_chain.py --emit`, already builds a
root file and task skills from a chain by placing each section by its load,
copying the rule text unchanged; `--inline-skills` puts the skills in the
root. It builds no hybrid file: the templates hold that emitted files name
no template file (their FR-06-07), and that no rule is left to a reference
alone, since nothing loads a referenced file (their ADR-058). Round 5e bore
that out: `hybrid` read 0.1 of the 13 templates it pointed to, so it ran on
the rules it inlined, a slightly shorter `inline`.

## Decision

From round 6 every arm a round runs is built by `generate_arm.py` with no
model call, and the same ref gives the same bytes; `inline` is what the
emitter builds with `--inline-skills`, and `hybrid`, `short` and `hand` run
no more.

## Rationale

- An arm that is the same file on every build is a method, not a sample of
  one; a round's result then speaks for it, and two rounds compare.
- The emitter is the templates' own build, so the arm is upstream's output,
  as the benchmark measures upstream only.
- `hybrid` has no build upstream that keeps the templates' rules, and its
  references went unread, so a scripted stand-in would measure the
  benchmark's choices rather than the templates'.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | No model writes an arm | `generate_arm.py` has no model path; every kind is fixed text, the emitter or a map |
| 2 | `inline` is the emitter's single file | `resolve_chain.py --emit --inline-skills`: every adopted rule in the root, a section a check enforces cut to its command and pass condition, as the emitter cuts it for every model |
| 3 | `skills` is the emitter's root and skills | `resolve_chain.py --emit`, as before |
| 4 | Every root states the brief | The emitter's description slot takes the brief whole, so an emitted root opens as every other arm's does |
| 5 | A committed arm is what the script builds | The self-test rebuilds every committed arm at its recorded ref and fails on any byte of difference, and builds one twice |
| 6 | The pilot's written arms stay as they are | `hand`, `short` and `hybrid` keep their files for the pilot rounds' reports; no script rebuilds them, and no round from 6 runs them |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | Every arm built by a script, `hybrid` dropped | Chosen |
| B | Several generations per written arm, trials spread across them | Why not: the arm stays a sample, and the spread between files has to be paid for in trials |
| C | A hybrid built by the benchmark: the emitter's root, the skills table cut, the chain listed | Why not: how the benchmark trims and joins shapes the arm, and the templates' rules forbid the result |
| D | Hybrid and inline modes added to the templates' emitter first | Why not: a hybrid that names template files breaks the templates' FR-06-07 and ADR-058; `--inline-skills` is already the inline build |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| `inline` changes | The emitter's file is 1,778 lines at `9abed019`, against the 552 a model wrote for round 5e: a new arm, with no round-5e reading |
| `skills` changes | Its root now carries the brief's paragraphs on personal data and on boundaries, which it lacked; a new arm too |
| Round 6's arms | `none`, `reference`, `inline`, `skills`, `lazyref`, `lazyskills`, and those #169 adds |
| The report still reads arm files from the checkout | The pilot arms' files stay so a pilot report can count their lines, until #171 |

## History

Every change to this decision, oldest first. `#N` is in this repository.

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-15 | Every arm is built by a script; `inline` from the emitter's `--inline-skills`; `hybrid`, `short` and `hand` run no more | A written arm changes with every writing; the owner kept only arms a script builds | #167 |
