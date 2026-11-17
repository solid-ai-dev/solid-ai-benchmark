# Base — Documentation

Which documents a project keeps, and how they stay true.

## Line width

- Wrap Markdown at the width the project declares, never at one written
  into a rule

### Enforcing the width

- Declare the width as the line-length setting in the Markdown linter's
  configuration (MUST); the linter reads no other file, so a width set only
  for editors goes unenforced
- Keep any second copy of the width, such as `.editorconfig` for editors,
  equal to the linter's
- Declare in the same place which of fenced blocks, table rows and headings
  are exempt
- Exempt a line only where it cannot wrap: an unbreakable token, a bare
  URL, a Markdown link, or a single-line directive a parser reads whole
- Enforce the width with the Markdown linter's line-length rule in CI
  (MUST); a project that declares no width has no rule
- Pass that CI run the configuration and the files to lint explicitly
  (MUST)
