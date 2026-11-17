# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Dependencies

- Keep the module graph acyclic; break a cycle with a third module or an
  interface, never with a divergent local copy
- Keep coupling shallow: a change inside one module MUST NOT require
  changes in unrelated modules
- Talk only to direct dependencies, and keep together what changes together
  (SHOULD)
- Reach a heavy, native or platform-limited dependency through one module
  that owns its import and names the install command when it is missing

### Optional dependencies

- Where a dependency is optional, run one CI leg without it installed,
  importing the package (MUST)

### Import bans

- Declare a directional import ban where one part of the tree must not
  import another (MAY), and check every ban declared

```bash
pre-commit run find-import-bans --all-files --verbose
```

Pass condition: the bans-declared and modules-inspected counts are above
zero and `import-ban violations` is zero. Each ban is a
`--forbid IMPORTER:IMPORTED` argument; `not applicable` means none is
declared.
