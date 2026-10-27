---
name: write-docs
description: Writing or restructuring documentation, a decision record or a diagram
---

# Writing or restructuring documentation, a decision record or a diagram

## Standard documents

- Carry these three in every project (MUST); their layout is the project's
  own, and `templates/core/agents.md` offers a default for the agent files

| File | Purpose |
| --- | --- |
| `README.md` | What the project is and how to use it |
| `AGENTS.md` | Agent context and project rules, for any agent |
| `CLAUDE.md` | Agent context and project rules, for Claude Code |

## Diagrams and assets

- Commit every editable source beside its rendered output; never commit a
  binary-only diagram
- Give a committed artefact one authority: commit its editable source or
  its generator, never both
- Never use proprietary formats such as Word, Illustrator or Affinity
  Designer
- Split a diagram that serves two purposes into two

## Docs as code

- Keep technical documentation in the repository, in Markdown, under the
  same review as code
