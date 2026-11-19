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
- `lazysections` is what `resolve_chain.py --emit --sections` builds: a root
  file that maps each topic to a section file, read the first time the work
  touches it, and the section files, every adopted rule in one of them
- `lazyrefold` is `lazyref` built at the parent of the templates commit that
  cuts the check loop to one check command, so the two differ by it alone

It writes `arms/<arm>/CLAUDE.md` (and, for an arm with skills or section
files, those beside it), and refuses to keep a result the specification
leaked into.

The same ref gives the same bytes, so the self-test rebuilds every committed
arm and fails on any difference. It still refuses to overwrite an existing
file without `--replace`, since a new ref is a new arm.
"""

import argparse
import datetime
import difflib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import textwrap

from harness import (ROUND5_DECLINED, ROUND5_REF,  # noqa: E402
                     ROUND5_ROOTS, SECTIONS_INTO, arm_vendor,
                     TEMPLATES_ENV, VENDORED, TrialError, source_record,
                     templates_root, assert_outside_repository, read_input)

HERE = os.path.dirname(os.path.abspath(__file__))

# The generated arms' project brief lives in a file of its own, its only
# copy, for the reason `harness.CHANGE_PROMPT` gives.
BRIEF = os.path.join(HERE, "brief.txt")

# The arms this module makes, each with the directory under `arms/` its file
# and record live in, and how it is made: fixed text, the templates' emitter
# with its skills apart, inlined or cut into section files, or a map of the
# chain's topics read as files or loaded as skills. An arm a model or a
# person writes would change with every writing, so none is made here.
GENERATED = {
    "reference": {"dir": "reference", "kind": "fixed"},
    "inline": {"dir": "inline", "kind": "emit", "inline_skills": True},
    "skills": {"dir": "skills", "kind": "emit", "inline_skills": False},
    "lazyref": {"dir": "lazyref", "kind": "map", "load": "read"},
    "lazyskills": {"dir": "lazyskills", "kind": "map", "load": "skill"},
    "lazysections": {"dir": "lazysections", "kind": "emit",
                     "inline_skills": False, "sections": True},
    "lazyrefold": {"dir": "lazyrefold", "kind": "map", "load": "read"},
}

# The arms that hand the agent its rules on demand rather than up front. No
# such arm may tell the agent to read everything at the start, or it loads
# the whole chain and measures nothing of loading on demand.
ON_DEMAND = ("lazyref", "lazyskills", "lazysections", "lazyrefold")

# The templates commit that cuts the check loop to one check command run
# before each commit, the file it changes and the section it changes there.
# `lazyrefold` is `lazyref` built at its parent, so the pair measures it.
CHECK_LOOP = {"commit": "a8079352", "file": "templates/core/quality.md",
              "section": "## Static checks"}

# Where the templates' emitter writes its skills, inside its output.
EMITTED_SKILLS = ".agents/skills"

# Every arm with a generation record under `arms/`, by its directory: the
# arms built here, and the pilot's written arms, whose records stay so a
# pilot round's report still cites how each was made and what it vendored.
RECORDED = dict({arm: entry["dir"] for arm, entry in GENERATED.items()},
                hybrid="hybrid", short="short")


def output_path(arm):
    """Where an arm's generated file is committed."""
    return os.path.join(HERE, "arms", GENERATED[arm]["dir"], "CLAUDE.md")


def parts_path(arm):
    """Where an arm's generated skills, one folder a kind, or its section
    files, one folder a template, are committed."""
    return os.path.join(HERE, "arms", GENERATED[arm]["dir"],
                        "sections" if GENERATED[arm].get("sections")
                        else "skills")


def read_tree(base, newline=None):
    """Every file under a folder, {path below it, with `/`: text}; empty
    where the folder does not exist."""
    files = {}
    for folder, _, names in os.walk(base):
        for name in names:
            path = os.path.join(folder, name)
            relative = os.path.relpath(path, base).replace(os.sep, "/")
            with io.open(path, encoding="utf-8", newline=newline) as handle:
                files[relative] = handle.read()
    return dict(sorted(files.items()))


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


def emit_arm(tree, roots, brief, entry):
    """An arm the templates' emitter builds: the root file with its facts
    filled, and its skills or section files, {path below their folder:
    text}, empty where the skills are inlined into the root."""
    out = tempfile.mkdtemp(prefix="efficacy-emit-")
    declined = os.path.join(out, "declined.txt")
    with io.open(declined, "w", encoding="utf-8", newline="\n") as handle:
        handle.write("".join(line + "\n" for line in ROUND5_DECLINED))
    flags = (["--inline-skills"] if entry["inline_skills"] else []) \
        + (["--sections"] if entry.get("sections") else [])
    try:
        proc = subprocess.run(
            [sys.executable, "tools/resolve_chain.py", "--emit",
             os.path.join(out, "emitted"), "--declined", declined]
            + flags + roots,
            cwd=tree, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise TrialError("the emitter failed: %s"
                             % (proc.stdout + proc.stderr).strip())
        with io.open(os.path.join(out, "emitted", "AGENTS.md"),
                     encoding="utf-8") as h:
            root = fill_facts(h.read(), brief)
        folder = SECTIONS_INTO if entry.get("sections") else EMITTED_SKILLS
        parts = read_tree(os.path.join(out, "emitted", *folder.split("/")))
        return root, parts
    finally:
        shutil.rmtree(out, ignore_errors=True)


def build_arm(arm, ref, brief):
    """One arm's files at a templates ref: (document, its skills or section
    files as {path below their folder: text}, what the record says of how
    they were built). The same arm, ref and brief always give the same
    files."""
    entry = GENERATED[arm]
    tree = worktree_at(ref)
    try:
        files = resolve_union(tree, ROUND5_ROOTS)
        details = {"commit": subprocess.run(
            ["git", "-C", tree, "rev-parse", "HEAD"], capture_output=True,
            text=True, encoding="utf-8").stdout.strip(),
            "resolved_files": files}
        parts = {}
        if entry["kind"] == "fixed":
            document = reference_text(files, brief)
        elif entry["kind"] == "emit":
            document, parts = emit_arm(tree, ROUND5_ROOTS, brief, entry)
            details["declined"] = ROUND5_DECLINED
            details["inline_skills"] = entry["inline_skills"]
            if entry.get("sections"):
                details["sections"] = True
        else:
            rows = moments(tree, files)
            document = map_text(rows, entry["load"], brief)
            if entry["load"] == "skill":
                parts = {"%s/SKILL.md" % kind: text for kind, text
                         in sorted(template_skills(tree, rows).items())}
            details["load"] = entry["load"]
            details["moments"] = [{"skill": kind, "moment": description,
                                   "file": name}
                                  for kind, description, name in rows]
    finally:
        remove_worktree(tree)
    return document.rstrip() + "\n", parts, details


def committed_arm(arm):
    """An arm's committed files: (document, its skills or section files as
    {path below their folder: text}), or None where the arm has no
    committed file."""
    path = output_path(arm)
    if not os.path.isfile(path):
        return None
    with io.open(path, encoding="utf-8", newline="") as handle:
        document = handle.read()
    return document, read_tree(parts_path(arm), newline="")


def vendored_files(ref):
    """The templates a vendoring arm's workspace carries at a ref, as
    {workspace path: text}."""
    proc = subprocess.run(["git", "-C", templates_root(), "archive",
                           "--format=tar", ref, VENDORED["path"]],
                          capture_output=True)
    if proc.returncode != 0:
        raise TrialError("could not export %s at %s: %s"
                         % (VENDORED["path"], ref,
                            proc.stderr.decode("utf-8", "replace").strip()))
    files = {}
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
        for member in archive.getmembers():
            if member.isfile():
                data = archive.extractfile(member).read()
                files["%s/%s" % (VENDORED["into"], member.name)] = \
                    data.decode("utf-8", "replace")
    return files


def templates_git(*args):
    """What a git command prints in the templates clone; raises on a
    non-zero status."""
    proc = subprocess.run(["git", "-C", templates_root()] + list(args),
                          capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise TrialError("git %s failed in the templates clone: %s"
                         % (" ".join(args), proc.stderr.strip()))
    return proc.stdout


def changed_lines(old, new):
    """The files two sets of files differ in, {path: (removed lines, added
    lines)}, a file missing from one set read as empty."""
    changed = {}
    for path in sorted(set(old) | set(new)):
        before = old.get(path, "").splitlines()
        after = new.get(path, "").splitlines()
        if before == after:
            continue
        removed, added = [], []
        matcher = difflib.SequenceMatcher(None, before, after, autojunk=False)
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != "equal":
                removed += before[i1:i2]
                added += after[j1:j2]
        changed[path] = (removed, added)
    return changed


HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def section_span(text, heading):
    """The 1-based lines a level-two section runs over, its heading to the
    line before the next level-two heading outside a fence; None where the
    text has no such heading."""
    lines, start, fence = text.splitlines(), None, False
    for number, line in enumerate(lines, 1):
        if line.lstrip().startswith("```"):
            fence = not fence
        elif not fence and line.startswith("## "):
            if start is not None:
                return start, number - 1
            if line.rstrip() == heading:
                start = number
    return (start, len(lines)) if start is not None else None


def commit_change(change):
    """A templates commit's change to one file: (removed lines, added
    lines), from the templates' own diff of that commit, and whether every
    changed line lies in the named section, before and after."""
    commit, name = change["commit"], change["file"]
    before = templates_git("show", "%s^:%s" % (commit, name))
    after = templates_git("show", "%s:%s" % (commit, name))
    spans = (section_span(before, change["section"]),
             section_span(after, change["section"]))
    removed, added, inside, hunks = [], [], None not in spans, False
    for line in templates_git("diff", "-U0", "--no-color", "--no-ext-diff",
                              "%s^" % commit, commit, "--",
                              name).splitlines():
        hunk = HUNK.match(line)
        if hunk:
            hunks = True
            for (start, count), span in zip(
                    ((hunk.group(1), hunk.group(2)),
                     (hunk.group(3), hunk.group(4))), spans):
                start, count = int(start), int(count or 1)
                if count and span and not (span[0] <= start
                                           and start + count - 1 <= span[1]):
                    inside = False
        elif hunks and line.startswith("-"):
            removed.append(line[1:])
        elif hunks and line.startswith("+"):
            added.append(line[1:])
    return removed, added, inside and bool(removed or added)


def pair_findings(old, new, path, change):
    """What makes two arms' files differ by more or less than one file's
    change: a file that differs besides `path`, or a change to it other
    than the lines given."""
    changed = changed_lines(old, new)
    findings = ["%s differs too" % other for other in changed
                if other != path]
    if changed.get(path, ([], [])) != change:
        findings.append("%s does not differ by exactly the commit's lines"
                        % path)
    return findings


def heading_blocks(text):
    """A Markdown text cut at each heading outside a fence: each block's
    heading path and its non-blank lines that are not headings."""
    blocks, stack, fence = [((), [])], [], None
    for line in text.splitlines():
        run = re.match(r"^\s*(`{3,}|~{3,})", line)
        heading = None if (fence or run) else re.match(r"^(#{1,6})\s", line)
        if run:
            mark = run.group(1)
            if fence is None:
                fence = mark
            elif mark[0] == fence[0] and len(mark) >= len(fence):
                fence = None
        if heading:
            level = len(heading.group(1))
            while stack and stack[-1][0] >= level:
                stack.pop()
            stack.append((level, line))
            blocks.append((tuple(h for _, h in stack), []))
        elif line.strip():
            blocks[-1][1].append(line)
    return [(path, tuple(body)) for path, body in blocks if body]


# The heading the inline root puts its procedures under. The root's own
# blocks carry no rule: the lines opening its rules and its procedures, and
# each procedure's description of its kind, the first block under it.
PROCEDURES = "## Procedures"


def union_findings(inline_root, sections):
    """Where the section files and the inline root's rules part ways, block
    by block: a rule block no section file holds, and a block a section
    file holds that no rule block is."""
    rules = inline_root.split("\n## Rules\n", 1)[-1]
    owed = {body for path, body in heading_blocks(rules)
            if path and path != (PROCEDURES,)
            and not (len(path) == 2 and path[0] == PROCEDURES)}
    held = {body for text in sections.values()
            for _, body in heading_blocks(text)}
    return (["no section file holds: %s" % body[0]
             for body in sorted(owed - held)]
            + ["no adopted rule is: %s" % body[0]
               for body in sorted(held - owed)])


SECTION_PATH = re.compile(r"`(" + re.escape(SECTIONS_INTO) + r"/[^`]+)`")


def map_findings(root, sections):
    """What a sections map gets wrong: a section file it names other than
    once, or a path it names that is no section file."""
    named = SECTION_PATH.findall(root)
    paths = ["%s/%s" % (SECTIONS_INTO, name) for name in sections]
    return (["the map names %s %d times" % (path, named.count(path))
             for path in paths if named.count(path) != 1]
            + ["the map names %s, which is no section file" % path
               for path in sorted(set(named) - set(paths))])


# What telling the agent to read everything at the start looks like: a
# sentence that reads or loads every template, section, skill or file, with
# a moment before the work, and no negation. "Do not read them before the
# work starts" and "the first time the work touches a topic, read it" pass.
READ_ALL = re.compile(r"\b(read|load)\b.*\b(every|each|all)\b.*"
                      r"\b(templates?|sections?|skills?|files?|rules?)\b",
                      re.IGNORECASE)
UP_FRONT = re.compile(r"\b(before (starting|you start|any|the work|work)|"
                      r"at (the )?(start|outset)|startup|up ?front|"
                      r"at session start)\b", re.IGNORECASE)
NEGATED = re.compile(r"\b(do not|don't|never|not)\b", re.IGNORECASE)


def startup_reads(text):
    """Each sentence of a text telling the agent to read everything at the
    start; empty where it tells no such thing."""
    sentences = re.split(r"(?<=[.!?])\s+", " ".join(text.split()))
    return [sentence for sentence in sentences
            if READ_ALL.search(sentence) and UP_FRONT.search(sentence)
            and not NEGATED.search(sentence)]


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
    return on_demand_checks(records, brief)


def on_demand_checks(records, brief):
    """What the on-demand arms owe beyond a rebuild; 0 where it all holds,
    1 at the first check that fails.

    Requires every on-demand arm committed, and no root of one telling the
    agent to read everything at the start, where a planted root saying so
    is caught. Requires `lazyref` and `lazyrefold` to differ by the
    check-loop commit's lines alone, and the section files to hold the
    inline root's rule blocks and no other, each named once by its map; a
    planted fault in each is caught.
    """
    missing = [arm for arm in ON_DEMAND if arm not in records]
    if missing:
        print("FAIL: on-demand arms not committed: %s" % ", ".join(missing))
        return 1

    # Every file of an on-demand arm is scanned, its skills and section
    # files too. The up-front arm is the natural control: `reference` tells
    # the agent to read every template before the work starts, so the scan
    # must fire on it, and on a sentence saying so planted in a root.
    arms = {arm: committed_arm(arm) for arm in ON_DEMAND}
    told = {arm: [sentence for text in [document] + list(parts.values())
                  for sentence in startup_reads(text)]
            for arm, (document, parts) in arms.items()}
    told = {arm: found for arm, found in told.items() if found}
    planted = arms["lazysections"][0] + ("\nRead every section file below "
                                         "at startup, before any work.\n")
    if told or not startup_reads(planted) \
            or not startup_reads(committed_arm("reference")[0]):
        print("FAIL: an on-demand root tells the agent to read everything "
              "at the start, or the scan misses one that does: %r" % told)
        return 1
    print("no on-demand arm tells the agent to read everything at startup")
    print("a root telling the agent to read everything at the start is "
          "caught")

    # `lazyrefold` is `lazyref` at the check-loop commit's parent: its
    # record names that parent, and the two arms' workspaces, root and
    # vendored templates, differ by that commit's lines alone, each in the
    # one section it changes.
    commit = CHECK_LOOP["commit"]
    parent = templates_git("rev-parse", "%s^" % commit).strip()
    if templates_git("rev-parse", records["lazyrefold"]["ref"]).strip() \
            != parent:
        print("FAIL: lazyrefold is not built at the check-loop commit's "
              "parent, %s" % parent[:8])
        return 1

    # The pair compared is the one a trial gets: each arm's committed root
    # and the templates vendored at the ref the harness reads from its
    # record, not a build made here, which no trial runs.
    def installed(arm, ref=None):
        """An arm's workspace files: its committed root and the templates
        vendored at `ref`, by default the one its record names."""
        return dict(vendored_files(ref or arm_vendor(arm)["ref"]),
                    **{"CLAUDE.md": committed_arm(arm)[0]})
    old, new = installed("lazyrefold"), installed("lazyref")
    removed, added, inside = commit_change(CHECK_LOOP)
    path = "%s/%s" % (VENDORED["into"], CHECK_LOOP["file"])
    findings = pair_findings(old, new, path, (removed, added))
    if findings or not inside:
        print("FAIL: lazyref and lazyrefold differ by more or less than the "
              "check-loop commit's lines in %s: %r"
              % (CHECK_LOOP["section"], findings))
        return 1
    print("lazyref and lazyrefold differ by the check-loop commit's lines "
          "alone, all in its section")
    extra = dict(new, **{"CLAUDE.md": new["CLAUDE.md"] + "- Check twice\n"})
    short = dict(new, **{path: new[path].replace(added[-1] + "\n", "", 1)})
    if not pair_findings(old, extra, path, (removed, added)) \
            or not pair_findings(old, short, path, (removed, added)) \
            or commit_change(dict(CHECK_LOOP, section="## Naming"))[2]:
        print("FAIL: a line changed besides the commit's, one of its lines "
              "missing, or a line outside its section is not reported")
        return 1
    print("a line changed besides the commit's, one of its lines missing, or "
          "one outside its section is reported")

    # A `lazyref` committed at another ref than the check-loop commit, as
    # one left at an earlier round's, makes a pair no trial should read.
    stale = installed("lazyref", "%s^" % parent)
    if not pair_findings(old, stale, path, (removed, added)):
        print("FAIL: a lazyref committed at another ref than the check-loop "
              "commit is not reported")
        return 1
    print("a lazyref committed at another ref than the check-loop commit is "
          "reported")

    # The section files and the inline root are two packagings of one rule
    # set at one ref, so each rule block of the one is a block of the other.
    document, sections = committed_arm("lazysections")
    inline = build_arm("inline", records["lazysections"]["ref"], brief)[0]
    findings = union_findings(inline, sections) \
        + map_findings(document, sections)
    if findings:
        print("FAIL: the section files and the adopted rules part ways, or "
              "the map misnames a file: %r" % findings[:5])
        return 1
    print("the section files hold every rule block the inline root does, "
          "and no other")
    print("the sections map names every section file once, under %s/"
          % SECTIONS_INTO)
    name = sorted(sections)[0]
    lines = sections[name].splitlines(True)
    last = max(i for i, line in enumerate(lines)
               if line.strip() and not line.startswith("#"))
    dropped = dict(sections,
                   **{name: "".join(lines[:last] + lines[last + 1:])})
    unmapped = dict(sections, **{"extra/unmapped.md": "# Extra\n\n- A rule\n"})
    if not union_findings(inline, dropped) \
            or not map_findings(document, unmapped):
        print("FAIL: a rule dropped from a section file, or a file the map "
              "does not name, is not reported")
        return 1
    print("a rule dropped from a section file, or a file the map does not "
          "name, is reported")
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
    document, parts, details = build_arm(arm, options.ref, read_brief())
    record.update(details)
    print("chain at %s (%s): %d unique files"
          % (options.ref, record["commit"][:8],
             len(record["resolved_files"])))

    texts = [document] + list(parts.values())
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

    told = [sentence for text in texts for sentence in startup_reads(text)]
    if told and arm in ON_DEMAND:
        record["outcome"] = "refused: reads everything at the start"
        print("refused: an on-demand arm's files tell the agent to read "
              "everything at the start: %r" % told)
        return write_record(options.root, record, started_at) or 1

    # A dry run of any arm stops here: it writes nothing under `arms/`,
    # so it never replaces a committed file or its record.
    unit = "section files" if entry.get("sections") else "skills"
    if options.dry_run:
        record["outcome"] = "dry-run"
        print("dry run: %s would be %d words%s; nothing written under arms/"
              % (output, len(document.split()),
                 ", with %d %s" % (len(parts), unit) if parts else ""))
        return write_record(options.root, record, started_at)

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with io.open(output, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(document)
    shutil.rmtree(parts_path(arm), ignore_errors=True)
    for name, text in parts.items():
        path = os.path.join(parts_path(arm), *name.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)

    # A skill is named by its folder, a section file by its path.
    if parts and entry.get("sections"):
        record["sections"] = {name: len(text.split())
                              for name, text in parts.items()}
    elif parts:
        record["skills"] = {name.split("/")[0]: len(text.split())
                            for name, text in parts.items()}
    record["outcome"] = "generated"
    record["output"] = output
    record["output_lines"] = document.rstrip("\n").count("\n") + 1
    record["output_words"] = len(document.split())
    print("wrote %s: %d lines, %d words%s"
          % (output, record["output_lines"], record["output_words"],
             ", %d %s" % (len(parts), unit) if parts else ""))
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
