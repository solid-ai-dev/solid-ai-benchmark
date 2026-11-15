"""Build one arm's context file from one chain of the templates, by script.

Every arm is made from one chain of the templates at one commit, so the arms
differ only in how they deliver it, and no model writes any of them:

- `reference` is fixed text naming each template of the chain
- `inline` is what `resolve_chain.py --emit --inline-skills` builds: one root
  file holding every adopted rule, the facts filled from the brief
- `skills` is what `resolve_chain.py --emit` builds: the root file and one
  skill per kind of task, the facts filled from the brief
- `lazyref` and `lazyskills` are fixed text too: a map from the topics the
  manifest gives each template of the chain to that template, read as a file
  or loaded as a skill the first time the work touches one of them, and for
  `lazyskills` one skill per template, holding it verbatim

It writes `arms/<arm>/CLAUDE.md` (and, for an arm with skills, the skills
beside it), and refuses to keep a result the specification leaked into.

The same ref gives the same bytes, so the self-test rebuilds every committed
arm and fails on any difference. It still refuses to overwrite an existing
file without `--replace`, since a new ref is a new arm.
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

from harness import (ROUND5_DECLINED, ROUND5_REF,  # noqa: E402
                     ROUND5_ROOTS,
                     TEMPLATES_ENV, VENDORED, TrialError, source_record,
                     templates_root, assert_outside_repository, read_input)

HERE = os.path.dirname(os.path.abspath(__file__))

# The generated arms' project brief lives in a file of its own, its only
# copy, for the reason `harness.CHANGE_PROMPT` gives.
BRIEF = os.path.join(HERE, "brief.txt")

# The arms this module makes, each with the directory under `arms/` its file
# and record live in, and how it is made: fixed text, the templates' emitter
# with its skills apart or inlined, or a map of the chain's topics read as
# files or loaded as skills. An arm a model or a person writes would change
# with every writing, so none is made here.
GENERATED = {
    "reference": {"dir": "reference", "kind": "fixed"},
    "inline": {"dir": "inline", "kind": "emit", "inline_skills": True},
    "skills": {"dir": "skills", "kind": "emit", "inline_skills": False},
    "lazyref": {"dir": "lazyref", "kind": "map", "load": "read"},
    "lazyskills": {"dir": "lazyskills", "kind": "map", "load": "skill"},
}

# Every arm with a generation record under `arms/`, by its directory: the
# arms built here, and the pilot's written arms, whose records stay so a
# pilot round's report still cites how each was made and what it vendored.
RECORDED = dict({arm: entry["dir"] for arm, entry in GENERATED.items()},
                hybrid="hybrid", short="short")


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
    return os.path.join(HERE, "arms", RECORDED[arm], "generation.json")


# The output scan. No arm is handed `SPEC.md`, so only arbitrary data the
# specification alone supplies counts as a leak: a seed sku, a rule id, a
# figure from the worked example. A name the templates' own rules imply,
# such as an error base called after the package, is no leak.
NON_INVENTABLE = [
    "WID-1", "GAD-2", "BOK-3", "SRV-4", "SEE-5",
    "r-tier-wid", "r-bulk-see", "r-pct-bok", "r-pct-all",
    "c-welcome", "c-tenoff",
    "228.35", "227.07", "195.24",
    "Ada Example", "ada@example.com",
]

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
# than inventing an answer. The description slot, under the title, takes
# the brief whole, so an emitted root opens as every other arm's does.
BRIEF_SLOT = "{{one-sentence description}}"
FACTS = {
    "{{project-name}}": "tariff",
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


# The tools a Python project most often chooses. Neither the brief nor the
# templates name one, so a built file that does carries a tool the chain
# took in, and an arm told a tool gets checks the other arms were never told
# to run. The list is a guard against the common case, not a proof: a rarer
# tool is caught by reading the built file, which is committed and reviewed.
TOOLING = re.compile(r"\b(mypy|pyright|ruff|flake8|pylint|black|isort|"
                     r"pytest|tox|nox|bandit|uv|pip|pipenv|poetry|hatch)\b",
                     re.IGNORECASE)


def named_tooling(texts):
    """The tool names the texts carry, lower-cased and sorted; empty where
    they name none."""
    return sorted({match.lower() for text in texts
                   for match in TOOLING.findall(text)})


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


def scan(text, label, tokens):
    """Every listed token this text carries, or None if it carries none."""
    hits = {token: text.count(token) for token in tokens if token in text}
    if not hits:
        return None
    return {"where": label, "hits": hits}


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


def fill_facts(text, brief):
    """The emitted root file with every fact slot filled from the brief, the
    description slot with the brief itself."""
    text = text.replace(BRIEF_SLOT, brief.strip())
    for slot, value in FACTS.items():
        text = text.replace(slot, value)
    left = SLOT.findall(text)
    if left:
        raise TrialError("the emitted root file has slots the brief does not "
                         "fill: %s" % ", ".join(sorted(set(left))))
    return text


def emit_arm(tree, roots, brief, inline_skills):
    """An arm the templates' emitter builds: the root file with its facts
    filled, and {kind: SKILL.md text}, empty where the skills are inlined
    into the root."""
    out = tempfile.mkdtemp(prefix="efficacy-emit-")
    declined = os.path.join(out, "declined.txt")
    with io.open(declined, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(entry + "\n" for entry in ROUND5_DECLINED))
    try:
        proc = subprocess.run(
            [sys.executable, "tools/resolve_chain.py", "--emit",
             os.path.join(out, "emitted"), "--declined", declined]
            + (["--inline-skills"] if inline_skills else []) + roots,
            cwd=tree, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise TrialError("the emitter failed: %s"
                             % (proc.stdout + proc.stderr).strip())
        with io.open(os.path.join(out, "emitted", "AGENTS.md"),
                     encoding="utf-8") as h:
            root = fill_facts(h.read(), brief)
        skills = {}
        base = os.path.join(out, "emitted", ".agents", "skills")
        for kind in sorted(os.listdir(base)) if os.path.isdir(base) else []:
            with io.open(os.path.join(base, kind, "SKILL.md"),
                         encoding="utf-8") as h:
                skills[kind] = h.read()
        return root, skills
    finally:
        shutil.rmtree(out, ignore_errors=True)


def build_arm(arm, ref, brief):
    """One arm's files at a templates ref: (document, {kind: SKILL.md text},
    what the record says of how they were built). The same arm, ref and
    brief always give the same files."""
    entry = GENERATED[arm]
    tree = worktree_at(ref)
    try:
        files = resolve_union(tree, ROUND5_ROOTS)
        details = {"commit": subprocess.run(
            ["git", "-C", tree, "rev-parse", "HEAD"], capture_output=True,
            text=True, encoding="utf-8").stdout.strip(),
            "resolved_files": files}
        skills = {}
        if entry["kind"] == "fixed":
            document = reference_text(files, brief)
        elif entry["kind"] == "emit":
            document, skills = emit_arm(tree, ROUND5_ROOTS, brief,
                                        entry["inline_skills"])
            details["declined"] = ROUND5_DECLINED
            details["inline_skills"] = entry["inline_skills"]
        else:
            rows = moments(tree, files)
            document = map_text(rows, entry["load"], brief)
            if entry["load"] == "skill":
                skills = template_skills(tree, rows)
            details["load"] = entry["load"]
            details["moments"] = [{"skill": kind, "moment": description,
                                   "file": name}
                                  for kind, description, name in rows]
    finally:
        remove_worktree(tree)
    return document.rstrip() + "\n", skills, details


def committed_arm(arm):
    """An arm's committed files: (document, {kind: SKILL.md text}), or None
    where the arm has no committed file."""
    path = output_path(arm)
    if not os.path.isfile(path):
        return None
    with io.open(path, encoding="utf-8", newline="") as handle:
        document = handle.read()
    skills = {}
    base = skills_path(arm)
    for kind in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        with io.open(os.path.join(base, kind, "SKILL.md"), encoding="utf-8",
                     newline="") as handle:
            skills[kind] = handle.read()
    return document, skills


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Build one arm's context file from the templates.")
    parser.add_argument("--arm", choices=sorted(GENERATED),
                        help="the arm to build; required for everything "
                             "but --self-test")
    parser.add_argument("--root",
                        help="scratch directory for the record; MUST be "
                             "outside this repository. Required for "
                             "everything but --self-test")
    parser.add_argument("--ref", default=ROUND5_REF,
                        help="the templates commit to resolve the chain at "
                             "(default %s, the registered one)" % ROUND5_REF)
    parser.add_argument("--templates",
                        help="a git clone of the templates repository, "
                             "upstream or a fork; overrides %s"
                             % TEMPLATES_ENV)
    parser.add_argument("--replace", action="store_true",
                        help="overwrite the arm's existing file; the arm "
                             "changes when you do")
    parser.add_argument("--dry-run", action="store_true",
                        help="build and scan the files, write nothing under "
                             "arms/")
    parser.add_argument("--self-test", action="store_true",
                        help="prove the scans, the fixed text and the facts "
                             "can fail, rebuild every committed arm, then "
                             "exit")
    return parser.parse_args(argv)


def self_test():
    """A scan that cannot fail is not a control, and neither is a fill or a
    build said to be the same twice.

    Plants a specification-only token and requires the scan to report it,
    and a clean text to scan clean. Requires the reference text to name
    every file under the vendored path and to be the same twice. Requires a
    fact slot the brief does not fill to be refused, and every known slot
    filled. Rebuilds every committed arm at its recorded ref and requires
    the same bytes, and requires every root to open with the brief.
    """
    clean = "A pricing and invoicing web application with discount rules."
    if scan(clean, "clean", NON_INVENTABLE) is not None:
        print("FAIL: the scan fired on text carrying no specification token")
        return 1
    planted = clean + " The seed product WID-1 costs 228.35."
    found = scan(planted, "planted", NON_INVENTABLE)
    if found is None or "WID-1" not in found["hits"]:
        print("FAIL: the scan missed a planted specification token")
        return 1
    print("the leak scan reports a planted token and passes clean text")

    # The brief and the emitter's facts name the stack the spec fixes and no
    # tooling: a tool the project chose would reach only the arms that copy
    # it, and the arms would then differ in what they were told.
    brief = read_brief()
    told = [brief] + list(FACTS.values())
    named = named_tooling(told)
    if named or "Python 3.12" not in told[0]:
        print("FAIL: the brief or the facts name tooling, or drop the "
              "stack: %r" % named)
        return 1
    print("the brief and the facts name the stack and no tooling")

    # A chain that took in a tool's name would hand it to the arms that
    # copy the chain's text; such a file is refused.
    if (named_tooling(["Run `mypy --strict .` and `uv run pytest`."])
            != ["mypy", "pytest", "uv"]
            or named_tooling(["Use Ruff for linting and Pyright for types."])
            != ["pyright", "ruff"]
            or named_tooling(["Run black --check . and isort --check ."])
            != ["black", "isort"]
            or named_tooling(["Type-check at the strictest setting; "
                              "lint and format clean."])):
        print("FAIL: a built file naming a tool is not caught, or a clean "
              "one is")
        return 1
    print("a built file naming a tool is refused")

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

        # Every root the generator builds states the same project facts:
        # the brief, verbatim, under the title and before any rule. The
        # emitter's own head is filled the same way.
        opening = "# tariff\n\n%s\n" % planted_brief.strip()
        emitted = fill_facts("# {{project-name}}\n\n%s\n\n- Owner: {{owner}}\n"
                             % BRIEF_SLOT, planted_brief)
        if not all(root.startswith(opening)
                   for root in (text, reading, loading, emitted)):
            print("FAIL: a built root does not open with the brief")
            return 1
        print("every built root opens with the brief, verbatim, the "
              "emitted ones too")
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

    known = " ".join([BRIEF_SLOT] + list(FACTS))
    if SLOT.search(fill_facts(known, planted_brief)):
        print("FAIL: a known fact slot was left unfilled")
        return 1
    try:
        fill_facts(known + " {{unknown}}", planted_brief)
        print("FAIL: a slot the brief does not fill was kept")
        return 1
    except TrialError:
        pass
    print("every known fact slot is filled, and an unknown one is refused")

    # A file without its record cannot say which source and ref made it, so
    # the report could not cite how its arm was built.
    records = {}
    for arm in GENERATED:
        if committed_arm(arm) is None:
            continue
        try:
            with io.open(record_path(arm), encoding="utf-8") as handle:
                records[arm] = json.load(handle)
        except (OSError, ValueError):
            records[arm] = {}
        if records[arm].get("arm") != arm \
                or records[arm].get("outcome") != "generated":
            print("FAIL: %s has no generation record beside it" % arm)
            return 1
    print("every built arm's file has its generation record beside it")

    # The committed files are what the script builds now at their recorded
    # ref, byte for byte: a hand edit, or a build that varies, fails here.
    # The first arm is built twice, so a build that varies from one run to
    # the next fails even where nothing is committed yet.
    for index, arm in enumerate(sorted(records)):
        ref = records[arm].get("ref")
        built = build_arm(arm, ref, brief)
        if index == 0 and build_arm(arm, ref, brief) != built:
            print("FAIL: %s built twice at %s gave different files"
                  % (arm, ref))
            return 1
        document, skills = committed_arm(arm)
        if (document, skills) != built[:2]:
            print("FAIL: %s's committed files are not what the script builds "
                  "at %s" % (arm, ref))
            return 1
        if not document.startswith("# tariff\n\n%s\n" % brief.strip()):
            print("FAIL: %s's committed root does not open with the brief"
                  % arm)
            return 1
    print("every committed arm is what the script builds at its recorded "
          "ref, byte for byte, the same twice")
    print("every committed arm's root opens with the brief, verbatim")
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
        print("refused: %s already exists. An arm is built once per ref; "
              "a new ref is a new arm. Pass --replace if that is what you "
              "mean." % output)
        return 1

    os.makedirs(options.root, exist_ok=True)
    started_at = datetime.datetime.now()
    record = {"arm": arm, "kind": entry["kind"], "ref": options.ref,
              "source": source_record(options.ref), "roots": ROUND5_ROOTS,
              "started_at": started_at.isoformat(timespec="seconds")}
    document, skills, details = build_arm(arm, options.ref, read_brief())
    record.update(details)
    print("chain at %s (%s): %d unique files"
          % (options.ref, record["commit"][:8],
             len(record["resolved_files"])))

    texts = [document] + list(skills.values())
    leak = scan("\n".join(texts), "built files", NON_INVENTABLE)
    record["output_leak"] = leak
    if leak is not None:
        record["outcome"] = "refused: specification leaked"
        print("refused: the built files carry data only the specification "
              "supplies: %r" % leak["hits"])
        return write_record(options.root, record, started_at) or 1

    tools = named_tooling(texts)
    record["named_tooling"] = tools
    if tools:
        record["outcome"] = "refused: names tooling"
        print("refused: the built files name tools the brief does not: %s"
              % ", ".join(tools))
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
        handle.write(document)
    shutil.rmtree(skills_path(arm), ignore_errors=True)
    for kind, text in skills.items():
        path = os.path.join(skills_path(arm), kind, "SKILL.md")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    if skills:
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
