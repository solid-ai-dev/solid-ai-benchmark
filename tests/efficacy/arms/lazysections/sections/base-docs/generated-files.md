# Base — Documentation

Which documents a project keeps, and how they stay true.

## Generated files

- Start every generated file with a banner naming the tool that wrote it
  and the command that refreshes it (SHOULD)
- Give every generator a `--check` flag that re-renders in memory and exits
  non-zero on a diff or a missing file, and require it in pre-commit and CI
  (SHOULD)
- Re-render to judge staleness; never rely on inspection, above all for a
  visual or binary output such as a diagram export
- Exclude generated paths from formatters (SHOULD)
- Re-run the generator when its inputs change; never edit its output
- Preserve human-entered content when refreshing a generated file, or fail
  naming what would be discarded (MUST)
