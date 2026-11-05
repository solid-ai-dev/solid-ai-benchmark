# Round 5e registration

Registered on 2026-11-05, while round 5d ran and before any round-5e trial ran.
Round 5d keeps its registration as it was when its first trial ran; this one is
a registration of its own.

Amended on 2026-11-05, before any round-5e trial ran: the report's reading of
the round moved from "still needed" to done in 13e.5; all five of round 5c's
arms are reused, so the screen of 13d.9 reads every candidate; and the reuse of
the earlier rounds' arms is what remains.

## 13e. Round 5e: the templates on demand, against rounds 5c and 5d

### 13e.1 What it takes from rounds 5c and 5d

Round 5e runs [round 5d's registration](round-5d.md) as it stands at `1baac26`:
block A, the spec at its registered sha256, `claude-sonnet-5` at effort `high`,
round 5b's prompt, the pen, the judge, the scoring on Python 3.12, the CLI
pinned at 2.1.314, the verdict rules of 13d.7, the radar of 13d.8 and the
round-6 screen of 13d.9.

The hidden suite is the revision at `8caaaa3`: the same tests as round 5d's
(the build imported afresh for every test), plus entry 9 of its ambiguities
file, which grades nothing new.

Three things differ: the arms, the order, and what is reused.

### 13e.2 The arms

| Arm | Trials | Where they come from |
| --- | --- | --- |
| `lazyref` | 15, fresh | `arms/lazyref/CLAUDE.md`, made for 5e |
| `lazyskills` | 15, fresh | `arms/lazyskills/`, root and 13 skills, made for 5e |
| round 5c's five arms | 15 each, reused | Round 5c's, re-scored in 5d's root |
| `hand`, `short` | 15 each, reused | Round 5d's, scored and read |

Both fresh arms live under `tests/efficacy/arms/`. They are fixed text, made by
`generate_arm.py` from round 5's chain at `9086e0ff` and the templates'
manifest, with no model call. Each row of their table is one template of the
chain, in the chain's order, and the moment that calls for it is the manifest's
own one-line description of that template. No person chose the moments, and the
two arms take them from the same source, so their tables differ in one column
alone.

**`lazyref`** maps each moment to the vendored template file.

- The root says: do not read the templates before the work starts; the first
  time the work touches a template's topics, read that template and apply every
  rule it holds that fits this project.
- The templates are vendored at `docs/solid-ai-templates/` at the recorded ref,
  as `reference` vendors them.
- 22 lines and 2,088 bytes, sha256
  `8c7f7698568643823988e4f9a7e4ade9d30f3965cb065e1dd7ee4117050b5d67`, with its
  generation record beside it.

**`lazyskills`** maps each moment to a skill holding that template.

- The root says the same, with "load that template's skill" in place of "read
  that template".
- Thirteen skills under `.claude/skills/`, one per template of the chain, each
  named by the template's manifest id, described by the manifest's one line,
  and holding the template verbatim: 76,023 bytes in all.
- 22 lines and 1,535 bytes, sha256
  `f98060a1d04263b6a630728d614d38ed2efc14385c07c789aad157883dffc5de`, with its
  generation record beside it.

**The reused arms** come with round 5d's root and tool lock, so every contrast
is graded by one suite.

Why: round 5c's `reference` is lazy in packaging only. Its root says "before
starting work, read each template below", and 13 of its 15 agents read all 13
templates whole before the first line of code, 161 KB in two turns. Its
`skills` arm, whose skills were offered by description alone, loaded none of
them. So no pilot arm has yet measured a rule read at the moment it applies.
Round 5e asks that question twice, once with a file read and once with a skill
load, and nothing else differs between its two arms.

### 13e.3 The order

One run of `lazyref` and `lazyskills` at K = 15, in a run root of round 5e's
own: 30 trials in the rotated order.

- The run starts `lazyref-1`, `lazyskills-1`, and each block starts one arm
  later.
- The two arms share every block, so `lazyskills` minus `lazyref` is paired.
- No fresh trial of a reused arm runs beside them, so drift against rounds 5c
  and 5d goes unchecked, as in round 5d. The CLI is pinned.
- A contrast pairs only trials that ran in one round; a reused trial keeps
  the root it ran in as its origin however many times it is copied on, so a
  contrast of two reused arms from different rounds is unpaired too.

### 13e.4 Hypotheses

A contrast with a round 5c or round 5d arm is unpaired, read as 13d.4 reads
one. The paired contrast is read as 13d.4 reads H6.

**H7, on demand against up front.** A template read when the work touches its
topics delivers at least what the same template read before the work starts
delivers.

| | |
| --- | --- |
| Contrast | `lazyref` minus round 5c's `reference`, unpaired |
| Primary rows | the round's primary rows, below |
| Supported | every primary row is held or better |
| Refuted | any primary row is worse |

**H8, a skill against a file.** Loading a template as a skill delivers at least
what reading it as a file delivers, the moments being the same.

| | |
| --- | --- |
| Contrast | `lazyskills` minus `lazyref`, paired within the block |
| Primary rows | the round's primary rows, below |
| Supported | every primary row is held or better |
| Refuted | any primary row is worse |

**H9, one skill per template against one skill per task.** Templates loaded
whole as skills, at a named moment, deliver at least what task skills offered
by description deliver.

| | |
| --- | --- |
| Contrast | `lazyskills` minus round 5c's `skills`, unpaired |
| Primary rows | the round's primary rows, below |
| Supported | every primary row is held or better |
| Refuted | any primary row is worse |

**The primary rows** are round 5d's: the hidden suite's pass rate, the security
and data-protection probe pass rates, each on working builds, and the judge's
security and data-protection rows. Reliability is a row of its own, as 13d.7
says. Adherence is printed without a verdict.

H7 to H9 are read under the rules of 13d.7, and each verdict is printed with
its confidence and the arm's profile.

**Against `none`, no hypothesis.** Each fresh arm is read against round 5c's
`none` by the rules of 13d.7, with no verdict of its own: the reading feeds the
round-6 screen of 13d.9, which round 5e's arms join as candidates.

**Secondary, no verdict:**

- every metric of [ch. 8.6](../architecture/08-crosscutting-concepts.md) for
  each fresh arm against round 5c's `none`, `reference` and `skills` and round
  5d's `hand` and `short`; `inline` and `hybrid` are reused for the screen
  alone;
- cost, turns, tokens and wall time, and the words each arm puts in context on
  every turn;
- **use of the map**, per trial, from the transcript, a subagent's included and
  charged to the turn that delegated to it: how many templates of the map the
  agent read (`lazyref`, a read of a file of the chain under the vendored path,
  by the read tool or a shell command that reads, a wildcard standing for every
  template it matches) or loaded (`lazyskills`, a skill call naming one of the
  arm's skills), which ones, the turn each happened at, and how many happened
  before the trial's first write to a file of its own: a write tool's call, or a
  shell command that redirects into a file, copies, moves or creates. A trial
  that never wrote says nothing about reading up front, a map no trial read was
  ignored rather than read on demand, and the note beside H7 says which case
  holds.

### 13e.5 Before the first trial

Done with this registration:

- `generate_arm.py` makes the two map arms from the chain and the manifest, the
  same moments in the same order for both, and refuses a chain file the
  manifest does not describe
- both arms are generated and committed with their records
- the harness reads them from their files, vendors the templates for `lazyref`,
  places the skills for `lazyskills`, proves before the run that the agent sees
  them, and builds both from round 5's spec at its registered content
- the report names both arms in plain words

Done after it, before any round-5e trial, each with a self-test:

- the report reads a round-5e run under round 5d's rules and against this
  registration, with the contrasts of H7 and H9, unpaired, and H8, paired
- the use-of-the-map rows of 13e.4, read from the transcripts, with the note
  beside H7
- the round-6 screen of 13d.9, with round 5e's arms among the candidates

Still needed: round 5c's five arms and round 5d's `hand` and `short` brought
into round 5e's root by `reuse.py` from round 5d's root, scored and read as
they were, with their tool lock.

### 13e.6 When it runs

After round 5d's last trial is in, scored, judged and reported. Its 30 trials
take about 20 hours at round 5c's pace and spend the plan's limit, so the run
waits for the owner's go.

Nothing in this registration changes once a round-5e trial has run.
