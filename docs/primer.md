# The benchmark in plain words

This page explains what the benchmark does and how to read what it finds.
It needs no programming. A word in **bold** on first use is defined in the
[glossary](architecture/12-glossary.md). The full rules are in the design,
[efficacy-benchmark.md](design/efficacy-benchmark.md), and the
[architecture](architecture/01-introduction-and-goals.md) describes how the
parts are built.

## 1. The question

Teams give AI coding agents a written note of house rules, a file named
`CLAUDE.md`. Such a note is a **context file**. The library
`solid-ai-templates` writes these files from a collection of rules.

The benchmark asks one question:

> Does an agent given one of these files build better software than the
> same agent given none, and at what cost?

"Better" is measured, not judged by eye: tests that check the app works,
attacks that check it is secure, tools that count defects, and a second AI
that scores the code without knowing which note its author had.

## 2. A fair contest

Think of a cooking contest built to be fair:

| In a cooking contest | In the benchmark |
| -------------------- | ---------------- |
| One recipe card, the same for every cook | The **spec**, `SPEC.md`: what the app must do |
| One cook, who never changes | The **builder model**, such as Claude Sonnet 5 |
| A note on the fridge: none, a short one, a long one | The context file: the only thing that changes |
| The same kitchen, the same time limit | The same tools, at most $100 or two hours |
| Each dish cooked three times, since one can be lucky | Each setting built three times: **K** = 3 |
| Tasters who do not know which note the cook had | The **blind judge** and the **hidden tests** |
| Rules for winning, written before anyone cooks | The rules, committed before the first run |

The app every agent builds is `tariff`, a small invoicing web app. It
prices a basket of products with discounts and tax, signs in one
administrator and keeps customer records. It is small enough to build in
one sitting and strict enough that a wrong cent shows.

## 3. The knobs

A round turns one knob at a time and holds everything else still. Then any
change on the meters has one cause.

![Four knobs the benchmark turns, each with its settings: the context file (none, inline, hybrid, reference, skills, with none selected), the specification (thin, normal, overspecified, pressure, conflict, broken, with normal selected), the builder model (Haiku 4.5, Sonnet 5, Opus 5.5, with Sonnet 5 selected) and the task (build, change, fix, refactor, review, evolve, with build selected). Below them, the meters: hidden tests, attack probes, the judge's scores, conventions, size, cost, and consistency, how alike an arm's runs are. Below that, what is fixed in every run: the app, the bounds of $100 or two hours, the prompt, the ruler, the judge and the runs per arm, 3 or 5 once when a result is close.](diagrams/knobs.png)

| Knob | Settings | What turning it asks |
| ---- | -------- | -------------------- |
| Context file, the **arm** | `none`, `inline`, `hybrid`, `reference`, `skills` | Does a file help, and which way of delivering the rules |
| Specification | `thin`, `normal`, `overspecified`, `pressure`, `conflict`, `broken` | Does a file supply what the spec leaves out, and hold or yield when the spec pushes against it |
| Builder model | Haiku 4.5, Sonnet 5, Opus 5.5 | Does a file help a weaker model more, and a stronger one less |
| Task | build, change, fix, refactor, review, evolve | Does a file help beyond a first build, and over a project's life |

The six specs:

| Spec | What it does | What it tests |
| ---- | ------------ | ------------- |
| Thin | Keeps the contract the hidden tests drive, drops the good practices | Does a file supply the defences the spec leaves out |
| Normal | The contract and the practices | The baseline every other spec is compared with |
| Overspecified | Dictates the "how" too: layout, tools, password storage | Should show no effect. A file that still moves the meters points at the ruler |
| Pressure | Asks for a bad practice, such as an export with no sign-in | Do the file's security rules hold |
| Conflict | Contradicts the file, such as a flat layout where the file says `src/` | Does the project's own decision win, as it should |
| Broken | Holds a planted fault, such as two rounding rules that clash, with the hidden tests asserting one | Does a file make the agent notice and report the fault, in its README or commit, instead of guessing |

The six tasks:

| Task | What the agent does | What it tests |
| ---- | ------------------- | ------------- |
| Build | Builds the app from an empty folder | The baseline every other task is compared with |
| Change | Adds a feature the design was not built for | How far the design has to be disturbed |
| Fix | Fixes a planted bug from a bug report | Does it fix it narrowly and add a test that catches it |
| Refactor | Improves the structure without changing behaviour | Does a file guide good design when nothing new is asked |
| Review | Reviews a change with planted defects | Does a file make it catch more of them |
| Evolve | Works on one project over a chain of sessions | Do the conventions hold over time, where a bare agent drifts |

The five arms:

| Arm | What the agent gets | What it isolates |
| --- | ------------------- | ---------------- |
| `none` | No file: the bare agent | The baseline every file is compared with |
| `inline` | Every rule that applies, copied in | Do the templates help when all of it is in the file |
| `hybrid` | The rules that matter copied in, the rest pointed to, the templates beside it | Does the way the owner's projects use help |
| `reference` | A file that only names the templates to read, with the templates beside it | Is pointing to the rules enough |
| `skills` | A short root file plus one skill per kind of task, loaded when the task needs it | Does a root file with skills deliver what hybrid does |

The design's section 13 registers the arms and the questions they answer.

## 4. One round, start to finish

![One round in four stages. Before the round, the project brief goes to the generator, which makes each arm's context file once with no person answering. In each run, a workspace holding SPEC.md and the arm's file goes to the AI agent, which builds the app in one session, and the app is frozen as it was left. Scoring runs the hidden tests, the attack probes, the code tools and the blind judge on each frozen app. Reading the result pairs each run with the run of the same block that had no file, takes an interval over the K differences, and gives one verdict per meter: better, worse or not shown](diagrams/round-flow.png)

1. **Make the files.** A generator turns a short project brief into each
   arm's context file, once, with nobody answering its questions. A person
   answering would put their judgement into the file.
2. **Build.** For each run, an empty folder gets the spec and the arm's
   file. The agent gets one fixed sentence: build what the spec describes.
   It works alone, with no web access, until it finishes or hits $100 or
   two hours.
3. **Freeze.** The folder is saved exactly as the agent left it, before
   anything reads it.
4. **Score.** Every frozen app goes through the same checks:
   - **hidden tests**, written before any run and kept where no agent can
     see them, check the app does what the spec says
   - **attack probes** try 11 security attacks and 3 personal-data checks
   - **code tools** count style, type and complexity defects
   - the blind judge, another AI, reads the code three times and scores
     design, readability, maintainability, security and data protection
     from 1 to 5
5. **Compare.** Each run with a file is compared with its no-file partner,
   and the differences give one verdict per meter. The runs of one arm are
   also compared with each other: how alike they came out is the arm's
   **consistency**.

## 5. Why runs are paired

![Fifteen runs in three blocks, five arms per block, run one after another: none-1, inline-1, hybrid-1, reference-1 and skills-1, then block 2, then block 3. A contrast such as inline minus none is three differences, inline-1 minus none-1, inline-2 minus none-2 and inline-3 minus none-3, with one interval over the three](diagrams/run-order.png)

A model's behaviour drifts from day to day. So the arms take turns: block 1
runs every arm once, back to back, then block 2, then block 3. Runs in one
block meet the same model on the same day.

The benchmark then compares partners, not averages. `inline-1` is
compared with `none-1`, `inline-2` with `none-2`, and so on. Three differences come
out, and those three decide.

## 6. How a verdict is read

![Five example rows, each with three dots for three pairs and a bar for the interval they allow. Two rows read Better: the bar lies wholly right of zero, once with the pairs nearly equal and once spread out. Not shown: the pairs disagree and the bar covers zero. Held: the same pairs, whose bar stays clear of the shaded loss past the margin. Worse: every pair got worse, and the bar lies wholly left of zero](diagrams/verdict.png)

| Verdict | Means | Does not mean |
| ------- | ----- | ------------- |
| **Better** | Every reasonable reading of the pairs improved | That the gain is large |
| **Worse** | Every reasonable reading got worse | That the file is useless |
| **Not shown** | The pairs disagree, so no direction is clear | That the two are equal |
| **Held** | Not shown, and no loss beyond a set **margin** | That it improved |

The bar is a **bootstrap interval**: the spread of averages the three
differences could produce if the runs were drawn again. A bar that covers
zero cannot tell better from worse.

Three runs describe a result. They do not prove it. Every report says so
beside every number. When a result is close, the rules allow one step up
to five runs, once, and never more. Running until a result appears would
manufacture one.

## 7. The rules that keep it honest

| Rule | Why |
| ---- | --- |
| The question, meters and verdict rule are written down before any run | Nobody can pick the metric that flatters the files after seeing results |
| No person touches a run | A person's judgement would leak into the arm they touched |
| The hidden tests live in a private repository | An agent that could read them would be graded on copying |
| The judge never sees which arm it reads | A judge that knows the arm can favour it |
| The judge is itself tested on damaged and improved code | A judge that cannot tell them apart measures nothing |
| A failed run is scored as it stands, never re-run | Re-running one arm's failures quietly improves that arm |
| A run the provider cut off is re-run once | The provider cut it, not the agent |
| A meter that turns out to measure something else is withdrawn | A wrong number is worse than no number |
| A tool that scanned nothing records "missing", never zero | Zero must mean "clean", not "not measured" |

## 8. What the evidence says so far

What the evidence supports today, in the words of the
[assessment](design/efficacy-assessment.md):

- **Supported, as a signal:** a file's conventions get followed more.
- **Supported:** a file does not break software that already works.
- **Not supported:** a file makes a strong model write better code.
- **Contradicted:** using the templates costs little. The files made the
  app up to 180 % bigger and most builds dearer.
- **Contradicted:** a longer file is better. Length tracked cost, not
  quality.

## 9. What it cannot tell you yet

- **One app.** Everything so far is `tariff`. A second app, `ledger`, is
  kept sealed for the final claim.
- **Three runs.** Every result is a signal, not proof.
- **One agent.** Every build is Claude Code. Another agent reading
  `AGENTS.md` is untested.
- **One sitting.** No run yet follows a project over months, which is
  where the templates claim to matter most.

## 10. Where to go next

| To | Read |
| -- | ---- |
| See every rule and threshold | [The design](design/efficacy-benchmark.md) |
| See what the evidence means for the templates | [The assessment](design/efficacy-assessment.md) |
| Understand how the parts fit together | [The architecture](architecture/01-introduction-and-goals.md) |
| Follow a person through a task | [User journeys](journeys/index.md) |
| Run it | [The harness guide](guides/efficacy-harness.md) |
