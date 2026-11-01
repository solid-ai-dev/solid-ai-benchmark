# Round 5d registration

Registered on 2026-10-31, while round 5c ran and before any round-5d trial ran.
Round 5c keeps its registration as it was when its first trial ran; this one is
a registration of its own.

## 13d. Round 5d: a person's file and a 40-line file, against round 5c

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
| `short` | 15, fresh | `tests/efficacy/arms/short/CLAUDE.md`, made for 5d |
| `none` | 3, fresh | The bare agent, as a check on drift |
| `none`, from 5c | 15, reused | Round 5c's `none-1` to `none-15`, scored and read |

**`hand`** is a person's file, written for round 3's brief.

- 39 lines and 1,376 bytes, sha256
  `25459854949f648837ac5ef37fca5d7472923b544dffb694cd40f8b8a53ec748`.
- Kept verbatim. It is not edited for round 5's brief.

**`short`** is round 3's arm made again from round 5's chain.

- One generation by `claude-sonnet-5` at effort `high`, in `agents.md`'s inline
  model, from the templates at `9086e0ff`, the brief and round 5's roots, with
  no interview: the way `inline` was made.
- Held to round 3's budget: at most 40 lines, none over 88 characters. The
  generator refuses a file over either bound rather than trimming it.
- 40 lines and 2,173 bytes, sha256
  `8abbcf098312e768e5e01fb6266ec230c13877fa71f40a0bc3ec06e89cd63aea`, with its
  generation record beside it.
- It replaces round 3's file, made from round 1's templates. An earlier round
  is re-run from the benchmark at its own commit, so its files need not stay.

**The reused `none`** comes with round 5c's tool lock, so both rounds are
measured with one ruler.

Why `hand`: it is the only arm that separates the templates from having a file
at all (the decision of 2026-09-12). Round 5 left it out because each of its
arms is made from the templates at `9086e0ff`, and a person's file is not.

Why `short`: round 5c's templates files are 22 to 57 KB, and `hand` is 1.4 KB,
so `hand` against them changes the content and the size at once. `short` and
`hand` sit within a line of each other, so `short` minus `hand` compares the
content at one length, as round 2's `short` minus `hand` did.

### 13d.3 The order

Two runs, in one run root of round 5d's own:

| Run | Arms | Trials, in order |
| --- | --- | --- |
| 1 | `none`, `hand`, `short`, K = 3 | the rotated order, 9 trials |
| 2 | `hand`, `short`, K = 15, from `short-4` | blocks 4 to 15, 24 trials |

- Run 1 starts `none-1`, `hand-1`, `short-1`, and each block starts one arm
  later.
- `hand` and `short` share every block, so `short` minus `hand` is paired.
- The fresh `none` trials share blocks 1 to 3 with them, so they see the same
  days as the round's start.
- Drift after block 3 goes unchecked for the contrasts with round 5c. The CLI
  is pinned (13d.5), which holds the one source of drift known to have moved.

Why the pin: the Claude CLI updated itself from 2.1.312 to 2.1.314 at 03:13 on
2026-10-30, in the middle of round 5c. Round 5c's interleaving spreads that
across its arms. Round 5d runs days later, so nothing would spread a further
update across the two rounds.

### 13d.4 Hypotheses

A contrast with a round 5c arm is unpaired: they never ran in one block. An
unpaired interval is wider than the paired one round 5 sized K on, so at K = 15
a row is harder to show as held.

**The drift check.** Round 5c's `none` stands in for a `none` run beside the
round's arms.

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

**H6, the templates' content at a person's length.** A 40-line file from the
templates delivers at least what a person's file of the same length delivers.

| | |
| --- | --- |
| Contrast | `short` minus `hand`, paired within the block |
| Primary rows | as round 5's H1 |
| Supported | every primary row is held or better |
| Refuted | any primary row is worse |

**Secondary, no verdict:** every metric of [ch.
8.6](../architecture/08-crosscutting-concepts.md) for `hand` and `short`
against round 5c's `none`; `short` against round 5c's `inline`, the same
generation without the budget; the fresh `none` against round 5c's `none`;
cost, turns, tokens and wall time; and the words each arm puts in context on
every turn, beside each 5c arm's.

### 13d.5 Before the first trial

Done with this registration:

- `generate_arm.py` makes `short` under its budget, and refuses a file over it
- `short` is generated and committed with its record
- the harness reads `short` from its new file
- the report already computes H6's contrast, `short` minus `hand`, paired, as
  it did for round 2
- K up to 15 for a run of `hand` and `short`, with round 5's spec check
- `--cli` pins the CLI file every trial runs, the updater is off in every
  trial, and every trial records the CLI's version; round 5d runs
  `C:/efficacy/cli/claude-2.1.314.exe`, a copy of 2.1.314 kept where the
  launcher's updater does not prune it
- scoring makes every environment on Python 3.12, the spec's version, and
  records it on every score. Round 5c was scored on Python 3.14.8, which
  refused three builds that capped `requires-python` below 3.13
- the scorer refuses a root holding scores on another Python, and the report
  a round whose scores were installed on more than one, so round 5c's
  `none` is re-scored on Python 3.12 before round 5d reads it

The report still gains, with a self-test:

- round 5c's `none` trials read with their scores, judgings, security readings
  and tool lock, kept apart from round 5d's `none-1` to `none-3`, whose names
  they share
- the unpaired contrasts of H4 and H5, and the drift check

### 13d.6 When it runs

After round 5c's last trial is in, scored and judged. Its 33 trials take about
22 hours at round 5c's pace and spend the plan's limit, so the run waits for
the owner's go.

Nothing in this registration changes once a round-5d trial has run.
