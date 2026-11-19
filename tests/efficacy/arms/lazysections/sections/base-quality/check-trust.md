# Base — Quality Attributes

How code is designed, kept clean, swept and checked.

## Check trust

- Confirm a validation, scraping, migration or codemod tool is correct
  before acting on its output in bulk
- Treat a physically implausible output as a tool defect: fix it, re-run,
  then apply
- Cross-check an independent source before overwriting stored data with a
  source that looks wrong
- Never weaken the rule behind a check to make it green or quiet
