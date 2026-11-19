# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Provenance

- Assert the source of a value, not the value, where a fix changes where it
  comes from
- For such a fix, inject a source that yields a different value, and assert
  the code overrides it
- Treat a new test that passes against the unfixed code as aimed at the
  wrong property, not as proof the fix was unnecessary
- Substitute at the name the module under test reads, not on the module
  that defines the type
