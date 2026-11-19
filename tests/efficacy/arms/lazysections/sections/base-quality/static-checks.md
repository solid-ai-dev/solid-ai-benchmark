# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Static checks

- Adopt the language's static type checker at its strictest setting where
  the language has one, and keep it clean (MUST)
- Annotate every public function's parameters and return type where the
  language allows it (MUST)
- Annotate types as the code is written
- Adopt a linter and a formatter, and keep both clean (MUST)
- Give the project one check command running format, lint, types and
  tests, and run it in CI
- While working, run the narrowest check that covers the affected
  behaviour and its dependents
- Run the full check command before each commit and at completion; an
  unchanged, passing full check satisfies both
- Do not re-run a check whose inputs have not changed since it passed
- Batch independent fixes before re-running; re-run earlier when needed to
  diagnose or to verify a prerequisite fix

```bash
<type-check-command>
<lint-command>
<format-check-command>
```

Pass condition: all three print nothing. Each command is the project's own,
in its quiet mode.
