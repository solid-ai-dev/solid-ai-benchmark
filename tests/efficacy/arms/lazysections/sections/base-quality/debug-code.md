# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Debug code

- Commit no debug output (`print()`, `console.log()`) and no hardcoded
  breakpoint
- Delete commented-out code
- Gate debug tooling behind a flag or environment variable, off by default

### Probe scripts

- Write a probe, a throwaway script that measures data or behaviour,
  rather than guess
- Delete a probe before the commit that uses its findings (MUST)
- Keep findings in source comments, decision records or docs, never in
  the probe
