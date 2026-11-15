# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Enforcement

- Enforce these conventions through the gates: editor, pre-commit, CI
- Merge to `main` only with passing tests

### Generated output

- Make a generator emit output that passes the linters natively; a needed
  `lint --fix` is a generator bug (MUST)
