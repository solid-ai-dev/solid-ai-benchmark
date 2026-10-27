# 3. Context and scope

The benchmark sits between the templates it measures and the services that
build, judge and store. This chapter draws that boundary: who is on either
side, what crosses it, and over which channel.

## 3.1 Business context

![The benchmark as one box with its neighbours. The owner gives it settings, and report readers get reports from it. It exchanges builds and judgings with Claude Code, sends a sample to the Codex CLI for a cross-check judgement, and exchanges packages with the Python package index. Templates come in from the templates source and reports go back to it. The hidden suite gives it acceptance tests, and it sends archived rounds to the runs archive](../diagrams/context.png)

| Neighbour | Gives the benchmark | Gets from the benchmark |
| --------- | ------------------- | ----------------------- |
| Owner | A registered hypothesis, a round's settings, the go to run | Refusals before cost, records after |
| Report reader | Nothing | The dated report and its caveats |
| Claude Code | Builds, generated files, judgings | Workspaces, prompts, bundles to judge |
| Codex CLI | Cross-check judgings on a sample | The same blind bundles |
| Python package index | The packages every app and every tool installs | Nothing |
| Templates source | The templates, the chain and the release an arm is built from | Reports under its `docs/audits/` |
| Hidden suite | Acceptance tests and the change suite, at scoring only | Nothing |
| Runs archive | A restored round, for a re-read | Each round's raw data |

Outside the boundary:

| Not the benchmark's | Who owns it |
| ------------------- | ----------- |
| The templates and the generator's instructions | The templates source |
| What the report concludes for a decision record | The owner, in the templates source |
| The hidden suite's checks and their reference implementation | `braboj/tariff-hidden-suite` |
| The models' behaviour | Anthropic and OpenAI |

## 3.2 Technical context

The channel to each neighbour, and who opens it.

| Interface | Between | Channel | Opened by |
| --------- | ------- | ------- | --------- |
| Agent session | harness and Claude | `claude -p`, prompt on standard input, JSON result on standard output, transcript in the scratch home | The harness |
| Generation | `generate_arm.py` and Claude | The same CLI, one non-interactive invocation per arm | The generator |
| Judging | `judge.py` and the judge CLI | `claude` or `codex exec`, the rubric as a JSON Schema, the bundle on standard input | The judge script |
| Hidden suite | `score.py` and GitHub | `gh repo clone` at a pinned revision, into the scoring area only | The scorer |
| Package installs | Trials, scoring, tools and PyPI | `pip` over HTTPS, the tools from `tool-lock.txt` | The trial or the scorer |
| Templates | Every script and the templates source | A local git clone, named by `--templates` | The operator |
| Archive | `archive.py` and `braboj/tariff-runs` | Files written into a local clone, pushed by the operator | The operator |
| Report | `report.py` and the templates source | A Markdown file under `docs/audits/` | The report script |
