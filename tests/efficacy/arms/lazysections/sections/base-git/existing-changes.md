# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## Existing changes

- Inspect the working tree and the index before starting a task
- Never discard, reset, stash or overwrite a change the task did not make
  (MUST NOT)
- Never clear the tree to obtain a clean test baseline; ask the owner
- Stage only the changes the task made: a whole file only when it held no
  prior change, otherwise only the task's hunks; never stage everything
- Read the staged diff before committing; it holds only the task's changes
- Stop and ask when a task change and a prior change share a hunk
- Report a pre-existing change that blocks the task rather than removing it
