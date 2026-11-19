# Base — Git Conventions

How changes are committed, reviewed, verified and merged.

## CI evidence

- Read the CI run for the push before describing a change as good; a local
  run is evidence about one platform
- Treat a pull request with no registered check as not passed: wait until
  one registers, then watch every check to completion
- Never merge while a check is failing, cancelled or not yet registered
- Re-run a verification a pull request body claims once the base has moved
  since it was written; above all a proof of absence
- Read a new or changed workflow's first run in its real environment, and
  require a verdict from it before trusting the workflow
