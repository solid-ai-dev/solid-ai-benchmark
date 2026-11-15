# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Library output

- Never write to the host's standard output or error from a library, and
  never configure logging beyond the library's own logger (MUST)
- Make the library's logger injectable, falling back to its module logger
- Check the silence in a fresh process; a test runner's handler hides the
  default
