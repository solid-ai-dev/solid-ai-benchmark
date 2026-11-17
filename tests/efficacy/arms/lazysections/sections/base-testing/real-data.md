# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Real data

- Drive a diagnostic view through the production entry point behind a
  flag, never a separate command with its own setup
- Run the real pipeline on the input a fix targets, and diff its output
  against the expected values
- Never take passing unit tests, suites and staleness checks as proof that
  the fix fired
