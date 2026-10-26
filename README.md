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

## The templates source

The benchmark carries no templates. Every run, the self-test included,
names a git clone of the templates repository, upstream or a fork, with
`--templates <path>` or the `BENCHMARK_TEMPLATES` variable:

```bash
py tests/efficacy/harness.py --self-test --templates ../solid-ai-templates
```

The release the arms are built from is the design's fixed ref; each
generation and vendoring record states the source's remote, ref and commit.
A run with no source refuses, because it could not deny the agent the
templates.

## Status

Moved here with its history from `Imbra-Ltd/imbra-ai-templates`
(solid-ai-dev/solid-ai-templates#2379). Next:

- Build the arms with the templates' generation tool, not the interview
- Run every arm fresh, and report the spread beside the mean

Results are reported in the templates repository, under `docs/audits/`.
