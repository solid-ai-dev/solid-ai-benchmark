# Round 5d registration

Registered on 2026-10-31, while round 5c ran and before any round-5d trial ran.
Round 5c keeps its registration as it was when its first trial ran; this one is
a registration of its own.

## 13d. Round 5d: the hand-written file, against round 5c

### 13d.1 What it takes from round 5c

Round 5d runs [round 5c's registration](round-5c.md) as it stood at `07d1641`:
block A, the spec at its registered sha256, `claude-sonnet-5` at effort `high`,
round 5b's prompt, the pen, the judge, the scoring and the code size rows, and
the margins of round 5's H1.

Three things differ: the arms, the order, and a reuse of round 5c's `none`.

### 13d.2 The arms

| Arm | Trials | Where they come from |
| --- | --- | --- |
| `hand` | 15, fresh | `tests/efficacy/arms/hand/CLAUDE.md` as it is at `010ee36` |
| `none` | 3, fresh | The bare agent, as a check on drift |
| `none`, from 5c | 15, reused | Round 5c's `none-1` to `none-15`, scored and read |

- The `hand` file is 39 lines and 1,376 bytes, sha256
  `25459854949f648837ac5ef37fca5d7472923b544dffb694cd40f8b8a53ec748`.
- It is kept verbatim, as it was written for round 3's brief. It is not edited
  for round 5's.
- The reused trials come with round 5c's tool lock, so both rounds are measured
  with one ruler.

Why `hand`: it is the only arm that separates the templates from having a file
at all (the decision of 2026-09-12). Round 5 left it out because each of its
arms is made from the templates at `9086e0ff`, and a person's file is not.

### 13d.3 The order

Two runs, in one run root of round 5d's own:

| Run | Arms | Trials, in order |
| --- | --- | --- |
| 1 | `none`, `hand` | `none-1`, `hand-1`, `hand-2`, `none-2`, `none-3`, `hand-3` |
| 2 | `hand`, from `hand-4` | `hand-4` to `hand-15` |

- The fresh `none` trials share blocks 1 to 3 with `hand`, so they see the same
  days as the start of `hand`.
- Drift after block 3 goes unchecked. The CLI is pinned (13d.5), which holds
  the one source of drift known to have moved.

Why the pin: the Claude CLI updated itself from 2.1.312 to 2.1.314 at 03:13 on
2026-10-30, in the middle of round 5c. Round 5c's interleaving spreads that
across its arms. Round 5d's `hand` runs days later and on its own, so nothing
would spread a further update.

### 13d.4 Hypotheses

Every contrast here is unpaired: `hand` and the 5c arms never ran in one block.
An unpaired interval is wider than the paired one round 5 sized K on, so at
K = 15 a row is harder to show as held.

**The drift check.** Round 5c's `none` stands in for a `none` run beside `hand`.

| | |
| --- | --- |
| Measure | each fresh `none` trial against round 5c's 15 |
| Holds | each trial's primary rows sit within the range of 5c's 15 |
| Fails | H4 and H5 read inconclusive, and the report says why |

**H4, a file at all.** A person's short file improves on no file.

| | |
| --- | --- |
| Contrast | `hand` minus round 5c's `none`, unpaired |
| Primary rows | as round 5's H1 |
| Supported | some primary row is better, and none is worse |
| Refuted | any primary row is worse |
| Otherwise | inconclusive |

**H5, the templates against a person's file.** Each templates arm, `inline`,
`hybrid`, `reference` and `skills`, delivers at least what a person's file
delivers.

| | |
| --- | --- |
| Contrast | each templates arm of round 5c, minus `hand`, unpaired |
| Primary rows | as round 5's H1 |
| Supported, per arm | every primary row is held or better |
| Refuted, per arm | any primary row is worse |

**Secondary, no verdict:** every metric of [ch.
8.6](../architecture/08-crosscutting-concepts.md) for `hand` against round 5c's
`none`; the fresh `none` against round 5c's `none`; cost, turns, tokens and wall
time; and the words `hand` puts in context on every turn, beside each 5c arm's.

### 13d.5 Before the first trial

The harness and the report gain, each with a self-test:

- K up to 15 for a run of `hand`, with round 5's spec check; today a run with no
  round-5 arm is capped at K = 5 and its spec is not checked
- the Claude CLI pinned at 2.1.314 for the round, with auto-update off and the
  version recorded on every trial
- round 5c's `none` trials read with their scores, judgings, security readings
  and tool lock, kept apart from round 5d's `none-1` to `none-3`, whose names
  they share
- the unpaired contrasts of H4 and H5, and the drift check

### 13d.6 When it runs

After round 5c's last trial is in, scored and judged. Its 18 trials take about
12 hours at round 5c's pace and spend the plan's limit, so the run waits for
the owner's go.

Nothing in this registration changes once a round-5d trial has run.
