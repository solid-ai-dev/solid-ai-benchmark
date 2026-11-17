# Base — Testing

What to test, how to keep tests honest, and how to prove a change.

## Rendered output

- Verify a visual change on its rendered output, read headless off the
  pixels or the resolved DOM, never off the source (MUST)
- Capture the render before the change as well as after it (SHOULD)
- Confirm the build is fresh before re-editing a change that still looks
  wrong
