# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

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
