# Rounds

Each round registers its question, its blocks and its hypotheses here
before its first trial runs. Nothing in a registration changes once a
trial of that round has run. The rules every round shares are in
[chapter 8](../architecture/08-crosscutting-concepts.md).

Rounds 1 to 5d are the pilot. They shaped the benchmark, and each is re-run
only from the benchmark at its own commit: the current version carries no
arm, contrast or rule that only they used. The benchmark proper starts with
round 6. From there a round is named by a letter for the knob it turns and a
number for how many rounds have turned that knob, as `C1` for the first round
that moves the context file; the trials inside keep their names, `inline-1`,
`none-1`. The letters are the primer's four knobs, `C` the context file, `S`
the specification, `M` the builder model and `T` the task
([ADR-022](../decisions/022-round-names.md)).

| Round | Registered | Asks |
| ----- | ---------- | ---- |
| [Round 4](round-4.md) | Before its first trial, after round 3 | Does a file supply what a thin spec leaves out, and help a weaker model more |
| [Round 5](round-5.md) | 2026-10-26, amended 2026-10-27, 2026-10-28 and 2026-10-29; stopped after its first start | Which way of delivering the rules gives the best and most consistent code |
| [Round 5b](round-5b.md) | 2026-10-29, after round 5 stopped; stopped after its first start | Round 5's question, with a prompt that tells every arm the spec is the approved plan |
| [Round 5c](round-5c.md) | 2026-10-29, after round 5b stopped | Round 5b's question, with each trial's workspace in a pen of its own |
| [Round 5d](round-5d.md) | 2026-10-31, while round 5c ran | Whether a person's short file does what the templates do, at their length and at its own |
| [Round 5e](round-5e.md) | 2026-11-05, while round 5d ran | Whether a template read at the moment the work touches its topics does what one read up front does, as a file and as a skill |

## Reports

Each round's report sits in this repository, in [`docs/reports/`](../reports/).
Rounds 1 to 3 were registered in the templates' own design, before this
repository existed.

| Round | Run | What it turned | Report |
| ----- | --- | -------------- | ------ |
| 1 | 2026-09-17 | Context file: none, the templates' inline file, a hand-written one | [Report](../reports/2026-09-17-efficacy.md) |
| 2 | 2026-09-18 | Context file: adds the short and hybrid files | [Report](../reports/2026-09-18-efficacy.md) |
| 3 | 2026-09-27 | Context file: every arm run fresh | [Report](../reports/2026-09-27-efficacy.md), [assessment of rounds 1 to 3](../reports/2026-09-27-efficacy-assessment.md) |
| 4 | 2026-10-17 | Spec: thin, and builder: Haiku 4.5 | [Summary](../reports/2026-10-17-round-4.md), [thin spec](../reports/2026-10-17-efficacy-thin.md), [weaker model](../reports/2026-10-17-efficacy-weaker.md) |
| 5 | Stopped 2026-10-29, after four trials | Context file: how the rules are delivered | — |
| 5b | Stopped 2026-10-29, after four trials | Context file: how the rules are delivered | — |
| 5c | 2026-10-29 to 2026-10-31 | Context file: how the rules are delivered | [Report](../reports/2026-11-01-efficacy.md), [post-hoc reading](../reports/2026-11-01-efficacy-posthoc.md) |
| 5d | Reported 2026-11-07 | Context file: a hand-written one and a 40-line one, against 5c | [Report](../reports/2026-11-07-efficacy.md) |
| 5e | Reported 2026-11-13 | Context file: the templates read on demand, as a file and as a skill, against 5c and 5d | [Report](../reports/2026-11-13-efficacy.md) |
