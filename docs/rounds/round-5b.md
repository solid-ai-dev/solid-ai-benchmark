# Round 5b registration

Registered on 2026-10-29, after round 5's first start was stopped and before any
round-5b trial ran. Round 5's registration stays as it was when its first trial
ran; this one is a registration of its own.

## 13b. Round 5b: round 5, with the headless prompt

### 13b.1 What it takes from round 5

Round 5b runs [round 5's registration](round-5.md) as it stood at `66d6a1f`, the
commit its first trial ran from, whole: the question, block A, the arms, the
hypotheses H1 to H3 and their margins, K = 15 and the rotated order, the judge,
the code size rows and the spec at its registered sha256. Its verdicts are the
ones round 5 would have read, and they decide what round 5's would have decided,
ADR-058 included.

One thing differs, the prompt.

### 13b.2 The prompt

Every arm's prompt gains one sentence after its first:

> SPEC.md is the approved plan, and nobody will answer questions during this
> run, so build it to the end without stopping for approval.

Why: `templates/core/review.md` at `9086e0ff` asks for a plan, and its
approval, before implementation code, unless the requester specified the change
in full. A trial runs headless, so nobody approves. Round 5's `inline-1`
printed a plan, cited that rule, and ended after 2 minutes and $0.30 with
nothing built. Without the sentence a templates arm loses for waiting, not for
the code it guides. The sentence goes to every arm, `none` included, so the
context file stays the only difference.

The harness records the prompt on every trial, and the report refuses a round
holding a build trial with something to score that was given another prompt.

### 13b.3 Round 5's start

Round 5 ran from 08:21 to 09:47 on 2026-10-29, in `C:/efficacy/r5-main`, and
was stopped:

| Trial | What happened |
| --- | --- |
| `none-1` | Voided for a command run outside its workspace, then rerun to completion |
| `inline-1` | Stopped after its plan, as above |
| `hybrid-1` | Stopped mid-build when the run was stopped |

None of its trials was scored or judged, and none counts toward round 5b.
Round 5b starts at block 1 in a run root of its own.

Nothing in this registration changes once a round-5b trial has run.
