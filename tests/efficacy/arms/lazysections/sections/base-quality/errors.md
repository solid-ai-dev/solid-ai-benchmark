# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Errors

- Validate input at boundaries and fail at once on invalid state
- Read a value from its source-of-truth field, and raise when the field is
  missing; never fall back to a value derived from a slug, name or hash
- Bound every wait on another thread, process or connection, report why it
  gave up, and check the worker's liveness as well as the deadline
- Never break a public catch contract: a raise callers catch by a built-in
  type keeps that type
- Add an error type only where a caller could act differently
- Never let a caller-side input filter stand in for a precondition: widen
  the filter, or assert the precondition inside the function
