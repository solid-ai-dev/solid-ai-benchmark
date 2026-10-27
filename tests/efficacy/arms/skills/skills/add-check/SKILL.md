---
name: add-check
description: Adding or tightening a check, such as a linter rule, a CI step, a hook or a threshold
---

# Adding or tightening a check, such as a linter rule, a CI step, a hook or a threshold

## Import bans

- Declare a directional import ban where one part of the tree must not
  import another (MAY), and check every ban declared

```bash
pre-commit run find-import-bans --all-files --verbose
```

Pass condition: the bans-declared and modules-inspected counts are above
zero and `import-ban violations` is zero. Each ban is a
`--forbid IMPORTER:IMPORTED` argument; `not applicable` means none is
declared.

## New constraints

- Run a new constraint (a rule, a check, a tightened bound, a narrowed
  exemption) against the existing corpus before it merges (MUST)

## Enforcing the width

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
