# Backend — Database Conventions

## Schema changes

- Make every schema change through a migration committed to source
  control — never edit the database manually
- Never regenerate or modify a migration that is already merged
- Write one migration per logical change — do not batch unrelated schema
  changes
- Provide a `down` migration for every `up`; where reversal would lose
  data, say so in the migration and get approval before applying it
