# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Empty results

### Reach

- Assert that a test expecting no violations reached its inputs: compare
  the files it discovered against what its roots should cover (MUST)
- Fail on that comparison; never print a count for a reader to notice
- Report every occurrence, not the first per line or per file
- Fail an "every item holds" assertion when the set shrinks unexpectedly
- Give the coverage assertion its own test and its own message (SHOULD)
- Assert that each item declares its own value where a permissive default
  exists; prefer a default that is not a legal value

### Floors

- Assert a known floor, not mere non-emptiness
- Size the floor from a measurement, and state the derivation beside the
  constant
- Use the measured count for an append-only corpus, and a stated margin
  below it for one that churns
