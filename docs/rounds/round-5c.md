# Round 5c registration

Registered on 2026-10-29, after round 5b's first start was stopped and before any
round-5c trial ran. Rounds 5 and 5b keep their registrations as they were when
their first trials ran; this one is a registration of its own.

## 13c. Round 5c: round 5b, with each trial in a pen

### 13c.1 What it takes from round 5b

Round 5c runs [round 5b's registration](round-5b.md) as it stood at `5068f26`,
whole: round 5's design as [its registration](round-5.md) states it, and round
5b's prompt. Its verdicts are the ones round 5 would have read, and they decide
what round 5's would have decided, ADR-058 included.

One thing differs, where a trial's workspace sits in the run root.

### 13c.2 The pen

Each trial gets a folder of its own in the run root, its pen. The workspace sits
inside it under the trial's name, with the trial's temporary directory beside it:

```text
run root/
  none-1/                 the pen
    none-1/               the workspace, where the agent starts
    tmp/none-1-<time>/    the trial's temporary directory
  none-1.tar              the frozen workspace, as before
```

- Anything the agent puts in the pen is the trial's own, and not a reach.
- The run root itself, another trial's pen, `home/` and the scoring area are
  still reaches, as before.
- A voided trial takes its whole pen to `void/`, so the re-run does not find what
  the voided try left beside its workspace.
- Processes started from anywhere in the pen are stopped when the trial ends.

Why: the prompt asks for `pip install .` to work in a clean virtualenv, and an
agent checking that puts the virtualenv beside the workspace, out of the
repository. With the workspace straight in the run root, that was a reach, and
it voided two of the first four trials of round 5 and 5b:

| Trial | What it did | What the void cost |
| --- | --- | --- |
| Round 5, `none-1` | Made `r5-main/tariff_venv_test`, and smoke-tested in `r5-main/tmp` | 20 min, $3.36 |
| Round 5b, `inline-1` | Made `r5b-main/_clean_venv_test`, installed and ran the build there | 46 min, $13.64 |

Neither read another trial. The rule exists to catch a trial that does, and
nesting keeps it doing that while letting the scratch work stand.

### 13c.3 Round 5b's start

Round 5b ran from 10:37 to 13:01 on 2026-10-29, in `C:/efficacy/r5b-main`, and
was stopped:

| Trial | What happened |
| --- | --- |
| `none-1` | Completed, 26 min, $4.78 |
| `inline-1` | Voided for its virtualenv beside the workspace, then rerun to completion, 61 min, $18.70 |
| `hybrid-1` | Stopped mid-build when the run was stopped |

None of its trials was scored or judged, and none counts toward round 5c.
Round 5c starts at block 1 in a run root of its own.

Nothing in this registration changes once a round-5c trial has run.
