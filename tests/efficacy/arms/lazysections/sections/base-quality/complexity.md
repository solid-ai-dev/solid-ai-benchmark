# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Complexity

- Keep cognitive complexity at or under 15 per function
- Nest at most three levels; use guard clauses and early returns
- Replace a boolean flag that selects behaviour with an enum or two named
  functions
- Name every magic number and magic string as a constant
- Size a tuned threshold, such as a latency alert, from its measured
  distribution (p95, p99, maximum legitimate); name the data source in
  the constant's docstring
- Take a limit a specification fixes, such as a protocol's maximum
  message size, from that specification and name it, never from an
  observed percentile
