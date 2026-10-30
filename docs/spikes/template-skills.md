# Spike: a short root file with each template as a skill

Issue: [#85](https://github.com/solid-ai-dev/solid-ai-benchmark/issues/85).
Written 2026-10-30, during round 5c's block A.

The idea: a short `CLAUDE.md`, like the reference arm's, with each template
the project adopted installed as a skill the agent loads when a task needs it.
This spike asks whether such an arm can be built, what it would measure, and
what decides whether it is worth a round.

## The skills arm today is not this

Round 5c's `skills` arm is what the templates' emitter builds. The emitter
keeps every untagged section in the root file, since those rules apply on
every task, and moves only the sections tagged `[LOAD: kind]` into skills.
Few sections carry a tag, so most of the text stays in the root.

| Arm | Root `CLAUDE.md` | Skills | Built by |
| --- | --- | --- | --- |
| reference | 0.9 KB, a list of template paths | none | fixed text |
| inline | 26 KB | none | a model, condensing |
| hybrid | 22 KB | none | a model, condensing |
| skills | 57 KB | 12, 17 KB in all | the emitter, verbatim |

The skills arm's root is the largest because the emitter copies rule text
unchanged, where the inline and hybrid arms are a model's condensation.

## What round 5c shows so far

Counted from the transcripts of trials 1 to 5 of each arm:

| Arm | How the rules reach the agent | Observed |
| --- | --- | --- |
| reference | the root says "read each template before starting" | all 13 read |
| skills | 12 task skills, each offered by its description | none used |

The two skill calls in those transcripts were Claude Code's built-in `run`
skill. An agent follows an explicit instruction to read, but picks no skill
from its description alone. That is the central risk for the new arm.

## Feasibility

| Piece | Work | Note |
| --- | --- | --- |
| Arm generator | small | a new kind: each template, verbatim, to a `SKILL.md` |
| Harness | none | it already places a skills folder and probes discovery |
| Descriptions | small | the manifest's `description:` names topics, not moments |
| Size | none | root about 3 KB; 27 skills of 0.5 to 6.7 KB, 74 KB in all |
| Measuring use | small | count the arm's skill calls per trial in the transcript |
| Cross-references | upstream | templates name each other by path, not by skill name |

Templates [#2415](https://github.com/solid-ai-dev/solid-ai-templates/pull/2415)
rewords the file pointers the emitter carried, which helps those
cross-references once each template is a skill.

The 13 templates the reference arm lists, by size:

| Template | Size | Sections |
| --- | --- | --- |
| `security/security.md` | 10.5 KB | 16 |
| `core/quality.md` | 9.9 KB | 18 |
| `core/testing.md` | 8.5 KB | 16 |
| `core/review.md` | 7.3 KB | 10 |
| `core/docs.md` | 6.7 KB | 13 |
| `core/git.md` | 5.9 KB | 7 |
| `backend/http.md` | 5.5 KB | 10 |
| `backend/api.md` | 4.5 KB | 8 |
| `backend/auth.md` | 3.9 KB | 7 |
| `data/data-governance.md` | 3.2 KB | 5 |
| `frontend/ux.md` | 3.1 KB | 5 |
| `data/data-modeling.md` | 2.8 KB | 5 |
| `backend/database.md` | 2.7 KB | 7 |

## How the root triggers loading decides it

1. **Descriptions only.** The root lists the skills and nothing more.
   Likely nothing loads, so the arm behaves as `none`.
2. **Load all first.** The root says "load these 13 skills before
   starting". This is the reference arm in other packaging, and tests
   nothing new.
3. **Load at the moment.** The root says "before writing a test, load
   `base-testing`; before a commit, load `base-git`". This tests whether
   rules loaded when they apply beat rules read up front, at less context.

Variant 3 is the one with a new question. Its triggers need writing, either
by hand for this arm or as a `load_when:` field per template in the
templates' manifest, which the generator would read. All 13 templates
become skills and the root stays short, as decided on #85.
Keeping `core/quality.md` and `security/security.md` in the root, since
they apply to nearly every edit, would grow it to about 22 KB, the hybrid
arm's size. They get a load moment like the rest instead.

```text
CLAUDE.md (about 3 KB)
  facts, commands
  "before <moment>, load <skill>" table
        |
        v
.claude/skills/
  quality-design/SKILL.md   <- core/quality.md, 5 sections, verbatim
  testing-design/SKILL.md   <- core/testing.md, 3 sections, verbatim
  backend-api/SKILL.md      <- backend/api.md, whole, verbatim
  ...                          27 in all
```

## Splitting the large templates

A template loaded whole fires whenever any of its rules applies, and
`core/quality.md` and `security/security.md` apply to nearly every task. So
the four largest templates are cut at their `##` headings into skills of
0.5 to 3 KB, each with a narrower moment; the text stays verbatim, and only
the cut points are chosen. One skill per section would make about 127, too
many to choose among, so sections are grouped.

| Template | Size | Skills |
| --- | --- | --- |
| `security/security.md` | 10.5 KB | 5 |
| `core/quality.md` | 9.9 KB | 5 |
| `core/testing.md` | 8.5 KB | 4 |
| `core/review.md` | 7.3 KB | 4 |
| the other 9 | 2.7 to 6.7 KB | 1 each, whole |

That makes 27 skills, and a root of about 3 KB with its load table. The
cost is a longer table and more chances to load the wrong skill.

Sizes are at templates `84f4bb51`, the merge of
[#2415](https://github.com/solid-ai-dev/solid-ai-templates/pull/2415). The
pilot builds there or later, so no skill names a template file.

## Load moments

Written by hand for the pilot. The root carries this table, one row a
skill. A whole template keeps its manifest ID as its name.

<!-- markdownlint-disable MD013 -->
| Skill | From | Sections | Size | Load it before |
| --- | --- | --- | --- | --- |
| `quality-design` | quality | Principles, Architecture, Naming, Complexity, Module structure | 2.0 KB | writing new code |
| `quality-dependencies` | quality | Dependencies, Deprecation and renames, Library output | 1.9 KB | adding a dependency or renaming something public |
| `quality-errors` | quality | Errors, Destructive operations, Debug code | 1.8 KB | handling errors, or deleting or overwriting data |
| `quality-files` | quality | Encoding and line endings, Comments | 2.3 KB | writing a file or a comment |
| `quality-finish` | quality | Rejected mechanisms, New constraints, Check trust, Enforcement, Completion | 1.9 KB | finishing a task |
| `security-input` | security | Input validation, Output encoding, Injection prevention, Deserialization, File uploads | 2.4 KB | code that takes input or renders output |
| `security-web` | security | CSRF, Security headers, CORS, Transport security | 2.8 KB | server setup or a form |
| `security-auth` | security | Authentication, Session management | 0.9 KB | sign-in or sessions |
| `security-secrets` | security | Secrets in code, Agent secrets handling, Logging, Error handling | 2.5 KB | config, logs or error messages |
| `security-ssrf` | security | Server-Side Request Forgery | 1.3 KB | calling out to a URL |
| `testing-design` | testing | Test types, Coverage, Testability | 1.8 KB | planning the tests for a feature |
| `testing-isolation` | testing | Isolation, Unique resources, Worker leaks, Fault injection | 2.1 KB | writing a test's setup or fixtures |
| `testing-assertions` | testing | External definitions, Guard use, Provenance, Thresholds, Empty results | 3.0 KB | writing assertions |
| `testing-fixes` | testing | Call sites, Real data, Rendered output, Drift guards | 1.5 KB | proving a fix or a visual change |
| `review-start` | review | Picking up an issue, Planning, Structure audit | 1.9 KB | starting an issue or a new project |
| `review-checklist` | review | Principle, Priority order, MUST and SHOULD checklists, Deviations | 2.5 KB | reviewing a change, your own included |
| `review-ci` | review | CI signals | 0.5 KB | reading a check's result |
| `review-verify` | review | Verifying a finding | 2.3 KB | reporting or acting on a finding |
| `base-docs` | docs | whole | 6.7 KB | writing a README, a doc or a docstring |
| `base-git` | git | whole | 5.9 KB | a commit, a branch or a pull request |
| `backend-http` | http | whole | 5.5 KB | writing a route, a handler or the server setup |
| `backend-api` | api | whole | 4.5 KB | designing or changing an endpoint or its contract |
| `backend-auth` | auth | whole | 3.9 KB | touching sign-in, sessions or access control |
| `base-data-governance` | data-governance | whole | 3.2 KB | storing, logging or exporting personal data |
| `frontend-ux` | ux | whole | 3.1 KB | writing a page, a template or a form |
| `base-data-modeling` | data-modeling | whole | 2.8 KB | designing tables or data shapes |
| `backend-database` | database | whole | 2.7 KB | writing a schema, a migration or a query |
<!-- markdownlint-enable MD013 -->

Every section of the four split templates lands in exactly one skill. A
skill that loads in no trial is a finding in itself.

## A comparison: the Nango blog pipeline

The Nango blog pipeline's `AGENTS.md`, a working project's root file,
already has this shape:

| Nango blog pipeline | This pilot |
| --- | --- |
| short root with a phase-to-skill table | short root with a moment-to-skill table |
| 9 skills, each a workflow | 27 skills, each a slice of rules |
| a person starts each phase, mostly by slash command | no person: one prompt, then hours alone |
| one session per phase | one session for the whole build |
| rules in shared files the skills read | the rules are the skills |

Two lessons carry over:

- **Auto-detection proved unreliable even there.** 7 of its 9 skills are
  marked explicit only, under "always prefer explicit /slash-command
  invocation over natural language to avoid skill confusion". That is with
  9 skills and a person at hand; the pilot has 27 and nobody.
- **Another variant to weigh.** Skills for the work phases (start, build,
  test, review, finish), each telling the agent which rule files to read,
  with the rules kept as files rather than cut into skills.

## Next steps

- [x] Choose how the triggers are written: by hand for the pilot; `load_when:`
  upstream only if the pilot shows the skills get loaded
- [ ] Generate the arm and commit it under `tests/efficacy/arms/`
- [ ] Count skill loads per trial in the harness or the scorer
- [ ] Pilot of about 3 trials, with the owner's go first, since it spends
  plan limits
- [ ] Decide from the pilot whether a round registers the arm
