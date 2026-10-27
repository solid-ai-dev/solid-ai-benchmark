---
name: write-tests
description: Writing or changing tests, fixtures or assertions
---

# Writing or changing tests, fixtures or assertions

## Fault injection

- Reproduce a fault that depends on the OS, filesystem, locale or
  interpreter with a double at the real call's seam; never wait for the
  platform to supply it (MUST)
- Clear a transient fault as it fires; give a permanent fault its own
  double (MUST)
- Name the platform the evidence came from wherever a test clears a
  suspected component
- Distrust a suspect cleared on one platform; retest it on the platforms
  the evidence did not cover (SHOULD)

## Unique resources

- Allocate a per-test port, directory, database or queue from a
  module-level counter or a fixture, never from a counter on a class other
  tests inherit (MUST)

## Worker leaks

- Assert after every test that no thread, subprocess or server the suite
  started survives it (MUST)
- Run the assertion per test, not once at session end
- Name the leak in the message, and the fix: join with a timeout, never
  sleep
- Leave the assertion on permanently
