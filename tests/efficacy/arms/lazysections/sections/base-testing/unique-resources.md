# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Unique resources

- Allocate a per-test port, directory, database or queue from a
  module-level counter or a fixture, never from a counter on a class other
  tests inherit (MUST)
