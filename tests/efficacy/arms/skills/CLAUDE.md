# tariff

A pricing and invoicing web application: a product catalog, discount rules, tax jurisdictions, customers and invoices.

- Model: root and skills
- Owner: Imbra Ltd
- Repository: this repository

## Commands

Python 3.12, Flask 3, Jinja, HTMX and SQLite, managed with uv; check with ruff, mypy strict and pytest. It runs locally; there is no deployment target.

## Answers

- Who approves a change: not stated in the brief
- How work is tracked: not stated in the brief
- What a release is: not stated in the brief; the application runs locally

## Rules

Built by `resolve_chain.py --emit`; change the templates, not the rules below.

The adopted rules that apply on every task.

### Base — Quality Attributes

How code is designed, kept clean, swept and checked.

#### Principles

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

#### Architecture

- Compute derived counts and statistics from the data; never hardcode them
- Remove unused modules, assets and data files promptly

#### Naming

- Name a function with a verb, a class or module with a noun, and a boolean
  with `is`, `has` or `can`
- Rename a name that needs a comment to explain it
- Use the same name for the same concept in every module
- Name a public enum member, CLI flag or result discriminator for the
  capability it offers, never the library behind it: `Transport.HEADED`,
  not `Transport.PLAYWRIGHT` (MUST). A private symbol MAY name its library

#### Complexity

- Keep cognitive complexity at or under 15 per function
- Nest at most three levels; use guard clauses and early returns
- Replace a boolean flag that selects behaviour with an enum or two named
  functions
- Name every magic number and magic string as a constant
- Size a tuned threshold, such as a latency alert, from its measured
  distribution (p95, p99, maximum legitimate); name the data source in
  the constant's docstring
- Take a limit a specification fixes, such as a protocol's maximum
  message size, from that specification and name it, never from an
  observed percentile

#### Dependencies

- Keep the module graph acyclic; break a cycle with a third module or an
  interface, never with a divergent local copy
- Keep coupling shallow: a change inside one module MUST NOT require
  changes in unrelated modules
- Talk only to direct dependencies, and keep together what changes together
  (SHOULD)
- Reach a heavy, native or platform-limited dependency through one module
  that owns its import and names the install command when it is missing

#### Errors

- Validate input at boundaries and fail at once on invalid state
- Read a value from its source-of-truth field, and raise when the field is
  missing; never fall back to a value derived from a slug, name or hash
- Bound every wait on another thread, process or connection, report why it
  gave up, and check the worker's liveness as well as the deadline
- Never break a public catch contract: a raise callers catch by a built-in
  type keeps that type
- Add an error type only where a caller could act differently
- Never let a caller-side input filter stand in for a precondition: widen
  the filter, or assert the precondition inside the function

#### Module structure

- Keep a CLI a thin layer over a library that holds its logic
- Keep constants beside the functions that use them

#### Library output

- Never write to the host's standard output or error from a library, and
  never configure logging beyond the library's own logger (MUST)
- Make the library's logger injectable, falling back to its module logger
- Check the silence in a fresh process; a test runner's handler hides the
  default

#### Encoding and line endings

- Encode every committed text file in UTF-8, with LF line endings (MUST)
- Keep identifiers ASCII (MUST); comments, docstrings, strings and
  documentation carry no charset restriction

```bash
pre-commit run check-ascii-identifiers --all-files --verbose
```

Pass condition: the inspected count is above zero and
`non-ASCII identifiers` is zero. The hook reads Python; `not applicable`
means the project tracks none.

- Set a program's output encoding explicitly, and pin its line ending where
  another program reads the output
- Commit a `.gitattributes` with `* text=auto`, adding `eol=lf` for hard
  LF
- Mark a text path exempt from LF with `-text` in `.gitattributes`
- Check line endings on every tracked file, whatever its name, exempting a
  `-text` file; count a file Git files `i/-text` as binary only when it
  holds a NUL byte
- Let a linter format on save, and keep manual style rules to a minimum
  (SHOULD)

```bash
seen=0 exempt=0 binary=0 bad=()
while IFS= read -r -d '' rec; do
  info=${rec%%$'\t'*} path=${rec#*$'\t'} seen=$((seen + 1))
  case " ${info#*attr/} " in *" -text "*) exempt=$((exempt + 1)); continue ;; esac
  case $info in "i/ "* | i/lf* | i/none*) continue ;; esac
  nuls=$(git cat-file blob ":0:$path" | tr -dc '\000' | wc -c)
  [[ $info == i/-text* && $nuls -gt 0 ]] && binary=$((binary + 1)) && continue
  bad+=("$path")
done < <(git ls-files -z --eol)
printf 'files inspected: %d\nexempt by -text: %d\n' "$seen" "$exempt"
printf 'binary by content: %d\nfiles not filed i/lf: %d\n' "$binary" "${#bad[@]}"
for f in "${bad[@]}"; do echo "  $f"; done
[ "$seen" -gt 0 ] && [ "${#bad[@]}" -eq 0 ]
```

Pass condition: exit zero, given only when the inspected count is above
zero and the not-`i/lf` count is zero. An empty `i/none` file passes; a
stray carriage return, filed `i/-text` with no NUL byte, still fails.

#### Comments

- Prefer code that needs no comment; comment only intent the code cannot
  express
- Re-verify a comment explaining why something is safe whenever the code
  is next read
- Never cite a ticket, PR or ADR number in a code comment, docstring or
  commented configuration; state the substance (MUST NOT)
- Name a source (author, year, method) where non-obvious or scientific
  logic needs one (MAY)

#### Debug code

- Commit no debug output (`print()`, `console.log()`) and no hardcoded
  breakpoint
- Delete commented-out code
- Gate debug tooling behind a flag or environment variable, off by default

##### Probe scripts

- Write a probe, a throwaway script that measures data or behaviour,
  rather than guess
- Delete a probe before the commit that uses its findings (MUST)
- Keep findings in source comments, decision records or docs, never in
  the probe

#### Rejected mechanisms

- Grep the codebase for a construct a comment records as not working,
  before moving on: `grep -rn '<the construct>' <source root>`
- Read every hit as a suspected instance of the same defect, not a style
  question

#### Destructive operations

- Delete, truncate, overwrite or kill only what the operation can prove it
  created: process ancestry, a key scheme, a filename prefix, a marker file
  or an ownership tag; never a path, a configuration value or a file
  extension
- Find nothing where the proof is unavailable: no error, no prompt, no
  guess
- Validate the input as well: reject an empty configuration value, and
  match the key scheme
- Apply this to every reaper: a cache clean, an output-directory clear, a
  log rotation, a temp-file sweep

```
match on ".html"              wrong directory -> README.html deleted
match on "[0-9a-f]{16}.html"  wrong directory -> nothing matched
```

#### Check trust

- Confirm a validation, scraping, migration or codemod tool is correct
  before acting on its output in bulk
- Treat a physically implausible output as a tool defect: fix it, re-run,
  then apply
- Cross-check an independent source before overwriting stored data with a
  source that looks wrong
- Never weaken the rule behind a check to make it green or quiet

#### Enforcement

- Enforce these conventions through the gates: editor, pre-commit, CI
- Merge to `main` only with passing tests

#### Completion

Adding pagination, for example, ends with bounded results, their tests and
an updated contract. It does not end with a rewrite of the service layer.

- Finish a task when the requested behaviour works through the entry point
  its user or caller reaches, and the checks that prove it pass
- Report a check that could not run as not run, never as a pass
- Add an abstraction, infrastructure or a process step only when a stated
  requirement, a demonstrated defect or a material risk justifies it
- Report a problem found outside the task, or file it as its own task,
  rather than fixing it in the same change (SHOULD)

### Base — Git Conventions

How changes are committed, reviewed, verified and merged.

#### Commits

- Commit under your full name and one consistent email; never change
  identity mid-project
- Work on a branch; never commit directly to `main`
- Never commit build output, dependency directories or secrets
- Commit a generated file only when the project tracks it on purpose, under
  the regeneration rules below
- Treat every repository as public: no secret, credential or sensitive
  value in source or history
- Keep a `.gitignore` (MUST) covering dependencies, build output, secrets,
  editor state, OS files and coverage output
- Commit lockfiles (MUST)

#### Existing changes

- Inspect the working tree and the index before starting a task
- Never discard, reset, stash or overwrite a change the task did not make
  (MUST NOT)
- Never clear the tree to obtain a clean test baseline; ask the owner
- Stage only the changes the task made: a whole file only when it held no
  prior change, otherwise only the task's hunks; never stage everything
- Read the staged diff before committing; it holds only the task's changes
- Stop and ask when a task change and a prior change share a hunk
- Report a pre-existing change that blocks the task rather than removing it

#### Pull requests

- Keep a pull request to one concern (SHOULD)
- Test locally before committing
- Review the diff against the base before merging, in the order security,
  correctness, clarity, conventions
- Merge only after the review passes and CI is green

#### CI evidence

- Read the CI run for the push before describing a change as good; a local
  run is evidence about one platform
- Treat a pull request with no registered check as not passed: wait until
  one registers, then watch every check to completion
- Never merge while a check is failing, cancelled or not yet registered
- Re-run a verification a pull request body claims once the base has moved
  since it was written; above all a proof of absence
- Read a new or changed workflow's first run in its real environment, and
  require a verdict from it before trusting the workflow

#### Updating a branch

- Never force-push, including with `--force-with-lease` (MUST NOT)
- Bring a branch up to date by merging the base into it; never rebase and
  force-push

#### Off-limits paths

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

### Base — Documentation

Which documents a project keeps, and how they stay true.

#### Rule language

- Read a plain imperative ("Use X", "Never Y") as MUST or MUST NOT
- Add an RFC 2119 key word where strength matters: SHOULD or MAY for a
  weaker rule, MUST to stress an absolute one

| Word | Meaning |
| --- | --- |
| MUST | Absolute requirement; a deviation needs an approver's sign-off |
| MUST NOT | Absolute prohibition; a deviation needs an approver's sign-off |
| SHOULD | Recommended; a deviation needs a justification |
| SHOULD NOT | Not recommended; may be ignored with a justification |
| MAY | Optional; the developer decides |

#### Single source of truth

- Keep the project structure in `README.md` only, and reference it
  elsewhere
- Keep the agent files' project-structure section a pointer to the README
  plus placement rules, never a second directory tree
- Never reference a file, component or service that does not exist

#### Upkeep

- Update every document a change touches, in the same commit:
  - `CLAUDE.md` when architecture, stack, design rules or conventions change
  - `README.md` when structure, stack or setup steps change
  - `AGENTS.md` whenever `CLAUDE.md` changes, so the two agree
- Write in present tense; past or future tense signals a stale document
- Write as little as needed; a document that drifts is worse than none
- Remove redundant, inconsistent or outdated text promptly (SHOULD), in
  its own change when it is unrelated to the one that finds it

#### Disagreements

- Establish which is wrong before changing a document or the system it
  contradicts
- Check whether the rule is inherited: a document generated from a template
  can drift while the system still matches the template
- Never act on the document alone when the observed state is defensible
  (MUST NOT)
- Read the document, observe the system, find the rule that governs both,
  then fix whichever one that rule does not support

#### Line width

- Wrap Markdown at the width the project declares, never at one written
  into a rule

#### Writing style

- Use bold and italic sparingly: never bold inline code or a whole
  sentence, and use at most one short bold label per list item
- Code-format only identifiers: file names, paths, environment variables
- Summarise a method, constant or flag in prose and link to its source;
  never transcribe its definition
- Put a command the reader runs in a fenced block, exactly as typed
- Point at a self-documenting source, such as `--help`, a generated schema
  or generated API docs, rather than restating it; document only what it
  cannot state itself
- State a count about the tree only inside a block a generator writes and
  gates, or in a dated record; elsewhere name the thing without counting it

#### Cold readers

- State the symptom before the mechanism
- Expand a term taken from the code at its first use, or avoid it
- Show a real example rather than describe one
- Keep to one idea per sentence
- Separate how bad it is now from how bad it becomes
- Apply these to every ticket, pull request and defect record an agent
  writes; the record outlives the session

### Base — Testing

What to test, how to keep tests honest, and how to prove a change.

#### Test types

Classify a test by the boundary it crosses, not by who runs it or which
tool drives it.

| Type | Boundary crossed | Focus |
| --- | --- | --- |
| Unit | None | One function or class in isolation |
| Integration | Process or component | Interaction with a real dependency |
| System | System | The product against its requirements |
| Regression | Any, reusing existing tests | Unintended change |
| Exploratory | Any, unscripted | Unexpected behaviour |

- Double only what a unit test would cross a boundary to reach: I/O, time,
  randomness, another process
- Keep deterministic in-process collaborators real
- Use the real dependency for the boundary an integration test covers; you
  MAY double the unrelated ones
- Add a regression test for every fixed defect (SHOULD)

#### Coverage

- Cover every happy path the functional requirements define
- Cover negative inputs and edge cases as well (SHOULD)
- Cover each dependency's faults at every tier: unavailable, malformed
  response, timeout, degraded operation (SHOULD)
- Meet the project's coverage threshold for new code before merging
- Never let coverage regress between releases
- Run every unit test from CI, with no human step
- Name a test so the name alone states the unit, the input and the expected
  outcome (SHOULD)
- Run a unit that reads a structured external artifact against real
  production data once before calling its suite complete, and add a
  regression test for each gap it shows

#### Testability

- Keep business logic in pure functions, and push I/O to thin adapters at
  the edges (SHOULD)
- Inject dependencies rather than construct them in the code under test
  (SHOULD)
- Split a function that needs more than two mocks to test (SHOULD)
- Treat code that is hard to test as a design problem

#### Isolation

- Test behaviour, not implementation details
- Set or clear every environment variable a test depends on, in that test;
  never rely on the ambient process state
- Treat a test that passes or fails by run order as an isolation bug
- Wait on a condition with a deadline, never a fixed sleep
- Never enumerate, signal or terminate a process the test did not start
  (MUST NOT)
- Never mutate host state outside the working directory: the process
  table, system services, the registry, the user's applications (MUST NOT)
- Stub every seam through which the code under test reaches a host
  resource the test does not own, even when its subject is already faked
- Keep the dependency an integration test covers real, isolated to that
  test, such as a throwaway container or a temporary database
- Investigate a failing test before anything else; never skip or suppress
  one without a documented reason
- Check the test's own logic first when it behaves unexpectedly

#### External definitions

- Assert at least one case against a fixed vector the specification
  publishes, wherever a format is defined outside the codebase (MUST)
- Never take a round trip through your own encoder and decoder as proof
  that either is correct
- Assert what an object does, not the type the runtime reports for it
- Assert that a misuse fails, and which error only where the interface
  declares one
- Never assert an exception class the runtime raises on its own

#### Guard use

- Assert that the code under test takes a guard, not only that the guard
  works, where the guard exists for other code to take (MUST)
- Prefer a behavioural assertion, such as "a stopped component does no
  work"
- Otherwise wrap the real guard in a recorder that logs entry and exit, and
  assert the order of the work against it
- Pair every "does nothing" assertion with its "does something" control
- Sweep the module for sibling guards when one proves inert

```bash
MODULE=<module-under-review>
FIELD=<guard-field-name>
echo "references to $FIELD in $MODULE: $(grep -c "$FIELD" "$MODULE" || true)"
grep -n "$FIELD" "$MODULE" || true
```

Pass condition: the count is at least two and the listed lines include a
consumer. A count of one is the assignment alone: the guard is built and
never consulted.

#### Provenance

- Assert the source of a value, not the value, where a fix changes where it
  comes from
- For such a fix, inject a source that yields a different value, and assert
  the code overrides it
- Treat a new test that passes against the unfixed code as aimed at the
  wrong property, not as proof the fix was unnecessary
- Substitute at the name the module under test reads, not on the module
  that defines the type

#### Thresholds

- State, beside every threshold assertion, the property it gates, the
  conditions it was calibrated under and what to do when an improvement
  moves it
- Name the property in the failure message, not only the observed value

#### Empty results

##### Reach

- Assert that a test expecting no violations reached its inputs: compare
  the files it discovered against what its roots should cover (MUST)
- Fail on that comparison; never print a count for a reader to notice
- Report every occurrence, not the first per line or per file
- Fail an "every item holds" assertion when the set shrinks unexpectedly
- Give the coverage assertion its own test and its own message (SHOULD)
- Assert that each item declares its own value where a permissive default
  exists; prefer a default that is not a legal value

##### Floors

- Assert a known floor, not mere non-emptiness
- Size the floor from a measurement, and state the derivation beside the
  constant
- Use the measured count for an append-only corpus, and a stated margin
  below it for one that churns

#### Call sites

- Exercise every call site of a changed shared path, not only the reported
  case (MUST)
- Run the ground-truth comparison on every entity that uses the path
- Re-run every consumer that derives a committed artifact from the changed
  surface, and keep that list beside the surface

#### Real data

- Drive a diagnostic view through the production entry point behind a
  flag, never a separate command with its own setup
- Run the real pipeline on the input a fix targets, and diff its output
  against the expected values
- Never take passing unit tests, suites and staleness checks as proof that
  the fix fired

#### Rendered output

- Verify a visual change on its rendered output, read headless off the
  pixels or the resolved DOM, never off the source (MUST)
- Capture the render before the change as well as after it (SHOULD)
- Confirm the build is fresh before re-editing a change that still looks
  wrong

#### Drift guards

- Give every fact stored in two places a test that fails when the copies
  diverge, such as:
  - a documented limit and its constant
  - live routes and the API contract
  - the runtime version and the package metadata
  - an export list and the module's bindings
- Introspect the live artifact rather than hardcode the expected value
  (SHOULD)
- Assert one direction: the derived copy matches the source of truth

### Base — Peer Review

How a change is reviewed, and how a finding is proven before it is reported.

#### Principle

- Peer-review all code before merging (MUST)
- Hold the reviewer accountable for what merges, and the developer for what
  they write
- Put reviews ahead of your own development; a blocked review blocks the
  team

#### MUST checklist

- [ ] No credential, token or sensitive value appears in a committed file
- [ ] Every failure path is handled; no silent catch, no swallowed exception
- [ ] Every new dependency carries a licence the project's policy allows
- [ ] Significant logic and architectural decisions are documented
- [ ] Existing documentation matches the code after the change
- [ ] Every changed section was re-read whole, not only the changed line
- [ ] Every claim changed text makes about itself, such as a count or "all",
      was checked by counting with a tool
- [ ] Input from outside the process, such as a URL parameter, is
      validated as untrusted before it is destructured, indexed or used as
      a key
- [ ] A refactor preserves behaviour on every path: each case, direction and
      mode, including null handling, sort order and boundary values

#### SHOULD checklist

- [ ] Each non-trivial function has a unit test per relevant variant
- [ ] Coverage does not fall
- [ ] Lint errors and warnings do not rise
- [ ] Each third-party dependency is necessary, understood and maintained
- [ ] No new abstraction without two call sites, and no new dependency
      without a documented reason

#### CI signals

- Read the log of a red check before calling the pull request green or red
- Separate an infrastructure failure (the check could not run) from a diff
  failure (it ran and found something), and say which in the merge decision
- File a separate task for an infrastructure failure, and note it in the
  merge decision
- Never retry until green without saying so (MUST NOT)
- Never bypass a failing check by skipping hooks or by an admin merge
  unless the maintainer explicitly accepts the risk (MUST NOT)

#### Structure audit

- Run a structure audit, which checks project completeness rather than
  changed files, after a new project setup, a framework or stack migration,
  a new major layer, and before a release milestone
- Verify every MUST in the base templates (the standard documents, a
  `.gitignore`) and in the project's layer and stack templates
- Verify each sub-clause of a MUST separately; a rule requiring examples and
  their output is two checks

#### Planning

- Produce a plan before implementing a feature or a non-trivial change: the
  files, the signatures or outline, the edge cases, and the assumptions
- Never write implementation code until the plan is approved (MUST NOT)
- Skip the plan for one-line fixes, typos, changes the requester has
  specified in full, and work whose approach the requester already approved
- Stay inside the approved plan; when a constraint invalidates it, stop and
  re-surface the options

#### Verifying a finding

- Label a finding unverified until it is demonstrated (MUST)

##### From an agent

- Check an agent's finding against the file, commit or document that
  settles it before acting on it or repeating it
- Distinguish a verified negative from a failed lookup, and say which
- Count a finding several agents agree on as one finding
- Correct a finding you passed on that proves wrong, and name what the
  check showed
- Reconcile a finding with a verified record it contradicts before
  changing anything: confirm both read the same artifact, prefer the more
  specific evidence, and record the outcome
- Record a reversal of a documented decision, with its reason, in the
  artifact that documented it
- Give a verifying agent the existing record and ask it to reconcile, not
  re-derive
- Never delete a record because a check "could not confirm" it (MUST NOT)

#### Deviations

- Explain a deviation from a SHOULD rule in the pull request
- Land a deviation from a MUST or MUST NOT rule only with a designated
  approver's sign-off and its reason recorded in the pull request (MUST)
- Never waive a MUST or MUST NOT rule yourself; stop and ask the approver

### Backend — HTTP Conventions

#### Port binding

- Read the port from an environment variable such as `PORT`; never
  hardcode it (MUST)
- Use a well-known default in development, and the port the platform
  assigns in production

#### Process lifecycle

- Start fast — keep initialisation short (MUST)
- Shut down gracefully on a stop signal (`SIGTERM`) in order: stop
  accepting new requests, let in-flight ones finish until the drain
  deadline, cancel what remains, wait up to a bounded cancellation period,
  release resources, then exit (MUST)
- Release resources when the cancellation period ends, even when some
  cancelled work is still running
- Force-exit when the whole shutdown, from draining to releasing
  resources, passes its hard deadline (MUST)
- Set the drain deadline plus the cancellation period below the hard
  deadline, leaving time to release resources
- Fit the hard deadline inside the grace period the platform allows
  before it kills the process
- Recover cleanly when a process is killed without warning (`SIGKILL`,
  power loss) (MUST)
- Keep no state in process memory that a restart cannot rebuild; put it in
  an external store, so any instance can be replaced

#### Admin processes

- Run one-off tasks (migrations, data fixes, REPL sessions) with the
  application's code, config and dependencies (MUST)
- Commit admin scripts to the repository; never run them as ad-hoc shell
  commands (MUST)
- Prefer idempotent scripts — safe to re-run
- Never run an admin task against production without a tested rollback plan

#### Handler design

- Keep handlers thin: decode request → call service → encode response
- Never put business logic in a handler; delegate it to a service layer
- Validate all incoming request data before processing
- Set a timeout on every outbound call (HTTP clients, database queries)

#### Query parameters

- Parse a typed query parameter explicitly so you can distinguish three
  states: absent (use the default), present-and-valid (use it), and
  present-but-invalid (raise 400)
- Never rely on a parsing helper that returns the default on a malformed
  value; it silently turns a client error into a successful default-valued
  200

#### Request headers

- Read every header name case-insensitively, as RFC 9110 defines them
  (MUST)
- Avoid the `X-` prefix on custom headers (SHOULD NOT); RFC 6648
  deprecated this convention
- Use a vendor or application-specific prefix on a custom header instead
  (SHOULD)

#### HTTP methods

- Never let a GET or HEAD request change resource state; RFC 9110 defines
  both as safe
- Make every PUT and DELETE idempotent, as RFC 9110 defines them

#### Resource representation

- Make a text payload's field types conform to the relevant ISO standard
  (MUST):
  - Date and time values: ISO 8601
  - Language codes: ISO 639
  - Country codes: ISO 3166-1 alpha-2
  - Currency codes: ISO 4217
- Serialise any JSON integer outside ±(2^53 − 1), -9007199254740991 to
  9007199254740991, as a string (MUST); JavaScript cannot represent one
  beyond that range precisely, in either direction
- Reject non-finite values in an endpoint that serialises computed floats
  to JSON (MUST); `NaN`/`Infinity` are not valid RFC 8259 JSON
- Configure the JSON encoder to reject them, so it fails loud at the
  serialisation boundary (a 500) instead of emitting a bare `NaN` token
  that strict parsers reject
- Represent an undefined computed float in JSON as `null`, normalised
  before serialisation
- Document such a JSON field as nullable in the contract
- Return only the fields the caller needs (MUST); never pad a payload
  with fields that are not consumed

#### Error responses

- Use consistent error response shape across all endpoints
- Never return stack traces, internal paths, or implementation details to the
  client
- Use 4xx for client errors, 5xx for server errors — never use 200 for errors
- Carry a gRPC or GraphQL error the way its protocol defines instead: a
  gRPC status code over HTTP 200, a GraphQL `errors` array under
  GraphQL-over-HTTP's status rules
- Set an explicit `Content-Type` on every JSON response

#### Authentication and authorisation

- Serve all API traffic over HTTPS outside local development (MUST);
  plain HTTP is not acceptable in staging or production
- Give access tokens a short, finite lifetime (MUST)
- Enforce both authentication and authorisation on every external API
  endpoint (MUST), except a public endpoint the project declares
- Make a public endpoint only a declared read, or a declared write that
  must run before the caller has an identity, such as a sign-up, sign-in,
  account recovery or a contact form
- Declare each public endpoint in the route definition and the API
  contract, in the change that makes it public; a public catalogue stays
  public, the account records beside it stay protected
- Require authentication at minimum on internal API endpoints (SHOULD)
- Never make any other write endpoint accessible without a valid
  authenticated identity (MUST NOT)
- Apply authentication and authorisation before any business logic runs
- Rate-limit each public endpoint per client — never expose an unbounded
  write operation
- Return no account data from a public write
- Rate-limit a sign-in or recovery endpoint per account and per client
- Answer a sign-up or recovery request the same way, in content and
  timing, whether or not the account exists
- Make each recovery token single-use, short-lived and bound to one account

### Backend — API Design

#### Statelessness
- Keep APIs stateless (MUST): store no client context on the server
  between requests
- Carry everything a request needs in the request itself (MUST)
- Keep session state in the client or a dedicated session store, never in
  the API service

### Base — Application Security

Apply these cross-cutting security rules to application code in every
project, regardless of language or framework.

The sections below cover the OWASP Top 10 categories: injection, broken
access control, cryptographic failures, insecure design, security
misconfiguration, vulnerable components, identification and authentication
failures, software and data integrity failures, logging and monitoring
failures, and server-side request forgery.

#### Input validation

- Validate all external input at the system boundary — the first point
  where untrusted data enters the application
- Validate complex input with a schema validation library; never
  hand-write it
- Use an allowlist, not a blocklist — define what is valid, reject
  everything else
- Reject invalid input with a clear error; do not silently coerce or strip
  fields
- Do not repeat the boundary's schema validation in inner layers; a
  function still asserts the preconditions it relies on

#### Output encoding (XSS)

- Encode dynamic data for its rendering context at the point of output:
  HTML, URL, JavaScript, SQL, shell
- Encode on output, not on input — store the raw value, encode when
  rendering
- Use the encoding the framework or template engine provides
- Never insert user-supplied data through a raw-HTML path that bypasses
  auto-escaping
- Apply the encoding that matches each context; HTML encoding does not
  prevent URL injection

#### Injection prevention

- Use parameterized queries for all database access; never concatenate user
  input into SQL strings
- Escape shell arguments when invoking external commands, or use API
  alternatives that do not invoke a shell
- Never pass user input to dynamic code execution, such as an `eval`

#### Authentication

- Hash passwords with a modern algorithm: bcrypt, scrypt, or Argon2 — never
  MD5, SHA-1, or plain SHA-256
- Require a minimum password length and reject known-breached passwords;
  never impose composition rules (NIST SP 800-63B)
- Use constant-time comparison for secrets and tokens; timing attacks leak
  information through response time
- Lock accounts or throttle after repeated failed attempts

#### Session management

- Generate session IDs with a cryptographic random generator
- Regenerate the session ID after login; this prevents session fixation
- Set cookie flags: `HttpOnly`, `Secure`, `SameSite=Lax` (or `Strict` for
  sensitive applications)
- Expire sessions after an idle period: 30 minutes for sensitive
  applications, configurable otherwise
- Invalidate sessions on logout; do not rely on cookie expiry alone

#### Cross-site request forgery (CSRF)

- Give every state-changing request a CSRF defence (MUST) when the session
  is authenticated by an ambient credential
- Treat as ambient any credential the browser attaches on its own: a
  cookie, HTTP Basic, or a client certificate
- Use the framework's built-in CSRF middleware; never hand-roll token
  generation or comparison
- Treat `SameSite=Lax` on the session cookie as defence in depth, not the
  defence; it does not cover top-level `POST` navigation on older browsers,
  and a subdomain takeover defeats it
- Prefer the synchroniser token pattern
- Use the signed double-submit cookie where the server holds no session
  state, with the token bound to the session identifier
- Validate the token on every `POST`, `PUT`, `PATCH` and `DELETE`, never on
  `GET`
- Never change state on a `GET` request (MUST NOT)
- Treat an API authenticated only by a bearer token the client attaches
  explicitly as needing no CSRF token; the browser never adds that header
  on its own
- Require a CSRF token on a bearer-token API that also accepts cookie
  authentication

#### Secrets in code

- Never hardcode secrets, API keys, tokens, or credentials in source files
- Keep local secret files out of version control
- Rotate a secret immediately if it is accidentally committed; removing it
  from git history is not sufficient, since the secret is compromised

#### Transport security

- Use HTTPS everywhere, with no exceptions for production traffic
- Enable HSTS on all production sites (MUST), with `includeSubDomains` and
  a minimum `max-age` of one year
- Require TLS 1.2 as the minimum version; disable TLS 1.0 and 1.1
- Use strong cipher suites; disable known-weak ciphers

#### Security headers

- Set security headers on every HTTP response at the reverse proxy or
  middleware level, not per route
- Set these required headers:
  - `Content-Security-Policy` — start strict, relax only what a page needs
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY` (or CSP `frame-ancestors`)
  - `Strict-Transport-Security` (see Transport security)
  - `Referrer-Policy: strict-origin-when-cross-origin`
  - `Permissions-Policy` — disable unused browser APIs
- Map each static asset type to its `Content-Type` in code when enabling
  `nosniff`; the browser then never corrects a wrong one
- Never let MIME resolution depend on the host when `nosniff` is enabled
  (MUST NOT)
- When enabling `nosniff`, verify script and style execution in a real
  browser, not just status codes
- Never use `unsafe-inline` or `unsafe-eval` in CSP without a written
  justification
- Do not expose server version or technology stack in headers; remove
  `X-Powered-By`, `Server` version strings

#### Error handling

- Never expose stack traces, internal paths, or database errors to end
  users; return generic error messages externally
- Log full error details server-side for debugging
- Use consistent error response formats; do not leak internal structure
  through varying error shapes
- Return each error through the protocol's own error signal, never as a
  success
- Do not reveal whether a resource exists via error messages: login errors
  should say "invalid credentials", not "user not found" vs "wrong password"

#### Logging

- Never log secrets, tokens or passwords
- Never log personally identifiable information (PII), except the client
  IP in the security log below
- Sanitize log output; user-supplied data in logs can enable log injection
  attacks
- Log security-relevant events: authentication attempts, access denials,
  privilege changes, configuration changes
- Include enough context for investigation: timestamp, an opaque user ID,
  action, result; never a name, email or submitted username
- Record the client IP only in the security log, access-restricted and
  purged at the end of its retention period
- Retain security logs for a defined period; compliance may require 90
  days to 7 years

#### CORS

- Restrict `Access-Control-Allow-Origin` to specific known origins; never
  use `*` for authenticated endpoints
- Do not reflect the `Origin` header back as `Access-Control-Allow-Origin`
  without validation
- Restrict allowed methods and headers to what the API actually needs

#### Deserialization and data integrity

- Never deserialize untrusted data with a format that can instantiate
  arbitrary types; use a data-only format such as JSON
- Validate the structure and types of deserialized data before use; treat
  it as untrusted input
- Verify integrity of downloaded artifacts, updates, and dependencies; use
  checksums or digital signatures
- Pin dependency versions and verify checksums in lockfiles; do not trust
  upstream registries blindly
- Use pinned, verified steps and images in CI/CD pipelines (MUST)
- Never pull `latest` tags in production CI/CD pipelines

#### Server-Side Request Forgery (SSRF)

- Never pass user-supplied URLs directly to server-side HTTP clients;
  validate and sanitize first
- Allowlist permitted destination hosts and schemes; reject anything not
  on the list
- Block a request whose resolved address is not public, in IPv4 and IPv6
  alike: loopback, private, link-local, unique-local, shared, unspecified,
  multicast and reserved ranges
- Unwrap an IPv4-mapped IPv6 address (`::ffff:127.0.0.1`) to its IPv4
  form before classifying it
- Classify with an address library, never a hand-kept CIDR list
- Use the standard library's address module where the runtime has one,
  and a maintained external library where it has none
- Test each excluded category by its own predicate; a library's single
  "is public" test can still admit multicast
- Resolve the hostname once, validate the IP, and connect only to that
  address; a client that resolves the name again can be rebound by DNS
- Keep TLS verifying the certificate against the original hostname when
  the connection is pinned to the validated address
- Disable HTTP redirects in server-side HTTP clients, or resolve and
  validate each redirect's destination the same way
- Limit response size and timeout for outbound requests to prevent
  resource exhaustion

#### File uploads

- Validate file type by content (magic bytes), not by extension or MIME
  type; both are trivially spoofed
- Enforce maximum file size at the boundary
- Store uploads outside the web root; never serve user uploads from the
  same domain without sanitization
- Generate random filenames; do not use the original filename (path
  traversal risk)
- Scan uploaded files for malware if the application serves them to other
  users

#### Agent secrets handling

- Never read, print, or cat files that may contain secrets (MUST NOT):
  `.env`, `credentials.json`, `*-key*`, `*.pem`, `*.key`,
  `serviceaccount.json`, `secrets.yaml`
- Never echo, log, or display environment variable values (MUST NOT)
- Check a variable's presence by its exact name without printing its value,
  and treat a set but empty variable as absent
- Never include secret values in commit messages, PR descriptions, or
  conversation output (MUST NOT)
- Warn the user (MUST) before committing files that commonly contain
  secrets (`.env`, `credentials.json`, private keys)
- Verify a secret's presence by a match count or an existence check,
  never by printing it
- Flag a secret exposed in a session to the user immediately: name the
  exposed secret, recommend immediate rotation, and note that session
  history may be cached or logged

### Backend — Authentication and Authorization

Rules for identity verification (authn) and access control (authz).
Applies to any backend service that has protected resources.
Extends `security/security.md`, "Authentication" (`security-authn`) and
"Session management" (`security-sessions`), with backend-specific depth.

#### General principles

- Keep authentication (who are you?) and authorization (what can you do?)
  in separate layers; they are separate concerns
- Never implement your own cryptographic primitives — use well-audited libraries
- Fail closed: deny access by default; grant explicitly
- Centralise auth logic; never scatter permission checks across route handlers

#### Authentication

- Prefer delegating authentication to an identity provider (IdP) over
  rolling your own
- Expire an access token within 15 minutes when the service issues tokens
  itself
- Issue refresh tokens only to user sessions, such as a browser or mobile
  client; rotate each on use and expire it within 7 days
- Never issue a refresh token to a service
- Authenticate a service by credentials of its own, such as OAuth 2.0
  client credentials, mutual TLS or a scoped API key (below)
- Validate every signed token's signature, expiry, issuer and audience
- Reject a token that lacks any required claim
- Store refresh tokens server-side, in a database or a dedicated session
  store, so they can be revoked; stateless refresh tokens cannot be
  invalidated before expiry

#### Token transport

- Send access tokens in the `Authorization: Bearer <token>` header (MUST)
- Do NOT accept tokens in query parameters — they appear in server logs and
  browser history
- Store a browser client's refresh tokens in `httpOnly`, `Secure`,
  `SameSite=Strict` cookies (MUST)
- Never store refresh tokens in `localStorage` or JavaScript-accessible memory

#### Authorization

- Use role-based access control (RBAC) as the baseline (SHOULD):
  assign permissions to roles, assign roles to users
- Add attribute-based access control (ABAC) as a layer on top of RBAC for
  fine-grained needs
- Replace RBAC with ABAC only with a reason in a decision record
- Enforce authorization at the service layer, not only at the route layer;
  a route that passes auth may call a service that operates on another
  user's data
- Never trust client-supplied IDs for ownership checks — always verify that
  the authenticated user owns or has access to the requested resource

#### API keys (service-to-service)

- Issue API keys with the minimum required scope
- Hash API keys before storing — treat them like passwords
- Rotate API keys on a schedule and immediately on suspected compromise
- Log every API key usage with the key ID (not the key value) and the
  calling service identity

#### Observability

- Log authentication failures at WARN to the security log, with IP and
  user agent
- Name the account by its opaque user ID when it exists; never log the
  submitted username or password
- Log authorization failures at WARN with user ID, resource, and action
- Alert on a spike in auth failures; it may indicate a credential stuffing
  attack

#### Testing

- Cover permission logic with unit tests for all role combinations,
  including edge cases (no role, multiple roles, deprecated role)
- Assert in an integration test that a protected endpoint rejects an
  unauthenticated request with an unauthenticated status, such as HTTP 401
- Assert in an integration test that it rejects an authenticated request
  lacking permission with a permission-denied status, such as HTTP 403
- Test token expiry: assert that an expired token is rejected
- Test token revocation where refresh tokens exist: assert that a revoked
  refresh token cannot obtain a new access token

### Backend — Database Conventions

#### Schema changes

- Make every schema change through a migration committed to source
  control — never edit the database manually
- Never regenerate or modify a migration that is already merged
- Write one migration per logical change — do not batch unrelated schema
  changes
- Provide a `down` migration for every `up`; where reversal would lose
  data, say so in the migration and get approval before applying it

#### Queries

- Parameterise every query that takes a value; never build a query by
  string interpolation
- Bound every query an interactive request runs with a limit or
  pagination; a filter alone is no bound, since a filter on a flag can
  still match millions of rows
- Stream or batch a deliberate export or batch scan, never load it whole
- Select only the columns or fields the code uses — never every column by
  default
- Fetch related data for a set of rows in one query or batch, never one
  query per row in a loop (N+1)

#### Transactions

- Wrap multi-step writes in a transaction — commit only after all writes
  succeed
- Never leave a transaction open across a request boundary
- Keep transactions short — do not call external services inside a transaction
- Use an isolation level stronger than the engine's default only when
  genuinely required

#### Connections

- Use a connection pool — never open a new connection per request
- Inject the database session/connection as a dependency — no global DB
  handles
- Set the pool size explicitly from the instance count and the
  database's connection cap, so all instances together stay under it
- Monitor pool exhaustion — alert when pool wait time exceeds threshold

#### Soft deletes

- Use soft deletes (`deleted_at` timestamp) only when audit history is
  required; otherwise use hard deletes
- If using soft deletes, filter deleted rows out of every query by
  default — never return deleted rows to callers
- Keep an append-only audit log table instead of soft deletes (MAY)

#### Testing

- Reset state between test runs — truncate tables or wrap each test in a
  transaction rolled back after completion
- Do not substitute a different database engine in tests, such as an
  in-memory one — behaviour differences cause false passes
- Never run schema migrations against a production database inside a test
  suite

### Frontend — UX Principles

#### UX principles

- Make every view usable on a small screen, not only on a desktop one
- Show only what the user needs at each step
- Never use a dark pattern: misleading UI, a forced action, a hidden cost
- Use the same interaction pattern for the same task throughout
- Treat a slow interface as a UX defect
- Make every component behave as it looks: what looks like a button acts
  like one

#### Accessibility — WCAG 2.1 AA

- Meet WCAG 2.1 AA
- Keep text contrast at 4.5:1 or more, 3:1 for large text
- Make every interactive element reachable and operable by keyboard
- Never put a click handler on a non-focusable element (MUST NOT); it adds
  no tab stop or keyboard activation
- Use a native interactive element for such a control instead: a button, a
  link or another native control
- Style focus with `:focus-visible`, not `:focus`, which also outlines
  mouse clicks
- Keep a visible focus indicator on every focusable element, links and nav
  links included (MUST); links often lack one even where buttons have it
- Never convey meaning by colour alone
- Give images descriptive `alt` text, and decorative ones `alt=""`
- Use semantic HTML: landmark elements and a correct heading hierarchy
- Give an icon-only or ambiguous control, such as a social link, a
  descriptive `aria-label`; never add one where visible text already names
  the control
- Make an accessible name contain the control's visible text, ideally at
  its start (WCAG 2.5.3, Label in Name)
- Close menus on Escape and restore focus

#### Accessibility testing

Automated tools catch about 30–40% of WCAG issues, so AA takes manual
testing too.

##### Automated (run in CI)

- Scan rendered pages or components with an automated accessibility
  checker in CI; merge on zero violations

##### Manual (run before shipping new interactive components)

- Tab through the whole feature without a mouse: every action reachable,
  focus order logical, no focus trap but an intentional modal
- Test it with one screen reader, such as NVDA, VoiceOver or TalkBack, and
  check every content and state change is announced
- Zoom to 200%: nothing clipped or overlapping, and no horizontal scroll
  at a 1280px viewport
- Check Windows High Contrast or the forced-colors media query: no
  information lost when colours are overridden

##### Criteria for done

A feature is not complete until:

- [ ] The automated accessibility check reports zero violations
- [ ] Keyboard navigation verified manually
- [ ] Screen reader walkthrough completed for new interactive elements

#### Design system

- Use the project's design system where one exists; never build an ad-hoc
  component that duplicates one of its patterns
- Take design tokens (colours, spacing, typography, radii, breakpoints)
  from the design system (MUST); never hardcode a visual value

#### Browser support

- Support the last two versions of Chrome, Firefox, Safari and Edge by
  default
- Degrade gracefully where a browser lacks a feature

### Base — Data Modeling

Rules for schema design, naming, normalization, and relationships, in any
store: a relational database, a document store or a static data file.

#### Naming conventions

- Use one naming convention per store for every table or collection,
  field, key and index; record it in the project's context file

#### Normalization

- Give every table or collection a primary key — prefer surrogate keys for
  internal use, natural keys for external-facing APIs
- Store each fact in one place by default — duplicate it only when
  measured read performance requires it
- Never pack several values into one string field, such as
  comma-separated values — use a list or a related record
- Document the rationale when intentionally denormalizing

#### Relationships

- Never rely on application code alone to keep references valid
- Enforce valid references with the store's own constraint where it has
  one, else with a check that every reference resolves
- Decide for every reference what deleting its target does:
  - delete the referencing records for strong ownership
  - clear the reference for a weak one
  - refuse the delete when an orphan indicates a bug
- Keep a record apart, referenced by key, unless it has no life outside
  its parent
- Document a self-referencing relationship's (e.g. `parent_id`) maximum
  depth and cycle prevention strategy (MUST)

#### Schema evolution

- Run every schema change through a versioned migration (MUST); never
  change a production schema by hand
- Prefer additive changes, such as a new field, table or collection
- Keep an additive change compatible with old writers: add a field
  optional or with a default, never required without one where records
  exist
- Give every destructive change (drop or rename a field) a migration plan:
  add new → migrate data → drop old (MUST)
- Include both up and down steps in every migration (MUST)
- Say so where a down step cannot restore the data, and get approval
  before applying that migration
- Test migrations against a production-like dataset before deploying

#### Data types

- Use the most specific type the store offers — a date type, not a
  string, for dates
- Store timestamps in UTC — convert to local time at the
  presentation layer
- Store monetary values as integers in minor units or as a decimal type —
  never floating point
- Use `UUID` or `ULID` for distributed ID generation — auto-increment
  is acceptable for single-database systems
- Document a maximum length for every text field (MUST); unbounded text
  invites abuse and complicates indexing

### Base — Data Governance

Rules for data classification, retention, privacy, and ownership.
Applies to any project that stores or processes user data, business
data, or regulated information.

#### Data classification

- Classify every data field into one of four tiers:
  - **Public** — safe to expose (product names, documentation)
  - **Internal** — business-sensitive, not for external use
    (internal metrics, cost data)
  - **Confidential** — restricted access (customer PII, financial
    records, API keys)
  - **Restricted** — highest sensitivity (passwords, payment card
    data, health records)
- Document the classification in the schema or data dictionary (MUST)
- Match access controls to the classification tier (MUST)
- Grant confidential and restricted data only to the roles or identities
  that need it

#### PII handling

- Identify all personally identifiable information (PII) fields
  in the schema — name, email, phone, address, IP, device IDs
- Encrypt PII at rest and in transit (MUST)
- Minimize PII collection — do not store what you do not need
- Provide a mechanism to delete PII — hard delete or anonymize, never
  just soft-delete it
- Never put PII in application logs, error messages, or stack traces
  (MUST NOT); the audit trail is a separate store, not a log
- Keep the client IP, the one PII field a security log may hold, in that
  log alone, access-restricted and purged when its retention ends
- Mask or redact PII in non-production environments

#### Retention

- Define a retention policy for each data category — document
  how long data is kept and when it is purged
- Meet every regulation that applies to the data in each retention
  period (MUST)
- Implement automated purging — do not rely on manual cleanup
- Apply retention policies to audit logs and backups too
- Never retain backups indefinitely
- Document the purge mechanism: soft delete → hard delete after
  N days, or direct hard delete

#### Data ownership

- Designate an owner for every data domain (users, orders, inventory)
  (MUST) — a team or individual accountable for quality, access, and
  lifecycle
- Have the data owner approve schema changes and access grants
- Document data ownership in the schema or data dictionary

#### Audit trail

- Log every change to confidential and restricted data (MUST):
  who changed what, when, and the previous value
- Never record a credential's or secret's value in the audit trail, old or
  new (MUST NOT); record that it changed, who changed it and when
- Record a PII field's change the same way, without its values, so
  deleting the PII leaves no copy in the append-only trail
- Keep the audit trail in its own store, never in application logs,
  with access restricted to the tier of the data it records
- Make audit logs append-only (MUST); never let application code edit
  or delete them
- Include the actor (user ID or service identity), timestamp,
  action (create, update, delete), and affected record

## Skills

Load a skill when its task starts; each holds that task's procedures.

| Skill | Load it when |
|-------|--------------|
| start-issue | Starting work on an issue, a ticket or a bug report |
| write-tests | Writing or changing tests, fixtures or assertions |
| add-check | Adding or tightening a check, such as a linter rule, a CI step, a hook or a threshold |
| add-dependency | Adding, upgrading or removing a dependency |
| regenerate | Editing a generated file's source, writing a generator, or merging the base branch into a branch that carries generated files |
| change-api | Adding or changing an endpoint, a field, an error response or the API contract |
| deprecate | Deprecating, renaming or removing a public name, an endpoint or a template |
| migrate-data | Writing or running a schema migration, a data fix or a backfill |
| write-docs | Writing or restructuring documentation, a decision record or a diagram |
| verify-finding | Reporting a defect, a measurement or a claim, or acting on another agent's finding |
| review | Reviewing a pull request or a diff, or judging whether it is ready to merge |
| generate-context | Generating or regenerating the project's agent context files |
