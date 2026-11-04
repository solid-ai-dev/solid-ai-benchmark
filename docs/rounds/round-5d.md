# Round 5d registration

Registered on 2026-10-31, while round 5c ran and before any round-5d trial ran.
Round 5c keeps its registration as it was when its first trial ran; this one is
a registration of its own.

Amended on 2026-11-01, before any round-5d trial ran: the three fresh `none`
trials and their drift check are dropped, and the round runs in one run of
`hand` and `short`.

Amended again on 2026-11-01, before any round-5d trial ran: the verdict rules of
13d.7 replace round 5's one-strike reading, and the radar plots how far each row
moved (13d.8).

Amended a third time on 2026-11-01, before any round-5d trial ran: adherence
leaves the primary rows, and the hidden tests take its place (13d.4).

## 13d. Round 5d: a person's file and a 40-line file, against round 5c

### 13d.1 What it takes from round 5c

Round 5d runs [round 5c's registration](round-5c.md) as it stood at `07d1641`:
block A, the spec at its registered sha256, `claude-sonnet-5` at effort `high`,
round 5b's prompt, the pen, the judge, the scoring and the code size rows, and
the margins of round 5's H1.

Three things differ: the arms, the order, and a reuse of round 5c's `none`.

Amended 2026-11-02, before any round-5d trial: the hidden suite is the
revision that imports the build afresh for every test (#116), and round 5c's
reused trials are re-scored with it in round 5d's root, so every contrast is
graded by one suite (ADR-021).

### 13d.2 The arms

| Arm | Trials | Where they come from |
| --- | --- | --- |
| `hand` | 15, fresh | `tests/efficacy/arms/hand/CLAUDE.md` as it is at `010ee36` |
| `short` | 15, fresh | `tests/efficacy/arms/short/CLAUDE.md`, made for 5d |
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

One run of `hand` and `short` at K = 15, in a run root of round 5d's own: 30
trials in the rotated order.

- The run starts `hand-1`, `short-1`, and each block starts one arm later.
- `hand` and `short` share every block, so `short` minus `hand` is paired.
- No fresh `none` runs beside them, so drift between round 5c and round 5d
  goes unchecked for the contrasts with round 5c. The CLI is pinned (13d.5),
  which holds the one source of drift known to have moved.

Why the pin: the Claude CLI updated itself from 2.1.312 to 2.1.314 at 03:13 on
2026-10-30, in the middle of round 5c. Round 5c's interleaving spreads that
across its arms. Round 5d runs days later, so nothing would spread a further
update across the two rounds.

### 13d.4 Hypotheses

A contrast with a round 5c arm is unpaired: they never ran in one block. An
unpaired interval is wider than the paired one round 5 sized K on, so at K = 15
a row is harder to show as held.

An unpaired interval resamples each arm on its own: a bias-corrected and
accelerated bootstrap of the difference of the two means, 10,000 resamples,
with the acceleration from each arm's jackknife (Efron and Tibshirani, 1993).

Round 5c's `none` stands in for a `none` run beside the round's arms, with no
check that the bare agent stayed where it was. The report says so beside H4
and H5.

**H4, a file at all.** A person's short file improves on no file.

| | |
| --- | --- |
| Contrast | `hand` minus round 5c's `none`, unpaired |
| Primary rows | the round's primary rows, below |
| Supported | some primary row is better, and none is worse |
| Refuted | any primary row is worse |
| Otherwise | inconclusive |

**H5, the templates against a person's file.** Each templates arm, `inline`,
`hybrid`, `reference` and `skills`, delivers at least what a person's file
delivers.

| | |
| --- | --- |
| Contrast | each templates arm of round 5c, minus `hand`, unpaired |
| Primary rows | the round's primary rows, below |
| Supported, per arm | every primary row is held or better |
| Refuted, per arm | any primary row is worse |

**H6, the templates' content at a person's length.** A 40-line file from the
templates delivers at least what a person's file of the same length delivers.

| | |
| --- | --- |
| Contrast | `short` minus `hand`, paired within the block |
| Primary rows | the round's primary rows, below |
| Supported | every primary row is held or better |
| Refuted | any primary row is worse |

**The primary rows** are outcomes:

- task success, the hidden suite's pass rate, on working builds;
- the security and data-protection probe pass rates, on working builds;
- the judge's security and data-protection rows.

Adherence is not among them. It scores the templates' own checklist, which
only the templates arms were given, so it shows whether the rules reached the
code, not whether the code is better. It is printed without a verdict.

H4 to H6 are read under the rules of 13d.7, and each verdict is printed with
its confidence and the arm's profile.

**Secondary, no verdict:** every metric of [ch.
8.6](../architecture/08-crosscutting-concepts.md) for `hand` and `short`
against round 5c's `none`; `short` against round 5c's `inline`, the same
generation without the budget; cost, turns, tokens and wall time; and the words
each arm puts in context on every turn, beside each 5c arm's.

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
  and tool lock, from round 5c's run root and scoring area
- the unpaired contrasts of H4 and H5
- the verdict rules of 13d.7 and the radar of 13d.8, each rule with a self-test
  that fails with the rule removed

### 13d.6 When it runs

After round 5c's last trial is in, scored and judged. Its 30 trials take about
20 hours at round 5c's pace and spend the plan's limit, so the run waits for
the owner's go.

Nothing in this registration changes once a round-5d trial has run.

### 13d.7 Verdict rules

Round 5c read a row as worse on one strike, and one broken build struck several
rows at once. Its two "worse" rows were the same two builds: they failed the
hidden tests and the data-protection probes together. Round 5d counts each
failure once and lets only a difference past the margin decide.

**Reliability is a row of its own.**

- It is the share of builds that install and boot.
- Each arm's share is printed with its exact interval, Clopper-Pearson.
- A contrast's interval is Newcombe's score interval for a difference of two
  shares (Newcombe, 1998), in its paired form for H6.
- Its margin is one build of 15: 6.7 pp.
- It can refute but never has to hold. At K = 15 even 15 of 15 against 15 of
  15 gives an interval near ±20 pp, so no result could show it held. A worse
  reliability refutes H4, H5 or H6; any other reading lets the other primary
  rows decide.

**Quality rows read working builds only.**

- Task success, the security probes and the data-protection probes are read
  on the builds that installed and booted.
- A build that does not boot counts against reliability, and nowhere else.
- Paired contrasts keep a block only where both builds work. The report prints
  how many blocks each row kept.

**A strike or a win needs the whole interval past the margin.**

- **Worse:** the whole interval lies past the row's margin, on the losing side.
- **Better:** the whole interval lies past the margin, on the improving side.
- **Held:** the whole interval lies inside the margin, as in ch. 8.1.2.
- Otherwise the row is unsettled, and it decides nothing.
- The margins are round 5's: ch. 8.1.2, round 5's app-code rows,
  and reliability's above.

**Economy has margins, and two rows on the radar.**

| Row | Margin | On the radar |
| --- | --- | --- |
| Cost | 25 % relative | yes |
| Turns | 25 % relative | yes |
| Output tokens | 25 % relative | appendix only |
| Wall time | 25 % relative | appendix only |

- Output tokens move with turns, and wall time with cost, so two rows stand for
  four.
- Economy stays secondary: it reads better, held or worse in the profile, and
  decides no hypothesis.

**Each verdict states its confidence.**

- Leave-two-out: the verdict is read again with every two trials dropped, from
  the 15 blocks of a paired contrast or from the 30 trials of an unpaired one.
- Each reading uses the interval rule of ch. 8.1.1, with 2,000 resamples and
  the recorded seed, to keep the 435 readings of an unpaired contrast cheap.
- **Robust:** every reading gives the same verdict. **Fragile:** any reading
  differs.

**A profile, beside the word.**

- Each arm's verdict is printed with one line per radar axis: better, held,
  worse or unsettled.
- An axis is worse where a row is worse and none better, better the other
  way round, and held where every row is held. Where rows went both ways, it
  takes the sign of its size on the radar (13d.8).
- A trade-off, such as better tests at a higher cost, stays visible instead of
  folding into "supported" or "refuted".

### 13d.8 The radar

The radar plots how far each row moved, not how many rows moved. Round 5c's
axes were (rows better minus rows worse) over rows, so a 1 % move counted as
much as a 200 % one.

Per row:

1. Take the bound of the interval nearest zero: the move the data vouches for.
   An interval across zero scores 0.
2. Divide it by the row's full scale and cap it at ±1, with + for better.
3. An axis is the mean of its rows.

| Row kind | Full scale: scores ±1 |
| --- | --- |
| Judge scores, 1–5 | 1 point |
| Shares: reliability, task success, probe pass rates, CSRF, XSS | 20 pp |
| Coverage | 20 points |
| Counts, per-KLOC rows, cost and turns | ×4 or ÷4 against `none`, on a log scale |

- A count row's move is a ratio, (n + d + 1) / (n + 1), where n is `none`'s
  mean, d the bound nearest zero of the difference, and 1 one unit of the
  row: one count, or one per KLOC. The ratio stays defined at zero, both for a
  `none` of 0 and for an arm that falls to 0. Its score is the ratio's log
  over log 4, signed by the row's direction.
- Cost and turns are never zero in a trial that ran, so they take the plain
  ratio, (n + d) / n, on the same log scale.
- The full scale is where an axis saturates. It is not the margin, which
  still decides better, held or worse.
- The radar describes the verdicts and decides nothing.

### 13d.9 Choosing round 6's arms

Added 2026-11-02, before any round-5d trial. Round 5d also screens which arms
round 6 runs again, fresh and paired. The rule is fixed here, before any trial
is read for it.

1. **Candidates:** `inline`, `hybrid`, `reference` and `skills` from round 5c,
   re-scored with the corrected hidden suite in round 5d's root, and `hand`
   and `short` from round 5d. Each is read against round 5c's `none` by the
   rules of 13d.7.
2. **Out:** an arm whose reliability, or any row 13d.7 decides on, reads worse
   than `none`: the hidden tests, the security probes, the data-protection
   probes, or the judge's security and data-protection rows.
3. **Ranked:** the rest by how many of those rows read better than `none`. On
   a tie, the arm with the lower mean cost per trial ranks higher.
4. **Round 6:** `none` and the top four; all of them if fewer than four remain.
5. **Not a verdict:** the screen decides which arms run again, not which arm is
   better. Round 6 runs them fresh and paired, so an arm that ranked high by
   luck still has to hold up.
