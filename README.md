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
| `docs/reports/` | Every round's dated report, with its appendix, record and radars |
| [The assessment](docs/reports/2026-09-27-efficacy-assessment.md) | What rounds 1 to 3 showed, beside their reports |
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

## The private repositories

Running a round needs two private repositories besides the templates. Ask
the owner for access to either.

| Repository | What it holds | Read by |
| --- | --- | --- |
| `braboj/tariff-hidden-suite` | The suite every trial is graded by | The scorer only |
| `braboj/tariff-runs` | Each round's frozen trees and scores | The owner |

The scorer clones the hidden suite with `gh` at scoring time, shallow and
fresh for every scoring, into the scoring area beside the run root. It never
lands in a trial's workspace, and each score records the suite's commit. So
`gh` must be logged in with access to it, or scoring refuses.

## Status

Moved here with its history from `Imbra-Ltd/imbra-ai-templates`
(solid-ai-dev/solid-ai-templates#2379). Next:

- Build the arms with the templates' generation tool, not the interview
- Run every arm fresh, and report the spread beside the mean

Results are reported in this repository, under `docs/reports/`, and [listed here by round](docs/rounds/README.md#reports).

## License

[MIT](LICENSE), as the templates.
