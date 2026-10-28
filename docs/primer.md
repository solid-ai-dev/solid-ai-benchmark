# The benchmark in plain words

This page explains what the benchmark does and how to read what it finds.
It needs no programming. A word in **bold** on first use is defined in the
[glossary](architecture/12-glossary.md). The full rules, and how the parts
are built, are in the [architecture](architecture/01-introduction-and-goals.md).

## 1. The question

Teams give AI coding agents a written note of house rules, a file named
`CLAUDE.md` or `AGENTS.md`. Such a note is a **context file**. The library
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
| Each dish cooked many times, since one can be lucky | Each setting built 15 times: **K** = 15 |
| Tasters who do not know which note the cook had | The **blind judge** and the **hidden tests** |
| Rules for winning, written before anyone cooks | The rules, committed before the first run |

The app every agent builds is `tariff`, a small invoicing web app. It
prices a basket of products with discounts and tax, signs in one
administrator and keeps customer records. It is small enough to build in
one sitting and strict enough that a wrong cent shows.

## 3. The test machine

The benchmark works like a test machine with knobs to turn and meters to
read. A round turns one knob at a time and holds everything else still.
Then any change on the meters has one cause.

### 3.1 Knobs and meters

![Four knobs the benchmark turns, each with its settings: the context file (none, inline, hybrid, reference, skills, with none selected), the specification (thin, normal, overspecified, pressure, conflict, broken, with normal selected), the builder model (Haiku 4.5, Sonnet 5, Opus 5.5, with Sonnet 5 selected) and the task (build, change, fix, refactor, review, evolve, with build selected). Below them, the meters: hidden tests, attack probes, the judge's scores, conventions, size, cost, and consistency, how alike an arm's runs are.](diagrams/knobs.png)

| Knob | Settings | What turning it asks |
| ---- | -------- | -------------------- |
| Context file, the **arm** | `none`, `inline`, `hybrid`, `reference`, `skills` | Does a context file help, and which way of delivering the rules |
| Specification | `thin`, `normal`, `overspecified`, `pressure`, `conflict`, `broken` | Does a context file supply what the spec leaves out, and hold or yield when the spec pushes against it |
| Builder model | Haiku 4.5, Sonnet 5, Opus 5.5 | Does a context file help a weaker model more, and a stronger one less |
| Task | build, change, fix, refactor, review, evolve | Does a context file help beyond a first build, and over a project's life |

The meters are described in [section 4](#4-one-round-start-to-finish),
where each run is scored.

### 3.2 Context files

The five arms, the settings of the first knob:

| Arm | What the agent gets | What it isolates |
| --- | ------------------- | ---------------- |
| `none` | No file: the bare agent | The baseline every file is compared with |
| `inline` | Every rule that applies, copied in | Do the templates help when all of it is in the context file |
| `hybrid` | The rules that matter copied in, the rest pointed to, the templates beside it | Does the way the owner's projects use help |
| `reference` | A context file that only names the templates to read, with the templates beside it | Is pointing to the rules enough |
| `skills` | A short root file plus one skill per kind of task, loaded when the task needs it | Does a root file with skills deliver what hybrid does |

[Round 5's registration](rounds/round-5.md) sets the arms and the questions
they answer.

### 3.3 Specs

| Spec | What it does | What it tests |
| ---- | ------------ | ------------- |
| Thin | Keeps the contract the hidden tests drive, drops the good practices | Does a context file supply the defences the spec leaves out |
| Normal | The contract and the practices | The baseline every other spec is compared with |
| Overspecified | Dictates the "how" too: layout, tools, password storage | Should show no effect. A context file that still moves the meters points at the ruler |
| Pressure | Asks for a bad practice, such as an export with no sign-in | Do the context file's security rules hold |
| Conflict | Contradicts the context file, such as a flat layout where it says `src/` | Does the project's own decision win, as it should |
| Broken | Holds a planted fault, such as two rounding rules that clash, with the hidden tests asserting one | Does a context file make the agent notice and report the fault, in its README or commit, instead of guessing |

### 3.4 Builder models

Each round names its own set of builder models in its registration before
its first run. Two rules hold for every set:

- Every model is pinned by its exact version, so the builder cannot change
  under a round
- No builder comes from the judge's vendor, so the judge never scores its
  own vendor's code

The models on the knob span weak to strong:

| Model | What it is | What it tests |
| ----- | ---------- | ------------- |
| Haiku 4.5 | The smallest and cheapest | Does a context file make up for what a weaker model does not know |
| Sonnet 5 | The middle model, and the benchmark's main builder | The baseline every other model is compared with |
| Opus 5.5 | The strongest | Does a context file still help a model that knows most of it already |

### 3.5 Tasks

| Task | What the agent does | What it tests |
| ---- | ------------------- | ------------- |
| Build | Builds the app from an empty folder | The baseline every other task is compared with |
| Change | Adds a feature the design was not built for | How far the design has to be disturbed |
| Fix | Fixes a planted bug from a bug report | Does it fix it narrowly and add a test that catches it |
| Refactor | Improves the structure without changing behaviour | Does a context file guide good design when nothing new is asked |
| Review | Reviews a change with planted defects | Does a context file make it catch more of them |
| Evolve | Works on one project over a chain of sessions | Do the conventions hold over time, where a bare agent drifts |

### 3.6 What stays fixed

Fixed in every run, so only the knobs can move the meters:

- **The app:** `tariff`, a small invoicing web app
- **The bounds:** at most $100 or two hours per run
- **The prompt:** one fixed sentence, the same for every arm
- **The ruler:** the measuring tools, at the same versions and settings for
  every run. An agent cannot score cleaner by loosening its own lint rules
- **The judge:** GPT-6 Astra at high effort, blind to the arm, reading
  each app three times
- **Runs per arm:** fixed by each round before it starts, 15 today

## 4. One round, start to finish

![One round in four stages. Before the round, the project brief goes to the generator, which makes each arm's context file once with no person answering. In each run, a workspace holding SPEC.md and the arm's file goes to the AI agent, which builds the app in one session, and the app is frozen as it was left. Scoring reads six meters on each frozen app, each on its own and in any order: hidden tests, attack probes, the judge's scores, conventions, size and cost. Reading the result compares each run with the bare run of the same block, checks whether the difference would hold if the runs were redone, and gives one verdict per meter: better, worse or undecided. Consistency compares an arm's runs with each other](diagrams/round-flow.png)

### 4.1 Before the round

A generator turns a short project brief into each arm's context file,
once, with nobody answering its questions. A person answering would put
their judgement into the file.

### 4.2 Each run

1. **Build.** An empty folder gets the spec and the arm's context file. The
   agent gets one fixed sentence: build what the spec describes. It works
   alone, with no web access, until it finishes or hits $100 or two hours.
2. **Freeze.** The folder is saved exactly as the agent left it, before
   anything reads it.

### 4.3 Scoring

Every frozen app is read on six meters. Each reads the same app on its
own, in any order.

| Meter | What it reads | Reads in |
| ----- | ------------- | -------- |
| **Hidden tests** | Does the app do what the spec says? Written before any run, and kept where no agent can see them | % passed |
| **Attack probes** | 11 security attacks and 3 personal-data checks, each set read as its own pass rate | passed, of 11 and of 3 |
| **Judge's scores** | The blind judge reads the code three times and scores design, readability, maintainability, security and data protection | 1 to 5 |
| **Conventions** | Code tools check a 13-item checklist, such as lint, types and test coverage | met, of 13 |
| **Size** | The lines and files of app code the agent wrote, tests counted apart. A small rise reads as held | lines |
| **Cost** | The dollars, turns and minutes the run took | $ |

### 4.4 Reading the result

1. **Compare with the bare run.** Each run with a context file is compared
   with the run of the same block, see 5.1, that had none: `inline-1` minus
   `none-1`.
2. **Luck check.** The differences are checked for whether they would hold
   if the runs were redone.
3. **Verdict.** Each meter gets one: better, worse or undecided.
4. **Consistency.** The runs of one arm are also compared with each other.
   How alike they came out is the arm's **consistency**, read in %.

Section 5 explains the comparison and the verdicts.

Every round's report is listed in [the rounds index](rounds/README.md#reports).

## 5. The verdicts, explained

### 5.1 Pairs, not averages

![Fifteen runs in a grid, one row per block and one column per arm: none, inline, hybrid, reference and skills. Each block runs every arm once, then the next block starts. Below the grid, each context-file arm has three deltas against none, such as inline-1 minus none-1, inline-2 minus none-2 and inline-3 minus none-3, which go through one luck check and get one verdict per meter](diagrams/run-order.png)

A model's behaviour drifts from day to day. So the arms take turns: block 1
runs every arm once, back to back, then block 2, then block 3. Runs in one
block meet the same model on the same day. Each block starts one arm later
than the last, so no arm always runs first or last.

The benchmark then compares partners, not averages. `inline-1` is compared
with `none-1`, `inline-2` with `none-2`, and so on. The picture shows three
blocks, so three differences come out.

The same pattern extends to any number K of blocks. Round 5 runs 15, so
each arm gets 15 deltas. Each extra block adds one more run per arm, and the
luck check gets sharper with every delta, as section 5.3 shows.

### 5.2 Reading the bar

![Four example ranges of the hidden-test delta, each answering two questions against a margin of 2 points: which way did it move, and has a big loss been ruled out. Plus 1 to plus 4: better, and yes. Minus 1 to plus 3: undecided, because the bar covers zero, but yes, because it stays right of the margin. Minus 5 to plus 3: undecided, and no, because it reaches past the margin. Minus 4 to minus 1: worse, and no](diagrams/verdict.png)

The bar is the luck check's **likely range**: where the average delta
would land if the runs were redone. Statisticians call it a bootstrap
interval.

Each bar answers two questions:

| Question | Answer | Read from the bar |
| -------- | ------ | ----------------- |
| Which way did it move? | Better, worse or **undecided** | Better if the bar lies wholly above zero, worse if wholly below, undecided if it covers zero |
| Big loss ruled out? | Yes or no | Yes if the bar stays above the **margin**, a loss fixed in advance. For hidden tests it is 2 points |

Undecided does not mean equal: some reruns would gain and some would lose.
A yes, which the rules call **held**, is what a trim of the templates
needs, or round 5's question whether skills deliver what hybrid does: proof
that a change is not much worse.

### 5.3 How many runs it takes

Each round fixes K, the runs per arm, before it starts, from how noisy the
meters were in the rounds before it. The more runs, the stronger the claim:

| Runs per arm | What a result can claim |
| ------------ | ----------------------- |
| 3 | A signal. Every report says so beside every number |
| 6 | The fewest where every pair pointing one way counts as proof |
| about 10 | Enough to catch an effect as big as the run-to-run noise |
| 15 | Round 5's count: a real loss is caught 98 times in 100, and a loss the size of the margin passes as held at most 5 times in 100 |

Runs are never added once the results are seen. With enough tries, luck
alone would produce the hoped-for answer, like flipping a coin until it
lands heads.

## 6. The rules that keep it honest

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
