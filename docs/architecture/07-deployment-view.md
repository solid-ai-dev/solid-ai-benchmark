# 7. Deployment view

A round runs on one machine, the owner's Windows workstation. Three
services and three repositories sit outside it. Nothing of the benchmark
runs anywhere else.

The diagram is a UML deployment diagram: a 3D box is a node with its
keyword, components sit inside their node, and a line is a path labelled
with its protocol.

![The owner's Windows machine holds a Python 3.12 environment running the benchmark's scripts, the run root at C:/efficacy/round, the scoring area beside it, Java with the Playwright browser, the Claude Code CLI, the Codex CLI, gh, a clone of the runs archive and a clone of the templates source. The Claude Code CLI reaches Anthropic over HTTPS, the Codex CLI reaches OpenAI over HTTPS, and gh reaches the hidden suite on GitHub over HTTPS. The archive clone is pushed to tariff-runs, and the templates clone is a git working copy of the templates source. The scripts install packages from the Python package index over HTTPS](../diagrams/deployment.png)

| Node or store | What it is | Needed for | Without it |
| ------------- | ---------- | ---------- | ---------- |
| Python 3.12 | Found as `py -3.12` or `python3.12` | Every scored trial's environment | The scorer refuses to score |
| Claude Code CLI | `claude` on `PATH`, logged in | Every trial and every generation | The preflight refuses the run |
| Codex CLI | `codex` on `PATH`, logged in | The rounds' judge, from round 5 | Each judging fails |
| `gh` | Logged in with access to the hidden suite | Scoring clones the suite | Scoring refuses |
| Java | A Java runtime on `PATH` | `html5validator`, the HTML validity metric | That metric is missing |
| Playwright browser | The browser scoring installs | The suite's browser flows and the accessibility probe | Scoring installs one, and refuses the trial where it cannot |
| Run root | A directory outside this repository, such as `C:/efficacy/2026-10-27-round-5` | Every trial | The harness refuses a root inside the repository |
| Scoring area | `<run root>-scoring`, beside the root | Every score, reading and judging | |
| Templates clone | A git working copy of `solid-ai-templates` or a fork, named by `--templates` | Generating arms, vendoring templates, writing reports | Every run refuses |
| Archive clone | A working copy of `braboj/tariff-runs` | Archiving a round before its report | The report refuses to write under `docs/audits/` |

A missing piece shows up as a refusal or a missing metric, not a crash.
`score.py --no-web` skips both browser-side probes and installs no browser.
The suite then skips its browser flows, and the trial is flagged as partial.

## 7.1 Where things must not be

| Must not | Why |
| -------- | --- |
| The run root inside this repository | An arm could read the templates the `none` arm is defined not to have. The harness refuses it |
| A `CLAUDE.md` above the run root | It would reach the bare arm. The harness refuses the run |
| The scoring area inside the run root | It would sit one `..` from the next trial's workspace |
| The hidden suite in any workspace | A trial that read it would measure the suite |
| Two runs of one scoring tool on one area | The second would delete what the first is reading. A `.running` claim refuses it |

## 7.2 Sizing

<!-- measured: 2026-09-27 -->
Round 3's root held 5.5 GB after both tasks. Each scored trial's
environment is about 290 MB.
<!-- /measured -->

Round 5's 75 build trials want about 40 GB free on the root's drive; a
K = 3 round of five arms and both tasks wanted about 15 GB. A full disk stops
a trial or a scoring with `No space left on device`, and that trial is not a
result.

## 7.3 Budget

Round 5 runs five arms at K = 15, the build task alone. Figures per trial
are round 3's, measured at `claude-sonnet-5`.

| Item | Count | Per item | Round total |
|---|---|---|---|
| Control fixture | 33 judgings (11 trees × 3) | — | ChatGPT plan quota, before block A |
| Build trials | 75 (5 arms × 15) | 10–29 min, $1.4–$3.5 | about 21 hours, about $185 |
| Judgings | 225 (75 trees × 3) | — | ChatGPT plan quota |

Both CLIs bill against a subscription, so this is quota, not invoice.
