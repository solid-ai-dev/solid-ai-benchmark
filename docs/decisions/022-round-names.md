---
id: "022"
status: Accepted
date: 2026-11-04
category: process
supersedes: []
superseded_by: []
---

# ADR-022: Round names

## Context

Rounds 1 to 5d were numbered in the order they ran, with a letter suffix for
a re-run that changed only procedure. The number says nothing about what a
round turned: round 4 moved the specification and the builder model, round 5
and its re-runs moved the context file. The primer describes the benchmark
as a test machine with four knobs, a round turning one at a time, and the
benchmark proper starts with round 6, so the names can follow the machine.

## Decision

From round 6 a round is named by a letter for the knob it turns and a number
for how many rounds have turned that knob, as `C1` for the first round that
moves the context file; the trials inside keep their names, `inline-1`,
`none-1`.

## Rationale

- The name says what the round tests: a reader sees the knob before the
  question.
- The number is a history of that knob alone, so `C3` is the third time the
  context file moved, whatever ran in between.
- A round turns one knob and holds the other three still, as the primer
  states, so one letter is enough.
- Trial names already carry the knob's setting, the arm, and the block, and
  every reader of the run root depends on them.

## Design

| # | Rule | In practice |
| - | ---- | ----------- |
| 1 | Four letters, the primer's four knobs | `C` the context file, `S` the specification, `M` the builder model, `T` the task |
| 2 | One knob per round | A round that would turn two is two rounds, each with the other knob at its registered setting |
| 3 | The number counts rounds of that knob | From 1, in the order they register; `C1` is the first round after the pilot that moves the context file |
| 4 | A change to what stays fixed is not a round | The prompt, the ruler, the app and the bounds are fixed in every run; a change to one is an amendment before the first trial, or a re-score under ADR-021, never a new letter |
| 5 | Trials keep their names | `<arm>-<block>`, as today; the registration, the run root, the archive and the report take the round's name |
| 6 | The pilot keeps its numbers | Rounds 1 to 5d stay as they were run and reported |

## Alternatives considered

| # | Alternative | Outcome |
| - | ----------- | ------- |
| A | A letter per knob, a number per round of it | Chosen |
| B | Keep counting rounds, 6, 7, 8 | Why not: the number tells nothing of what a round tested, and re-runs needed suffixes |
| C | A letter per anything that can change, the prompt and the ruler included | Why not: those are held fixed by design, so a change to one is an amendment or a re-score, not an experiment |
| D | `A` for the arms | Why not: the knob is the context file, and `C` says so |

## Consequences

| Consequence | Effect |
| ----------- | ------ |
| Round 6 is `C1`, `S1`, `M1` or `T1` by what it turns | Its registration takes that name, and so do its run root, archive and report |
| The primer and the rounds README name the scheme | A reader meets it before the first round under it |
| The harness and the report know nothing of round names | They read trial names and registrations; nothing in `tests/` changes |

## History

Every change to this decision, oldest first. An issue `solid-ai-templates#N`
is in `solid-ai-dev/solid-ai-templates`, where the benchmark lived until the
split; `#N` is in this repository; a dash means none.

| Date | Change | Why | Issue |
| ---- | ------ | --- | ----- |
| 2026-11-04 | A round is named by the knob it turns and the count of rounds of that knob; the letters are the primer's four knobs, `C`, `S`, `M`, `T` | The benchmark proper starts with round 6, after the pilot; a name that says what a round tests reads better than a running number | #129 |
