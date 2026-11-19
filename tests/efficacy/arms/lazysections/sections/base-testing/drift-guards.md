# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Drift guards

- Give every fact stored in two places a test that fails when the copies
  diverge, such as:
  - a documented limit and its constant
  - live routes and the API contract
  - the runtime version and the package metadata
  - an export list and the module's bindings
- Introspect the live artifact rather than hardcode the expected value
  (SHOULD)
- Assert one direction: the derived copy matches the source of truth
