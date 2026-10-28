# solid-ai-benchmark

Measures whether a generated agent context file improves the code an agent
writes, and how consistent the result is across runs and projects. One
ruler for every templates source: upstream `solid-ai-templates` or a fork.

New here? Start with the [primer](docs/primer.md): what the benchmark
does and how to read its results, with no programming needed.

| Path | What it is |
|---|---|
| `docs/primer.md` | The benchmark in plain words: the knobs, a round, a verdict |
| `docs/architecture/` | The one source of truth: how it is built and every rule it follows, in arc42's twelve chapters |
| `docs/journeys/` | A person walked through each task, with its findings |
| `docs/diagrams/` | Every diagram, as draw.io source beside its PNG |
| `docs/rounds/` | Each round's registration, fixed before its first trial, and [every round's report](docs/rounds/README.md#reports) |
| [The assessment](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-09-27-efficacy-assessment.md) | What rounds 1 to 3 showed, beside the reports in `solid-ai-templates` |
| `tests/efficacy/` | The harness, scorer, judge and report |
| `tests/lib.py` | Shared helpers the harness imports |

## The templates source

The benchmark carries no templates. Every run, the self-test included,
names a git clone of the templates repository, upstream or a fork, with
`--templates <path>` or the `BENCHMARK_TEMPLATES` variable:

```bash
py tests/efficacy/harness.py --self-test --templates ../solid-ai-templates
```

The release the arms are built from is the round's registered ref; each
generation and vendoring record states the source's remote, ref and commit.
A run with no source refuses, because it could not deny the agent the
templates.

## Status

Moved here with its history from `Imbra-Ltd/imbra-ai-templates`
(solid-ai-dev/solid-ai-templates#2379). Next:

- Build the arms with the templates' generation tool, not the interview
- Run every arm fresh, and report the spread beside the mean

Results are reported in the templates repository, under `docs/audits/`,
and [listed here by round](docs/rounds/README.md#reports).
