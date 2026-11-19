# Backend — HTTP Conventions

## Admin processes

- Run one-off tasks (migrations, data fixes, REPL sessions) with the
  application's code, config and dependencies (MUST)
- Commit admin scripts to the repository; never run them as ad-hoc shell
  commands (MUST)
- Prefer idempotent scripts — safe to re-run
- Never run an admin task against production without a tested rollback plan
