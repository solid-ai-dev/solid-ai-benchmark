"""Generate one round-5 arm's context file, once, with nobody answering.

Every round-5 arm is made from one chain of the templates at one commit, so
the arms differ only in how they deliver it. This module makes them:

- `reference` is fixed text naming each template of the chain
- `inline` and `hybrid` are one non-interactive generation each, following
  `templates/core/agents.md` with no interview
- `short` is the same generation in the inline model, held to 40 lines of
  88 characters
- `skills` is what `resolve_chain.py --emit` builds, the facts filled from
  the brief
- `lazyref` and `lazyskills` are fixed text too: a map from the topics the
  manifest gives each template of the chain to that template, read as a file
  or loaded as a skill the first time the work touches one of them, and for
  `lazyskills` one skill per template, holding it verbatim

It writes `arms/<arm>/CLAUDE.md` (and, for an arm with skills, the skills
beside it), and refuses to keep a result the specification leaked into, or
one over its arm's budget.

Run it once per arm. Re-running it produces a different file and therefore
a different arm, so it refuses to overwrite an existing one without
`--replace`, and the record it writes is what the report cites.
"""

import argparse
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time

from harness import (ROUND5_DECLINED, ROUND5_REF,  # noqa: E402
                     ROUND5_ROOTS,
                     TEMPLATES_ENV, VENDORED, TrialError, source_record,
                     templates_root, agent_environment, agent_executable,
                     assert_authenticated, assert_outside_repository,
                     prepare_home, read_input)

HERE = os.path.dirname(os.path.abspath(__file__))

# The generated arms' project brief lives in a file of its own, its only
# copy, for the reason `harness.CHANGE_PROMPT` gives.
BRIEF = os.path.join(HERE, "brief.txt")

# The arms this module makes, each with the directory under `arms/` its file
# and record live in, and how it is made: fixed text, a model generation in
# one of `agents.md`'s models, the emitter, or a map of the chain's topics
# read as files or loaded as skills, and a model arm's budget as (lines,
# width) where it has one. `hand` is a person's file, kept verbatim with no
# record, so it is not made here.
GENERATED = {
    "reference": {"dir": "reference", "kind": "fixed"},
    "inline": {"dir": "inline", "kind": "model", "model": "inline"},
    "hybrid": {"dir": "hybrid", "kind": "model", "model": "hybrid"},
    "skills": {"dir": "skills", "kind": "emit"},
    "short": {"dir": "short", "kind": "model", "model": "inline",
              "budget": (40, 88)},
    "lazyref": {"dir": "lazyref", "kind": "map", "load": "read"},
    "lazyskills": {"dir": "lazyskills", "kind": "map", "load": "skill"},
}


def output_path(arm):
    """Where an arm's generated file is committed."""
    return os.path.join(HERE, "arms", GENERATED[arm]["dir"], "CLAUDE.md")


def skills_path(arm):
    """Where an arm's generated skills are committed, one folder a kind."""
    return os.path.join(HERE, "arms", GENERATED[arm]["dir"], "skills")


def record_path(arm):
    """The record of the generation behind an arm's file, committed beside
    it. The report cites it, and a scratch directory would not outlive the
    run."""
    return os.path.join(HERE, "arms", GENERATED[arm]["dir"],
                        "generation.json")


# Two lists, because the prompt and the output are different questions.
#
# The PROMPT scan is a wiring check: a generation is never handed
# `SPEC.md`, so any of these appearing in the prompt means the plumbing is
# wrong. It can afford to be broad, since a false positive costs a look
# rather than a generation.
PROMPT_TOKENS = [
    "half-even", "ROUND_HALF_EVEN", "n-for-m",
    "WID-1", "GAD-2", "BOK-3", "SRV-4", "SEE-5",
    "r-tier-wid", "r-bulk-see", "r-pct-bok", "r-pct-all",
    "c-welcome", "c-tenoff", "WELCOME", "TENOFF",
    "PricedInvoice", "TariffError",
    "/invoices/preview", "/invoices/new", "export.csv", "export.json",
    "228.35", "227.07", "195.24", "0.135",
    "TARIFF_ADMIN_PASSWORD", "/sign-in", "/sign-out",
    "Ada Example", "ada@example.com",
]

# The OUTPUT scan asks something narrower, and the prompt scan is what
# earns it: once the prompt is clean, the model demonstrably never read the
# specification, so anything specification-shaped in the output was
# *inferred*. Only arbitrary data can survive that argument — a seed sku, a
# rule id, a figure from the worked example. Nothing derives those.
NON_INVENTABLE = [
    "WID-1", "GAD-2", "BOK-3", "SRV-4", "SEE-5",
    "r-tier-wid", "r-bulk-see", "r-pct-bok", "r-pct-all",
    "c-welcome", "c-tenoff",
    "228.35", "227.07", "195.24",
    "Ada Example", "ada@example.com",
]

# Two tokens taught this the hard way.
#
# `HX-Request` came off the prompt list: the templates document the header
# themselves, as any HTMX guidance would, so the scan fired on a clean
# prompt. `/customers/` came off it the same way, from the templates' REST
# rule, whose example nests `/customers/{id}/orders`. Every other token was then checked the same way against the chain
# at the release and appears nowhere in it.
#
# `TariffError` came off the *output* list on the first real generation. The
# prompt had already scanned clean, so the model could not have read it —
# it named the error base after the package, which is exactly what the
# templates' one-hierarchy rule asks of a package called `tariff`. The
# specification chose the same name for the same reason. `PricedInvoice`,
# the routes, the coupon codes and `half-even` are all derivable the same
# way and stay out of the output list for the same reason.

INSTRUCTION = """\
You generate one project's `CLAUDE.md` from the solid-ai-templates, with no
person to answer questions.

Follow `templates/core/agents.md`, given in full below, for what the file
holds and how it is written. The project brief below is the whole of what
the project has said about itself. Adopt every rule of the chain below that
applies to the project the brief describes, and leave out every rule that
does not. Where the brief does not settle something, choose what the rules
already imply and move on; do not ask.

The brief names no tools, and the project has chosen none. Where a rule asks
for a type checker, a linter, a formatter, a test runner or a package
manager, or a template shows a command as a placeholder, say what the check
must do and name no tool and no command: that choice is the project's.

Output the finished `CLAUDE.md` and nothing else: no preamble, no
explanation, no code fence around the whole document.

%s
## Project brief

%s

## templates/core/agents.md

%s

## The rules this project's chain resolves

%s
"""

# What each output model's clause tells the generation. The hybrid clause
# names where the templates sit in the workspace, because the harness
# vendors them there rather than adding a submodule, and a file telling its
# reader to add one would be wrong from its first line.
MODELS = {
    "inline": "Use the inline model of `agents.md`.",
    "hybrid": ("Use the hybrid model of `agents.md`. The templates are "
               "present in the project at `%s/%s/`, the repository's `%s/` "
               "directory at the same revision as the rules below, as a "
               "vendored copy rather than a submodule: point there, list the "
               "template files to read by their paths under it, and do not "
               "tell anyone to add a submodule."
               % (VENDORED["into"], VENDORED["path"], VENDORED["path"])),
}

# The `reference` arm's whole file: the brief, then the chain named, no rule
# copied in. Every arm's root states the same project facts, so the arms
# differ in how they hand over the rules and in nothing the project says of
# itself.
REFERENCE = """\
# tariff

{brief}

Before starting work, read each template below and apply every rule it
holds that fits this project. They are vendored at `{into}/`,
at the revision the project adopted.

{files}
"""

# The facts the emitted root file leaves as slots, each filled from the
# brief and nothing else. A slot the brief does not settle says so rather
# than inventing an answer.
FACTS = {
    "{{project-name}}": "tariff",
    "{{one-sentence description}}":
        "A pricing and invoicing web application: a product catalog, "
        "discount rules, tax jurisdictions, customers and invoices.",
    "{{owner}}": "Imbra Ltd",
    "{{repository}}": "this repository",
    "{{the commands to build, test and run the project}}":
        "Python 3.12, Flask 3, Jinja, HTMX and SQLite; the brief names no "
        "tooling. It runs locally; there is no deployment target.",
    "{{approver}}": "not stated in the brief",
    "{{tracker}}": "not stated in the brief",
    "{{release}}": "not stated in the brief; the application runs locally",
}
SLOT = re.compile(r"\{\{[^}]+\}\}")


# The budget clause. The width keeps a line from carrying a paragraph. The
# closing check adds no content; it asks the model to hold a bound it is
# already given, since a file over it is refused whole.
BUDGET = """\
The finished `CLAUDE.md` MUST be at most {lines} lines, blank lines counted,
and no line may be longer than {width} characters. Keep the rules that matter
most for this project and leave the rest out; a rule that does not fit is left
out, not squeezed onto another rule's line.

Before you answer, measure every line against {width} characters and shorten
or split each one over it, then count the lines again. A file over either
bound is refused whole, never trimmed."""


def arm_clause(arm):
    """The model and budget paragraphs for one model arm's instruction."""
    entry = GENERATED[arm]
    lines = ["## The output model", "", MODELS[entry["model"]]]
    if entry.get("budget"):
        count, width = entry["budget"]
        lines.extend(["", "## The budget", "",
                      BUDGET.format(lines=count, width=width)])
    return "\n".join(lines) + "\n"


# Tools a Python project might choose. Neither the brief nor the templates
# name one, so a generated file that does invented it, and an arm told a
# tool gets checks the other arms were never told to run.
TOOLING = re.compile(r"\b(mypy|pyright|ruff|flake8|pylint|pytest|uv|pip|"
                     r"poetry)\b", re.IGNORECASE)


def named_tooling(texts):
    """The tool names the texts carry, lower-cased and sorted; empty where
    they name none."""
    return sorted({match.lower() for text in texts
                   for match in TOOLING.findall(text)})


def over_budget(document, budget):
    """Every way a file exceeds its (lines, width) budget, as sentences;
    empty where it fits or has no budget."""
    if not budget:
        return []
    lines, width = budget
    text = document.rstrip("\n").split("\n")
    findings = []
    if len(text) > lines:
        findings.append("%d lines, over the budget of %d" % (len(text), lines))
    widest = max((len(line) for line in text), default=0)
    if widest > width:
        findings.append("a line of %d characters, over the width of %d"
                        % (widest, width))
    return findings


def read_brief(path=BRIEF):
    """The pinned brief, read from its only copy.

    Reading it here rather than restating it keeps one source of truth: a
    brief duplicated in code drifts from the one fixed before the round, and
    the arm would then be generated from something nobody agreed.
    """
    brief = read_input(path)
    if len(brief) < 100:
        raise TrialError("the brief read from %s is implausibly short: %r"
                         % (path, brief))
    return brief


def worktree_at(ref):
    """A throwaway worktree of the templates pinned to `ref`.

    Resolution reads a tree. Running the resolver against the checkout would
    read whatever is checked out now, which is the defect this avoids: a
    parallel session moves HEAD and the arm is silently generated from a
    different revision.
    """
    path = tempfile.mkdtemp(prefix="efficacy-%s-" % ref.replace(".", "_"))
    shutil.rmtree(path)
    proc = subprocess.run(["git", "-C", templates_root(), "worktree", "add",
                           "-q", "--detach", path, ref],
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise TrialError("could not create a worktree at %s: %s"
                         % (ref, proc.stderr.strip()))
    return path


def remove_worktree(path):
    subprocess.run(["git", "-C", templates_root(), "worktree", "remove",
                    "--force", path],
                   capture_output=True, text=True, encoding="utf-8")


def resolve_union(tree, roots):
    """The deduplicated file list for every root, in resolution order."""
    union = []
    for root in roots:
        proc = subprocess.run([sys.executable, "tools/resolve_chain.py", root],
                              cwd=tree, capture_output=True, text=True,
                              encoding="utf-8")
        if proc.returncode != 0:
            raise TrialError("resolving %s failed: %s"
                             % (root, (proc.stdout + proc.stderr).strip()))
        files = [line.strip() for line in proc.stdout.splitlines()
                 if line.strip().endswith(".md")]
        if not files:
            raise TrialError("root %s resolved to no files" % root)
        for name in files:
            if name not in union:
                union.append(name)
    return union


def read_chain(tree, files):
    """Concatenate the resolved templates, each under its own path."""
    parts = []
    for name in files:
        path = os.path.join(tree, name)
        if not os.path.exists(path):
            raise TrialError("resolved file %s is not in the tree" % name)
        with io.open(path, encoding="utf-8") as handle:
            parts.append("<!-- %s -->\n%s" % (name, handle.read()))
    return "\n\n".join(parts)


def scan(text, label, tokens):
    """Every listed token this text carries, or None if it carries none."""
    hits = {token: text.count(token) for token in tokens if token in text}
    if not hits:
        return None
    return {"where": label, "hits": hits}


def build_prompt(tree, arm, files):
    """The model arm's prompt: its model, the brief, agents.md, the chain."""
    with io.open(os.path.join(tree, "templates", "core", "agents.md"),
                 encoding="utf-8") as handle:
        agents = handle.read()
    return INSTRUCTION % (arm_clause(arm), read_brief(), agents,
                          read_chain(tree, files))


def reference_text(files, brief):
    """The `reference` arm's file for a chain and a brief, the same for the
    same two."""
    listed = "\n".join("- `%s/%s`" % (VENDORED["into"], name)
                       for name in files)
    return REFERENCE.format(brief=brief.strip(), into=VENDORED["into"],
                            files=listed)


# The templates' manifest: one entry per template, with the file it lives in
# and its one-line description. The fields are frozen for the 3.x line, so
# three line patterns read them without a YAML library.
MANIFEST = os.path.join("templates", "manifest.yaml")
MANIFEST_ID = re.compile(r"^\s*- id: (\S+)\s*$")
MANIFEST_FIELD = re.compile(r"^\s*(file|description|deprecated): (.*?)\s*$")


def read_manifest(tree):
    """The manifest's live entries, {file: (id, description)}, a deprecated
    entry never shadowing the one that replaces it."""
    found_entries = []
    with io.open(os.path.join(tree, MANIFEST), encoding="utf-8") as handle:
        for line in handle:
            found = MANIFEST_ID.match(line)
            if found:
                found_entries.append({"id": found.group(1)})
                continue
            found = MANIFEST_FIELD.match(line)
            if found and found_entries:
                found_entries[-1][found.group(1)] = found.group(2)
    # An entry is read whole before it counts, since its fields come in any
    # order and a deprecation may follow its description.
    entries = {}
    for entry in found_entries:
        if "file" in entry and "description" in entry \
                and "deprecated" not in entry:
            entries.setdefault(entry["file"],
                               (entry["id"], entry["description"]))
    return entries


def moments(tree, files):
    """Each template of the chain with the moment that calls for it: (id,
    description, file), in the chain's order.

    The moment is the manifest's own description of the template, so the
    map puts no person's judgement into the arm, and the two map arms name
    the same moments from the same source.
    """
    entries = read_manifest(tree)
    rows = []
    for name in files:
        if name not in entries:
            raise TrialError("%s is in the chain and not in the manifest, so "
                             "the map has no moment for it" % name)
        kind, description = entries[name]
        rows.append((kind, description, name))
    return rows


# The map arms' root file. The two differ in one column and one verb: what
# the agent does when a moment arrives, read a vendored file or load a skill.
# Everything before the table says the same thing in both, so the arms
# measure the mechanism and not the wording. The brief comes first, as in
# every arm's root.
MAP = """\
# tariff

{brief}

{paragraph}

| When the work first touches | {column} |
| --- | --- |
{rows}
"""

MAP_PARAGRAPH = ("The project's rules are the templates below, one per topic. "
                 "Do not read them before the work starts. {when}, {act}; "
                 "then apply every rule it holds that fits this project.")

MAP_LOAD = {
    "read": {
        "when": "The first time the work touches a template's topics",
        "act": "read that template, vendored at `{into}/` at the revision "
               "the project adopted",
        "column": "Read first",
        "cell": "`{into}/{file}`",
    },
    "skill": {
        "when": "The first time the work touches a template's topics",
        "act": "load that template's skill",
        "column": "Load first",
        "cell": "`{kind}`",
    },
}


def map_text(rows, load, brief):
    """A map arm's root file for a brief: the same moments, in the same
    order, for either way of loading."""
    words = MAP_LOAD[load]
    into = VENDORED["into"]
    table = "\n".join(
        "| %s | %s |" % (description,
                         words["cell"].format(into=into, file=name, kind=kind))
        for kind, description, name in rows)
    paragraph = textwrap.fill(
        MAP_PARAGRAPH.format(when=words["when"],
                             act=words["act"].format(into=into)), width=79)
    return MAP.format(brief=brief.strip(), paragraph=paragraph,
                      column=words["column"], rows=table)


def template_skills(tree, rows):
    """One skill per template of the chain, {id: SKILL.md text}: the
    manifest's description as what the skill is for, and the template
    verbatim as its body."""
    skills = {}
    for kind, description, name in rows:
        with io.open(os.path.join(tree, name), encoding="utf-8") as handle:
            body = handle.read()
        skills[kind] = ("---\nname: %s\ndescription: %s\n---\n\n%s"
                        % (kind, description, body))
    return skills


def fill_facts(text):
    """The emitted root file with every fact slot filled from the brief."""
    for slot, value in FACTS.items():
        text = text.replace(slot, value)
    left = SLOT.findall(text)
    if left:
        raise TrialError("the emitted root file has slots the brief does not "
                         "fill: %s" % ", ".join(sorted(set(left))))
    return text


def emit_arm(tree, roots):
    """The `skills` arm, built by the templates' emitter: the root file with
    its facts filled, and {kind: SKILL.md text}."""
    out = tempfile.mkdtemp(prefix="efficacy-emit-")
    declined = os.path.join(out, "declined.txt")
    with io.open(declined, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(entry + "\n" for entry in ROUND5_DECLINED))
    try:
        proc = subprocess.run(
            [sys.executable, "tools/resolve_chain.py", "--emit",
             os.path.join(out, "emitted"), "--declined", declined] + roots,
            cwd=tree, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise TrialError("the emitter failed: %s"
                             % (proc.stdout + proc.stderr).strip())
        with io.open(os.path.join(out, "emitted", "AGENTS.md"),
                     encoding="utf-8") as h:
            root = fill_facts(h.read())
        skills = {}
        base = os.path.join(out, "emitted", ".agents", "skills")
        for kind in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            with io.open(os.path.join(base, kind, "SKILL.md"),
                         encoding="utf-8") as h:
                skills[kind] = h.read()
        return root, skills
    finally:
        shutil.rmtree(out, ignore_errors=True)


def agent_command(home, model, effort, budget):
    """The generator invocation: isolated, offline, non-interactive."""
    argv = [
        agent_executable(), "-p",
        "--output-format", "json",
        "--model", model,
        "--effort", effort,
        "--permission-mode", "bypassPermissions",
        "--setting-sources", "",
        "--settings", os.path.join(home, "settings.json"),
        "--strict-mcp-config",
        "--disallowed-tools", "WebSearch", "WebFetch",
    ]
    if budget is not None:
        argv.extend(["--max-budget-usd", str(budget)])
    return argv


def extract_document(payload, raw):
    """The generated file, from the CLI's JSON envelope or its raw output."""
    if isinstance(payload, dict):
        for key in ("result", "text", "content"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return raw.strip()


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Generate one round-5 arm's context file.")
    parser.add_argument("--arm", choices=sorted(GENERATED),
                        help="the arm to generate; required for everything "
                             "but --self-test")
    parser.add_argument("--root",
                        help="scratch directory for the isolated home and the "
                             "record; MUST be outside this repository. "
                             "Required for everything but --self-test")
    parser.add_argument("--ref", default=ROUND5_REF,
                        help="the templates commit to resolve the chain at "
                             "(default %s, the registered one)" % ROUND5_REF)
    parser.add_argument("--templates",
                        help="a git clone of the templates repository, "
                             "upstream or a fork; overrides %s"
                             % TEMPLATES_ENV)
    parser.add_argument("--model", default="claude-sonnet-5")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--budget", type=float, default=None)
    parser.add_argument("--timeout", type=int, default=3600)
    parser.add_argument("--replace", action="store_true",
                        help="overwrite the arm's existing file; the arm "
                             "changes when you do")
    parser.add_argument("--dry-run", action="store_true",
                        help="build and scan the prompt, call no model")
    parser.add_argument("--self-test", action="store_true",
                        help="prove the scans, the fixed text and the facts "
                             "can fail, then exit")
    return parser.parse_args(argv)


def self_test():
    """A scan that cannot fail is not a control, and neither is a fill or a
    budget.

    Plants a specification-only token and requires the scan to report it,
    and a clean text to scan clean. Requires the reference text to name
    every file under the vendored path and to be the same twice. Requires a
    fact slot the brief does not fill to be refused, and every known slot
    filled. Requires a file one line over the budget, and one a character
    too wide, refused, and a file at both bounds kept.
    """
    clean = "A pricing and invoicing web application with discount rules."
    if scan(clean, "clean", PROMPT_TOKENS) is not None:
        print("FAIL: the scan fired on text carrying no specification token")
        return 1
    planted = clean + " Rounding is half-even to two places."
    found = scan(planted, "planted", PROMPT_TOKENS)
    if found is None or "half-even" not in found["hits"]:
        print("FAIL: the scan missed a planted specification token")
        return 1
    print("the leak scan reports a planted token and passes clean text")

    # The brief and the emitter's facts name the stack the spec fixes and no
    # tooling: a tool the project chose would reach only the arms that copy
    # it, and the arms would then differ in what they were told.
    told = [read_brief()] + list(FACTS.values())
    named = named_tooling(told)
    if named or "Python 3.12" not in told[0]:
        print("FAIL: the brief or the facts name tooling, or drop the "
              "stack: %r" % named)
        return 1
    print("the brief and the facts name the stack and no tooling")

    # A model arm may still fill a template's command placeholder with a
    # tool of its own choosing; such a file is refused.
    if (named_tooling(["Run `mypy --strict .` and `uv run pytest`."])
            != ["mypy", "pytest", "uv"]
            or named_tooling(["Use Ruff for linting and Pyright for types."])
            != ["pyright", "ruff"]
            or named_tooling(["Type-check at the strictest setting; "
                              "lint and format clean."])
            or "name no tool and no command" not in INSTRUCTION):
        print("FAIL: a generated file naming a tool is not caught, a clean "
              "one is, or the prompt does not forbid naming tools")
        return 1
    print("a generated file naming a tool is refused, and the prompt forbids "
          "one")

    files = ["templates/core/quality.md", "templates/backend/api.md"]
    planted_brief = "`tariff` - a planted brief - Python 3.12 / Flask 3\n"
    text = reference_text(files, planted_brief)
    if text != reference_text(files, planted_brief) or not all(
            "`%s/%s`" % (VENDORED["into"], f) in text for f in files):
        print("FAIL: the reference text is not the chain under the vendored "
              "path, the same every time")
        return 1
    print("the reference text names every file under %s/, the same twice"
          % VENDORED["into"])

    # A map is checked against a small tree of its own: a manifest with a
    # deprecated entry sharing a live one's file, and two templates.
    tree = tempfile.mkdtemp(prefix="efficacy-map-self-test-")
    try:
        chain = ["templates/core/quality.md", "templates/backend/api.md"]
        bodies = {chain[0]: "# Quality\n\n- Keep it simple (MUST)\n",
                  chain[1]: "# API\n\n- Version the contract\n"}
        for name, body in bodies.items():
            path = os.path.join(tree, *name.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, "w", encoding="utf-8", newline="\n") as h:
                h.write(body)
        manifest = os.path.join(tree, MANIFEST)
        with io.open(manifest, "w", encoding="utf-8", newline="\n") as h:
            h.write("version: \"1.0\"\n\nbase:\n"
                    "  - id: old-quality\n    file: templates/core/quality.md\n"
                    "    description: An old name\n"
                    "    deprecated: base-quality\n"
                    "  - id: base-quality\n    file: templates/core/quality.md\n"
                    "    description: Architecture, code style, testing\n"
                    "backend:\n"
                    "  - id: backend-api\n    file: templates/backend/api.md\n"
                    "    description: API-first, contracts, versioning\n")
        rows = moments(tree, chain)
        reading = map_text(rows, "read", planted_brief)
        loading = map_text(rows, "skill", planted_brief)

        # Every root the generator builds from fixed text states the same
        # project facts as the model arms are given: the brief, verbatim,
        # under the title and before any rule.
        opening = "# tariff\n\n%s\n" % planted_brief.strip()
        if not all(root.startswith(opening)
                   for root in (text, reading, loading)):
            print("FAIL: a fixed-text root does not open with the brief")
            return 1
        print("every fixed-text root opens with the brief, verbatim")
        first = [line.split(" | ")[0] for line in reading.splitlines()
                 if line.startswith("| ") and not line.startswith("| ---")]
        second = [line.split(" | ")[0] for line in loading.splitlines()
                  if line.startswith("| ") and not line.startswith("| ---")]
        expected = ["| When the work first touches",
                    "| Architecture, code style, testing",
                    "| API-first, contracts, versioning"]
        if first != expected or second != expected:
            print("FAIL: the two map arms do not name the same moments in "
                  "the chain's order: %r, %r" % (first, second))
            return 1
        print("the two map arms name the same moments in the chain's order")
        if any(reading.count("`%s/%s`" % (VENDORED["into"], name)) != 1
               for name in chain) or "`base-quality`" in reading:
            print("FAIL: the reading map does not name every template once "
                  "under the vendored path")
            return 1
        print("the reading map names every template of the chain once, under "
              "%s/" % VENDORED["into"])
        skills = template_skills(tree, rows)
        head = "---\nname: backend-api\ndescription: API-first, contracts, " \
               "versioning\n---\n\n"
        if sorted(skills) != ["backend-api", "base-quality"] \
                or skills["backend-api"] != head + bodies[chain[1]] \
                or "`backend-api`" not in loading:
            print("FAIL: a template skill is not its template verbatim under "
                  "the manifest's name and description")
            return 1
        print("each template skill is its template verbatim, named by the "
              "manifest")
        try:
            moments(tree, chain + ["templates/core/git.md"])
            print("FAIL: a chain file the manifest does not describe was "
                  "given a moment")
            return 1
        except TrialError:
            pass
        print("a chain file the manifest does not describe is refused")
    finally:
        shutil.rmtree(tree, ignore_errors=True)

    known = " ".join(FACTS)
    if SLOT.search(fill_facts(known)):
        print("FAIL: a known fact slot was left unfilled")
        return 1
    try:
        fill_facts(known + " {{unknown}}")
        print("FAIL: a slot the brief does not fill was kept")
        return 1
    except TrialError:
        pass
    print("every known fact slot is filled, and an unknown one is refused")

    budget = GENERATED["short"]["budget"]
    lines, width = budget
    at_bounds = "\n".join(["x" * width] * lines) + "\n"
    if over_budget(at_bounds, budget):
        print("FAIL: a file at both bounds was refused")
        return 1
    long = "\n".join(["x"] * (lines + 1)) + "\n"
    wide = "\n".join(["x" * (width + 1)] + ["x"] * (lines - 1)) + "\n"
    if not over_budget(long, budget) or not over_budget(wide, budget):
        print("FAIL: a file over the budget was kept")
        return 1
    if over_budget(long, None):
        print("FAIL: an arm with no budget refused a file")
        return 1
    print("the budget keeps a file at %d lines of %d characters and refuses "
          "one over either" % (lines, width))
    if "MUST be at most %d lines" % lines not in arm_clause("short") \
            or "measure every line against %d" % width \
            not in arm_clause("short") \
            or "budget" in arm_clause("inline").lower():
        print("FAIL: the budget clause is not in short's instruction alone")
        return 1
    print("the budget is stated in short's instruction and no other")

    # A generated file without its record cannot say which source, model and
    # ref made it, so the report could not cite how its arm was built.
    for arm in GENERATED:
        path = record_path(arm)
        if not os.path.isfile(output_path(arm)):
            continue
        try:
            with io.open(path, encoding="utf-8") as handle:
                record = json.load(handle)
        except (OSError, ValueError):
            record = {}
        if record.get("arm") != arm or record.get("outcome") != "generated":
            print("FAIL: %s has no generation record beside it" % arm)
            return 1
    print("every generated arm's file has its generation record beside it")
    return 0


def main(argv):
    options = parse_args(argv)
    if options.templates:
        os.environ[TEMPLATES_ENV] = options.templates
    if options.self_test:
        return self_test()
    if not options.root or not options.arm:
        print("refused: --root and --arm are required")
        return 2

    try:
        templates_root()
        assert_outside_repository(options.root)
    except TrialError as error:
        print("refused: %s" % error)
        return 1

    arm, entry = options.arm, GENERATED[options.arm]
    output = output_path(arm)
    if os.path.exists(output) and not options.replace:
        print("refused: %s already exists. An arm is generated once; "
              "regenerating changes the arm. Pass --replace if that is what "
              "you mean." % output)
        return 1

    os.makedirs(options.root, exist_ok=True)
    started_at = datetime.datetime.now()
    record = {"arm": arm, "kind": entry["kind"],
              "output_model": entry.get("model"), "ref": options.ref,
              "source": source_record(options.ref), "roots": ROUND5_ROOTS,
              "started_at": started_at.isoformat(timespec="seconds")}
    tree = worktree_at(options.ref)
    try:
        files = resolve_union(tree, ROUND5_ROOTS)
        record["commit"] = subprocess.run(
            ["git", "-C", tree, "rev-parse", "HEAD"], capture_output=True,
            text=True, encoding="utf-8").stdout.strip()
        record["resolved_files"] = files
        skills = {}
        if entry["kind"] == "fixed":
            document = reference_text(files, read_brief())
        elif entry["kind"] == "emit":
            document, skills = emit_arm(tree, ROUND5_ROOTS)
            record["declined"] = ROUND5_DECLINED
        elif entry["kind"] == "map":
            rows = moments(tree, files)
            document = map_text(rows, entry["load"], read_brief())
            if entry["load"] == "skill":
                skills = template_skills(tree, rows)
            record["load"] = entry["load"]
            record["moments"] = [{"skill": kind, "moment": description,
                                  "file": name}
                                 for kind, description, name in rows]
        else:
            prompt = build_prompt(tree, arm, files)
    finally:
        remove_worktree(tree)
    print("chain at %s (%s): %d unique files"
          % (options.ref, record["commit"][:8], len(files)))

    if entry["kind"] == "model":
        document = generate(options, record, prompt, started_at)
        if document is None:
            write_record(options.root, record, started_at)
            return 0 if record.get("outcome") == "dry-run" else 1

    # A file over its budget is refused whole rather than trimmed, since
    # trimming would put a person's judgement into the arm.
    record["budget"] = entry.get("budget")
    over = over_budget(document, entry.get("budget"))
    if over:
        record["outcome"] = "refused: over budget"
        record["over_budget"] = over
        print("refused: the generated file is over its budget: %s"
              % "; ".join(over))
        return write_record(options.root, record, started_at) or 1

    texts = [document] + list(skills.values())
    leak = scan("\n".join(texts), "generated files", NON_INVENTABLE)
    record["output_leak"] = leak
    if leak is not None:
        record["outcome"] = "refused: specification leaked"
        print("refused: the generated files carry data only the "
              "specification supplies: %r" % leak["hits"])
        return write_record(options.root, record, started_at) or 1

    tools = named_tooling(texts)
    record["named_tooling"] = tools
    if tools:
        record["outcome"] = "refused: names tooling"
        print("refused: the generated files name tools the brief does not: "
              "%s" % ", ".join(tools))
        return write_record(options.root, record, started_at) or 1

    # A dry run of any arm stops here: it writes nothing under `arms/`,
    # so it never replaces a committed file or its record.
    if options.dry_run:
        record["outcome"] = "dry-run"
        print("dry run: %s would be %d words%s; nothing written under arms/"
              % (output, len(document.split()),
                 ", with %d skills" % len(skills) if skills else ""))
        return write_record(options.root, record, started_at)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with io.open(output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(document.rstrip() + "\n")
    if skills:
        shutil.rmtree(skills_path(arm), ignore_errors=True)
        for kind, text in skills.items():
            path = os.path.join(skills_path(arm), kind, "SKILL.md")
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
        record["skills"] = {kind: len(text.split())
                            for kind, text in skills.items()}
    record["outcome"] = "generated"
    record["output"] = output
    record["output_lines"] = document.rstrip("\n").count("\n") + 1
    record["output_words"] = len(document.split())
    print("wrote %s: %d lines, %d words%s"
          % (output, record["output_lines"], record["output_words"],
             ", %d skills" % len(skills) if skills else ""))
    keep_record(record, record_path(arm))
    print("Record kept beside it: %s" % record_path(arm))
    return write_record(options.root, record, started_at)


def generate(options, record, prompt, started_at):
    """Run the model generation; the document, or None with the record
    saying why not."""
    record["prompt_chars"] = len(prompt)
    leak = scan(prompt, "prompt", PROMPT_TOKENS)
    record["prompt_leak"] = leak
    if leak is not None:
        record["outcome"] = "refused: prompt leak"
        print("refused: the prompt carries specification-only tokens, so the "
              "wiring is wrong: %r" % leak["hits"])
        return None
    prompt_path = os.path.join(options.root, "arm-%s-prompt.txt" % options.arm)
    with io.open(prompt_path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(prompt)
    record["prompt_file"] = prompt_path
    if options.dry_run:
        record["outcome"] = "dry-run"
        print("dry run: prompt written to %s, no model called" % prompt_path)
        return None

    home = prepare_home(options.root)
    try:
        record["auth_probe"] = assert_authenticated(
            home, agent_environment, agent_executable())
    except TrialError as error:
        record["outcome"] = "refused: not authenticated"
        print("refused: %s" % error)
        return None
    argv_ = agent_command(home, options.model, options.effort, options.budget)
    record.update({"command": argv_, "model": options.model,
                   "effort": options.effort})
    started = time.monotonic()
    try:
        proc = subprocess.run(argv_, input=prompt, cwd=options.root,
                              env=agent_environment(home),
                              capture_output=True, text=True,
                              encoding="utf-8", timeout=options.timeout)
    except subprocess.TimeoutExpired:
        record["outcome"] = "timeout"
        print("the generator did not finish within %ds" % options.timeout)
        return None
    record["elapsed_s"] = round(time.monotonic() - started, 1)
    record["exit_status"] = proc.returncode
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        payload = None
    record["result"] = payload if isinstance(payload, dict) else None
    document = extract_document(payload, proc.stdout)
    if proc.returncode != 0 or not document:
        record["outcome"] = "failed"
        record["stderr"] = proc.stderr[-4000:]
        print("the generator failed (status %s)" % proc.returncode)
        return None
    return document


def keep_record(record, path):
    """Write the record of the generation behind the committed file."""
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)


def write_record(root, record, started_at):
    path = os.path.join(root, "arm-%s-generation-%s.json"
                        % (record["arm"],
                           started_at.strftime("%Y-%m-%dT%H-%M-%S")))
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(record, handle, indent=2)
    print("Record: %s" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
