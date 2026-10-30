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
| Size | none | root 1–2 KB; 13 skills of 2.7 to 10.5 KB, 74 KB in all |
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
templates' manifest, which the generator would read. Some templates apply to
nearly every edit (`core/quality.md`, `security/security.md`), so variant 3
may keep those in the root and offer the rest as skills.

```text
CLAUDE.md (1-2 KB)
  facts, commands
  "before <moment>, load <skill>" table
        |
        v
.claude/skills/
  base-testing/SKILL.md    <- core/testing.md, verbatim
  base-git/SKILL.md        <- core/git.md, verbatim
  backend-api/SKILL.md     <- backend/api.md, verbatim
  ...                         13 in all
```

## Next steps

- [ ] Choose how the triggers are written: by hand, or `load_when:` upstream
- [ ] Generate the arm and commit it under `tests/efficacy/arms/`
- [ ] Count skill loads per trial in the harness or the scorer
- [ ] Pilot of about 3 trials, with the owner's go first, since it spends
  plan limits
- [ ] Decide from the pilot whether a round registers the arm
