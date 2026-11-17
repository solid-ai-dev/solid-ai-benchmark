# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## Commits

- Commit under your full name and one consistent email; never change
  identity mid-project
- Work on a branch; never commit directly to `main`
- Never commit build output, dependency directories or secrets
- Commit a generated file only when the project tracks it on purpose, under
  the regeneration rules below
- Treat every repository as public: no secret, credential or sensitive
  value in source or history
- Keep a `.gitignore` (MUST) covering dependencies, build output, secrets,
  editor state, OS files and coverage output
- Commit lockfiles (MUST)
