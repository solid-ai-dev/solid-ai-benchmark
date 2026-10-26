# solid-ai-benchmark

Measures whether a generated agent context file improves the code an agent
writes, and how consistent the result is across runs and projects. One
ruler for every templates source: upstream `solid-ai-templates` or a fork.

| Path | What it is |
|---|---|
| `docs/design/efficacy-benchmark.md` | The design: arms, metrics, verdict rules |
| `docs/design/efficacy-assessment.md` | The assessment of the benchmark itself |
| `tests/efficacy/` | The harness, scorer, judge and report; its README lists each part |
| `tests/lib.py` | Shared helpers the harness imports |

## Status

Moved here with its history from `Imbra-Ltd/imbra-ai-templates`
(solid-ai-dev/solid-ai-templates#2379). The paths are unchanged, so the
harness still assumes it runs inside a templates repository. Next:

- Take the templates source as an input: a repository and a ref
- Build the arms with the templates' generation tool, not the interview
- Run every arm fresh, and report the spread beside the mean

Results are reported in the templates repository, under `docs/audits/`.
