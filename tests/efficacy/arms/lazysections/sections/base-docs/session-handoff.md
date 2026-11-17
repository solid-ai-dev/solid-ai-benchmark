# Base — Documentation

Which documents a project keeps, and how they stay true.

## Session handoff

- At a natural boundary a project MAY keep a short handoff file in the
  repository: a "Now and next" section rewritten each session, and lasting
  facts only where no authoritative source (code, history, ADRs, issues)
  holds them
- Treat a missing handoff file as no defect, and a boundary as no reason
  to end the session
- Where the project keeps one:
  - Name it `HANDOFF.md`, at the repository root, with the sections "Now
    and next" and "Lasting facts"
  - Keep it in the repository, never in an agent tool's own store, so any
    agent reads it
  - Read it when a session starts
  - State in "Now and next" where the work stands and the next step
  - Point at the decision record or issue that holds a decision or a plan;
    never copy it
  - Prune a lasting fact once it stops being true
  - Keep it out of the agent context files, which hold no progress log
