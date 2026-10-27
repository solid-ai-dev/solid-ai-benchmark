# 7. Deployment view

A round runs on one machine, the owner's Windows workstation. Three
services and three repositories sit outside it. Nothing of the benchmark
runs anywhere else.

The diagram is a UML deployment diagram: a 3D box is a node with its
keyword, components sit inside their node, and a line is a path labelled
with its protocol.

![The owner's Windows machine holds a Python 3.12 environment running the benchmark's scripts, the run root at C:/efficacy/round, the scoring area beside it, Java with the Playwright browser, the Claude Code CLI, the Codex CLI, gh, a clone of the runs archive and a clone of the templates source. The Claude Code CLI reaches Anthropic over HTTPS, the Codex CLI reaches OpenAI over HTTPS, and gh reaches the hidden suite on GitHub over HTTPS. The archive clone is pushed to tariff-runs, and the templates clone is a git working copy of the templates source. The scripts install packages from the Python package index over HTTPS](../diagrams/deployment.png)

| Node or store | What it is | Needed for |
| ------------- | ---------- | ---------- |
| Python 3.12 | The interpreter the scripts run under, as `py -3.12` | Every scored trial's environment |
| Claude Code CLI | `claude` on `PATH`, logged in | Every trial and every generation |
| Codex CLI | `codex` on `PATH`, logged in | The rounds' judge, from round 5 |
| `gh` | Logged in with access to the hidden suite | Scoring clones the suite |
| Java and a Playwright browser | A Java runtime on `PATH`, and the browser scoring installs | HTML validity, the browser flows and the accessibility probe |
| Run root | A directory outside this repository, such as `C:/efficacy/2026-10-27-round-5` | Every trial |
| Scoring area | `<run root>-scoring`, beside the root | Every score, reading and judging |
| Templates clone | A git working copy of `solid-ai-templates` or a fork | Generating arms, vendoring templates, writing reports |
| Archive clone | A working copy of `braboj/tariff-runs` | Archiving a round before its report |

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

A K = 3 round with five arms and both tasks wants about 15 GB free on the
root's drive. A full disk stops a trial or a scoring with
`No space left on device`, and that trial is not a result.
