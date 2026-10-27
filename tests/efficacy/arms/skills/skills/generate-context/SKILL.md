---
name: generate-context
description: Generating or regenerating the project's agent context files
---

# Generating or regenerating the project's agent context files

## Adopting shared rules

- Treat template rules as candidates; the project chooses what it adopts
- Adopt a rule when it addresses a named local defect, a requirement or a
  credible material risk; a preventive security control needs no incident
- Never let a template update create compliance work, tickets or decision
  records by itself (MUST NOT); a newer tag alone is no reason to move the
  pin
- Record a declined candidate in at most one line, if at all (MAY), in the
  existing pull request or discussion
- Keep adopted rules in force until the project changes them, and keep the
  operative selection in the project's context file
- Inline this adoption boundary in a reference or hybrid context file
  (MUST), so a new upstream MUST cannot widen the adopted set
- Assess security fixes in tools the project runs promptly; review new
  conventions when a project need warrants it

## Output file by agent

| Agent | Context file |
| --- | --- |
| Claude Code | `CLAUDE.md` |
| Cursor | `.cursor/rules/project.mdc` |
| GitHub Copilot | `.github/copilot-instructions.md` |
| OpenAI Codex CLI | `AGENTS.md` |
| Generic or other | `AGENTS.md` |
