# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## External definitions

- Assert at least one case against a fixed vector the specification
  publishes, wherever a format is defined outside the codebase (MUST)
- Never take a round trip through your own encoder and decoder as proof
  that either is correct
- Assert what an object does, not the type the runtime reports for it
- Assert that a misuse fails, and which error only where the interface
  declares one
- Never assert an exception class the runtime raises on its own
