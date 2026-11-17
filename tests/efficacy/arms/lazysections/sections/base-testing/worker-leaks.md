# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Worker leaks

- Assert after every test that no thread, subprocess or server the suite
  started survives it (MUST)
- Run the assertion per test, not once at session end
- Name the leak in the message, and the fix: join with a timeout, never
  sleep
- Leave the assertion on permanently
