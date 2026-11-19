# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Principles

- Keep one authoritative representation of each piece of knowledge (DRY);
  the third copy is a bug
- Extract shared logic only where substantial logic repeats; a few similar
  lines inline are not duplication
- Choose the simplest solution a stated requirement justifies (KISS)
- Build what is needed now, never for a hypothetical requirement (YAGNI)
- Record beside every deferral the concrete condition that reopens it
- Delete a path once evidence shows it unreachable or obsolete: no caller,
  or a retired input
- Treat a real-data probe that never reaches a path as a lead, not proof;
  a sample misses rare cases
