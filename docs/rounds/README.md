# Rounds

Each round registers its question, its blocks and its hypotheses here
before its first trial runs. Nothing in a registration changes once a
trial of that round has run. The rules every round shares are in
[chapter 8](../architecture/08-crosscutting-concepts.md).

| Round | Registered | Asks |
| ----- | ---------- | ---- |
| [Round 4](round-4.md) | Before its first trial, after round 3 | Does a file supply what a thin spec leaves out, and help a weaker model more |
| [Round 5](round-5.md) | 2026-10-26, amended 2026-10-27, 2026-10-28 and twice on 2026-10-29 | Which way of delivering the rules gives the best and most consistent code |

## Reports

Each round's report sits beside the templates, in their `docs/audits/`.
Rounds 1 to 3 were registered in the templates' own design, before this
repository existed.

| Round | Run | What it turned | Report |
| ----- | --- | -------------- | ------ |
| 1 | 2026-09-17 | Context file: none, the templates' inline file, a hand-written one | [Report](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-09-17-efficacy.md) |
| 2 | 2026-09-18 | Context file: adds the short and hybrid files | [Report](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-09-18-efficacy.md) |
| 3 | 2026-09-27 | Context file: every arm run fresh | [Report](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-09-27-efficacy.md), [assessment of rounds 1 to 3](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-09-27-efficacy-assessment.md) |
| 4 | 2026-10-17 | Spec: thin, and builder: Haiku 4.5 | [Summary](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-10-17-round-4.md), [thin spec](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-10-17-efficacy-thin.md), [weaker model](https://github.com/solid-ai-dev/solid-ai-templates/blob/main/docs/audits/2026-10-17-efficacy-weaker.md) |
| 5 | Not run yet | Context file: how the rules are delivered | — |
