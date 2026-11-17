# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Test types

Classify a test by the boundary it crosses, not by who runs it or which
tool drives it.

| Type | Boundary crossed | Focus |
| --- | --- | --- |
| Unit | None | One function or class in isolation |
| Integration | Process or component | Interaction with a real dependency |
| System | System | The product against its requirements |
| Regression | Any, reusing existing tests | Unintended change |
| Exploratory | Any, unscripted | Unexpected behaviour |

- Double only what a unit test would cross a boundary to reach: I/O, time,
  randomness, another process
- Keep deterministic in-process collaborators real
- Use the real dependency for the boundary an integration test covers; you
  MAY double the unrelated ones
- Add a regression test for every fixed defect (SHOULD)

## Coverage

- Cover every happy path the functional requirements define
- Cover negative inputs and edge cases as well (SHOULD)
- Cover each dependency's faults at every tier: unavailable, malformed
  response, timeout, degraded operation (SHOULD)
- Meet the project's coverage threshold for new code before merging
- Never let coverage regress between releases
- Run every unit test from CI, with no human step
- Name a test so the name alone states the unit, the input and the expected
  outcome (SHOULD)
- Run a unit that reads a structured external artifact against real
  production data once before calling its suite complete, and add a
  regression test for each gap it shows

## Testability

- Keep business logic in pure functions, and push I/O to thin adapters at
  the edges (SHOULD)
- Inject dependencies rather than construct them in the code under test
  (SHOULD)
- Split a function that needs more than two mocks to test (SHOULD)
- Treat code that is hard to test as a design problem

# Backend — Database Conventions

## Testing

- Reset state between test runs — truncate tables or wrap each test in a
  transaction rolled back after completion
- Do not substitute a different database engine in tests, such as an
  in-memory one — behaviour differences cause false passes
- Never run schema migrations against a production database inside a test
  suite
