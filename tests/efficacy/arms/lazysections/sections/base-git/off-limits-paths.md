# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## Off-limits paths

- Declare an Off-limits section in the project's context file, listing the
  paths that MUST NOT change without explicit approval (MUST)
- Offer this default set for the project to cut down: auth and session
  code, payment code, migrations, `.env*` and secrets, and CI/CD
  workflows
- Propose a change inside an off-limits path before making it, with a
  rollback strategy and the tests that would catch a regression (MUST)
- Treat an approval as covering the proposed plan, never the whole path
- Apply the restriction to executable content: steps, commands, flags,
  permissions, triggers, pins
- Treat a diff confined to prose as ordinary work
- Treat a comment a tool reads as executable, such as a linter disable or
  a coverage pragma
- Classify by the diff: it is prose only when removing every comment line
  leaves nothing
- Name an off-limits path at the top of the change's summary whenever the
  diff touches one, proposal or not (MUST)

```bash
pre-commit run report-off-limits-paths --hook-stage manual --all-files --verbose
```

- Require the paths-declared and files-changed counts above zero
- Pass each path as a `--path` argument, kept beside the declared list;
  `--base` defaults to `origin/main`
- State every off-limits line in the summary as an escalation; it is not
  a failure
- Run it after committing: at or behind the base with a clean tree it
  prints `not applicable`, and a base that does not resolve fails it
