# Agent rules

Rules for any coding agent working in this repository. The
[README](README.md) says what the benchmark is; the
[architecture](docs/architecture/) holds every rule it follows.

## Commands

Every module has its own self-test. It needs a clone of the templates
repository, named with `--templates <path>` or `BENCHMARK_TEMPLATES`:

```bash
export BENCHMARK_TEMPLATES=../solid-ai-templates
py tests/efficacy/harness.py --self-test
py tests/efficacy/generate_arm.py --self-test
py tests/efficacy/score.py --self-test
py tests/efficacy/judge.py --self-test
py tests/efficacy/report.py --self-test
py tests/efficacy/archive.py --self-test
py tests/efficacy/reuse.py --self-test
py tests/efficacy/progress.py --self-test
py tests/efficacy/security.py --self-test
py tests/efficacy/control/control.py --self-test
py tests/efficacy/trace.py --self-test
py tests/efficacy/trace.py
py -m pyflakes tests
```

`trace.py` runs every self-test and fails on a requirement in
[`docs/requirements.md`](docs/requirements.md) with no row in
[`docs/coverage.md`](docs/coverage.md), or on a label there no self-test
prints. A new rule gets a row in both, and a new check its label.

A self-test makes no model call and runs no trial. Running a trial or a
judging spends a plan's limit, so ask first.

## Branches and commits

- Branch off `main` for every change: `feat/…`, `docs/…`, `chore/…`.
- Commit messages follow Conventional Commits with a scope where one fits:
  `feat(efficacy): …`, `docs(primer): …`.
- Open a pull request that names the issues it closes.
- Never merge without the owner's approval.
- Never force-push, and never rebase a branch that is already pushed. When a
  pull request stops merging cleanly, merge `main` into it.

## Code and docs

- Python states each rule itself. It never cites a doc section, a doc path
  or an issue number.
- A docstring states the contract and stays short. The reasoning goes in a
  comment above the rule it explains.
- The files under `tests/efficacy/arms/` are generator output, kept verbatim.
  Never edit or reflow them by hand; regenerate them instead.
- A round's registration under `docs/rounds/` is fixed once its first trial
  has run.
- Wrap prose and code at 88 columns.
