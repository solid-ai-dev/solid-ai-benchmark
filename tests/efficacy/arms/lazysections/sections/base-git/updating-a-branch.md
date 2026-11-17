# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## Updating a branch

- Never force-push, including with `--force-with-lease` (MUST NOT)
- Bring a branch up to date by merging the base into it; never rebase and
  force-push

### Regenerating after a merge

- Regenerate derived artifacts and re-run the staleness comparison after
  every such merge, and stage what they produce
