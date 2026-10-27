# Round 4 registration

Registered in the design before any round-4 trial ran, and moved here
unchanged but for its links. Issue numbers refer to `solid-ai-templates`,
where the benchmark lived until the split. Nothing below changes once a
round-4 trial has run.

## 12. Hypotheses registered after round 3

Each entry is committed before the analysis or trial that tests it, with one
primary measure, its threshold and the result that refutes it. Every other
measure it names is reported without a verdict.

### 12.1 Consistency across trials (#1874)

**Hypothesis.** A context file makes an arm's independent trials agree with
each other more than bare trials do.

**Data.** Round 3's fifteen build trials as re-read on 2026-09-27, K = 3. No
new trials. When this entry was written, the per-trial adherence fractions
had been seen in the report; no agreement measure had been computed.

**Primary measure: conventions agreement.** For one arm, take the adherence
checklist items measured in all three of its trials. Agreement is the share
of those items on which all three trials give the same verdict, pass or
fail alike.

| | |
|---|---|
| Contrast | `hybrid` minus `none` |
| Supported | the difference is at least 0.15, about two items |
| Refuted | the difference is below 0.15 |

`hybrid` is the contrast because it is the arm whose adherence moved in round
3. With one agreement value per arm there is no interval; the result is
descriptive.

**Secondary measures, no verdict:**

- conventions agreement for `full`, `short` and `hand` against `none`
- structure agreement: the mean, over the three pairs of an arm's trials, of
  the Jaccard similarity of their Python file paths, where a trial's files
  are those its own Git state would commit (tracked, plus untracked files its
  `.gitignore` does not exclude) and scoring's `.score` artefacts are left
  out
- security agreement: the same pairwise mean over the sets of security and
  data-protection probes each trial fails, two empty sets counting as full
  agreement; round 3's arms pass nearly every probe, so this measure sits at
  its ceiling and is expected to say little

### 12.2 Round 4: the protocol both entries share

Round 4 is two runs, each in a root of its own, and neither reuses a trial:

| Run | Generator | Specification | Tasks |
|---|---|---|---|
| thin | `claude-sonnet-5`, effort `high` | `SPEC-thin.md` (`--spec thin`) | build |
| weaker | `claude-haiku-4-5-20251001`, effort `high` | `SPEC.md` | build and change |

Both use round 3's five arms and files, K = 3, the rounds' judge three times per trial,
the trial deny rules of [ch. 11.3](../architecture/11-risks-and-technical-debt.md), and
an archive before the report. Round 4 runs without the cross-check of [ch.
8.6.6](../architecture/08-crosscutting-concepts.md): its judge is `claude-opus-5-5`
alone, as round 3's was, and the report says so. When these entries were written, and
when the cross-check was dropped, no round 4 trial had run.

Each primary measure is a growth over round 3: for one file arm and one
row, the round-4 contrast's mean paired difference against `none`, minus
round 3's for the same arm and row, as `docs/audits/2026-09-27-efficacy.md`
prints it. A growth counts only where the round-4 contrast's verdict is
better.

### 12.3 A thin specification (#1876)

**Hypothesis.** Round 3's specification states the defences a context file
would otherwise bring, so with a specification that states only the
contract, the files' gain on security and data protection shows.

**The thin specification** keeps everything the hidden suite drives: the
domain, the pricing algorithm, the API, the routes and form fields, the
export formats, the seed and the worked example. It drops 45 of 475 lines,
every one a practice: no network at runtime, valid HTML, the
JavaScript-disabled path, the 400 and 404 answers and server-side
validation, CSRF, sign-in required on every route, the failed sign-in, and
what erasure must leave behind. The issue estimated about 40 lines in all;
that cannot hold, because the suite checks the pricing algorithm figure by
figure and the algorithm alone runs to 70 lines.

**Primary measure:** the growth over round 3 of the four security and
data-protection rows: the judge's security and data-protection rows and the
two probe pass rates.

| | |
|---|---|
| Supported | at least one file arm grows on at least one of the four rows by that row's smallest change that matters (0.5 points, 9 pp, 30 pp) with a better verdict |
| Refuted | no file arm grows on any of the four by that much |

**The probes read sign-in without assuming it is required.** The thin
specification leaves a page free to be public, so a client is read as
signed in where some page shows it what an anonymous client is not shown,
or, where every page is public, where its sign-in answered with the
redirect to `next` a success gives. A sign-in sent without its token fails
the CSRF probe only where it is accepted by the same reading: where every
page is public, one answered otherwise than a real sign-in is refused,
whatever a failed sign-in answers, and the probe fails as unreadable only
where all three answer alike. A public dashboard alone fails nothing. This
was fixed before any round-4 trial ran, and reads round 3's applications as
before, since every one of them gated its pages.

**Secondary, no verdict:** the hidden suite's pass rate per arm, which now
also counts the dropped practices the suite checks, and each probe's result
per arm.

### 12.4 A weaker generator (#1875)

**Hypothesis.** A context file makes up for what a weaker model does not
know, so the files' gap to `none` opens as the model weakens.

**Primary measure:** the growth over round 3 of the seven primary rows and
task success.

| | |
|---|---|
| Supported | at least one file arm grows on at least one of the eight by its smallest change that matters ([ch. 8.6.8](../architecture/08-crosscutting-concepts.md)'s for the primaries; 5 pp for task success, declared here) with a better verdict |
| Refuted | no file arm grows on any of the eight by that much |

**Secondary, no verdict:** the change task's success and churn, cost per
trial, and the trials lost to the provider, a weaker model being likelier to
end a trial on the budget or the timeout.
