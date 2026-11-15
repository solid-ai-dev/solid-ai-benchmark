# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Call sites

- Exercise every call site of a changed shared path, not only the reported
  case (MUST)
- Run the ground-truth comparison on every entity that uses the path
- Re-run every consumer that derives a committed artifact from the changed
  surface, and keep that list beside the surface
