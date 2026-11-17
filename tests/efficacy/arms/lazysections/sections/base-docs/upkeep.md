# Base — Documentation

Which documents a project keeps, and how they stay true.

## Upkeep

- Update every document a change touches, in the same commit:
  - `CLAUDE.md` when architecture, stack, design rules or conventions change
  - `README.md` when structure, stack or setup steps change
  - `AGENTS.md` whenever `CLAUDE.md` changes, so the two agree
- Write in present tense; past or future tense signals a stale document
- Write as little as needed; a document that drifts is worse than none
- Remove redundant, inconsistent or outdated text promptly (SHOULD), in
  its own change when it is unrelated to the one that finds it
