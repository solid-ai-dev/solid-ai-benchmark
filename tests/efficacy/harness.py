"""Set up and run one efficacy-benchmark trial.

This module owns a trial's protocol: the
workspace an arm starts from, the isolated configuration it runs under, the
one prompt every arm receives, and the freeze that ends a trial.

Scoring is not here. A trial produces a frozen workspace and a record; the
hidden suite and the graders read them afterwards.
"""

import argparse
import contextlib
import datetime
import fnmatch
import glob
import hashlib
import io
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time

# This module sits a level below the other runners, so the shared library
# is reached by path rather than as a sibling.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SPEC = os.path.join(HERE, "SPEC.md")

# The specifications a round can build against, by the word `--spec` takes.
# Each reaches the workspace as SPEC.md, so the prompt is one text for both.
# The thin one keeps the contract the hidden suite drives and drops the
# practices a context file might otherwise supply.
SPECS = {"normal": SPEC, "thin": os.path.join(HERE, "SPEC-thin.md")}
ARMS_DIR = os.path.join(HERE, "arms")

# The change task's prompt lives in a file of its own, its only copy. A copy
# restated in code could drift from it, and a prompt found by a heading in a
# document breaks when the document is restructured.
CHANGE_PROMPT = os.path.join(HERE, "change-prompt.txt")

# Identical for every arm, so the context file is the only difference.
# Changing it changes what the benchmark measures, so it is a constant and
# not an option. A trial runs headless, so a context file asking the agent to
# wait for a plan's approval would end the trial with nothing built; the spec
# stands as the approved plan, and the prompt says nobody will answer.
PROMPT = (
    "Implement the application described in SPEC.md. SPEC.md is the approved "
    "plan, and nobody will answer questions during this run, so build it to "
    "the end without stopping for approval. Done means: "
    "`pip install .` succeeds in a clean virtualenv, your own tests pass, "
    "and every page and route in the spec works end to end against the "
    "seed fixture. Commit when done."
)

# The two bounds on a trial, fixed before any round runs. The budget is
# read against the CLI's own cost figure and checked between turns.
BUDGET_USD = 100.0
TIMEOUT_S = 7200

# A round registers its K before its first trial and no run goes past it,
# because sampling until an interval clears zero is the failure the bound
# exists to prevent. Round 5 registers fifteen blocks, sized from the
# per-trial noise of the rounds before it, which left three blocks unable to
# decide its hypotheses.
ROUND5_ARMS = ("inline", "reference", "skills")
ROUND5_K = 15

# A run is short unless the registered K is asked for by name.
K_DEFAULT = 3

# Round 5d runs `hand` and `short` under round 5's design: its K, its spec
# at its registered content, against round 5c's arms.
ROUND5D_ARMS = ("hand", "short")

# Round 5e runs the two map arms under the same design: the templates read
# as files, or loaded as skills, at the moment the work touches their topics.
ROUND5E_ARMS = ("lazyref", "lazyskills")

# The release every generated arm is produced from, and the one the hybrid
# arm's vendored templates are taken at, fixed before the first round: the
# last 2.x, before the v3.0 split moves any template.
RELEASE = "v2.90.0"

# The templates every arm is generated from and the hybrid arm vendors: a
# git clone of upstream or of a fork, named by this variable or by
# `--templates`. The benchmark carries no templates of its own, so one ruler
# measures any source.
TEMPLATES_ENV = "BENCHMARK_TEMPLATES"

# What a vendoring arm's workspace carries besides its file: the templates
# source's `templates/` directory at the arm's recorded ref, where a
# submodule would put it. The rest of that repository stays out.
VENDORED = {"ref": RELEASE, "path": "templates",
            "into": "docs/solid-ai-templates"}

# Round 5's templates and roots, as registered: one commit and one
# chain for every arm, so the arms differ only in how they deliver it.
ROUND5_REF = "9086e0ff"

# Round 5's specification, as registered: one file at one content for every
# trial. A spec edited while a two-day run is under way would otherwise mix two
# specifications in one round without a trace in its verdicts.
ROUND5_SPEC = ("normal",
               "48ee93ff968ef4a3175408c349afd6ce7223d0f3bd25b49ad4521f0fc307e55e")

# Round 6's specification: round 5's plus the two non-functional lines a team
# would write, data surviving a restart and errors naming the field, each
# graded by the hidden suite. Round 5's arms keep their own content above and
# are re-run only from the benchmark at their commit.
ROUND6_SPEC = ("normal",
               "a99e19ac006605d06af214552de1ce5a3f0f5c4b087f1a461acb8d3f3b869a5f")
ROUND5_ROOTS = ["backend-api", "backend-auth", "backend-database",
                "frontend-ux", "base-security", "base-data-governance"]

# The sections the brief rules out for tariff, which the `skills` arm's
# emitter leaves out as a project's declined list would. Fixed once, from the
# brief alone, for every trial of the round.
ROUND5_DECLINED = [
    "templates/security/security.md#Server-Side Request Forgery (SSRF)",
    "templates/security/security.md#File uploads",
    "templates/security/security.md#CORS",
    "templates/backend/auth.md#API keys (service-to-service)",
]

# Where the `skills` arm's skills go in the workspace: the folder Claude
# Code loads skills from on demand.
SKILLS_INTO = ".claude/skills"

# The arms, each a word, and the context file each starts with, relative to
# `arms/`. Arm `none` carries no file: it is the bare agent. An arm's
# vendored ref comes from its generation record. `generate_arm.py` builds
# every arm a round may run; `hand`, `short` and `hybrid` are the pilot
# rounds' arms, a person's file and two a model wrote, kept as they are for
# the pilot rounds' reports, and no script rebuilds them.
ARMS = {
    "none": {"label": "no context file", "context": None},
    "short": {"label": "the templates' file, inline, 40 lines",
              "context": "short/CLAUDE.md"},
    "hybrid": {"label": "the templates' file, hybrid",
               "context": "hybrid/CLAUDE.md", "vendor": VENDORED},
    "hand": {"label": "the hand-written file",
             "context": "hand/CLAUDE.md"},
    "reference": {"label": "the templates, named only",
                  "context": "reference/CLAUDE.md", "vendor": VENDORED},
    "inline": {"label": "the emitted root file, every rule inline",
               "context": "inline/CLAUDE.md"},
    "skills": {"label": "the emitted root file and task skills",
               "context": "skills/CLAUDE.md", "skills": "skills/skills"},
    "lazyref": {"label": "the templates, mapped to the work, read on demand",
                "context": "lazyref/CLAUDE.md", "vendor": VENDORED},
    "lazyskills": {"label": "the templates, mapped to the work, one skill "
                            "each",
                   "context": "lazyskills/CLAUDE.md",
                   "skills": "lazyskills/skills"},
}

# The rounds from 6 on, each as registered: its spec, its arms, and per task
# its K and the digest of the prompt every arm is given. A run names its round
# with `--round` and is held to this entry rather than to what its arm names
# suggest, since a round may reuse a pilot arm's name. The pilot rounds have no
# entry and keep the checks they ran under.
REGISTRATIONS = {
    "C1": {
        "spec": {"name": "normal", "file": "SPEC.md",
                 "sha256": ROUND6_SPEC[1]},
        "arms": ["none", "reference", "inline", "skills", "lazyref",
                 "lazyskills"],
        "tasks": {
            "build": {
                "k": 15,
                "prompt_sha256": "e6ca96707fb227d9053eeffcca344963803a2b34"
                                 "2ca8dddab5951e26b914724b"},

            # Every arm's change task of a block starts from the same build,
            # one arm `none` made in round 5e, so the change measures the
            # file and not the build the arm happened to leave. The manifest,
            # beside this module, lists the builds that qualified, each with
            # its tarball's hash, so a fixture swapped later no longer matches.
            "change": {
                "k": 15,
                "prompt_sha256": "52f053c49e0103535e3e966bbcf8f27915be5a7c"
                                 "412283e61b7799cabbdaf829",
                "fixtures": {
                    "manifest": "change-fixtures.json",
                    "from": {"round": "5e", "arm": "none"},
                    "order": "ascending trial number, block b takes the b-th "
                             "qualifying build, cycling when fewer qualify"}},
        },
    },
}

def trial_name(arm, block):
    """A trial's name: the arm's word, a hyphen, the block it runs in."""
    return "%s-%d" % (arm, int(block))


def split_name(name):
    """A trial name as (arm, block).

    The block is the last hyphenated part, so an arm's word never carries a
    hyphen of its own.
    """
    arm, _, block = name.rpartition("-")
    if not arm or not block.isdigit():
        raise TrialError("%r is not a trial name; one reads as `hand-1`, the "
                         "arm's word and its block" % name)
    return arm, int(block)


def canonical(name):
    """A trial name as the arms spell it, `none-1` for `none-01`."""
    return trial_name(*split_name(name))


def name_of(record):
    """The trial a run record or a score describes, by canonical name."""
    return trial_name(record.get("arm"), record.get("trial"))

# Web access is a confound: an arm that reads the
# templates online is not the arm being measured. The two web tools are
# disallowed; the shell keeps its network, because every trial installs
# packages, so a fetch through it shows only in the transcript.
DISALLOWED_TOOLS = ["WebSearch", "WebFetch"]

# What a tool call names when a trial reaches for what no arm may read: this
# repository, which a generated file names in its footer, and the private
# hidden suite under any clone's name, the scorer's own included.
REACH_TERMS = ("solid-ai-templates", "hidden-suite")

# The hybrid arm's workspace carries the templates by design, so a call
# naming that tree is the arm reading its own file. For it the repository is
# reached only under an owner's name, which no path into the vendored copy
# carries and every clone or fetch of the repository does. The repository
# moved organisation and the host redirects the old name, so a fetch under
# either owner reaches it and both are terms.
REPOSITORY_TERMS = ("solid-ai-dev/solid-ai-templates",
                    "braboj/solid-ai-templates")

# The workspace's own project settings and nothing else: no user or local
# settings, and no MCP server the harness did not pass -- which is none.
# The project source is what makes Claude Code discover the skills arm's
# `.claude/skills/`; every arm gets it, so the arms differ only in what
# their workspace holds. The deny rules come from the harness's own
# settings file, passed apart from the sources.
SETTING_SOURCES = "project"

# What the skills probe asks: the names the agent sees, and nothing else.
SKILLS_PROMPT = ("Without using any tool, list the names of the skills "
                 "available to you, one per line, and nothing else. If there "
                 "are none, reply NONE.")

# A minimal settings file, so `--settings` names something real rather than
# falling back to whatever the machine carries.
ISOLATED_SETTINGS = {"includeCoAuthoredBy": False}

# The outcomes that void a trial: the provider's cut, and a session whose
# tool calls reached past its workspace, each re-run once in its place; and a
# trial whose harness died under it, which `recover` voids before the next
# run. None is a measurement of the arm.
VOIDING = ("blocked", "reached", "interrupted")


def rule_path(path):
    """`path` as a permission rule spells an absolute path: `//c/x` for
    `C:\\x`. The CLI matches the long form, so a short 8.3 name never
    matches."""
    full = os.path.abspath(path).replace("\\", "/").rstrip("/")
    if len(full) > 1 and full[1] == ":":
        full = "/%s%s" % (full[0].lower(), full[2:])
    return "/" + full


def reach_denials(root, workspace):
    """Read and Edit deny rules for what a trial may not reach that a path
    names: this repository, the scoring area, and every entry of the run root
    but the trial's own workspace and temporary directory.

    The shell is not covered, since a deny rule matches a command's prefix
    and not the paths in it; the transcript scan reads what the shell sent.
    """
    root = os.path.abspath(root)
    own = os.path.basename(os.path.abspath(workspace))

    # Every block any run may hold, so no trial of a long round is left
    # readable by the trials of its other blocks.
    names = {trial_name(arm, trial) for arm in ARMS
             for trial in range(1, ROUND5_K + 1)}
    names |= {"change-" + name for name in names}
    targets = [repository_root(), scoring_area(root),
               os.path.join(root, "home"), os.path.join(root, "void")]
    source = templates_root(required=False)
    if source:
        targets.append(source)
    targets += [os.path.join(root, name) for name in sorted(names)
                if name != own]
    patterns = ["%s/**" % rule_path(target) for target in targets]
    patterns += ["%s/%s" % (rule_path(root), entry)
                 for entry in ("*.tar", "run-*.json")]
    return ["%s(%s)" % (tool, pattern)
            for pattern in patterns for tool in ("Read", "Edit")]


# Commands that stop processes by name, as a deny rule's glob spells them.
# Stopping a dev server by name stops every process of that name on the
# machine, the harness's own interpreter among them, which is how round 4's
# thin run ended mid-trial. Stopping one by PID or by port stays allowed:
# that is how an agent stops only what it started.
KILL_BY_NAME = ("*Get-Process*Stop-Process*", "*Stop-Process*Get-Process*",
                "*Stop-Process -Name*", "*Stop-Process -ProcessName*",
                "*Get-Process*Kill(*", "*taskkill*/IM*", "*pkill*",
                "*killall*", "*Win32_Process*", "*wmic*process*")

# The tools a command runs through. Both match a glob across the whole
# command, so a kill chained after `cd ... &&` is denied too; a probe showed
# the rules deny those calls and let a kill by PID through.
SHELL_TOOLS = ("Bash", "PowerShell")

# The same globs as one pattern for the transcript scan. A rule may match
# case-sensitively, so the scan ignores case and catches what slipped by.
KILL_PATTERN = re.compile("|".join(fnmatch.translate(pattern)
                                   for pattern in KILL_BY_NAME),
                          re.IGNORECASE)


def kill_denials():
    """Deny rules for every shell command that stops processes by name, in
    each glob's own spelling and in lower case."""
    patterns = sorted({form for pattern in KILL_BY_NAME
                       for form in (pattern, pattern.lower())})
    return ["%s(%s)" % (tool, pattern)
            for pattern in patterns for tool in SHELL_TOOLS]


def trial_settings(home, root, workspace):
    """Write a trial's own settings file into the scratch home, which its
    deny rules cover, and return its path."""
    os.makedirs(home, exist_ok=True)
    path = os.path.join(home, "settings-%s.json"
                        % os.path.basename(os.path.abspath(workspace)))
    settings = dict(ISOLATED_SETTINGS,
                    permissions={"deny": reach_denials(root, workspace)
                                 + kill_denials()})
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2)
    return path


class TrialError(Exception):
    """A trial could not be set up or run as the protocol requires."""


# The CLI a run pins with `--cli`: one file, run as it is. The launcher on
# PATH updates itself in place, and an update in the middle of a round would
# change every trial after it without a trace in the records.
PINNED_CLI = {"path": None}


def cli_version(executable):
    """What the CLI says its version is, as `2.1.314 (Claude Code)`."""
    proc = subprocess.run([executable, "--version"], capture_output=True,
                          text=True, encoding="utf-8", timeout=60)
    version = proc.stdout.strip()
    if proc.returncode != 0 or not version:
        raise TrialError("%s did not say its version: %s"
                         % (executable, proc.stderr.strip()[:300]))
    return version


def agent_executable():
    """The generator CLI's absolute path.

    A bare "claude" in an argv list is not launchable on Windows, where the
    command is a `.CMD` shim and `CreateProcess` resolves no extension: the
    run dies with "the system cannot find the file specified" before a
    single trial starts. Resolving it here fails with a sentence naming the
    problem instead. A run given `--cli` uses that file and no other.
    """
    if PINNED_CLI["path"]:
        if not os.path.isfile(PINNED_CLI["path"]):
            raise TrialError("the pinned CLI %s is not a file, so no trial "
                             "can run" % PINNED_CLI["path"])
        return PINNED_CLI["path"]
    found = shutil.which("claude")
    if found is None:
        raise TrialError(
            "the `claude` CLI is not on PATH, so no trial can run")
    return found


def repository_root():
    """The benchmark repository's absolute root."""
    return os.path.abspath(lib.ROOT)


def templates_root(required=True):
    """The templates source's absolute root, a git clone, or None when it is
    unset and not required."""
    path = os.environ.get(TEMPLATES_ENV)
    if not path:
        if not required:
            return None
        raise TrialError("no templates source: set %s to a clone of the "
                         "templates repository, or pass --templates"
                         % TEMPLATES_ENV)
    path = os.path.abspath(path)
    if not os.path.exists(os.path.join(path, ".git")):
        raise TrialError("the templates source %s is not a git clone" % path)
    return path


def source_record(ref):
    """Which templates a run used: the source's remote, the ref, and the
    commit the ref named, so a report can say what it measured."""
    root = templates_root()
    commit = subprocess.run(["git", "-C", root, "rev-parse",
                             "%s^{commit}" % ref], capture_output=True,
                            text=True, encoding="utf-8").stdout.strip()
    remote = subprocess.run(["git", "-C", root, "remote", "get-url",
                             "origin"], capture_output=True, text=True,
                            encoding="utf-8").stdout.strip()
    return {"remote": remote or None, "ref": ref, "commit": commit or None}


def assert_outside_repository(root):
    """Refuse a workspace root inside the benchmark or the templates source.

    A workspace under the templates lets the agent walk up and read the very
    templates arm `none` is defined not to have, and one under the benchmark
    lets it read the hidden specification. Both are confounds, controlled
    by not mounting either repository, so the mount is refused here rather
    than trusted to the caller.
    """
    root = os.path.abspath(root)
    for label, repo in (("benchmark", repository_root()),
                        ("templates source", templates_root(required=False))):
        if repo and (root == repo or root.startswith(repo + os.sep)):
            raise TrialError(
                "workspace root %s is inside the %s at %s; an arm there can "
                "read it" % (root, label, repo))


# A trial's workspace is created inside the run root, so whatever scoring wrote
# there, the hidden suite's clone and every scored trial's extracted code among
# it, would sit one `..` away from the next trial.
def scoring_area(root):
    """The directory beside a run root that scoring and judging write to."""
    return os.path.abspath(root).rstrip("\\/") + "-scoring"


def dry_run_area(root):
    """The directory beside a run root that a dry run prepares in."""
    return os.path.abspath(root).rstrip("\\/") + "-dry-run"


# An agent checking a clean install puts its virtualenv beside the workspace,
# out of the repository. Beside every other trial in the run root, that reads
# as a reach and voids the trial; in a folder the trial owns, it stays the
# trial's. So each trial gets a pen: its workspace, its temporary directory,
# and whatever the agent puts beside the workspace.
def trial_workspace(root, name):
    """A trial's workspace: in its pen in the run root, under its own name."""
    return os.path.join(root, name, name)


def pen_of(workspace):
    """The pen a workspace sits in, or the workspace itself where it sits
    straight in the run root, as trials did before pens."""
    workspace = os.path.abspath(workspace)
    parent = os.path.dirname(workspace)
    if os.path.basename(parent).lower() == os.path.basename(workspace).lower():
        return parent
    return workspace


def assert_no_ambient_context(workspace, home):
    """Refuse a run that a context file outside the arm would reach.

    The scratch home exists so no global `CLAUDE.md` reaches the bare arm.
    An assertion that it is empty of one is cheap and deterministic, where
    reading the loaded context back costs a model call. Every directory
    from the workspace up to the filesystem root is checked too, because
    memory discovery walks parents.
    """
    found = []
    candidate = os.path.join(home, ".claude", "CLAUDE.md")
    if os.path.exists(candidate):
        found.append(candidate)
    if os.path.exists(os.path.join(home, "CLAUDE.md")):
        found.append(os.path.join(home, "CLAUDE.md"))

    # The workspace's own CLAUDE.md is the arm's, so start above it.
    current = os.path.dirname(os.path.abspath(workspace))
    while True:
        candidate = os.path.join(current, "CLAUDE.md")
        if os.path.exists(candidate):
            found.append(candidate)
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    if found:
        raise TrialError(
            "a context file outside the arm would reach this run: %s"
            % ", ".join(found))


def now():
    """The time now, with this machine's UTC offset."""

    # A record is read on whatever machine writes the report, so a time
    # without its offset would be read in that machine's zone, and could
    # order wrongly against a commit's date.
    return datetime.datetime.now().astimezone()


def git(workspace, *args, env=None):
    """Run git in the workspace, raising on a non-zero status."""
    proc = subprocess.run(["git", "-C", workspace] + list(args),
                          capture_output=True, text=True, encoding="utf-8",
                          env=env)
    if proc.returncode != 0:
        raise TrialError("git %s failed in %s: %s"
                         % (" ".join(args), workspace, proc.stderr.strip()))
    return proc.stdout.strip()


def vendor_templates(workspace, vendor):
    """Put the templates source's templates at the release into the
    workspace, where a submodule would, and return the record of what was
    vendored.

    The copy is kept out of the workspace's index through `.git/info/exclude`
    rather than a `.gitignore`: it is the arm's reading matter, not its
    output, so it must count in no size or scope metric; a submodule would
    add one entry, and the agent may rewrite a `.gitignore` at will.
    """
    target = os.path.join(workspace, *vendor["into"].split("/"))
    os.makedirs(target, exist_ok=True)
    source = templates_root()
    proc = subprocess.run(["git", "-C", source, "archive",
                           "--format=tar", vendor["ref"], vendor["path"]],
                          capture_output=True)
    if proc.returncode != 0:
        raise TrialError("could not export %s at %s: %s"
                         % (vendor["path"], vendor["ref"],
                            proc.stderr.decode("utf-8", "replace").strip()))
    with tarfile.open(fileobj=io.BytesIO(proc.stdout)) as archive:
        archive.extractall(target, filter="data")
    tree = subprocess.run(["git", "-C", source, "rev-parse",
                           "%s:%s" % (vendor["ref"], vendor["path"])],
                          capture_output=True, text=True,
                          encoding="utf-8").stdout.strip()
    exclude = os.path.join(workspace, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with io.open(exclude, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("/%s/\n" % vendor["into"])
    return dict(vendor, tree=tree, source=source_record(vendor["ref"]))


def arm_vendor(arm):
    """What an arm vendors, at the ref its generation record names; None
    for an arm that vendors nothing."""
    vendor = ARMS[arm].get("vendor")
    if not vendor:
        return None
    record = os.path.join(ARMS_DIR, os.path.dirname(ARMS[arm]["context"]),
                          "generation.json")
    if os.path.isfile(record):
        with io.open(record, encoding="utf-8") as handle:
            ref = json.load(handle).get("ref")
        if ref:
            return dict(vendor, ref=ref)
    return dict(vendor)


def place_skills(workspace, source):
    """Copy an arm's skills to where Claude Code loads them, kept out of the
    workspace's index like the vendored templates, so no size or scope
    metric counts them; return the kinds placed."""
    target = os.path.join(workspace, *SKILLS_INTO.split("/"))
    shutil.copytree(source, target)
    exclude = os.path.join(workspace, ".git", "info", "exclude")
    os.makedirs(os.path.dirname(exclude), exist_ok=True)
    with io.open(exclude, "a", encoding="utf-8", newline="\n") as handle:
        handle.write("/%s/\n" % SKILLS_INTO)
    return sorted(os.listdir(target))


def prepare_workspace(arm, trial, root, spec=SPEC):
    """Create the starting workspace for one trial; return its path and the
    record of what was vendored into it, None for every arm but the hybrid.

    Fresh directory, `git init`, the arm's starting files, one commit. The
    commit is what the freeze at the end of the trial is measured against:
    without it, a trial that wrote nothing looks the same as one whose work
    was never committed.
    """
    if arm not in ARMS:
        raise TrialError("unknown arm %r; the arms are %s"
                         % (arm, ", ".join(sorted(ARMS))))
    workspace = trial_workspace(root, trial_name(arm, trial))
    if os.path.exists(pen_of(workspace)):
        raise TrialError("workspace %s already exists; a trial never reuses "
                         "one" % workspace)
    os.makedirs(workspace)

    shutil.copyfile(spec, os.path.join(workspace, "SPEC.md"))
    vendored = install_arm(workspace, arm)
    commit_start(workspace, "start: %s arm %s" % (ARMS[arm]["label"], arm))
    return workspace, vendored


def install_arm(workspace, arm):
    """Give a workspace, not yet a repository, its arm's context: the file,
    the vendored templates, the skills; `git init` it; return what was
    vendored, None for an arm that vendors nothing."""
    context = ARMS[arm]["context"]
    if context:
        source = os.path.join(ARMS_DIR, context)
        if not os.path.isfile(source):
            raise TrialError(
                "arm %s needs %s, which does not exist. A generated file is "
                "made by generate_arm.py at the recorded ref, never "
                "hand-written." % (arm, source))
        shutil.copyfile(source, os.path.join(workspace, "CLAUDE.md"))

    git(workspace, "init", "-q")
    vendored = None
    if ARMS[arm].get("vendor"):
        vendored = vendor_templates(workspace, arm_vendor(arm))
    if ARMS[arm].get("skills"):
        source = os.path.join(ARMS_DIR, ARMS[arm]["skills"])
        if not os.path.isdir(source):
            raise TrialError("arm %s needs its skills at %s, which do not "
                             "exist" % (arm, source))
        place_skills(workspace, source)
    return vendored


def commit_start(workspace, message):
    """Commit everything in the workspace as its starting state."""
    git(workspace, "add", "-A")
    git(workspace, "-c", "user.name=efficacy",
        "-c", "user.email=efficacy@example.invalid",
        "commit", "-q", "-m", message)


# The one thing the scratch home must inherit. Credentials live under the
# real home, so a fully scratch home authenticates as nobody and every
# trial dies on "Not logged in" — which the CLI reports as a successful
# result with `is_error` set, so it reads like a model answer rather than
# a failure to run.
CREDENTIALS = os.path.join(".claude", ".credentials.json")


def expiry_of(data):
    """When the access token in a credentials file's bytes expires, or 0
    where they say nothing readable."""
    try:
        stamp = json.loads(data.decode("utf-8"))["claudeAiOauth"]["expiresAt"]
    except (ValueError, KeyError, TypeError, AttributeError):
        return 0
    return stamp if isinstance(stamp, (int, float)) else 0


def expires_at(path):
    """When a credentials file's access token expires, or 0 where it says
    nothing readable."""
    try:
        with io.open(path, "rb") as handle:
            return expiry_of(handle.read())
    except OSError:
        return 0


def write_back(source, target, attempts=5):
    """Write the home's credentials over the account's, in place, where they
    expire later; True when they were written."""
    for _ in range(attempts):
        try:
            with io.open(target, "rb") as handle:
                fresh = handle.read()
        except OSError:
            return False
        expiry = expiry_of(fresh)

        # The account's file is compared through the handle that is then
        # written, so the comparison is with the very file overwritten, not
        # one a CLI's save has since put in its place.
        with io.open(source, "r+b") as handle:
            if expiry_of(handle.read()) >= expiry:
                return False
            handle.seek(0)
            handle.write(fresh)
            handle.truncate()
            written = os.fstat(handle.fileno())

        # A save that replaced the file after it was opened leaves the write
        # on the file it replaced, and the account's is the save's. The next
        # attempt compares against that one.
        try:
            current = os.stat(source)
        except OSError:
            continue
        if (current.st_ino, current.st_dev) == (written.st_ino,
                                                written.st_dev):
            return True
    return False


def refresh_credentials(home, account=None):
    """Give the scratch home the account's live credentials; say how.

    A hard link to the real file rather than a copy. Another client of the
    account — a parallel session starting on this machine — rotates the
    tokens, and a snapshot taken before that holds a revoked token: one
    ended a trial eighteen minutes in. Through the link a rotation written
    in place reaches the trial's CLI as it happens. Where no link can be
    made the file is copied, and the copy is taken again before every
    trial and every probe, so at worst a trial starts fresh. `account`
    names the real file, for a test; it defaults to the user's own.
    """
    source = account or os.path.join(os.path.expanduser("~"), CREDENTIALS)
    target = os.path.join(home, CREDENTIALS)
    if not os.path.exists(source):
        return None
    os.makedirs(os.path.dirname(target), exist_ok=True)

    # Two runs on one machine share the account's file, and the lock keeps
    # one's write-back and re-link from interleaving with the other's. A CLI
    # saving its own token takes no lock; the write-back guards against it.
    with credential_lock(source):
        if os.path.lexists(target):

            # A trial's CLI that refreshes an expired token saves the new one
            # as a new file, which breaks the link: the home then holds the
            # only live refresh token, and the account's has been rotated
            # out. It is written back over the account's file in place,
            # keeping that file and its other links, before the link is
            # remade; dropping it would hand the next trial a revoked token,
            # and it ended two trials at their first call.
            if not os.path.samefile(source, target):
                write_back(source, target)
            os.remove(target)
        try:
            os.link(source, target)
            return "linked"
        except OSError:
            shutil.copyfile(source, target)
            return "copied"


@contextlib.contextmanager
def credential_lock(source, stale_s=60, poll_s=0.05):
    """Hold the lock file beside the account's credentials while inside."""
    lock = source + ".lock"
    while True:
        try:
            os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
            break
        except FileExistsError:

            # The lock is held for milliseconds, so one this old was left by
            # a run that died holding it.
            try:
                if time.time() - os.path.getmtime(lock) > stale_s:
                    os.remove(lock)
                    continue
            except OSError:
                continue
            time.sleep(poll_s)
    try:
        yield
    finally:
        try:
            os.remove(lock)
        except OSError:
            pass


# How often a running trial's credentials are looked at. The account's own
# clients go without a live token from a trial's refresh until the next look.
WATCH_EVERY_S = 15


@contextlib.contextmanager
def credential_watch(home, account=None, every_s=WATCH_EVERY_S):
    """While inside, write a token the trial refreshed back to the account's
    file as soon as it is seen; yields a list that counts the write-backs."""
    source = account or os.path.join(os.path.expanduser("~"), CREDENTIALS)
    target = os.path.join(home, CREDENTIALS)
    written, stop = [], threading.Event()

    # A trial's refresh retires the refresh token the account's file holds,
    # so every other session on the machine holds a dead one until the new
    # token is written back. Left to the end of the trial, that gap ran an
    # hour and forced a login; the link is still remade only between trials.
    def sync():
        try:
            if not os.path.exists(target) or not os.path.exists(source) \
                    or os.path.samefile(source, target):
                return
            with credential_lock(source):
                if write_back(source, target):
                    written.append(time.time())
                    print("  credentials: a token the trial refreshed was "
                          "written back to the account's file", flush=True)
        except OSError:

            # The CLI may be mid-save; the next look reads the file whole.
            pass

    def look():
        while not stop.wait(every_s):
            sync()

    watcher = threading.Thread(target=look, daemon=True)
    watcher.start()
    try:
        yield written
    finally:
        stop.set()
        watcher.join(every_s + 30)

        # A refresh after the last look would otherwise wait for the next
        # trial's re-link, which the last trial of a run, or one followed by
        # a long wait for the generator, does not reach for hours.
        sync()


def prepare_home(root):
    """Create the scratch home every trial runs under, and return it.

    One home for the whole run rather than one per trial: it holds no trial
    state, and a single directory is one thing to assert about.

    Everything a trial must be isolated from is absent by construction —
    no global `CLAUDE.md`, no hooks, no auto-memory, no MCP — because the
    directory is new. The credential file is linked in, and nothing else
    is: it carries no context, and without it there is no run at all.
    """
    home = os.path.join(root, "home")
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    settings = os.path.join(home, "settings.json")
    with io.open(settings, "w", encoding="utf-8") as handle:
        json.dump(ISOLATED_SETTINGS, handle)
    refresh_credentials(home)
    return home


def assert_authenticated(home, env_builder, executable):
    """Refuse a run the CLI would answer without reaching a model.

    "Not logged in" comes back as a result object with `is_error` true and
    a zero cost, not as a crash, so a whole run can complete with nine
    trials that never called anything. One cheap call up front is the
    difference between a failed run and a run of failures.
    """
    proc = subprocess.run(
        [executable, "-p", "--output-format", "json",
         "--setting-sources", "", "--settings",
         os.path.join(home, "settings.json"), "--strict-mcp-config"],
        input="Reply with the single word: ready", env=env_builder(home),
        capture_output=True, text=True, encoding="utf-8", timeout=180)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        raise TrialError("the CLI returned no JSON for a trivial prompt: %s"
                         % (proc.stdout or proc.stderr)[:400])
    if payload.get("is_error"):
        raise TrialError("the CLI is not usable in the isolated home: %s"
                         % payload.get("result", "")[:200])
    return payload.get("result", "").strip()


def missing_skills(listed, kinds):
    """The kinds an agent's list of its skills leaves out."""
    names = {line.strip().strip("-*` ").lower()
             for line in (listed or "").splitlines()}
    return [kind for kind in kinds if kind.lower() not in names]


def assert_skills_discovered(home, env_builder, executable, source):
    """Refuse a run whose agent would not see the skills arm's skills.

    Placing the files proves nothing: Claude Code discovers project skills
    only under the project setting source. One cheap call from a scratch
    workspace holding the arm's real skills, under the trial's own flags,
    asks for the names it sees; every kind must be among them.
    """
    kinds = sorted(os.listdir(source))
    workspace = tempfile.mkdtemp(prefix="efficacy-skills-probe-")
    try:
        git(workspace, "init", "-q")
        place_skills(workspace, source)
        proc = subprocess.run(
            [executable, "-p", "--output-format", "json",
             "--setting-sources", SETTING_SOURCES, "--settings",
             os.path.join(home, "settings.json"), "--strict-mcp-config"],
            input=SKILLS_PROMPT, cwd=workspace, env=env_builder(home),
            capture_output=True, text=True, encoding="utf-8", timeout=180)
    finally:
        remove_tree(workspace)
    try:
        payload = json.loads(proc.stdout)
    except ValueError:
        raise TrialError("the skills probe returned no JSON: %s"
                         % (proc.stdout or proc.stderr)[:400])
    listed = payload.get("result", "")
    missing = missing_skills(listed, kinds)
    if payload.get("is_error") or missing:
        raise TrialError("the agent does not see the skills arm's skills: "
                         "missing %s" % ", ".join(missing or ["all"]))
    return kinds


# A trial inherits this machine, not the process that launched it. Each group
# reaches a child process through its environment, which the scratch home and
# the isolated settings leave untouched.
INHERITED_PREFIXES = (
    # The calling agent session: a nested CLI that sees these joins that
    # session, takes its effort, or answers on its socket.
    "CLAUDE", "ANTHROPIC_", "MCP_", "AI_AGENT",

    # The editor the caller runs in.
    "VSCODE_", "ELECTRON_", "TERM_PROGRAM", "GIT_EDITOR", "COPILOT_",

    # An activated interpreter, which every trial would otherwise share.
    "VIRTUAL_ENV", "CONDA_", "PYTHONPATH", "PYTHONHOME",
)

# Credentials the caller holds. A trial runs with every permission bypassed,
# and nothing in the task needs another service's key.
CREDENTIAL_SUFFIXES = ("_API_KEY", "_TOKEN", "_SECRET", "_PASSWORD")

# Kept despite its prefix: it locates a binary and carries no context.
KEPT = ("CLAUDE_CODE_GIT_BASH_PATH",)

# Where an activated interpreter lives. Its directories leave PATH as well,
# or `python` in a trial still resolves into it.
INTERPRETER_ROOTS = ("VIRTUAL_ENV", "CONDA_PREFIX")


def inherited_names(environ):
    """The variable names a trial must not inherit, sorted."""
    return sorted(
        name for name in environ
        if name.upper() not in KEPT
        and (name.upper().startswith(INHERITED_PREFIXES)
             or name.upper().endswith(CREDENTIAL_SUFFIXES)))


def interpreter_directories(environ):
    """The PATH entries that lie inside an activated interpreter."""
    roots = [os.path.normcase(os.path.abspath(environ[name]))
             for name in INTERPRETER_ROOTS if environ.get(name)]
    found = []
    for entry in environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        normal = os.path.normcase(os.path.abspath(entry))
        if any(normal == root or normal.startswith(root + os.sep)
               for root in roots):
            found.append(entry)
    return found


# A credential helper the machine configures answers any Git that asks, and
# the private hidden suite is one authenticated clone away. An empty helper,
# set the way `git -c` sets one, clears every helper configured before it;
# a Git that cannot prompt then fails rather than waits.
GIT_WITHOUT_CREDENTIALS = {
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "credential.helper",
    "GIT_CONFIG_VALUE_0": "",
    "GIT_TERMINAL_PROMPT": "0",
    "GCM_INTERACTIVE": "never",
}

# The names a temporary directory is read from, on Windows and elsewhere.
TEMP_NAMES = ("TEMP", "TMP", "TMPDIR")


def agent_environment(home, environ=None, temp=None):
    """The environment a trial runs under: this machine's, minus the caller's.

    `temp`, where given, is the trial's own temporary directory.
    """
    source = dict(os.environ if environ is None else environ)
    dropped = set(inherited_names(source))
    stale = set(interpreter_directories(source))
    env = {name: value for name, value in source.items()
           if name not in dropped}
    if "PATH" in source:
        env["PATH"] = os.pathsep.join(
            entry for entry in source["PATH"].split(os.pathsep)
            if entry and entry not in stale)
    env["HOME"] = home
    env["USERPROFILE"] = home
    env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
    env.update(GIT_WITHOUT_CREDENTIALS)

    # A trial never updates the CLI it runs under, so the version a run
    # starts with is the one every trial records.
    env["DISABLE_AUTOUPDATER"] = "1"
    if temp:
        env.update((name, temp) for name in TEMP_NAMES)
    return env


def agent_command(home, model, effort, budget, settings=None):
    """The argv for one trial; the prompt goes on standard input.

    `--max-turns`, the natural bound on a trial, is not a flag this
    CLI carries. The bound is a dollar budget and the wall-clock timeout the
    caller applies, and the record states which of them ended a trial.
    `settings` is the trial's own settings file, the home's by default.
    """
    argv = [
        agent_executable(), "-p",
        "--output-format", "json",
        "--model", model,
        "--effort", effort,

        # Deny rules hold in this mode: a probe denied one file under it read
        # the file beside it and not the denied one, and read both without
        # the rule.
        "--permission-mode", "bypassPermissions",
        "--setting-sources", SETTING_SOURCES,
        "--settings", settings or os.path.join(home, "settings.json"),
        "--strict-mcp-config",
        "--disallowed-tools",
    ]
    argv.extend(DISALLOWED_TOOLS)
    if budget is not None:
        argv.extend(["--max-budget-usd", str(budget)])
    return argv


def freeze(workspace, record_dir, name):
    """Freeze the workspace before anything scores it.

    Returns the commit the trial ended on and the tarball path. Scoring
    reads the tarball, so a later run in the same directory cannot change
    what was graded.
    """
    status = git(workspace, "status", "--porcelain")
    head = git(workspace, "rev-parse", "HEAD")
    tarball = os.path.join(record_dir, "%s.tar" % name)
    with tarfile.open(tarball, "w") as archive:
        archive.add(workspace, arcname=name)
    return {"head": head, "uncommitted": status.splitlines(), "tarball": tarball}


def frozen_top(tarball, unpacked):
    """The one top-level directory a frozen tarball unpacked to.

    A workspace is frozen under the name it had on the day, which a reused
    trial need not keep, so the reader takes the one directory it finds
    rather than looking for the trial's name.
    """
    entries = os.listdir(unpacked)
    if len(entries) != 1 or not os.path.isdir(os.path.join(unpacked,
                                                           entries[0])):
        raise TrialError("%s did not unpack to one directory: %s"
                         % (tarball, ", ".join(entries) or "nothing"))
    return entries[0]


# The one error ending the protocol sets itself. A trial the budget stopped
# stands and is scored, as a timed-out one does.
BUDGET_SUBTYPE = "error_max_budget_usd"


def classify(status, result):
    """A finished CLI run's outcome, and why where it was blocked."""

    # Fail closed. What a usage limit returns cannot be observed on demand,
    # so a check matching its wording would pass any limit worded otherwise
    # straight into scoring as the model's own failure.
    if not isinstance(result, dict):
        return "blocked", "the CLI returned no JSON result (status %s)" % status
    if result.get("subtype") == BUDGET_SUBTYPE:
        return "budget", None
    if status == 0 and not result.get("is_error"):
        return "completed", None
    return "blocked", ("the CLI ended with an error (status %s, subtype %s, "
                       "API status %s): %s"
                       % (status, result.get("subtype"),
                          result.get("api_error_status"),
                          str(result.get("result") or "")[:300]))


def void(root, workspace, frozen, name):
    """Move a blocked trial's pen, its workspace with it, and its tarball
    under `void/`."""
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    target = os.path.join(root, "void", "%s-%s" % (name, stamp))
    moved = {"dir": target, "workspace": os.path.join(target, name),
             "tarball": os.path.join(target, "%s.tar" % name)}

    # The whole pen goes, so the re-run does not find what the voided try
    # left beside its workspace. A process the agent left running can hold a
    # file open. A pen that cannot move would block the re-run, so the caller
    # stops the run.
    pen = pen_of(workspace)
    try:
        os.makedirs(target)
        if pen == os.path.abspath(workspace):
            shutil.move(workspace, moved["workspace"])
        else:
            for entry in os.listdir(pen):
                shutil.move(os.path.join(pen, entry),
                            os.path.join(target, entry))
            os.rmdir(pen)
        shutil.move(frozen["tarball"], moved["tarball"])
    except OSError as error:
        raise TrialError("could not void %s: %s" % (name, error))
    return moved


def project_folder(workspace):
    """The folder the CLI files a workspace's sessions under."""
    return re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(workspace))


def transcript_files(home, workspace, since=None):
    """The transcripts the CLI wrote for a session run in `workspace`, left
    out where last written before `since`.

    The CLI files a session under its working directory with every character
    other than a letter or digit replaced by a hyphen.
    """
    files = sorted(glob.glob(os.path.join(home, ".claude", "projects",
                                          project_folder(workspace),
                                          "*.jsonl")))

    # A voided trial re-runs in the same workspace, so its folder also holds
    # the voided attempt's transcripts. Those stopped being written before the
    # re-run started, and a scan charging them to the re-run reports calls it
    # never made.
    if since is None:
        return files
    return [file for file in files if os.path.getmtime(file) >= since]


def tool_calls(files):
    """Every tool call in the transcripts, as (tool, input as JSON text)."""
    calls = []
    for file in files:
        with io.open(file, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(entry, dict):
                    continue
                content = (entry.get("message") or {}).get("content")
                if not isinstance(content, list):
                    continue
                calls.extend(
                    (block.get("name"),
                     json.dumps(block.get("input"), ensure_ascii=False))
                    for block in content
                    if isinstance(block, dict)
                    and block.get("type") == "tool_use")
    return calls


def stopped_by_name(files):
    """The shell calls in the transcripts that stopped processes by name and
    were not denied, as reach hits.

    A denied call comes back as an error opening "Permission to use", and it
    stopped nothing. A call with no result at all counts as run, because a
    session that ended mid-call may well have ended by it.
    """
    calls, denied = [], set()
    for file in files:
        with io.open(file, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                content = (entry.get("message") or {}).get("content") \
                    if isinstance(entry, dict) else None
                for block in content if isinstance(content, list) else []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "tool_use" \
                            and block.get("name") in SHELL_TOOLS:
                        command = (block.get("input") or {}).get("command")
                        if isinstance(command, str) \
                                and KILL_PATTERN.match(command):
                            calls.append((block.get("id"), block["name"],
                                          command))
                    elif block.get("type") == "tool_result" \
                            and block.get("is_error"):
                        text = block.get("content")
                        if isinstance(text, list):
                            text = " ".join(part.get("text", "")
                                            for part in text
                                            if isinstance(part, dict))
                        if str(text or "").startswith("Permission to use"):
                            denied.add(block.get("tool_use_id"))
    return [{"tool": tool, "term": "a process stopped by name",
             "call": command[:300]}
            for call_id, tool, command in calls if call_id not in denied]


def read_transcripts(home, workspace, since=None):
    """A trial's transcript files and every tool call in them."""
    files = transcript_files(home, workspace, since)
    return files, tool_calls(files)


def reach(files, calls, workspace=None, temp=None, vendored=None):
    """The tool calls naming this repository or the hidden suite and, given
    the trial's workspace, the scoring area or any part of the run root other
    than the trial's own workspace and temporary directory.

    Only what the agent sent is read, never what came back: a generated file
    names this repository, and reading it is not reaching for it. A trial
    whose workspace carries the templates (`vendored`) names them in every
    read, so for it the repository counts as reached only under its owner's
    name. With no transcript the hits are None rather than empty, because
    nothing scanned and nothing found are opposite facts.
    """
    if not files:
        return {"transcripts": [], "hits": None}
    terms, outside = list(REACH_TERMS), None
    if vendored:
        terms = [owned for term in terms
                 for owned in (REPOSITORY_TERMS
                               if term == "solid-ai-templates" else (term,))]
    if workspace:
        root = os.path.dirname(pen_of(workspace))
        terms.append(os.path.basename(scoring_area(root)).lower())
        outside = outside_pattern(workspace, temp)
    hits = []
    for tool, text in calls:
        lowered = text.lower()
        hits.extend({"tool": tool, "term": term, "call": text[:300]}
                    for term in terms if term in lowered)
        if outside is None:
            continue

        # A call's input arrives as JSON, which doubles a Windows path's
        # backslashes; both spellings become forward slashes.
        normal = lowered.replace("\\\\", "/").replace("\\", "/")
        hits.extend({"tool": tool, "term": match.group(0),
                     "call": text[:300]}
                    for match in outside.finditer(normal))
    return {"transcripts": files, "hits": hits}


# Where a path ends on a command line: the end of the text, a separator, a
# space, a quote or a list delimiter.
PATH_END = "(?=$|[/\\s\"';,])"


def path_forms(paths):
    """Each path lowercased with forward slashes, in its Windows form and its
    Git Bash `/c/` form."""
    forms = set()
    for path in paths:
        full = os.path.abspath(path).replace("\\", "/").lower().rstrip("/")
        forms.add(full)
        if len(full) > 1 and full[1] == ":":
            forms.add("/%s%s" % (full[0], full[2:]))
    return sorted(forms)


def path_pattern(paths):
    """A pattern matching any of `paths` the way a command line spells it.

    It ends where the path does, so `none-1` matches neither `none-10` nor
    `none-1.tar`.
    """
    return re.compile("(?:%s)%s" % (
        "|".join(re.escape(form) for form in path_forms(paths)), PATH_END))


def outside_pattern(workspace, temp):
    """A pattern matching a path into the run root other than the trial's own
    pen, workspace or temporary directory, as normalised by `reach`."""
    workspace = os.path.abspath(workspace)
    pen = pen_of(workspace)
    root = os.path.dirname(pen)
    own = [re.escape(os.path.basename(pen).lower())]
    if temp:
        name = os.path.basename(os.path.abspath(temp)).lower()
        own.append("tmp/" + re.escape(name))

    # A sentence can end on the trial's own path, as in "the repo at
    # ...\none-1. I need", so punctuation before the path ends still leaves
    # it the trial's own, and so does a pip extra, as in `pip install
    # "...\hybrid-2[dev]"`. A suffix is not punctuation: `none-1.tar` stays
    # another entry of the root.
    not_own = "(?!(?:%s)(?:\\[[^\\]/\\s\"';,]*\\])?[.:!?)\\]]*%s)" % (
        "|".join(own), PATH_END)
    forms = "|".join(re.escape(form) for form in path_forms([root]))

    # The root itself, whose listing names every other trial, and any entry
    # of it named from the root. The entries hold earlier trials' workspaces,
    # their tarballs, and the shared home with every transcript.
    alternatives = ["(?:%s)/?(?=$|[\\s\"';,])" % forms,
                    "(?:%s)/%s[^/\\s\"';,]+" % (forms, not_own)]

    # An entry of the root climbed to by a relative path, from any depth: a
    # command can change directory first, so `../` reaches the root from the
    # pen as `../../` does from the workspace. The pen's own entries are not
    # the root's, so a virtualenv beside the workspace stays the trial's.
    entries = (sorted(entry.lower() for entry in os.listdir(root))
               if os.path.isdir(root) else [])
    if entries:
        alternatives.append("\\.\\./%s(?:%s)%s" % (
            not_own, "|".join(re.escape(entry) for entry in entries),
            PATH_END))
    return re.compile("|".join(alternatives))


def process_table():
    """Every running process, as (pid, executable, command line)."""
    if os.name == "nt":
        script = ("[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
                  "Get-CimInstance Win32_Process | Select-Object ProcessId, "
                  "ExecutablePath, CommandLine | ConvertTo-Json -Compress")
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", script],
                              capture_output=True, text=True, encoding="utf-8",
                              errors="replace", timeout=120)
        rows = json.loads(proc.stdout or "[]")
        if isinstance(rows, dict):
            rows = [rows]
        return [(row["ProcessId"], row.get("ExecutablePath") or "",
                 row.get("CommandLine") or "") for row in rows]
    proc = subprocess.run(["ps", "-eo", "pid=,args="], capture_output=True,
                          text=True, encoding="utf-8", errors="replace",
                          timeout=120)
    table = []
    for line in proc.stdout.splitlines():
        pid, _, command = line.strip().partition(" ")
        if pid.isdigit():
            table.append((int(pid), "", command))
    return table


def stop_processes(paths, table=None):
    """Stop every process running from one of `paths`; return what stopped.

    A server the agent started in the background outlives the CLI, holds its
    files open, and answers on a port the next trial may choose.
    """
    pattern = path_pattern(paths)
    spared = {os.getpid(), os.getppid()}
    stopped = []
    for pid, executable, command in (process_table() if table is None
                                     else table):
        text = ("%s %s" % (executable, command)).replace("\\", "/").lower()
        if pid in spared or not pattern.search(text):
            continue

        # A process the tree kill already took is not an error.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/T", "/F"],
                           capture_output=True, timeout=60)
        else:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        stopped.append({"pid": pid, "command": (command or executable)[:300]})
    return stopped


class LiveRunError(Exception):
    """Another run of the same tool is live against the same scoring area."""


def claim_path(area, tool):
    """Where a run of `tool` marks `area` as in use."""
    return os.path.join(area, "%s.running" % os.path.splitext(tool)[0])


def read_claim(path):
    """The run a marker names, or None when it holds no readable record."""
    try:
        with io.open(path, encoding="utf-8") as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        return None
    return record if isinstance(record.get("pid"), int) else None


def running_as(pid, tool):
    """Whether process `pid` is running and its command line names `tool`.

    The command line is read as well as the pid, because an ended run's pid
    is soon reused by some other process, and that process holds nothing.
    """
    table = process_table()

    # A listing that cannot see this process cannot see any other either, and
    # read as empty it would call every live run ended.
    if not any(listed == os.getpid() for listed, _, _ in table):
        raise LiveRunError("the process listing does not show this run, so "
                           "whether another is live cannot be told")
    named = re.compile(r"(?:^|[\\/\s\"'])%s(?:$|[\s\"'])" % re.escape(tool),
                       re.IGNORECASE)
    return any(listed == pid and named.search(command or "")
               for listed, _, command in table)


def claim_area(area, tool):
    """Mark `area` as in use by this run of `tool`; return the marker's path.

    Every tool clears a trial's working directory before rebuilding it, so a
    second run against the same area deletes what the first is reading. A
    marker naming a live run of `tool` refuses this one. A marker whose
    process has ended, or whose pid now belongs to something else, is taken
    over, so a run that crashed does not hold the area for good.
    """
    os.makedirs(area, exist_ok=True)
    path = claim_path(area, tool)
    record = {"pid": os.getpid(), "tool": tool, "argv": sys.argv,
              "started": datetime.datetime.now().isoformat(timespec="seconds")}

    # Two attempts: the second follows a takeover, and failing it means
    # another run took the area over in between.
    for _ in range(2):
        try:
            handle = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            holder = read_claim(path)
            if holder is None:
                raise LiveRunError("%s names no run; remove it if no %s run "
                                   "is live" % (path, tool))
            if running_as(holder["pid"], tool):
                raise LiveRunError("a %s run is live against %s: pid %d, "
                                   "started %s" % (tool, area, holder["pid"],
                                                   holder.get("started")))
            print("taking over %s: pid %d, started %s, is no longer a %s run"
                  % (path, holder["pid"], holder.get("started"), tool))
            try:
                os.remove(path)
            except FileNotFoundError:
                pass
            continue
        with io.open(handle, "w", encoding="utf-8") as out:
            json.dump(record, out)
        return path
    raise LiveRunError("another %s run claimed %s during the takeover"
                       % (tool, area))


def release_area(path):
    """Remove this run's marker, and leave one another run holds."""
    holder = read_claim(path)
    if holder is not None and holder["pid"] == os.getpid():
        os.remove(path)


def created_at(path):
    """When a file or directory was created, or last changed where the
    platform records no creation time."""
    stat = os.stat(path)
    return getattr(stat, "st_birthtime", stat.st_ctime)


def shared_leftovers(shared, since, calls):
    """What a trial left in the machine's temporary directory, by name.

    Git Bash maps `/tmp` to that directory whatever `TEMP` says, so a trial
    writing to `/tmp` by name bypasses its own. An entry counts only when it
    appeared after the trial started and a tool call names it, because other
    programs write there too.
    """
    named = "\n".join(text.lower() for _, text in calls)
    found = []
    for entry in sorted(os.listdir(shared)) if os.path.isdir(shared) else []:
        try:
            if created_at(os.path.join(shared, entry)) < since:
                continue
        except OSError:
            continue
        if re.search(r"(?<![\w.-])%s(?![\w.-])" % re.escape(entry.lower()),
                     named):
            found.append(entry)
    return found


def gather_leftovers(shared, entries, target):
    """Move the entries from `shared` under `target`; return where each went."""
    moved = []
    for entry in entries:
        source = os.path.join(shared, entry)
        destination = os.path.join(target, entry)
        try:
            os.makedirs(target, exist_ok=True)
            shutil.move(source, destination)
            moved.append({"from": source, "to": destination})
        except OSError as error:
            moved.append({"from": source, "to": None, "error": str(error)})
    return moved


def contain(workspace, temp, home, shared, since, vendored=None):
    """Close a finished trial off from the next one; say what it left.

    Processes are stopped before anything moves, because a running process
    holds its files open.
    """
    files, calls = read_transcripts(home, workspace, since)
    leftovers = shared_leftovers(shared, since, calls)

    # The pen, not only the workspace: a server started from a virtualenv
    # beside the workspace runs from the pen.
    owned = [pen_of(workspace), temp, home] + [os.path.join(shared, entry)
                                               for entry in leftovers]
    result = {"reach": reach(files, calls, workspace, temp, vendored),
              "shared_temp_dir": shared}

    # Stopping processes by name reaches every process of that name on the
    # machine, so it voids the trial as a path past the workspace does.
    if result["reach"]["hits"] is not None:
        result["reach"]["hits"].extend(stopped_by_name(files))
    try:
        result["stopped"] = stop_processes(owned)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result["stopped"], result["stop_error"] = None, str(error)
    result["shared_temp"] = gather_leftovers(shared, leftovers,
                                             os.path.join(temp, "shared"))
    return result


def read_input(path):
    """A pinned input's text, stripped; refused where the file is empty."""
    try:
        with io.open(path, encoding="utf-8") as handle:
            text = handle.read().strip()
    except OSError as error:
        raise TrialError("cannot read %s: %s" % (path, error))
    if not text:
        raise TrialError("%s is empty" % path)
    return text


def read_change_prompt(path=CHANGE_PROMPT):
    """The change task's prompt, as pinned before the round."""
    return read_input(path)


def prepare_change_workspace(arm, trial, root, build):
    """Unpack a build trial's frozen workspace for its change task.

    Returns the workspace and the commit its starting state is recorded in.
    """
    name = "change-%s" % trial_name(arm, trial)
    workspace = trial_workspace(root, name)
    if os.path.exists(pen_of(workspace)):
        raise TrialError("workspace %s already exists; a trial never reuses "
                         "one" % workspace)
    tarball = (build.get("frozen") or {}).get("tarball")
    if not tarball or not os.path.isfile(tarball):
        raise TrialError("build trial %s left no frozen tarball at %s"
                         % (trial_name(arm, trial), tarball))

    # Unpacked beside the workspace and renamed, because the tarball's top
    # directory carries the build trial's name as it was spelled when frozen,
    # not the change task's.
    unpacking = os.path.join(root, ".unpacking-%s" % name)
    shutil.rmtree(unpacking, ignore_errors=True)
    try:
        with tarfile.open(tarball) as archive:
            archive.extractall(unpacking, filter="data")
        os.makedirs(pen_of(workspace))
        shutil.move(os.path.join(unpacking, frozen_top(tarball, unpacking)),
                    workspace)
    except (OSError, tarfile.TarError) as error:
        raise TrialError("could not unpack %s: %s" % (tarball, error))
    finally:
        shutil.rmtree(unpacking, ignore_errors=True)

    # What the build trial left uncommitted is part of the starting state, so
    # it is committed here and churn counts only what the change adds.
    git(workspace, "add", "-A")
    git(workspace, "-c", "user.name=efficacy",
        "-c", "user.email=efficacy@example.invalid",
        "commit", "-q", "--allow-empty", "-m",
        "start: change task, %s arm %s" % (ARMS[arm]["label"], arm))
    return workspace, git(workspace, "rev-parse", "HEAD")


def spec_digest(path):
    """The sha256 of a file's bytes, read in chunks, so a tarball of a build's
    virtualenv is hashed without being held in memory."""
    digest = hashlib.sha256()
    with io.open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_digest(text):
    """The sha256 of a text as UTF-8."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def registration_digest(entry):
    """The sha256 of a registration entry, its keys sorted, so one entry has
    one digest whatever order it is written in."""
    return text_digest(json.dumps(entry, sort_keys=True,
                                  separators=(",", ":")))


def round_problem(round_name, arms, k, task):
    """Why a run of these arms, at this K, on this task, may not run as the
    named round, or None."""
    entry = REGISTRATIONS.get(round_name)
    if entry is None:
        return ("round %s is not registered; the registered rounds are %s"
                % (round_name, ", ".join(sorted(REGISTRATIONS))))
    stray = [arm for arm in arms if arm not in entry["arms"]]
    if stray:
        return ("round %s does not register the arm %s; its arms are %s"
                % (round_name, ", ".join(stray), ", ".join(entry["arms"])))
    registered = entry["tasks"].get(task)
    if registered is None:
        return "round %s registers no %s task" % (round_name, task)
    if k > registered["k"]:
        return ("--k %d is past round %s's registered K = %d for its %s task"
                % (k, round_name, registered["k"], task))
    return None


def prompt_problem(round_name, task, prompt):
    """Why a task's prompt is not the one the named round registers, or
    None."""
    registered = REGISTRATIONS[round_name]["tasks"][task]["prompt_sha256"]
    digest = text_digest(prompt)
    if digest != registered:
        return ("the %s prompt is not the one round %s registers: sha256 %s, "
                "registered %s" % (task, round_name, digest, registered))
    return None


def spec_problem(arms, spec_name, digest, round_name=None):
    """Why a run of these arms may not build from this spec, or None.

    A run naming a round builds from the spec that round's entry registers.
    A run naming none, holding a round-5, round-5d or round-5e arm, builds
    from the spec round 5 registers; any other run is not checked here.
    """
    if round_name is not None:
        spec = REGISTRATIONS[round_name]["spec"]
        if spec_name != spec["name"]:
            return ("round %s registers the %s spec, and this run names %s"
                    % (round_name, spec["name"], spec_name))
        if digest != spec["sha256"]:
            return ("the %s spec is not the content round %s registers: "
                    "sha256 %s, registered %s"
                    % (spec_name, round_name, digest, spec["sha256"]))
        return None
    if not set(arms) & set(ROUND5_ARMS + ROUND5D_ARMS + ROUND5E_ARMS):
        return None
    name, registered = ROUND5_SPEC
    if spec_name != name:
        return ("round 5 registers the %s spec, and this run names %s"
                % (name, spec_name))
    if digest != registered:
        return ("the %s spec is not the content round 5 registers: sha256 %s, "
                "registered %s; a round from 6 on is named with --round"
                % (name, digest, registered))
    return None


def run_files(root):
    """Every run record in a root, by path, in time order."""
    if not os.path.isdir(root):
        return []
    return sorted(os.path.join(root, entry) for entry in os.listdir(root)
                  if entry.startswith("run-") and entry.endswith(".json"))


# What every trial record of a named round carries, so a record read on its
# own, copied or reused, still says which round, task, arm and block it was.
IDENTITY = ("round", "task", "arm", "block")

# What a named round's run record says of the round as a whole, which any
# rewrite of the record keeps.
RUN_IDENTITY = ("round", "registration", "fixtures")


def identity_problem(root, round_name=None, digest=None):
    """Why the run records in `root` do not fit a run of `round_name` under
    the registration at `digest`, or None. With no round named, no record
    may name one."""
    for file in run_files(root):
        with io.open(file, encoding="utf-8") as handle:
            run = json.load(handle)
        named, base = run.get("round"), os.path.basename(file)

        # A header naming no round over trials that name one is a named
        # round's record that lost its identity, as a copy written without
        # it would be; read as the pilot's, it would let any run join it.
        if named is None:
            marked = [record for record in run.get("trials", [])
                      if record.get("round") is not None]
            if marked:
                return ("%s names no round, yet its trial %s names round %s"
                        % (base, name_of(marked[0]), marked[0]["round"]))

        # A root holds one round. A run naming none in a named round's root
        # would be read under the pilot's rules, and the reverse would put a
        # named round's trials beside records no registration covers.
        if named is None and round_name is not None:
            return ("%s names no round, so this root is not round %s's"
                    % (base, round_name))
        if named is not None and round_name is None:
            return ("%s is round %s's, so a run in this root names it with "
                    "--round %s" % (base, named, named))
        if named is None:
            continue
        if named != round_name:
            return ("%s is round %s's, and this run names round %s"
                    % (base, named, round_name))
        if run.get("registration") != digest:
            return ("%s ran under round %s's registration at sha256 %s, and "
                    "the registration now reads %s"
                    % (base, named, run.get("registration"), digest))
        for record in run.get("trials", []):
            missing = [key for key in IDENTITY if record.get(key) is None]
            if missing or record["round"] != named:
                return ("%s holds trial %s with %s, so it cannot be shown to "
                        "be round %s's"
                        % (base, name_of(record),
                           "no %s" % ", ".join(missing) if missing
                           else "round %s" % record["round"], named))
    return None


def recorded_round(root):
    """The round a root's run records name, and why they do not hold it
    whole: (None, None) for records from before rounds were named."""
    named = None
    for file in run_files(root):
        with io.open(file, encoding="utf-8") as handle:
            named = json.load(handle).get("round")
        if named is not None:
            break
    if named is None:
        return None, identity_problem(root)
    if named not in REGISTRATIONS:
        return named, ("the run records name round %s, which is not "
                       "registered" % named)
    return named, identity_problem(root, named,
                                   registration_digest(REGISTRATIONS[named]))


def owed_by_task(entry, records):
    """The blocks each task of a registered round still owes, by task.

    A block is owed until every registered arm has a scorable trial of that
    task in it. A change task counts whatever its arm's build trial did,
    since it starts from a fixture and not from that build.
    """
    owed = {}
    for task, registered in sorted(entry["tasks"].items()):
        done = {(record.get("arm"), record.get("trial")) for record in records
                if record.get("task", "build") == task
                and record.get("outcome") in SCORABLE}
        owed[task] = [block for block in range(1, registered["k"] + 1)
                      if any((arm, block) not in done
                             for arm in entry["arms"])]
    return owed


def manifest_path(entry):
    """Where a round's fixture manifest is, beside this module."""
    return os.path.join(HERE, entry["tasks"]["change"]["fixtures"]["manifest"])


def read_fixtures(entry, directory):
    """The fixtures a round's change task starts from, each checked against
    its tarball in `directory`, in the order the blocks take them."""
    path = manifest_path(entry)
    try:
        with io.open(path, encoding="utf-8") as handle:
            listed = json.load(handle).get("fixtures") or []
    except (OSError, ValueError) as error:
        raise TrialError("cannot read the fixture manifest %s: %s"
                         % (path, error))

    # No fixture means no change task can start the same for every arm, and
    # falling back to each arm's own build would mix the build into the change.
    if not listed:
        raise TrialError("the fixture manifest %s lists no fixture, so no "
                         "change task can start; a build is listed once it "
                         "qualifies" % path)
    source = entry["tasks"]["change"]["fixtures"]["from"]["arm"]
    fixtures = []
    for fixture in listed:
        trial = fixture.get("trial") or ""
        if split_name(trial)[0] != source:
            raise TrialError("fixture %s is not a build of arm %s"
                             % (trial, source))

        # The readings that qualified a build are what its change tasks are
        # read against, so one listed without them has not qualified.
        if not isinstance(fixture.get("baseline"), dict) \
                or not fixture["baseline"]:
            raise TrialError("fixture %s carries no baseline readings, so it "
                             "has not qualified" % trial)
        tarball = os.path.join(directory, "%s.tar" % trial)
        if not os.path.isfile(tarball):
            raise TrialError("fixture %s has no tarball at %s"
                             % (trial, tarball))
        digest = spec_digest(tarball)
        if digest != fixture.get("sha256"):
            raise TrialError("fixture %s's tarball %s has sha256 %s, and the "
                             "manifest lists %s"
                             % (trial, tarball, digest, fixture.get("sha256")))
        fixtures.append(dict(fixture, tarball=tarball))
    return sorted(fixtures, key=lambda fixture: split_name(fixture["trial"])[1])


def fixture_for(fixtures, block):
    """The fixture a block's change tasks start from: the block-th in
    order, cycling when fewer qualified than the round has blocks."""
    return fixtures[(block - 1) % len(fixtures)]


def run_fixtures(options):
    """A named round's change run's fixtures, checked, and what its run
    record says of them: the manifest's hash, how many qualified, how many
    distinct ones its blocks start from, and which each block takes."""
    entry = REGISTRATIONS[options.round]
    if not getattr(options, "fixtures", None):
        raise TrialError("round %s's change task starts from its fixtures; "
                         "name the directory holding their tarballs with "
                         "--fixtures" % options.round)
    fixtures = read_fixtures(entry, options.fixtures)
    blocks = {block: fixture_for(fixtures, block)["trial"]
              for block in range(1, options.k + 1)}
    return fixtures, {"manifest_sha256": spec_digest(manifest_path(entry)),
                      "qualified": len(fixtures),
                      "distinct": len(set(blocks.values())),
                      "blocks": {str(block): trial
                                 for block, trial in blocks.items()}}


def fixtures_problem(root, summary):
    """Why a named round's change run, taking its fixtures as `summary`
    says, may not join the change runs already in `root`, or None."""

    # The registration names the manifest only by its file, so a manifest
    # edited between two runs of one round would start a block's arms from
    # different builds; its content and each block's build must hold.
    for file in run_files(root):
        with io.open(file, encoding="utf-8") as handle:
            run = json.load(handle)
        if run.get("task") != "change":
            continue
        earlier, base = run.get("fixtures") or {}, os.path.basename(file)
        if earlier.get("manifest_sha256") != summary["manifest_sha256"]:
            return ("%s took its fixtures from a manifest at sha256 %s, and "
                    "the manifest now reads %s"
                    % (base, earlier.get("manifest_sha256"),
                       summary["manifest_sha256"]))
        for block, trial in sorted(summary["blocks"].items()):
            started = (earlier.get("blocks") or {}).get(block, trial)
            if started != trial:
                return ("%s started block %s from %s, and this run would "
                        "start it from %s" % (base, block, started, trial))
    return None


def round_records(root):
    """Every trial record in a root's run records, in time order."""
    records = []
    for file in run_files(root):
        with io.open(file, encoding="utf-8") as handle:
            records.extend(json.load(handle).get("trials", []))
    return records


def registered_run(options, arms):
    """Hold a run to the round it names and its root to that round; return
    the identity its run record carries, None for a run naming no round."""
    round_name = getattr(options, "round", None)
    if round_name is None:
        problem = identity_problem(options.root)
        if problem:
            raise TrialError(problem)
        return None
    problem = round_problem(round_name, arms, options.k, options.task)
    if problem:
        raise TrialError(problem)
    prompt = PROMPT if options.task == "build" else read_change_prompt()
    digest = registration_digest(REGISTRATIONS[round_name])
    problem = (prompt_problem(round_name, options.task, prompt)
               or spec_problem(arms, options.spec,
                               spec_digest(SPECS[options.spec]), round_name)
               or identity_problem(options.root, round_name, digest))
    if problem:
        raise TrialError(problem)
    return {"round": round_name, "registration": digest}


# What a fixture's tree loses before an arm's change task starts from it:
# what its builder was told or read, its settings, its databases, its caches
# and environments, and its history. Each would hand every arm the build
# trial's context or state, and the arm's own context is installed after.
FIXTURE_DROPPED_DIRS = (".git", ".claude", "__pycache__", ".pytest_cache",
                        ".mypy_cache", ".ruff_cache", ".hypothesis", ".tox",
                        ".nox", ".cache", "node_modules", "htmlcov", ".vscode",
                        ".idea")
FIXTURE_DROPPED_FILES = ("claude.md", "claude.local.md", "agents.md",
                         ".coverage")
FIXTURE_DROPPED_SUFFIXES = (".sqlite", ".sqlite3", ".db", ".pyc", ".pyo",
                            ".jsonl")


def kept_from_fixture(relative, environments):
    """Whether a path in a fixture's tree, relative to its top, is code or a
    test the change task starts from; `environments` names the virtualenvs
    in the tree."""
    parts = relative.split("/")
    lowered = [part.lower() for part in parts]
    if any(part in FIXTURE_DROPPED_DIRS or part.endswith(".egg-info")
           for part in lowered):
        return False
    if lowered[:2] == VENDORED["into"].lower().split("/"):
        return False
    if any("/".join(parts[:index]) in environments
           for index in range(1, len(parts) + 1)):
        return False

    # The round's spec replaces the one the build was given.
    if lowered == ["spec.md"]:
        return False
    return not (lowered[-1] in FIXTURE_DROPPED_FILES
                or lowered[-1].endswith(FIXTURE_DROPPED_SUFFIXES))


def unpack_fixture(tarball, target):
    """Unpack the code and tests of a fixture's tree into `target`."""
    with tarfile.open(tarball) as archive:
        members = archive.getmembers()
        tops = {member.name.split("/")[0] for member in members}
        if len(tops) != 1:
            raise TrialError("%s does not hold one directory: %s"
                             % (tarball, ", ".join(sorted(tops))))
        prefix = tops.pop() + "/"
        inside = [member for member in members
                  if member.name.startswith(prefix)
                  and (member.isfile() or member.isdir())]
        for member in inside:
            member.name = member.name[len(prefix):]

        # A virtualenv is known by the file every one carries at its root.
        environments = {member.name.rpartition("/")[0] for member in inside
                        if member.isfile()
                        and member.name.rpartition("/")[2] == "pyvenv.cfg"}
        environments.discard("")
        kept = [member for member in inside
                if kept_from_fixture(member.name, environments)]
        archive.extractall(target, members=kept, filter="data")


def prepare_fixture_workspace(arm, block, root, fixture, spec):
    """Lay out an arm's change task of a block on its fixture: the build's
    code and tests, the round's spec, the arm's context, one commit.

    Returns the workspace, its starting commit and what was vendored.
    """
    if arm not in ARMS:
        raise TrialError("unknown arm %r; the arms are %s"
                         % (arm, ", ".join(sorted(ARMS))))
    workspace = trial_workspace(root, "change-%s" % trial_name(arm, block))
    if os.path.exists(pen_of(workspace)):
        raise TrialError("workspace %s already exists; a trial never reuses "
                         "one" % workspace)

    # Checked again here, as the tarball is the one unpacked, so a fixture
    # replaced after the run started refuses the trials after it.
    digest = spec_digest(fixture["tarball"])
    if digest != fixture["sha256"]:
        raise TrialError("fixture %s's tarball %s has sha256 %s, and the "
                         "manifest lists %s" % (fixture["trial"],
                                                fixture["tarball"], digest,
                                                fixture["sha256"]))
    os.makedirs(workspace)
    try:
        unpack_fixture(fixture["tarball"], workspace)
    except (OSError, tarfile.TarError) as error:
        remove_tree(pen_of(workspace))
        raise TrialError("could not unpack %s: %s"
                         % (fixture["tarball"], error))
    shutil.copyfile(spec, os.path.join(workspace, "SPEC.md"))
    vendored = install_arm(workspace, arm)
    commit_start(workspace, "start: change task on %s, %s arm %s"
                 % (fixture["trial"], ARMS[arm]["label"], arm))
    return workspace, git(workspace, "rev-parse", "HEAD"), vendored


def run_trial(arm, trial, root, home, options):
    """Run one build trial and return its record."""
    spec_name = getattr(options, "spec", "normal")
    spec = SPECS[spec_name]
    round_name = getattr(options, "round", None)

    # Read again for every trial, so an edit made after the run started
    # refuses the trials after it rather than building them from a new spec.
    arms = getattr(options, "arm_list", ())
    problem = spec_problem(arms, spec_name, spec_digest(spec), round_name)
    if problem:
        raise TrialError(problem)
    workspace, vendored = prepare_workspace(arm, trial, root, spec)

    # The copy is what the agent reads, and the source can change between the
    # check above and the copy, so the copy is what is checked and recorded.
    # A refused workspace is removed, so the trial's slot stays free.
    digest = spec_digest(os.path.join(workspace, "SPEC.md"))
    problem = spec_problem(arms, spec_name, digest, round_name)
    if problem:
        remove_tree(pen_of(workspace))
        raise TrialError(problem)
    record = {"arm": arm, "label": ARMS[arm]["label"], "trial": trial,
              "task": "build", "vendored": vendored,
              "spec": {"file": os.path.basename(spec), "sha256": digest}}
    if round_name is not None:
        record.update(round=round_name, block=trial)
    return run_agent(workspace, trial_name(arm, trial), PROMPT, record, root,
                     home, options)


def run_change_trial(arm, trial, root, home, options, build):
    """Run one change task on a copy of its build trial; return its record."""
    workspace, base = prepare_change_workspace(arm, trial, root, build)
    record = {"arm": arm, "label": ARMS[arm]["label"], "trial": trial,
              "task": "change", "base": base,
              "build_frozen": build.get("frozen"),
              "vendored": build.get("vendored")}
    return run_agent(workspace, "change-%s" % trial_name(arm, trial),
                     read_change_prompt(), record, root, home, options)


def run_fixture_change_trial(arm, block, root, home, options, fixture):
    """Run one registered round's change task on its block's fixture; return
    its record."""
    round_name = options.round
    spec_name = REGISTRATIONS[round_name]["spec"]["name"]
    spec = SPECS[spec_name]
    prompt = read_change_prompt()

    # Both read again for every trial, as a build trial's spec is.
    problem = (prompt_problem(round_name, "change", prompt)
               or spec_problem(options.arm_list, spec_name, spec_digest(spec),
                               round_name))
    if problem:
        raise TrialError(problem)
    workspace, base, vendored = prepare_fixture_workspace(arm, block, root,
                                                          fixture, spec)
    digest = spec_digest(os.path.join(workspace, "SPEC.md"))
    problem = spec_problem(options.arm_list, spec_name, digest, round_name)
    if problem:
        remove_tree(pen_of(workspace))
        raise TrialError(problem)
    record = {"arm": arm, "label": ARMS[arm]["label"], "trial": block,
              "block": block, "round": round_name, "task": "change",
              "base": base, "vendored": vendored,
              "fixture": {key: fixture[key]
                          for key in ("trial", "sha256", "tarball")},
              "spec": {"file": os.path.basename(spec), "sha256": digest}}
    return run_agent(workspace, "change-%s" % trial_name(arm, block), prompt,
                     record, root, home, options)


# The endings a trial is scored on. A blocked trial was voided and its re-run
# carries the score; a refused one never started.
SCORABLE = ("completed", "budget", "timeout")


def scorable_trials(root, run=None, task="build"):
    """Every trial of `task` the run records offer for scoring, by name."""
    if run:
        files = [run]
    else:
        files = sorted(os.path.join(root, entry)
                       for entry in (os.listdir(root)
                                     if os.path.isdir(root) else [])
                       if entry.startswith("run-") and entry.endswith(".json"))
    if not files:
        raise TrialError("no run record in %s; the harness writes one" % root)
    found, sources = {}, {}
    for file in files:
        with io.open(file, encoding="utf-8") as handle:
            records = json.load(handle).get("trials", [])
        for record in records:
            name = name_of(record)

            # A record written before the change task existed is a build one.
            if record.get("task", "build") != task:
                continue
            if record.get("outcome") not in SCORABLE:
                continue

            # Two records offering one trial means two workspaces for one
            # slot. Picking either would be a choice made after the fact.
            if name in found:
                raise TrialError("%s is offered for scoring by both %s and %s"
                                 % (name, sources[name], file))
            found[name] = record
            sources[name] = file
    return found


# How long the CLI gets to exit after printing its result. It usually exits
# at once; a shell it left running keeps its pipes open, and on Windows the
# `.CMD` shim it runs behind is the process a plain timeout kills, leaving
# the CLI an orphan that holds the pipes for good — which is how round 2's
# `none-3` sat finished for six hours. So the output is watched for the
# result line, and after the grace the whole tree is ended.
RESULT_GRACE_S = 120


def kill_tree(proc):
    """End a process and everything running under it."""
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                       capture_output=True, timeout=60)
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except OSError:
            proc.kill()


def result_of(stdout):
    """The CLI's result object in its output, or None."""
    try:
        payload = json.loads(stdout)
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        return payload
    for line in stdout.splitlines():
        if line.startswith("{") and '"result"' in line:
            try:
                payload = json.loads(line)
            except ValueError:
                continue
            if isinstance(payload, dict) and payload.get("type") == "result":
                return payload
    return None


def run_cli(argv, prompt, cwd, env, timeout, grace=RESULT_GRACE_S,
            clock=time.monotonic):
    """Run the CLI on a prompt; return its status, output, errors and how it
    ended: `exited` on its own, `hung` with its result printed and the tree
    ended after the grace, or `timeout` with the tree ended at the bound and
    whatever it printed kept."""
    extra = {} if os.name == "nt" else {"start_new_session": True}
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            cwd=cwd, env=env, text=True, encoding="utf-8",
                            errors="replace", **extra)
    out, err, seen = [], [], []

    def read(stream, sink, watch):
        for line in stream:
            sink.append(line)
            if watch and not seen and line.startswith("{") \
                    and result_of(line) is not None:
                seen.append(clock())

    readers = [threading.Thread(target=read, args=(proc.stdout, out, True),
                                daemon=True),
               threading.Thread(target=read, args=(proc.stderr, err, False),
                                daemon=True)]
    for reader in readers:
        reader.start()
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except OSError:
        pass

    started, ended = clock(), "exited"
    while proc.poll() is None:
        now = clock()
        if now - started > timeout:
            ended = "timeout"
            kill_tree(proc)
            break
        if seen and now - seen[0] > grace:
            ended = "hung"
            kill_tree(proc)
            break
        time.sleep(0.5)
    proc.wait()

    # The pipes close once every holder is gone, which the tree kill sees to.
    for reader in readers:
        reader.join(timeout=120)
    return proc.returncode, "".join(out), "".join(err), ended


def run_agent(workspace, name, prompt, record, root, home, options):
    """Run the agent in a prepared workspace and complete its record.

    The record carries everything the protocol says a trial must report:
    what ran, under which model and configuration, what it cost, how long
    it took, and the frozen state it left.
    """
    assert_no_ambient_context(workspace, home)
    argv = agent_command(home, options.model, options.effort, options.budget,
                         trial_settings(home, root, workspace))
    record.update({
        "workspace": workspace,
        "prompt": prompt,
        "command": argv,
        "model": options.model,
        "effort": options.effort,
        "cli_version": cli_version(argv[0]),
        "budget_usd": options.budget,
        "timeout_s": options.timeout,
        "environment_removed": {"names": inherited_names(os.environ),
                                "path": interpreter_directories(os.environ)},
        "templates_tree": lib.tree_id(),
        "started_at": now().isoformat(timespec="seconds"),
    })
    if options.dry_run:
        record["outcome"] = "dry-run"
        return record

    # The trial's own temporary directory, apart from the machine's, which
    # every trial shares, and in its pen, so the directory above it is the
    # trial's too. Stamped, because a voided trial re-runs under its own name.
    pen = pen_of(workspace)
    stamp = datetime.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    temp = os.path.join(root if pen == os.path.abspath(workspace) else pen,
                        "tmp", "%s-%s" % (name, stamp))
    os.makedirs(temp)
    record["temp"] = temp
    shared = tempfile.gettempdir()
    since = time.time()
    started = time.monotonic()

    # On standard input, not as an argument: on Windows the CLI is a `.CMD`
    # shim, and `cmd.exe` expands a `%NAME%` pair inside an argument.
    status, stdout, stderr, ended = run_cli(
        argv, prompt, workspace, agent_environment(home, temp=temp),
        options.timeout)
    record["exit_status"] = status
    record["stdout"] = stdout
    record["stderr"] = stderr[-4000:]
    record["ended"] = ended
    record["result"] = result_of(stdout)
    if ended == "timeout" and record["result"] is None:
        record["outcome"], record["reason"] = "timeout", None
    else:

        # A CLI that printed its result and then had to be ended finished
        # the trial; the status the kill left is not the trial's ending.
        record["outcome"], record["reason"] = classify(
            status if ended == "exited" else 0, record["result"])

    record["elapsed_s"] = round(time.monotonic() - started, 1)
    record.update(contain(workspace, temp, home, shared, since,
                          record.get("vendored")))
    record.update(reached(record))
    record["frozen"] = freeze(workspace, root, name)
    if record["outcome"] in VOIDING:
        try:
            record["void"] = void(root, workspace, record["frozen"], name)
            record["frozen"]["tarball"] = record["void"]["tarball"]
        except TrialError as error:
            record["void"] = None
            record["void_error"] = str(error)
    return record


def reached(record):
    """The outcome a finished trial takes when its scan found a reach: a
    scorable trial that read past its workspace is not a measurement of its
    arm, and is voided like a blocked one."""
    hits = (record.get("reach") or {}).get("hits")
    if not hits or record.get("outcome") not in SCORABLE:
        return {}
    return {"outcome": "reached",
            "reason": "a tool call reached past the workspace: %s"
                      % ", ".join(sorted({hit["term"] for hit in hits}))}


def order(arms, k):
    """Interleave the trials by block, each block starting one arm later:
    none-1, short-1, hybrid-1, short-2, hybrid-2, none-2, hybrid-3, ...

    A model-side change part-way through a run then lands across the arms
    rather than on one of them, where it would pass for the arm's effect.
    Rotating the start keeps any arm from always running first or last in
    its block, where a drift within the block would land on it every time.
    """
    count = len(arms)
    return [(arms[(trial - 1 + place) % count], trial)
            for trial in range(1, k + 1) for place in range(count)]


def pending_trials(arms, k, start=None):
    """The interleaved order, from `start` onwards where one is given."""
    if not 1 <= k <= ROUND5_K:
        raise TrialError("--k %d is outside 1 to %d: a round registers its K "
                         "and runs no block past it" % (k, ROUND5_K))
    trials = order(arms, k)
    if start is None:
        return trials
    names = [trial_name(*pair) for pair in trials]
    if start not in names:
        raise TrialError("--from %s is not in this run's order: %s"
                         % (start, ", ".join(names)))
    return trials[names.index(start):]


def write_run(run_file, started_at, records, task="build", prompt=PROMPT,
              arms=(), k=None, identity=None):
    """Rewrite the run record with every trial so far. The run's arms and
    its K are written from the start, so a reader knows the whole run
    before its first trial of each arm is in. `identity` names the round
    and its registration's digest, for a run that names a round."""

    # Written to a sibling and swapped in, so a run killed mid-write leaves
    # the previous record whole rather than half of a new one.
    partial = run_file + ".partial"
    header = {"started_at": started_at.isoformat(timespec="seconds"),
              "task": task, "prompt": prompt}
    if arms:
        header["arms"] = list(arms)
    if k is not None:
        header["k"] = k

    # Every trial record of a named round carries its identity, the running
    # and refused ones too, so none reads as a record of no round.
    if identity:
        header.update(identity)
        for record in records:
            record.setdefault("round", identity["round"])
            record.setdefault("task", task)
            record.setdefault("block", record.get("trial"))
    with io.open(partial, "w", encoding="utf-8") as handle:
        json.dump(dict(header, trials=records), handle, indent=2)
    os.replace(partial, run_file)


def wait_for_generator(probe, every_s, limit_s, sleep=time.sleep,
                       clock=time.monotonic):
    """Probe at once, then on an interval, until the generator answers;
    False on giving up."""

    # The first probe comes before any wait: a block that has already
    # cleared, as one over a token another client had refreshed does the
    # moment the trial's CLI ends, costs the run nothing but the probe.
    deadline = clock() + limit_s
    while True:
        try:
            probe()
            return True
        except (TrialError, subprocess.TimeoutExpired) as error:
            print("  still blocked: %s" % str(error)[:160])
        if clock() >= deadline:
            return False
        sleep(every_s)


# A token the trial's CLI refreshes mid-trial can lose to another client of
# the account refreshing first, which revokes the refresh token the CLI
# holds: that ended a trial four minutes in. One cheap call before a trial
# whose ceiling outlasts the token lets the CLI renew it, where it renews
# near expiry, so the trial itself has nothing to refresh.
def fresh_token(home, ceiling_s, probe, now=time.time):
    """Ask the generator once where the home's token expires within
    `ceiling_s`; return the lines to report, none where the token lasts."""
    path = os.path.join(home, CREDENTIALS)
    expiry = expires_at(path) / 1000.0
    if not expiry:
        return []
    left = expiry - now()
    if left >= ceiling_s:
        return []
    lines = ["credentials: the token expires in %d min, within the trial's "
             "ceiling; asking the generator for a fresh one" % (left // 60)]
    try:
        probe()
    except (TrialError, subprocess.TimeoutExpired) as error:
        lines.append("credentials: the generator did not answer: %s"
                     % str(error)[:120])
        return lines
    renewed = expires_at(path) / 1000.0
    if renewed > expiry:
        lines.append("credentials: the token now expires in %d min"
                     % ((renewed - now()) // 60))
    else:
        lines.append("credentials: the CLI kept the token")
    return lines


def run_in_place(arm, trial, runner, wait, records, write):
    """Run one trial, re-running it once in its place if it was blocked.

    Returns False when the run has to stop.
    """
    name = trial_name(arm, trial)
    lost = None
    while True:
        print("%s  %s%s" % (name, ARMS[arm]["label"],
                            "  (re-run)" if lost else ""))

        # Recorded before it starts, so a harness that dies mid-trial leaves
        # the trial it was on in the record for `recover` to find.
        records.append(in_flight(arm, trial))
        write()
        try:
            record = runner(arm, trial)
        except TrialError as error:
            print("  refused: %s" % error)
            records[-1] = {"arm": arm, "trial": trial, "outcome": "refused",
                           "error": str(error)}
            write()
            return True
        if lost:
            record["substitutes"] = lost["void"]["dir"]
        records[-1] = record
        write()
        print("  %s in %ss" % (record["outcome"], record.get("elapsed_s", 0)))
        hits = (record.get("reach") or {}).get("hits")
        if hits:
            print("  REACHED for %s" % ", ".join(sorted({hit["term"]
                                                         for hit in hits})))
        if record.get("stopped"):
            print("  stopped %d process(es) the trial left running"
                  % len(record["stopped"]))
        if record["outcome"] not in VOIDING:
            return True

        print("  %s: %s" % (record["outcome"],
                            (record.get("reason") or "")[:200]))
        if not record.get("void"):
            print("  stopping: %s" % record.get("void_error"))
            return False

        # A reach is the agent's doing, not the provider's, so it needs no
        # wait, and a second one loses the trial without stopping the run.
        if record["outcome"] == "reached":
            if lost:
                print("  %s was lost twice; it is recorded and not scored"
                      % name)
                return True
            lost = record
            continue
        if lost:
            print("  stopping: %s was blocked twice" % name)
            return False
        lost = record
        if not wait():
            print("  stopping the run")
            return False


def in_flight(arm, trial):
    """The record a trial holds while it runs: whose run it is, and since
    when."""
    return {"arm": arm, "trial": trial, "outcome": "running",
            "harness_pid": os.getpid(),
            "started_at": now().isoformat(timespec="seconds")}


def harness_alive(pid, table):
    """Whether `pid` is a running harness in the process table."""
    return any(row == pid and "harness.py" in command
               for row, _, command in table)


def recover(root, home, table=None):
    """Void every trial a dead harness left in flight in `root`; return the
    workspaces voided.

    A harness stopped mid-trial writes no ending, its agent may still be
    running, and the workspace it leaves blocks the re-run, since a
    workspace is never reused. A trial whose harness still runs belongs to a
    live run, so the root is refused rather than taken from under it.
    """
    table = process_table() if table is None else table
    voided = []
    for run_file in sorted(glob.glob(os.path.join(root, "run-*.json"))):
        with io.open(run_file, encoding="utf-8") as handle:
            run = json.load(handle)
        records = run.get("trials", [])
        changed = False
        for index, record in enumerate(records):
            if record.get("outcome") != "running":
                continue
            name = trial_name(record["arm"], record["trial"])
            if run.get("task") == "change":
                name = "change-" + name
            if harness_alive(record.get("harness_pid"), table):
                raise TrialError("%s is running under harness process %s; a "
                                 "live run holds %s"
                                 % (name, record.get("harness_pid"), root))

            # The orphaned agent names its settings file on its command line,
            # and what it started runs from the pen. A root laid out before
            # pens holds the workspace straight in the root.
            workspace = trial_workspace(root, name)
            if not os.path.isdir(workspace):
                workspace = os.path.join(root, name)
            settings = os.path.join(home, "settings-%s.json" % name)
            ending = {"outcome": "interrupted",
                      "reason": "the harness ended while the trial ran",
                      "stopped": stop_processes([pen_of(workspace), settings],
                                                table)}
            if os.path.isdir(workspace):
                frozen = freeze(workspace, root, name)
                ending["void"] = void(root, workspace, frozen, name)
                frozen["tarball"] = ending["void"]["tarball"]
                ending["frozen"] = frozen
                voided.append(workspace)
            records[index] = dict(record, **ending)
            changed = True
        if changed:
            identity = {key: run[key] for key in RUN_IDENTITY if key in run}
            write_run(run_file, datetime.datetime.fromisoformat(
                run["started_at"]), records, run.get("task", "build"),
                run.get("prompt", PROMPT), run.get("arms") or (),
                run.get("k"), identity or None)
    return voided


# One variable of each kind the trial environment sheds, and two it must keep.
# Planted in a copy rather than in this process, so the check exercises the
# function and not whatever happened to launch the test.
PLANTED_LEAKS = {
    "CLAUDECODE": "1",
    "CLAUDE_EFFORT": "low",
    "CLAUDE_CODE_MESSAGING_SOCKET": "planted",
    "ANTHROPIC_API_KEY": "planted",
    "AI_AGENT": "planted",
    "VSCODE_PID": "1",
    "GIT_EDITOR": "code --wait",
    "LINEAR_API_KEY": "planted",
    "NOTION_TOKEN": "planted",
}
PLANTED_KEPT = {
    "SYSTEMROOT": "planted",
    "CLAUDE_CODE_GIT_BASH_PATH": "planted",
}


def environment_checks():
    """A trial's environment sheds what the launching process carries."""
    interpreter = os.path.abspath(os.path.join(os.sep, "planted", "venv"))
    stale = os.path.join(interpreter, "Scripts")
    kept = os.path.abspath(os.path.join(os.sep, "planted", "tools"))
    home = os.path.abspath(os.path.join(os.sep, "planted", "home"))

    planted = dict(PLANTED_LEAKS)
    planted.update(PLANTED_KEPT)
    planted["VIRTUAL_ENV"] = interpreter
    planted["PATH"] = os.pathsep.join([stale, kept])
    env = agent_environment(home, planted)

    checks = []

    # The plant landed: every name is in the input, so an absent name in the
    # output is the function's doing and not a missing plant.
    checks.append(("every planted name is in the input",
                   all(name in planted for name in PLANTED_LEAKS)
                   and planted["VIRTUAL_ENV"] == interpreter))
    for name in sorted(PLANTED_LEAKS) + ["VIRTUAL_ENV"]:
        checks.append(("%s is removed" % name, name not in env))
    for name, value in sorted(PLANTED_KEPT.items()):
        checks.append(("%s is kept" % name, env.get(name) == value))
    checks.append(("the interpreter leaves PATH", stale not in
                   env.get("PATH", "").split(os.pathsep)))
    checks.append(("every other PATH entry stays",
                   env.get("PATH") == kept))
    checks.append(("the scratch home is the home", env.get("HOME") == home
                   and env.get("USERPROFILE") == home))
    checks.append(("the record names what was removed",
                   "VIRTUAL_ENV" in inherited_names(planted)
                   and interpreter_directories(planted) == [stale]))
    return checks


# Fabricated CLI endings, one per branch of `classify`. The budget ending has
# the shape the installed CLI returned when a real run reached its cap.
ENDINGS = (
    ("a clean finish", 0, {"subtype": "success", "is_error": False},
     "completed"),
    ("the budget cap", 1,
     {"subtype": BUDGET_SUBTYPE, "is_error": True,
      "errors": ["Reached maximum budget ($0.001)"]}, "budget"),
    ("a usage limit, by its wording", 1,
     {"subtype": "success", "is_error": True,
      "result": "Claude AI usage limit reached"}, "blocked"),
    ("a rate limit, by its status", 1,
     {"subtype": "success", "is_error": True, "api_error_status": 429},
     "blocked"),
    ("an error subtype nobody listed", 1,
     {"subtype": "error_during_execution", "is_error": True}, "blocked"),
    ("an error behind a zero status", 0,
     {"subtype": "success", "is_error": True, "result": "Not logged in"},
     "blocked"),
    ("no JSON at all", 1, None, "blocked"),
)


def outcome_checks():
    """Every ending classifies as the protocol says, and a blocked one moves."""
    checks = [("%s is %s" % (label, expected),
               classify(status, result)[0] == expected)
              for label, status, result, expected in ENDINGS]

    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-void-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    workspace = os.path.join(scratch, "none-1")
    os.makedirs(workspace)
    with io.open(os.path.join(workspace, "partial.py"), "w",
                 encoding="utf-8") as handle:
        handle.write("# partial work\n")
    tarball = os.path.join(scratch, "none-1.tar")
    with io.open(tarball, "wb") as handle:
        handle.write(b"frozen")

    # The plant is read before the move, so an empty void is the function's
    # failure and not a workspace that was never there.
    checks.append(("the workspace to void exists",
                   os.path.isfile(os.path.join(workspace, "partial.py"))
                   and os.path.isfile(tarball)))
    try:
        moved = void(scratch, workspace, {"tarball": tarball}, "none-1")
    except TrialError:
        moved = None
    checks.append(("a voided workspace leaves its slot", moved is not None
                   and not os.path.exists(workspace)
                   and not os.path.exists(tarball)))
    checks.append(("a voided workspace is kept under void/", moved is not None
                   and os.path.isfile(os.path.join(moved["workspace"],
                                                   "partial.py"))
                   and os.path.isfile(moved["tarball"])
                   and os.path.dirname(moved["dir"])
                   == os.path.join(scratch, "void")))
    shutil.rmtree(scratch, ignore_errors=True)
    return checks


def replay(outcomes, answers):
    """Drive `run_in_place` through planted outcomes and report what it did."""
    queue, replies = list(outcomes), list(answers)
    records, writes, waits = [], [], []

    def runner(arm, trial):
        return dict(queue.pop(0))

    def wait():
        waits.append(True)
        return replies.pop(0)

    saved, sys.stdout = sys.stdout, io.StringIO()
    try:
        carried_on = run_in_place("none", 1, runner, wait, records,
                                  lambda: writes.append(len(records)))
    finally:
        sys.stdout = saved
    return {"carried_on": carried_on, "records": records, "writes": writes,
            "waits": len(waits),
            "outcomes": [record["outcome"] for record in records]}


def resume_checks():
    """A blocked trial re-runs once in its place; the run stops when it must."""
    checks = []
    arms = ["none", "short", "hybrid"]
    names = [trial_name(*pair) for pair in pending_trials(arms, 3, "short-2")]
    checks.append(("--from short-2 starts there and keeps the order",
                   names == ["short-2", "hybrid-2", "none-2", "hybrid-3",
                             "none-3", "short-3"]))
    try:
        pending_trials(arms, 3, "other-1")
        checks.append(("--from an unknown trial refuses", False))
    except TrialError:
        checks.append(("--from an unknown trial refuses", True))
    try:
        pending_trials(["none", "hybrid"], ROUND5_K + 1)
        checks.append(("a K past the registered ceiling refuses", False))
    except TrialError:
        checks.append(("a K past the registered ceiling refuses", True))
    names = [trial_name(*pair)
             for pair in pending_trials(arms, 5, trial_name("none", 4))]
    checks.append(("--from a later block keeps the rotated order",
                   names == ["none-4", "short-4", "hybrid-4", "short-5",
                             "hybrid-5", "none-5"]))

    # Round 5's five arms: each block starts one arm later, so over five
    # blocks every arm runs once in every place of its block.
    round5 = ["none", "inline", "hybrid", "reference", "skills"]
    rotated = order(round5, 5)
    checks.append(("each block starts one arm later",
                   [arm for arm, _ in rotated[5:10]]
                   == ["inline", "hybrid", "reference", "skills", "none"]))
    places = {arm: {index % 5 for index, (other, _) in enumerate(rotated)
                    if other == arm} for arm in round5}
    checks.append(("over five blocks every arm runs in every place",
                   all(found == set(range(5)) for found in places.values())))
    try:
        held = len(pending_trials(round5, ROUND5_K))
    except TrialError:
        held = None
    try:
        pending_trials(round5, ROUND5_K + 1)
        refused = False
    except TrialError:
        refused = True
    checks.append(("a round-5 run takes K = %d and refuses more" % ROUND5_K,
                   held == 5 * ROUND5_K and refused))
    try:
        later = len(pending_trials(["hand", "short"], ROUND5_K))
    except TrialError:
        later = None
    checks.append(("a round-5d run of hand and short takes K = %d too"
                   % ROUND5_K, later == 2 * ROUND5_K))

    blocked = {"outcome": "blocked", "reason": "planted",
               "void": {"dir": os.path.join("void", "none-1-planted")}}
    completed = {"outcome": "completed"}

    rerun = replay([blocked, completed], [True])
    checks.append(("a blocked trial re-runs in its place",
                   rerun["carried_on"]
                   and rerun["outcomes"] == ["blocked", "completed"]))
    checks.append(("the re-run names the trial it substitutes",
                   rerun["records"][-1].get("substitutes")
                   == blocked["void"]["dir"]))
    checks.append(("the record is written as every trial starts and ends",
                   rerun["writes"] == [1, 1, 2, 2]))
    checks.append(("no trial stays recorded as running",
                   "running" not in rerun["outcomes"]))

    twice = replay([blocked, blocked], [True])
    checks.append(("a second block stops the run", not twice["carried_on"]
                   and twice["outcomes"] == ["blocked", "blocked"]))

    unanswered = replay([blocked], [False])
    checks.append(("no answer stops the run", not unanswered["carried_on"]
                   and unanswered["waits"] == 1))

    reached_once = dict(blocked, outcome="reached")
    redone = replay([reached_once, completed], [])
    checks.append(("a reached trial re-runs at once, with no wait",
                   redone["carried_on"] and redone["waits"] == 0
                   and redone["outcomes"] == ["reached", "completed"]
                   and redone["records"][-1].get("substitutes")
                   == blocked["void"]["dir"]))
    lost_twice = replay([reached_once, reached_once], [])
    checks.append(("a second reach loses the trial and the run goes on",
                   lost_twice["carried_on"]
                   and lost_twice["outcomes"] == ["reached", "reached"]))
    hit = {"tool": "Bash", "term": "hidden-suite", "call": "planted"}
    checks.append(("a scorable trial with a reach becomes reached",
                   reached({"outcome": "completed",
                            "reach": {"hits": [hit]}}).get("outcome")
                   == "reached"
                   and reached({"outcome": "completed",
                                "reach": {"hits": []}}) == {}
                   and reached({"outcome": "blocked",
                                "reach": {"hits": [hit]}}) == {}))

    unmoved = replay([dict(blocked, void=None, void_error="planted")], [])
    checks.append(("a workspace that could not move stops the run",
                   not unmoved["carried_on"] and unmoved["waits"] == 0))

    clock = [0.0]

    def sleep(seconds):
        clock[0] += seconds

    replies = [TrialError("planted"), TrialError("planted"), None]

    def probe():
        reply = replies.pop(0)
        if reply is not None:
            raise reply

    def refuse():
        raise TrialError("planted")

    saved, sys.stdout = sys.stdout, io.StringIO()
    try:
        answered = wait_for_generator(probe, 60, 600, sleep=sleep,
                                      clock=lambda: clock[0])
        answered_at = clock[0]
        clock[0] = 0.0
        gave_up = wait_for_generator(refuse, 60, 180, sleep=sleep,
                                     clock=lambda: clock[0])
    finally:
        sys.stdout = saved
    checks.append(("probing stops when the generator answers",
                   answered and answered_at == 120))
    checks.append(("probing gives up at its limit",
                   not gave_up and clock[0] == 180))
    clock[0] = 0.0
    saved, sys.stdout = sys.stdout, io.StringIO()
    try:
        at_once = wait_for_generator(lambda: None, 60, 600, sleep=sleep,
                                     clock=lambda: clock[0])
    finally:
        sys.stdout = saved
    checks.append(("a blocked trial is probed at once, so an answer costs "
                   "no wait", at_once and clock[0] == 0))

    # By default a block is waited out and the trial re-run; the flag that
    # used to ask for that is still taken, and --stop-on-block refuses it.
    checks.append(("a blocked trial is probed and re-run by default, and "
                   "--stop-on-block stops the run instead",
                   parse_args(["--root", "r"]).resume_after_block
                   and parse_args(["--root", "r",
                                   "--resume-after-block"]).resume_after_block
                   and not parse_args(["--root", "r",
                                       "--stop-on-block"]).resume_after_block))
    return checks


def token_checks():
    """A trial whose ceiling outlasts the account's token is preceded by one
    call to the generator; one whose token lasts is not."""
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-token-self-test")
    remove_tree(scratch)
    home = os.path.join(scratch, "home")
    path = os.path.join(home, CREDENTIALS)
    os.makedirs(os.path.dirname(path))
    moment = 1_700_000_000.0
    probes = []

    def write(expires_s):
        with io.open(path, "w", encoding="utf-8") as handle:
            json.dump({"claudeAiOauth": {"expiresAt": expires_s * 1000}},
                      handle)

    def renewing():
        probes.append("renewing")
        write(moment + 8 * 3600)

    def keeping():
        probes.append("keeping")

    def refusing():
        probes.append("refusing")
        raise TrialError("planted")

    write(moment + 600)
    renewed = fresh_token(home, 7200, renewing, now=lambda: moment)
    write(moment + 3 * 3600)
    kept = fresh_token(home, 7200, keeping, now=lambda: moment)
    write(moment + 600)
    refused = fresh_token(home, 7200, refusing, now=lambda: moment)
    write(moment + 600)
    lasting = fresh_token(home, 300, keeping, now=lambda: moment)
    os.remove(path)
    absent = fresh_token(home, 7200, keeping, now=lambda: moment)
    remove_tree(scratch)
    return [
        ("a trial whose ceiling outlasts its token asks the generator first",
         probes[:1] == ["renewing"] and len(renewed) == 2
         and "expires in 10 min" in renewed[0]
         and "now expires in 480 min" in renewed[1]),
        ("a token that outlasts the ceiling is left alone",
         "keeping" not in probes[:2] and kept == [] and lasting == []
         and probes == ["renewing", "refusing"]),
        ("a generator that does not answer the ask is reported, and the "
         "trial goes on to its own ending",
         len(refused) == 2 and "did not answer" in refused[1]),
        ("without a credentials file nothing is asked", absent == []),
    ]


def remove_tree(path):
    """Delete a directory, including the read-only files git writes."""
    def writable(function, target, _):
        os.chmod(target, 0o700)
        function(target)

    if os.path.exists(path):
        shutil.rmtree(path, onexc=writable)


def change_checks():
    """The change prompt is its file's, whole, and names what the grader
    drives; its workspace starts committed."""
    prompt = read_change_prompt()
    with io.open(CHANGE_PROMPT, encoding="utf-8") as handle:
        whole = handle.read().strip()
    checks = [
        ("the change prompt is read whole from its file",
         prompt == whole
         and prompt.startswith("Add a **spend-threshold** discount")),

        # Round 1's grader drove names the prompt never gave, and its pass
        # rate measured which trials guessed them.
        ("the change prompt names the API and fields the grader drives",
         all(name in prompt for name in (
             "tariff.ThresholdRule", "caps=", "`threshold`", "`minimum`",
             "`caps`", "/invoices/preview"))),
    ]

    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-change-self-test")
    remove_tree(scratch)
    build = os.path.join(scratch, "frozen-elsewhere")
    os.makedirs(build)
    git(build, "init", "-q")
    with io.open(os.path.join(build, "app.py"), "w",
                 encoding="utf-8") as handle:
        handle.write("committed = True\n")
    git(build, "add", "-A")
    git(build, "-c", "user.name=efficacy",
        "-c", "user.email=efficacy@example.invalid",
        "commit", "-q", "-m", "build")
    with io.open(os.path.join(build, "draft.py"), "w",
                 encoding="utf-8") as handle:
        handle.write("left_uncommitted = True\n")

    # Frozen under another name, as a reused trial's tarball may be, so the
    # change task of `none-1` has to take the top directory it finds.
    frozen = freeze(build, scratch, "frozen-elsewhere")

    # The plant landed: the build trial ended with work it never committed,
    # which is the state a change task has to take into its starting commit.
    checks.append(("the build trial left uncommitted work",
                   frozen["uncommitted"] == ["?? draft.py"]))
    try:
        workspace, base = prepare_change_workspace("none", 1, scratch,
                                                   {"frozen": frozen})
    except TrialError:
        workspace, base = None, None
    checks.append(("the change workspace unpacks under its own name, in its "
                   "pen, from a tarball frozen under another name",
                   workspace == trial_workspace(scratch, "change-none-1")
                   and os.path.isfile(os.path.join(workspace, "draft.py"))))
    checks.append(("its starting state is committed", workspace is not None
                   and git(workspace, "status", "--porcelain") == ""
                   and git(workspace, "rev-parse", "HEAD") == base
                   and base != frozen["head"]))
    try:
        prepare_change_workspace("none", 1, scratch, {"frozen": frozen})
        checks.append(("a change workspace is never reused", False))
    except TrialError:
        checks.append(("a change workspace is never reused", True))
    remove_tree(scratch)
    return checks


def listing(path):
    """Every path under `path`, relative to it, sorted."""
    return sorted(os.path.relpath(os.path.join(base, name), path)
                  for base, dirs, files in os.walk(path)
                  for name in dirs + files)


def dry_run_checks():
    """A dry run leaves the root as it found it, so the run that follows in
    the same root prepares every trial the dry run did.

    The root holds what a change task starts from: a frozen build trial and
    the run record offering it. The generator is a stand-in on `PATH` and the
    home a scratch one, so no real CLI or credential is reached.
    """
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-dry-run-self-test")
    remove_tree(scratch)
    root = os.path.join(scratch, "root")
    build = os.path.join(scratch, "built", "none-1")
    os.makedirs(build)
    os.makedirs(root)
    git(build, "init", "-q")
    with io.open(os.path.join(build, "app.py"), "w",
                 encoding="utf-8") as handle:
        handle.write("built = True\n")
    git(build, "add", "-A")
    git(build, "-c", "user.name=efficacy",
        "-c", "user.email=efficacy@example.invalid",
        "commit", "-q", "-m", "build")
    frozen = freeze(build, root, "none-1")
    write_run(os.path.join(root, "run-planted.json"), datetime.datetime.now(),
              [{"arm": "none", "trial": 1, "task": "build",
                "outcome": "completed", "frozen": frozen}])

    stand_in = os.path.join(scratch, "bin")
    os.makedirs(stand_in)
    claude = os.path.join(stand_in,
                          "claude.cmd" if os.name == "nt" else "claude")
    # The stand-in answers each call with a new version, as a CLI updated
    # between two trials would, so a version read once per run shows. It
    # keeps every call's arguments, so a call that asks for a reply shows.
    with io.open(claude, "w", encoding="utf-8") as handle:
        handle.write(
            '@echo off\r\nset n=0\r\n'
            'if exist "%~dp0calls" set /p n=<"%~dp0calls"\r\n'
            'set /a n=n+1\r\n>"%~dp0calls" echo %n%\r\n'
            '>>"%~dp0args" echo %*\r\n'
            'echo 0.0.%n% (stand-in)\r\n' if os.name == "nt" else
            '#!/bin/sh\ncalls="$(dirname "$0")/calls"\n'
            'n=$(($(cat "$calls" 2>/dev/null || echo 0) + 1))\n'
            'echo $n > "$calls"\necho "$@" >> "$(dirname "$0")/args"\n'
            'echo "0.0.$n (stand-in)"\n')
    os.chmod(claude, 0o755)
    saved = {key: os.environ.get(key) for key in ("PATH", "HOME", "USERPROFILE")}
    os.environ["PATH"] = stand_in + os.pathsep + saved["PATH"]
    os.environ["HOME"] = os.environ["USERPROFILE"] = os.path.join(scratch, "me")

    # The account's token expires within every trial's ceiling, so a run
    # proper would ask the generator for a fresh one before each trial. A
    # dry run calls no model, so no call to the stand-in asks it for a
    # reply: only its version is read.
    account = os.path.join(scratch, "me", CREDENTIALS)
    os.makedirs(os.path.dirname(account))
    with io.open(account, "w", encoding="utf-8") as handle:
        json.dump({"claudeAiOauth": {"expiresAt": (time.time() + 600) * 1000}},
                  handle)
    args = os.path.join(stand_in, "args")

    dry = dry_run_area(root)
    before = listing(root)
    outcomes = []
    try:
        for task, prepared in (("change", "change-none-1"), ("build", "none-1")):
            with contextlib.redirect_stdout(io.StringIO()):
                code = main(["--root", root, "--arms", "none", "--k", "1",
                             "--task", task, "--dry-run"])
            outcomes.append((task, code == 0
                             and os.path.isdir(os.path.join(dry, prepared)),
                             listing(root) == before))
        with contextlib.redirect_stdout(io.StringIO()):
            main(["--root", root, "--arms", "none", "--k", "2", "--dry-run"])
        recorded = []
        for run in glob.glob(os.path.join(dry, "run-*.json")):
            with io.open(run, encoding="utf-8") as handle:
                recorded.extend(trial.get("cli_version")
                                for trial in json.load(handle)["trials"])
        try:
            with io.open(args, encoding="utf-8") as handle:
                asked = [line for line in handle.read().splitlines()
                         if " -p " in " %s " % line.strip()]
        except OSError:
            asked = None
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    # The run proper prepares in the root, where a workspace a dry run left
    # would refuse it.
    try:
        prepare_change_workspace("none", 1, root, {"frozen": frozen})
        prepare_workspace("none", 1, root)
        followed = True
    except TrialError:
        followed = False

    # The thin specification reaches its workspace under the one name the
    # prompt gives, so the prompt stays a single text across specifications.
    thin_workspace, _ = prepare_workspace("inline", 1, root, SPECS["thin"])
    with io.open(os.path.join(thin_workspace, "SPEC.md"), "rb") as handle:
        given = handle.read()
    with io.open(SPECS["thin"], "rb") as handle:
        thin = handle.read()
    with io.open(SPEC, "rb") as handle:
        normal = handle.read()

    # A pinned CLI is the one file every trial runs, and a missing one stops
    # the run before a trial rather than falling back to PATH's.
    try:
        PINNED_CLI["path"] = claude
        pinned = agent_executable() == claude
        PINNED_CLI["path"] = os.path.join(scratch, "missing", "claude.exe")
        try:
            agent_executable()
            missing_refused = False
        except TrialError:
            missing_refused = True
    finally:
        PINNED_CLI["path"] = None
    remove_tree(scratch)
    checks = [("the root holds a frozen build and its run record",
               "none-1.tar" in before and "run-planted.json" in before),
              ("every trial records the CLI's version, read as it starts",
               len(recorded) == 2 and len(set(recorded)) == 2
               and all(str(version).endswith("(stand-in)")
                       for version in recorded)),
              ("a pinned CLI is the file a trial runs", pinned),
              ("a pinned CLI that is not there refuses the run",
               missing_refused),
              ("a trial's environment turns the CLI's updater off",
               agent_environment(scratch).get("DISABLE_AUTOUPDATER") == "1")]
    for task, prepared, untouched in outcomes:
        checks.append(("a %s dry run prepares beside the root" % task,
                       prepared))
        checks.append(("a %s dry run leaves the root as it was" % task,
                       untouched))
    checks.append(("the run that follows prepares in the same root",
                   followed))
    checks.append(("a dry run asks the generator for no token, so it calls "
                   "no model", asked == []))
    checks.append(("--spec thin gives the thin spec as SPEC.md",
                   given == thin and thin != normal))
    return checks


def credential_checks():
    """A trial's Git cannot borrow a credential the machine stores."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-credential-self-test")
    remove_tree(scratch)
    os.makedirs(scratch)
    config = os.path.join(scratch, "gitconfig")
    with io.open(config, "w", encoding="utf-8") as handle:
        handle.write('[credential]\n\thelper = "!f() { echo username=planted; '
                     'echo password=planted-secret; }; f"\n')

    # Only the planted helper is configured, so the check neither depends on
    # nor prompts through whatever helper this machine carries.
    planted = dict(os.environ, GIT_CONFIG_GLOBAL=config,
                   GIT_CONFIG_NOSYSTEM="1", GIT_TERMINAL_PROMPT="0")

    def answers(env):
        proc = subprocess.run(["git", "credential", "fill"],
                              input="protocol=https\nhost=example.invalid\n\n",
                              env=env, capture_output=True, text=True,
                              encoding="utf-8", timeout=60)
        return "planted-secret" in proc.stdout

    temp = os.path.join(scratch, "tmp")
    env = agent_environment(os.path.join(scratch, "home"), planted, temp)
    checks = [("a planted Git helper answers outside a trial",
               answers(planted)),
              ("it does not answer inside one", not answers(env)),
              ("the trial's temp directory is its own",
               all(env.get(name) == temp for name in TEMP_NAMES))]
    remove_tree(scratch)
    return checks


def process_checks():
    """A process running from a trial's directory is stopped, and no other."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-process-self-test")
    owned = os.path.join(scratch, "none-1")
    neighbour = os.path.join(scratch, "none-10")
    sleeper = [sys.executable, "-c", "import time; time.sleep(120)"]
    procs = [subprocess.Popen(sleeper + [os.path.join(where, "server.db")])
             for where in (owned, neighbour)]
    try:

        # Both run and are listed before the stop, so one that ends was
        # stopped rather than never started.
        listed = {pid for pid, _, _ in process_table()}
        started = all(proc.poll() is None and proc.pid in listed
                      for proc in procs)
        stopped = stop_processes([owned])
        try:
            procs[0].wait(timeout=30)
        except subprocess.TimeoutExpired:
            pass
        checks = [("two planted processes run and are listed", started),
                  ("the one running from the trial is stopped",
                   procs[0].poll() is not None),
                  ("one whose path only extends it is not",
                   procs[1].poll() is None),
                  ("the record lists what was stopped",
                   any(entry["pid"] == procs[0].pid for entry in stopped))]
    finally:
        stop_processes([neighbour])
        for proc in procs:
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
    return checks


def planted_run(tool):
    """Start a process that reads as a live run of `tool`: a sleeping
    interpreter whose command line names it."""
    return subprocess.Popen([sys.executable, "-c",
                             "import time; time.sleep(120)", tool])


def plant_claim(area, tool, pid):
    """Write a marker naming `pid` as a run of `tool`; return its path."""
    path = claim_path(area, tool)
    os.makedirs(area, exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump({"pid": pid, "tool": tool, "started": "planted"}, handle)
    return path


def claimed(area, tool):
    """The marker's path when claiming `area` for `tool` succeeds, or None
    when it is refused."""
    try:
        return claim_area(area, tool)
    except LiveRunError:
        return None


def claimed_pid(path):
    """The pid a marker names, or None."""
    return (read_claim(path) or {}).get("pid")


def claim_checks():
    """A live run refuses a second; an ended or reused one is taken over."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-claim-self-test")
    remove_tree(scratch)
    live = planted_run("judge.py")
    try:

        # Listed first, so a takeover below is the rule's rather than a
        # stand-in that had not started.
        listed = running_as(live.pid, "judge.py")
        judge = plant_claim(scratch, "judge.py", live.pid)
        planted = claimed_pid(judge) == live.pid
        refused = claimed(scratch, "judge.py") is None
        kept = claimed_pid(judge) == live.pid

        # The same live pid under another tool's marker is a reused pid: in
        # use, and not by that tool.
        score_path = plant_claim(scratch, "score.py", live.pid)
        reused_before = claimed_pid(score_path) == live.pid
        reused = (claimed(scratch, "score.py") == score_path
                  and claimed_pid(score_path) == os.getpid())
    finally:
        live.kill()
        live.wait()
    ended = not running_as(live.pid, "judge.py")
    taken = (claimed(scratch, "judge.py") == judge
             and claimed_pid(judge) == os.getpid())
    release_area(judge)
    released = not os.path.exists(judge)

    plant_claim(scratch, "judge.py", live.pid)
    release_area(judge)
    left = claimed_pid(judge) == live.pid
    with io.open(judge, "w", encoding="utf-8") as handle:
        handle.write("")
    unreadable = claimed(scratch, "judge.py") is None
    remove_tree(scratch)
    return [("a planted live run is listed as that tool",
             listed and planted and reused_before),
            ("a live run refuses a second, and keeps its marker",
             refused and kept),
            ("a live pid that is not the tool is taken over", reused),
            ("an ended run is taken over", ended and taken),
            ("a run removes its own marker, and no other",
             released and left),
            ("a marker naming no run refuses", unreadable)]


def claim_refusal_check(tool, main, root, *extra):
    """Whether `main` on `root`, given `extra` arguments, refuses while a live
    run of `tool` holds the scoring area, and leaves that run's marker as it
    was."""
    live = planted_run(tool)
    try:
        path = plant_claim(scoring_area(root), tool, live.pid)
        before = claimed_pid(path)
        listed = running_as(live.pid, tool)
        printed = io.StringIO()

        # A run that got past the claim may fail anywhere after it, and that
        # is the check failing, not the self-test.
        with contextlib.redirect_stdout(printed):
            try:
                code = main(["--root", root] + list(extra))
            except Exception:
                code = None
        after = claimed_pid(path)
    finally:
        live.kill()
        live.wait()
    return ("a live %s run refuses a second" % tool,
            listed and before == live.pid and after == before
            and bool(code) and "is live" in printed.getvalue())


def leftover_checks():
    """A temp entry a trial made and named moves to its own; nothing else."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-leftover-self-test")
    remove_tree(scratch)
    shared = os.path.join(scratch, "shared")
    before = os.path.join(shared, "old_named")
    os.makedirs(before)

    # Apart in time on either side of the start, so no plant can share a tick
    # of the file system's clock with it.
    time.sleep(0.1)
    since = time.time()
    time.sleep(0.1)
    made = os.path.join(shared, "planted_venv")
    unnamed = os.path.join(shared, "unnamed.tmp")
    os.makedirs(made)
    os.makedirs(unnamed)
    landed = (created_at(before) < since
              <= min(created_at(made), created_at(unnamed)))

    calls = [("Bash", json.dumps({"command": "py -m venv /tmp/planted_venv "
                                             "&& ls /tmp/old_named"}))]
    found = shared_leftovers(shared, since, calls)
    target = os.path.join(scratch, "trial", "shared")
    gather_leftovers(shared, found, target)
    checks = [("the plants straddle the trial's start", landed),
              ("an entry the trial made and named is found",
               found == ["planted_venv"]),
              ("it moves under the trial's own directory",
               os.path.isdir(os.path.join(target, "planted_venv"))
               and not os.path.exists(made)),
              ("an older or unnamed entry stays",
               os.path.isdir(before) and os.path.isdir(unnamed))]
    remove_tree(scratch)
    return checks


# On Windows, the folder name the CLI itself wrote for a real trial, so the
# check holds the harness to the CLI rather than to the harness's own rule.
PLANTED_TRANSCRIPT = ((r"C:\efficacy\run-v290\none-1",
                       "C--efficacy-run-v290-none-1")
                      if os.name == "nt" else
                      ("/efficacy/run-v290/none-1", "-efficacy-run-v290-none-1"))


def reach_checks():
    """A tool call fetching the templates is flagged; reading them is not."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-reach-self-test")
    remove_tree(scratch)
    home = os.path.join(scratch, "home")
    workspace, folder = PLANTED_TRANSCRIPT
    os.makedirs(os.path.join(home, ".claude", "projects", folder))
    transcript = os.path.join(home, ".claude", "projects", folder,
                              "planted.jsonl")
    fetch = ("curl -sL https://github.com/solid-ai-dev/solid-ai-templates/"
             "archive/main.zip -o t.zip")
    entries = [
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Bash",
             "input": {"command": fetch}}]}},
        {"type": "user", "message": {"content": [
            {"type": "tool_result",
             "content": "<!-- Generated with solid-ai-templates -->"}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "text", "text": "The footer names solid-ai-templates."}]}},
        {"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Read",
             "input": {"file_path": "CLAUDE.md"}}]}},
    ]
    with io.open(transcript, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(entry) + "\n" for entry in entries)

    files, calls = read_transcripts(home, workspace)
    hits = reach(files, calls)["hits"] or []
    unscanned = reach(*read_transcripts(home, workspace + "0"))
    checks = [("the planted transcript is found", files == [transcript]),
              ("a fetch of the templates is flagged, and only that",
               [(hit["tool"], hit["term"]) for hit in hits]
               == [("Bash", "solid-ai-templates")]),
              ("no transcript reads as not scanned",
               unscanned["hits"] is None)]

    # A voided attempt in the same workspace: its transcript was last written
    # an hour before the re-run started, and the re-run's is written after.
    voided = os.path.join(os.path.dirname(transcript), "voided.jsonl")
    with io.open(voided, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(entries[0]) + "\n")
    since = time.time()
    os.utime(voided, (since - 3600, since - 3600))
    os.utime(transcript, (since + 1, since + 1))
    landed = (sorted(transcript_files(home, workspace))
              == sorted([transcript, voided])
              and os.path.getmtime(voided) < since
              <= os.path.getmtime(transcript))
    checks.append(("a re-run reads only transcripts written since it "
                   "started", landed
                   and transcript_files(home, workspace, since)
                   == [transcript]))
    remove_tree(scratch)
    return checks


def outside_checks():
    """A call into another part of the run is flagged; the trial's own
    workspace and temporary directory are not."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-outside-self-test")
    remove_tree(scratch)
    root = os.path.abspath(os.path.join(scratch, "run"))
    workspace = os.path.join(root, "none-1")
    temp = os.path.join(root, "tmp", "none-1-planted")
    for directory in (workspace, temp, os.path.join(root, "short-1"),
                      os.path.join(root, "tmp", "short-1-planted"),
                      os.path.join(root, "home", ".claude")):
        os.makedirs(directory)
    io.open(os.path.join(root, "short-1.tar"), "wb").close()
    bash_root = root.replace("\\", "/")
    if bash_root[1:2] == ":":
        bash_root = "/%s%s" % (bash_root[0].lower(), bash_root[2:])

    # The first five stay inside the trial; each of the last four reaches out.
    calls = [
        ("Write", {"file_path": os.path.join(workspace, "tariff", "rules.py")}),
        ("Bash", {"command": 'cd "%s" && ls' % workspace}),
        ("Bash", {"command": "pip install . --cache-dir %s"
                             % os.path.join(temp, "pip")}),
        ("Agent", {"prompt": "The repo is at %s. Map its modules."
                             % workspace}),
        ("PowerShell", {"command": 'pip install "%s[dev]"' % workspace}),
        ("Bash", {"command": "cat ../short-1/src/tariff/pricing.py"}),
        ("PowerShell", {"command": "Get-Item %s"
                                   % os.path.join(root, "short-1.tar")}),
        ("Bash", {"command": "ls %s/home/.claude/projects" % bash_root}),
        ("Read", {"file_path": os.path.join(scoring_area(root),
                                            "hidden-suite", "conftest.py")}),
    ]
    texts = [(tool, json.dumps(payload)) for tool, payload in calls]

    # The plant landed: the root holds another trial beside this one, so a
    # call left unflagged is the scan's doing and not an empty run.
    landed = sorted(os.listdir(root)) == ["home", "none-1", "short-1",
                                          "short-1.tar", "tmp"]
    hits = reach(["planted.jsonl"], texts, workspace, temp)["hits"] or []
    flagged = sorted({index for index, (_, text) in enumerate(texts)
                      for hit in hits if hit["call"] == text[:300]})
    remove_tree(scratch)
    return [("the planted run holds another trial", landed),
            ("the scoring area lies outside the run root",
             not scoring_area(root).startswith(root + os.sep)),
            ("the trial's own paths are not flagged, a pip extra included",
             not [index for index in flagged if index < 5]),
            ("every call reaching past the trial is flagged",
             flagged == [5, 6, 7, 8])]


def pen_checks():
    """A trial's workspace sits in a pen of its own: what the agent puts
    beside the workspace is the trial's, another pen and the root are not,
    and a voided trial takes its whole pen with it."""
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-pen-self-test")
    remove_tree(scratch)
    root = os.path.abspath(os.path.join(scratch, "run"))
    os.makedirs(root)
    workspace, _ = prepare_workspace("none", 1, root)
    pen = os.path.join(root, "none-1")
    temp = os.path.join(pen, "tmp", "none-1-planted")
    venv = os.path.join(pen, "_clean_venv_test")
    for directory in (temp, venv, trial_workspace(root, "short-1"),
                      os.path.join(root, "home", ".claude")):
        os.makedirs(directory)

    # The first four stay in the pen; each of the last five reaches out, the
    # last after changing directory to the pen, one level above the
    # workspace.
    calls = [
        ("Bash", {"command": 'python -m venv "%s"' % venv}),
        ("Bash", {"command": 'cd "%s" && pip install ./none-1' % pen}),
        ("Bash", {"command": "../_clean_venv_test/Scripts/python -m tariff"}),
        ("Bash", {"command": 'cd "%s" && ls' % os.path.dirname(temp)}),
        ("Bash", {"command": 'cd "%s" && ls' % root}),
        ("Read", {"file_path": os.path.join(trial_workspace(root, "short-1"),
                                            "app.py")}),
        ("Bash", {"command": "cat ../../short-1/short-1/app.py"}),
        ("Bash", {"command": "ls %s" % os.path.join(root, "home")}),
        ("Bash", {"command": 'cd "%s" && cat ../short-1/short-1/app.py'
                             % pen}),
    ]
    texts = [(tool, json.dumps(payload)) for tool, payload in calls]
    hits = reach(["planted.jsonl"], texts, workspace, temp)["hits"] or []
    flagged = sorted({index for index, (_, text) in enumerate(texts)
                      for hit in hits if hit["call"] == text[:300]})
    checks = [
        ("a new trial's workspace sits in a pen under its own name",
         workspace == trial_workspace(root, "none-1")
         and pen_of(workspace) == pen),
        ("a workspace straight in the root is its own pen",
         pen_of(os.path.join(root, "none-1")) == pen),
        ("a virtualenv beside the workspace is not flagged",
         not [index for index in flagged if index < 4]),
        ("the root, another pen and a climb out of the pen are flagged",
         flagged == [4, 5, 6, 7, 8]),
    ]

    # The plant landed: the voided try left a virtualenv beside its
    # workspace, which the re-run must not find.
    frozen = freeze(workspace, root, "none-1")
    moved = void(root, workspace, frozen, "none-1")
    checks.append(("a voided trial takes its whole pen and its tarball",
                   not os.path.exists(pen)
                   and os.path.isdir(moved["workspace"])
                   and os.path.isdir(os.path.join(moved["dir"],
                                                  "_clean_venv_test"))
                   and os.path.isfile(moved["tarball"])))
    remove_tree(scratch)
    return checks


def naming_checks():
    """A trial is named by its arm's word and its block, and nothing else
    reads as one."""
    checks = [
        ("a trial is the arm's word, a hyphen and its block",
         trial_name("short", 2) == "short-2"
         and split_name("short-2") == ("short", 2)),
        ("a record names its trial by its arm and block",
         name_of({"arm": "hand", "trial": 1}) == "hand-1"
         and name_of({"arm": "hybrid", "trial": 3}) == "hybrid-3"),
        ("a word name canonicalises to itself",
         canonical("hybrid-3") == "hybrid-3"),
    ]
    for name in ("none", "A1", "short-x", "-1"):
        try:
            split_name(name)
            checks.append(("%r is refused as a trial name" % name, False))
        except TrialError:
            checks.append(("%r is refused as a trial name" % name, True))
    return checks


# A stand-in for the CLI: prints a result, or not, and then lingers with a
# child that inherits its pipes — the shape of a shell left running.
LINGERING_CLI = """\
import json, os, subprocess, sys, time
mode = sys.argv[1]
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(90)"])
open(sys.argv[2], "w").write(str(child.pid))
if mode != "silent":
    print(json.dumps({"type": "result", "subtype": "success",
                      "is_error": False, "result": "done"}), flush=True)
if mode == "exits":
    child.kill()
    sys.exit(0)
time.sleep(90)
"""


def alive(pid):
    """Whether a process exists, without signalling it."""
    if os.name == "nt":
        proc = subprocess.run(["tasklist", "/FI", "PID eq %d" % pid],
                              capture_output=True, text=True, timeout=60)
        return str(pid) in proc.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def hang_checks():
    """A CLI that lingers after its result, or never answers, is ended with
    everything under it, and what it printed is kept."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-hang-self-test")
    remove_tree(scratch)
    os.makedirs(scratch)
    script = os.path.join(scratch, "cli.py")
    with io.open(script, "w", encoding="utf-8") as handle:
        handle.write(LINGERING_CLI)
    checks = []
    for label, mode, timeout, grace, expected, has_result in (
            ("a CLI that exits after its result is read as exited",
             "exits", 30, 30, "exited", True),
            ("one that lingers after its result is ended after the grace",
             "lingers", 60, 2, "hung", True),
            ("one that never answers is ended at the timeout",
             "silent", 3, 30, "timeout", False)):
        pid_file = os.path.join(scratch, "%s.pid" % mode)
        started = time.monotonic()
        status, stdout, _, ended = run_cli(
            [sys.executable, script, mode, pid_file], "", scratch,
            dict(os.environ), timeout, grace)
        elapsed = time.monotonic() - started
        with io.open(pid_file, encoding="utf-8") as handle:
            child = int(handle.read())
        time.sleep(1)
        checks.append((label, ended == expected and elapsed < 40
                       and (result_of(stdout) is not None) == has_result
                       and (status == 0 if expected == "exited" else True)
                       and not alive(child)))
    remove_tree(scratch)
    return checks


def credential_rotation_checks():
    """A token a trial refreshed into a file of its own reaches the account's
    file before the link is remade, and an older one never does."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-credential-rotation-self-test")
    remove_tree(scratch)
    home = os.path.join(scratch, "home")
    account = os.path.join(scratch, "account", ".credentials.json")
    os.makedirs(os.path.dirname(account))
    target = os.path.join(home, CREDENTIALS)

    def write(path, expires):
        # A new file each time, as the CLI saves a refreshed token.
        if os.path.lexists(path):
            os.remove(path)
        with io.open(path, "w", encoding="utf-8") as handle:
            json.dump({"claudeAiOauth": {"expiresAt": expires}}, handle)

    write(account, 1000)
    refresh_credentials(home, account)
    checks = [("the home links the account's file",
               os.path.samefile(account, target))]
    write(target, 2000)
    refresh_credentials(home, account)
    checks.append(("a token refreshed into a new file reaches the account's",
                   expires_at(account) == 2000
                   and os.path.samefile(account, target)))
    write(target, 500)
    refresh_credentials(home, account)
    checks.append(("an older home file leaves the account's as it was",
                   expires_at(account) == 2000
                   and os.path.samefile(account, target)))
    write(target, 3000)
    write(account, 4000)
    refresh_credentials(home, account)
    checks.append(("an account file refreshed elsewhere is kept",
                   expires_at(account) == 4000
                   and os.path.samefile(account, target)))

    # Two runs refresh at once: this home holds 5000 and the other 6000.
    # The other is started after this one has read its home's file and
    # before it writes.
    other = os.path.join(scratch, "other")
    refresh_credentials(other, account)
    write(target, 5000)
    write(os.path.join(other, CREDENTIALS), 6000)
    plain = globals()["expiry_of"]
    racer = threading.Thread(target=refresh_credentials,
                             args=(other, account))

    def paused(data):
        stamp = plain(data)
        if (stamp == 5000 and racer.ident is None
                and threading.current_thread() is threading.main_thread()):
            racer.start()
            time.sleep(0.5)
        return stamp

    globals()["expiry_of"] = paused
    try:
        refresh_credentials(home, account)
    finally:
        globals()["expiry_of"] = plain
    racer.join(30)
    checks.append(("a newer token written back at the same time wins",
                   expires_at(account) == 6000
                   and os.path.samefile(account, target)
                   and os.path.samefile(account,
                                        os.path.join(other, CREDENTIALS))))

    # A CLI's save replaces the account's file, taking no lock, after this
    # run has read its home's file and before it writes.
    write(target, 6500)
    fresh = os.path.join(scratch, "saved.json")
    with io.open(fresh, "w", encoding="utf-8") as handle:
        json.dump({"claudeAiOauth": {"expiresAt": 7000}}, handle)

    def replaced(data):
        stamp = plain(data)
        if stamp == 6500 and os.path.exists(fresh):
            os.replace(fresh, account)
        return stamp

    globals()["expiry_of"] = replaced
    try:
        refresh_credentials(home, account)
    finally:
        globals()["expiry_of"] = plain
    checks.append(("a CLI's save racing the write-back is not overwritten",
                   expires_at(account) == 7000
                   and os.path.samefile(account, target)))

    # A run that died holding the lock leaves it behind.
    left = account + ".lock"
    io.open(left, "w").close()
    os.utime(left, (time.time() - 3600, time.time() - 3600))
    checks.append(("a lock left by a dead run is broken, not waited on",
                   refresh_credentials(home, account) == "linked"
                   and not os.path.exists(left)))
    remove_tree(scratch)
    return checks


def credential_watch_checks():
    """A token a running trial refreshed reaches the account's file before
    the trial ends, an older one never does, and the watch stops with it."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-credential-watch-self-test")
    remove_tree(scratch)
    home = os.path.join(scratch, "home")
    account = os.path.join(scratch, "account", ".credentials.json")
    os.makedirs(os.path.dirname(account))
    target = os.path.join(home, CREDENTIALS)

    def write(path, expires):
        # A new file each time, as the CLI saves a refreshed token.
        if os.path.lexists(path):
            os.remove(path)
        with io.open(path, "w", encoding="utf-8") as handle:
            json.dump({"claudeAiOauth": {"expiresAt": expires}}, handle)

    def settle(until, bound_s=10):
        deadline = time.time() + bound_s
        while not until() and time.time() < deadline:
            time.sleep(0.02)
        return until()

    write(account, 1000)
    refresh_credentials(home, account)
    with credential_watch(home, account, every_s=0.05) as written:
        write(target, 2000)
        reached = settle(lambda: expires_at(account) == 2000)
        write(target, 1500)
        time.sleep(0.5)
        older_kept = expires_at(account) == 2000
        threads = threading.active_count()
    stopped = threading.active_count() == threads - 1

    # A refresh after the last look, with no look due before the trial ends.
    with credential_watch(home, account, every_s=3600):
        write(target, 3000)
    last_kept = expires_at(account) == 3000
    remove_tree(scratch)
    return [("a token refreshed mid-trial reaches the account's file "
             "while the trial runs", reached and len(written) == 1),
            ("an older token seen mid-trial leaves the account's as it was",
             older_kept),
            ("the watch stops when the trial ends", stopped),
            ("a token refreshed after the last look is written back as the "
             "trial ends", last_kept)]


def credential_link_checks():
    """The scratch home reads the account's live credentials, and gets them
    back before a trial where they went missing."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-credential-link-self-test")
    remove_tree(scratch)
    real = os.path.join(os.path.expanduser("~"), CREDENTIALS)
    if not os.path.exists(real):
        return [("no credentials on this machine, so nothing to link", True)]
    home = prepare_home(scratch)
    target = os.path.join(home, CREDENTIALS)
    checks = [("the scratch home's credentials are the live file itself",
               os.path.exists(target) and os.path.samefile(real, target))]
    os.remove(target)
    how = refresh_credentials(home)
    checks.append(("a refresh before a trial restores them, live",
                   how == "linked" and os.path.samefile(real, target)))
    remove_tree(scratch)
    checks.append(("removing the scratch home leaves the live file",
                   os.path.exists(real)))
    return checks


def vendor_checks():
    """The hybrid arm's workspace carries the templates at the release, out
    of its index, and the reach scan reads that tree as the arm's own."""
    if templates_root(required=False) is None:
        return [("a templates source is set in %s, so the vendoring can be "
                 "proved" % TEMPLATES_ENV, False)]
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-vendor-self-test")
    remove_tree(scratch)
    workspace = os.path.join(scratch, "hybrid-1")
    os.makedirs(workspace)
    git(workspace, "init", "-q")
    vendored = vendor_templates(workspace, VENDORED)
    git(workspace, "add", "-A")
    expected = git(templates_root(), "rev-parse",
                   "%s:%s" % (VENDORED["ref"], VENDORED["path"]))
    # The release's layout varies by source, so the check reads the first
    # template the vendored tree holds rather than a fixed path.
    vendored_root = os.path.join(workspace, "docs", "solid-ai-templates")
    planted = next((os.path.join(folder, name)
                    for folder, _, names in sorted(os.walk(vendored_root))
                    for name in sorted(names) if name.endswith(".md")), "")
    checks = [
        ("the templates at the release are in the workspace",
         os.path.isfile(planted) and len(expected) == 40
         and vendored["tree"] == expected),
        ("the vendored tree is out of the workspace's index",
         git(workspace, "ls-files") == ""
         and git(workspace, "status", "--porcelain") == ""),
    ]

    # The first call reads the vendored tree; the second and third fetch the
    # repository, under its owner and under the owner the host redirects
    # from. All three name it, and only the fetches reach for it.
    calls = [("Read", json.dumps({"file_path": planted})),
             ("Bash", json.dumps({"command": "git clone https://github.com/"
                                             "solid-ai-dev/solid-ai-templates"})),
             ("Bash", json.dumps({"command": "git clone https://github.com/"
                                             "braboj/solid-ai-templates"}))]
    own = reach(["planted.jsonl"], calls, workspace, None, vendored)["hits"]
    bare = reach(["planted.jsonl"], calls, workspace, None)["hits"]
    checks.append(("a read of the vendored tree is not a reach for the arm "
                   "carrying it, and a fetch of the repository is",
                   [hit["call"] for hit in own]
                   == [calls[1][1], calls[2][1]]))
    checks.append(("the same read is a reach for an arm carrying no copy",
                   [hit["call"] for hit in bare]
                   == [calls[0][1][:300], calls[1][1], calls[2][1]]))
    remove_tree(scratch)
    return checks


def denial_checks():
    """A trial's deny rules cover everything it may not reach that a path
    names, and leave its own workspace readable."""
    root = os.path.join(tempfile.gettempdir(), "efficacy-deny-self-test")
    remove_tree(root)
    workspace = os.path.join(root, "none-1")
    rules = reach_denials(root, workspace)
    spelled = rule_path(root)

    def denied(target):
        return ("Read(%s/**)" % rule_path(target) in rules
                and "Edit(%s/**)" % rule_path(target) in rules)

    settings = trial_settings(os.path.join(root, "home"), root, workspace)
    with io.open(settings, encoding="utf-8") as handle:
        written = json.load(handle)
    remove_tree(root)
    windows = rule_path("C:\\Runs\\round") == "//c/Runs/round"
    return [
        ("a Windows path is spelled as a rule spells it",
         windows if os.name == "nt" else rule_path("/runs") == "//runs"),
        ("this repository and the scoring area are denied",
         denied(repository_root()) and denied(scoring_area(root))),
        ("the templates source is denied whenever one is set",
         templates_root(required=False) is None
         or denied(templates_root(required=False))),
        ("other trials, their change tasks, home and void are denied",
         all(denied(os.path.join(root, entry))
             for entry in ("inline-1", "none-2", "change-none-1",
                           "change-hand-5", "home", "void"))),
        ("a round-5 run's last block is denied too",
         all(denied(os.path.join(root, trial_name(arm, ROUND5_K)))
             for arm in ROUND5_ARMS)),
        ("tarballs and run records are denied",
         "Read(%s/*.tar)" % spelled in rules
         and "Read(%s/run-*.json)" % spelled in rules),
        ("the trial's own workspace is not denied",
         not any(rule_path(workspace) + "/" in rule for rule in rules)),
        ("the settings file carries the rules and the isolation",
         written.get("permissions", {}).get("deny")
         == rules + kill_denials()
         and written.get("includeCoAuthoredBy") is False
         and os.path.dirname(settings) == os.path.join(root, "home")),
    ]


# The command that ended round 4's thin run, and its kin. Each MUST meet a
# deny rule; a stop by PID or by port MUST meet none.
KILLS = {
    "Bash": ['cd "C:/runs/inline-1" && powershell -NoProfile -Command '
             '"Get-Process -Name python -ErrorAction SilentlyContinue | '
             'Where-Object { $_.MainWindowTitle -eq \'\' } | '
             'Stop-Process -Force"',
             "taskkill //IM python.exe //F", "pkill -f flask",
             "killall python3"],
    "PowerShell": ["Stop-Process -Name python -Force",
                   "Get-Process python | ForEach-Object { $_.Kill() }",
                   "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\""
                   " | Invoke-CimMethod -MethodName Terminate"],
}
SPARED = {
    "Bash": ["kill 4242", "taskkill //PID 4242 //F",
             "powershell -Command \"Stop-Process -Id 4242\""],
    "PowerShell": ["Stop-Process -Id 4242 -Force",
                   "Get-NetTCPConnection -LocalPort 5055"],
}


def kill_checks():
    """A kill by name meets a deny rule and, where it ran, voids the trial;
    a denied one and a kill by PID do neither."""
    rules = kill_denials()

    def denied(tool, command):
        return any(fnmatch.fnmatchcase(command, rule[len(tool) + 1:-1])
                   for rule in rules if rule.startswith(tool + "("))

    checks = [
        ("every kill by name meets a deny rule",
         all(denied(tool, command)
             for tool, commands in KILLS.items() for command in commands)),
        ("no stop by PID or port meets one",
         not any(denied(tool, command)
                 for tool, commands in SPARED.items()
                 for command in commands)),
    ]

    scratch = os.path.join(tempfile.gettempdir(), "efficacy-kill-self-test")
    remove_tree(scratch)
    os.makedirs(scratch)
    transcript = os.path.join(scratch, "planted.jsonl")
    ran, refused, unanswered = KILLS["Bash"][0], KILLS["Bash"][2], \
        KILLS["PowerShell"][0]

    def use(call_id, tool, command):
        return {"message": {"content": [
            {"type": "tool_use", "id": call_id, "name": tool,
             "input": {"command": command}}]}}

    def answer(call_id, text, error):
        return {"message": {"content": [
            {"type": "tool_result", "tool_use_id": call_id,
             "is_error": error, "content": text}]}}

    entries = [use("t1", "Bash", ran), answer("t1", "", False),
               use("t2", "Bash", refused),
               answer("t2", "Permission to use Bash with command %s has "
                            "been denied." % refused, True),
               use("t3", "Bash", SPARED["Bash"][0]), answer("t3", "", False),
               use("t4", "PowerShell", unanswered)]
    with io.open(transcript, "w", encoding="utf-8") as handle:
        handle.writelines(json.dumps(entry) + "\n" for entry in entries)
    hits = stopped_by_name([transcript])
    remove_tree(scratch)
    checks.append(("a kill by name that ran, or never answered, is a hit",
                   sorted(hit["call"] for hit in hits)
                   == sorted([ran[:300], unanswered])))
    checks.append(("a trial that stopped processes by name is reached",
                   reached({"outcome": "completed",
                            "reach": {"hits": hits}}).get("outcome")
                   == "reached"))
    return checks


def recover_checks():
    """A trial a dead harness left in flight is voided and its slot freed; a
    live harness's trial refuses the root."""
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-recover-self-test")
    remove_tree(scratch)
    root = os.path.join(scratch, "run")
    home = os.path.join(root, "home")
    workspace = os.path.join(root, "short-1")
    os.makedirs(home)
    os.makedirs(workspace)
    with io.open(os.path.join(workspace, "partial.py"), "w",
                 encoding="utf-8") as handle:
        handle.write("# partial work\n")
    git(workspace, "init", "-q")
    git(workspace, "add", "-A")
    git(workspace, "-c", "user.name=efficacy",
        "-c", "user.email=efficacy@example.invalid", "commit", "-q", "-m",
        "planted")

    started = datetime.datetime(2026, 10, 16, 0, 0, 0)
    finished = {"arm": "none", "trial": 1, "outcome": "completed"}
    dead = dict(in_flight("short", 1), harness_pid=4242)
    run_file = os.path.join(root, "run-planted.json")
    write_run(run_file, started, [finished, dead], arms=("short", "hand"),
              k=3)

    # The plant is read before recovery, so a voided slot is recovery's doing
    # and not a workspace that was never there.
    checks = [("the in-flight trial's workspace exists",
               os.path.isfile(os.path.join(workspace, "partial.py")))]
    live = [(4242, "", "python tests/efficacy/harness.py --root run")]
    try:
        recover(root, home, live)
        checks.append(("a live harness's trial refuses the root", False))
    except TrialError:
        checks.append(("a live harness's trial refuses the root",
                       os.path.isdir(workspace)))

    voided = recover(root, home, [])
    with io.open(run_file, encoding="utf-8") as handle:
        records = json.load(handle)["trials"]
    kept = (records[1].get("void") or {}).get("workspace") or ""
    checks += [
        ("a dead harness's trial is voided and its slot freed",
         voided == [workspace] and not os.path.exists(workspace)
         and os.path.isfile(os.path.join(kept, "partial.py"))),
        ("the record names the ending and keeps the rest",
         records[0] == finished
         and records[1]["outcome"] == "interrupted"
         and records[1]["outcome"] in VOIDING
         and os.path.isfile(records[1]["frozen"]["tarball"])),
        ("a second recovery finds nothing", recover(root, home, []) == []),
        ("the record names the run's arms and its K from the start",
         json.load(io.open(run_file, encoding="utf-8")).get("arms")
         == ["short", "hand"]
         and json.load(io.open(run_file, encoding="utf-8")).get("k") == 3),
    ]
    remove_tree(scratch)
    return checks


def round5_checks():
    """Round 5's arms are registered as they are made, a vendoring arm
    takes its recorded ref, and the skills land where Claude Code loads
    them, out of the workspace's index."""
    checks = [
        ("round 5's arms: reference vendors, inline does not, skills has "
         "skills",
         all(arm in ARMS for arm in ("none", "reference", "inline", "hybrid",
                                      "skills"))
         and ARMS["reference"].get("vendor") is not None
         and ARMS["inline"].get("vendor") is None
         and ARMS["skills"].get("skills") is not None),
        ("an arm that vendors nothing has no vendored ref",
         arm_vendor("none") is None and arm_vendor("inline") is None),
        ("round 5e's arms: lazyref vendors, lazyskills has skills, and both "
         "build from round 5's spec",
         ARMS["lazyref"].get("vendor") is not None
         and ARMS["lazyref"].get("skills") is None
         and ARMS["lazyskills"].get("skills") is not None
         and ARMS["lazyskills"].get("vendor") is None
         and spec_problem(["lazyref"], "thin", ROUND5_SPEC[1]) is not None
         and spec_problem(["lazyskills"], *ROUND5_SPEC) is None),
    ]
    record = os.path.join(ARMS_DIR, "lazyref", "generation.json")
    with io.open(record, encoding="utf-8") as handle:
        recorded = json.load(handle).get("ref")
    checks.append(("a vendoring arm vendors at its recorded ref",
                   recorded is not None
                   and arm_vendor("lazyref")["ref"] == recorded))

    scratch = os.path.join(tempfile.gettempdir(), "efficacy-skills-self-test")
    remove_tree(scratch)
    source = os.path.join(scratch, "source", "review")
    os.makedirs(source)
    with io.open(os.path.join(source, "SKILL.md"), "w",
                 encoding="utf-8") as handle:
        handle.write("---\nname: review\n---\n")
    workspace = os.path.join(scratch, "skills-1")
    os.makedirs(workspace)
    git(workspace, "init", "-q")
    kinds = place_skills(workspace, os.path.dirname(source))
    placed = os.path.join(workspace, *SKILLS_INTO.split("/"), "review",
                          "SKILL.md")
    argv = agent_command(scratch, "model", "high", None)
    checks.append(("a trial reads the workspace's project settings and no "
                   "other source",
                   argv[argv.index("--setting-sources") + 1] == "project"))

    # The web tools go after the flag that names them; anything else there
    # would be read as one more tool to refuse, or as the prompt.
    refused = (argv[argv.index("--disallowed-tools") + 1:][:2]
               if "--disallowed-tools" in argv else [])
    checks.append(("a trial may not fetch or search the web",
                   sorted(refused) == ["WebFetch", "WebSearch"]))
    listed ="review\n- write-tests\n`add-check`\ndataviz"
    checks.append(("the skills probe finds a listed kind and names a missing "
                   "one",
                   missing_skills(listed, ["add-check", "review",
                                           "write-tests"]) == []
                   and missing_skills(listed, ["review", "regenerate"])
                   == ["regenerate"]))
    checks.append(("the skills land where Claude Code loads them, out of "
                   "the index",
                   kinds == ["review"] and os.path.isfile(placed)
                   and git(workspace, "status", "--porcelain") == ""))
    remove_tree(scratch)
    return checks


def spec_checks():
    """A round-5 run builds from the registered spec, and from nothing else."""
    import argparse as _argparse

    round5 = ["none", "inline", "hybrid", "reference", "skills"]
    name, registered = ROUND5_SPEC
    checks = [
        ("round 6's registered digest is SPEC.md's content, and round 5's "
         "is another",
         spec_digest(SPECS[name]) == ROUND6_SPEC[1]
         and registered != ROUND6_SPEC[1] and len(registered) == 64),
        ("a round-5 run on the registered spec passes",
         spec_problem(round5, name, registered) is None),
        ("a round-5 run on other content is refused",
         spec_problem(round5, name, "0" * 64) is not None),
        ("a round-5 run on the thin spec is refused",
         spec_problem(round5, "thin", spec_digest(SPECS["thin"])) is not None),
        ("a run without a round-5 arm is not checked",
         spec_problem(["none", "hybrid"], "thin", "0" * 64) is None),
        ("a round-5d run on other content is refused",
         spec_problem(["hand", "short"], name, "0" * 64) is not None),
    ]

    # The spec edited after the run started: the next trial is refused before
    # its workspace is laid out, so nothing is built from the new content.
    # The planted run registers the file as it stands, since round 5's
    # registered content is no longer the file's: each refusal below must then
    # come from the edit, named as such, not from the registration.
    scratch = tempfile.mkdtemp(prefix="efficacy-spec-")
    original = SPECS[name]
    registration = ROUND5_SPEC
    try:
        globals()["ROUND5_SPEC"] = (name, spec_digest(original))
        edited = os.path.join(scratch, "SPEC.md")
        with io.open(original, "rb") as source, io.open(edited, "wb") as out:
            out.write(source.read() + b"\nOne more line.\n")
        SPECS[name] = edited
        # The options name no model, so a trial that got past the check stops
        # on that before any CLI is called.
        options = _argparse.Namespace(spec=name, arm_list=round5)
        root = os.path.join(scratch, "root")
        os.makedirs(root)
        try:
            run_trial("none", 2, root, scratch, options)
            refused = False
        except TrialError as error:
            refused = "not the content" in str(error)
        except Exception:
            refused = False
        checks.append(("a spec edited mid-run refuses the next trial unbuilt",
                       refused and os.listdir(root) == []))

        # The source edited between its check and its copy: the planted copy
        # step writes the edit into the workspace after the source passed.
        SPECS[name] = original
        prepare = globals()["prepare_workspace"]

        def edited_in_flight(*args, **kwargs):
            workspace, vendored = prepare(*args, **kwargs)
            with io.open(os.path.join(workspace, "SPEC.md"), "ab") as copy:
                copy.write(b"\nOne more line.\n")
            return workspace, vendored

        globals()["prepare_workspace"] = edited_in_flight
        try:
            run_trial("none", 3, root, scratch, options)
            refused = False
        except TrialError as error:
            refused = "not the content" in str(error)
        except Exception:
            refused = False
        finally:
            globals()["prepare_workspace"] = prepare
        checks.append(("a spec changed as it is copied refuses the trial and "
                       "frees its slot", refused and os.listdir(root) == []))
    finally:
        SPECS[name] = original
        globals()["ROUND5_SPEC"] = registration
        shutil.rmtree(scratch, ignore_errors=True)
    return checks


def registration_checks():
    """A run naming a round is held to its entry: its arms, K, spec and
    prompts; its root holds that round alone, every record naming it."""
    entry = REGISTRATIONS["C1"]
    change = read_change_prompt()
    checks = [
        ("C1 pins SPEC.md, both prompts and its fixtures by content",
         entry["spec"]["sha256"] == spec_digest(SPEC) == ROUND6_SPEC[1]
         and entry["tasks"]["build"]["prompt_sha256"] == text_digest(PROMPT)
         and entry["tasks"]["change"]["prompt_sha256"] == text_digest(change)
         and os.path.isfile(manifest_path(entry))),
        ("an unknown round is refused",
         round_problem("C9", ["none"], 3, "build") is not None
         and round_problem("C1", ["none"], 3, "build") is None),
        ("an arm the round does not register is refused",
         round_problem("C1", ["none", "hand"], 3, "build") is not None
         and round_problem("C1", ["none", "lazyskills"], 3, "change")
         is None),
        ("a K past the round's registered K is refused",
         round_problem("C1", ["none"], 16, "change") is not None
         and round_problem("C1", ["none"], 15, "change") is None),

        # C1 runs pilot arms' names on round 6's spec, which the pilot's
        # check, going by those names, would refuse.
        ("a C1 run reads its spec from its entry, not its arms' names",
         spec_problem(["inline", "lazyref"], "normal", ROUND6_SPEC[1], "C1")
         is None
         and spec_problem(["inline"], "normal", ROUND5_SPEC[1], "C1")
         is not None
         and spec_problem(["inline"], "thin", ROUND6_SPEC[1], "C1")
         is not None),
        ("a build or change prompt the round does not pin is refused",
         prompt_problem("C1", "build", PROMPT) is None
         and prompt_problem("C1", "build", PROMPT + " ") is not None
         and prompt_problem("C1", "change", change) is None
         and prompt_problem("C1", "change", change + " ") is not None),
    ]

    scratch = tempfile.mkdtemp(prefix="efficacy-registration-")
    digest = registration_digest(entry)
    stamp = datetime.datetime.now().astimezone()

    def planted(name, header, trials):
        root = os.path.join(scratch, name)
        os.makedirs(root, exist_ok=True)
        with io.open(os.path.join(root, "run-%d.json" % len(os.listdir(root))),
                     "w", encoding="utf-8") as handle:
            json.dump(dict(header, trials=trials), handle)
        return root

    whole = {"round": "C1", "task": "build", "arm": "none", "block": 1,
             "trial": 1, "outcome": "completed"}
    legacy = planted("legacy", {}, [{"arm": "none", "trial": 1}])
    other = planted("other", {"round": "C2", "registration": digest},
                    [dict(whole, round="C2")])
    stale = planted("stale", {"round": "C1", "registration": "0" * 64},
                    [whole])
    bare = planted("bare", {"round": "C1", "registration": digest},
                   [dict(whole, block=None)])
    good = planted("good", {"round": "C1", "registration": digest}, [whole])
    unheaded = planted("unheaded", {}, [whole])
    checks += [
        ("a root holding another round's or registration's runs is refused",
         identity_problem(other, "C1", digest) is not None
         and identity_problem(stale, "C1", digest) is not None
         and identity_problem(good, "C1", digest) is None),
        ("a named round and records naming none never share a root",
         identity_problem(legacy, "C1", digest) is not None
         and "--round C1" in (identity_problem(good) or "")
         and identity_problem(legacy) is None),
        ("a named round's trial record missing its identity is refused",
         identity_problem(bare, "C1", digest) is not None
         and recorded_round(bare)[1] is not None
         and recorded_round(good) == ("C1", None)
         and recorded_round(legacy) == (None, None)),
        ("a run whose trials name a round under a header naming none is "
         "refused",
         identity_problem(unheaded) is not None
         and identity_problem(unheaded, "C1", digest) is not None
         and recorded_round(unheaded)[1] is not None),
    ]
    written = os.path.join(scratch, "written", "run-1.json")
    os.makedirs(os.path.dirname(written))
    write_run(written, stamp, [{"arm": "none", "trial": 2,
                                "outcome": "refused"}],
              "change", change, ["none"], 2,
              {"round": "C1", "registration": digest})
    with io.open(written, encoding="utf-8") as handle:
        run = json.load(handle)
    checks.append(("every trial record of a named round names its round, "
                   "task, arm and block",
                   run["round"] == "C1" and run["registration"] == digest
                   and {key: run["trials"][0].get(key) for key in IDENTITY}
                   == {"round": "C1", "task": "change", "arm": "none",
                       "block": 2}
                   and identity_problem(os.path.dirname(written), "C1",
                                        digest) is None))

    # A harness that died mid-trial leaves its run record for the next run
    # to rewrite, which keeps the round it names.
    recovered = os.path.join(scratch, "recovered")
    os.makedirs(recovered)
    summary = {"manifest_sha256": "1" * 64, "blocks": {"1": "none-2"}}
    write_run(os.path.join(recovered, "run-1.json"), stamp,
              [dict(in_flight("none", 1), harness_pid=4242)], "change",
              change, ["none"], 1,
              {"round": "C1", "registration": digest, "fixtures": summary})
    recover(recovered, os.path.join(scratch, "home"), [])
    with io.open(os.path.join(recovered, "run-1.json"),
                 encoding="utf-8") as handle:
        run = json.load(handle)
    checks.append(("recovery keeps a named round's identity in its run "
                   "record",
                   run["trials"][0]["outcome"] == "interrupted"
                   and run.get("fixtures") == summary
                   and identity_problem(recovered, "C1", digest) is None))

    # A round of two tasks, two arms and two blocks: the change tasks come
    # after the builds, and one build lost leaves its change task counted.
    small = {"arms": ["none", "inline"],
             "tasks": {"build": {"k": 2}, "change": {"k": 2}}}
    builds = [{"arm": arm, "trial": block, "task": "build",
               "outcome": "completed"} for arm in small["arms"]
              for block in (1, 2)]
    changes = [dict(record, task="change") for record in builds]
    failed = [dict(record, outcome="blocked")
              if (record["arm"], record["trial"]) == ("inline", 2) else record
              for record in builds]
    checks += [
        ("a round of two tasks is complete only with both at K for every arm",
         owed_by_task(small, builds) == {"build": [], "change": [1, 2]}
         and owed_by_task(small, builds + changes[:3])
         == {"build": [], "change": [2]}
         and owed_by_task(small, builds + changes)
         == {"build": [], "change": []}),
        ("a change task counts though its arm's build trial failed",
         owed_by_task(small, failed + changes)
         == {"build": [2], "change": []}),
    ]
    try:
        checks += fixture_checks(scratch)
    finally:
        REGISTRATIONS.pop("T1", None)
        PINNED_CLI["path"] = None
        remove_tree(scratch)
    return checks


def fixture_checks(scratch):
    """A named round's change task starts every arm of a block from one
    fixture whose hash matches, cleaned of what its builder was given."""
    entry = json.loads(json.dumps(REGISTRATIONS["C1"]))
    manifest = os.path.join(scratch, "change-fixtures.json")
    entry["tasks"]["change"]["fixtures"]["manifest"] = manifest
    REGISTRATIONS["T1"] = entry

    # One build, as a `none` trial leaves it: its code and tests, and beside
    # them all a change task must not inherit.
    build = os.path.join(scratch, "build")
    planted = {
        "tariff/app.py": "built = True\n",
        "tests/test_app.py": "def test_built():\n    assert True\n",
        "pyproject.toml": "[project]\nname = 'tariff'\n",
        ".gitignore": "*.db\n",
        "CLAUDE.md": "inherited\n", "AGENTS.md": "inherited\n",
        "tariff/CLAUDE.md": "inherited\n",
        ".claude/settings.json": "{}\n",
        ".claude/skills/inherited/SKILL.md": "---\nname: inherited\n---\n",
        "docs/solid-ai-templates/templates/base.md": "vendored\n",
        ".venv312/pyvenv.cfg": "home = x\n",
        ".venv312/Lib/site-packages/thing.py": "x = 1\n",
        "tariff/__pycache__/app.cpython-312.pyc": "",
        ".pytest_cache/README.md": "cache\n",
        "tariff.egg-info/PKG-INFO": "Name: tariff\n",
        "data.sqlite": "", "tariff/app.db": "", "session.jsonl": "{}\n",
        "SPEC.md": "the build's own spec\n",
    }
    for relative, text in planted.items():
        path = os.path.join(build, *relative.split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
    git(build, "init", "-q")
    commit_start(build, "build")
    tarballs = os.path.join(scratch, "fixtures")
    os.makedirs(tarballs)
    hashes = {}
    for name in ("none-7", "none-2", "none-11"):
        hashes[name] = spec_digest(freeze(build, tarballs, name)["tarball"])

    def listing_as(fixtures):
        with io.open(manifest, "w", encoding="utf-8") as handle:
            json.dump({"fixtures": fixtures}, handle)

    def refused(*args):
        try:
            read_fixtures(*args)
            return False
        except TrialError:
            return True

    listed = [{"trial": name, "sha256": hashes[name],
               "baseline": {"build_suite": 1.0}} for name in hashes]
    listing_as([])
    checks = [("an empty fixture manifest refuses a named round's change "
               "task", refused(entry, tarballs))]
    listing_as([dict(listed[0], sha256="0" * 64)] + listed[1:])
    mismatched = refused(entry, tarballs)
    listing_as([dict(listed[0], baseline={})] + listed[1:])
    checks.append(("a fixture listed without its baseline readings is "
                   "refused", refused(entry, tarballs)))
    listing_as(listed)
    fixtures = read_fixtures(entry, tarballs)
    order = [fixture_for(fixtures, block)["trial"] for block in range(1, 5)]
    checks.append(("block b starts from the b-th qualifying build, ascending, "
                   "cycling", order == ["none-2", "none-7", "none-11",
                                        "none-2"]))
    import argparse as _argparse
    two = run_fixtures(_argparse.Namespace(round="T1", fixtures=tarballs, k=2))
    five = run_fixtures(_argparse.Namespace(round="T1", fixtures=tarballs,
                                            k=5))
    checks.append(("a named round's change run records how many distinct "
                   "fixtures its blocks take",
                   two[1]["distinct"] == 2 and two[1]["qualified"] == 3
                   and five[1]["distinct"] == 3
                   and five[1]["blocks"]["4"] == "none-2"))

    root = os.path.join(scratch, "root")
    os.makedirs(root)
    first = fixtures[0]
    prepared = {arm: prepare_fixture_workspace(arm, 1, root, first, SPEC)
                for arm in ("none", "inline", "skills")}
    files = {arm: git(workspace, "ls-files").splitlines()
             for arm, (workspace, _, _) in prepared.items()}
    inline = prepared["inline"][0]
    skills = os.path.join(prepared["skills"][0], *SKILLS_INTO.split("/"))

    def read(path):
        try:
            with io.open(path, "rb") as handle:
                return handle.read()
        except OSError:
            return None

    kept = ("tariff/app.py", "tests/test_app.py", "pyproject.toml",
            ".gitignore")
    dropped = [relative for relative in planted
               if relative not in kept + ("CLAUDE.md", "SPEC.md")]
    checks.append(("a change workspace keeps its fixture's code and tests",
                   all(os.path.isfile(os.path.join(inline, *path.split("/")))
                       for path in kept)))
    checks.append(("a change workspace drops the fixture's instructions, "
                   "settings, databases, caches, environments and history",
                   not any(os.path.exists(os.path.join(workspace,
                                                       *path.split("/")))
                           for workspace, _, _ in prepared.values()
                           for path in dropped + [".venv312", "__pycache__"])
                   and not os.path.exists(os.path.join(
                       prepared["none"][0], "CLAUDE.md"))
                   and all(git(workspace, "rev-list", "--count", "HEAD")
                           == "1" for workspace, _, _ in prepared.values())))
    checks.append(("a change workspace carries the round's spec and only its "
                   "arm's context",
                   read(os.path.join(inline, "SPEC.md")) == read(SPEC)
                   and read(os.path.join(inline, "CLAUDE.md"))
                   == read(os.path.join(ARMS_DIR, ARMS["inline"]["context"]))
                   and sorted(os.listdir(skills)) == sorted(os.listdir(
                       os.path.join(ARMS_DIR, ARMS["skills"]["skills"])))))
    checks.append(("a change workspace starts from one commit, with nothing "
                   "uncommitted",
                   all(git(workspace, "status", "--porcelain") == ""
                       and git(workspace, "rev-parse", "HEAD") == base
                       for workspace, base, _ in prepared.values())))
    checks.append(("every arm's change workspace of a block holds the same "
                   "code",
                   files["none"] == [path for path in files["inline"]
                                     if path != "CLAUDE.md"]
                   == [path for path in files["skills"]
                       if path != "CLAUDE.md"]))

    # Replaced after the run checked it, the tarball refuses its trial.
    replaced = os.path.join(scratch, "replaced.tar")
    shutil.copyfile(first["tarball"], replaced)
    with io.open(replaced, "ab") as handle:
        handle.write(b"\0" * 1024)
    try:
        prepare_fixture_workspace("none", 2, root,
                                  dict(first, tarball=replaced), SPEC)
        swapped = False
    except TrialError:
        swapped = not os.path.exists(os.path.join(root, "change-none-2"))
    checks.append(("a fixture whose tarball differs from its listed hash is "
                   "refused, at the start and at each trial",
                   mismatched and swapped))
    return checks + fixture_run_checks(scratch, tarballs)


def fixture_run_checks(scratch, tarballs):
    """A named round's change run needs no build trial, and its root takes
    no run naming another round or none; the CLI is a stand-in."""
    stand_in = os.path.join(scratch, "bin",
                            "claude.cmd" if os.name == "nt" else "claude")
    os.makedirs(os.path.dirname(stand_in))
    with io.open(stand_in, "w", encoding="utf-8") as handle:
        handle.write("@echo off\r\necho 0.0.1 (stand-in)\r\n"
                     if os.name == "nt"
                     else '#!/bin/sh\necho "0.0.1 (stand-in)"\n')
    os.chmod(stand_in, 0o755)
    root = os.path.join(scratch, "change-root")
    argv = ["--root", root, "--round", "T1", "--task", "change", "--arms",
            "none,inline", "--k", "1", "--fixtures", tarballs, "--cli",
            stand_in, "--dry-run"]
    saved = {key: os.environ.get(key) for key in ("HOME", "USERPROFILE")}
    os.environ["HOME"] = os.environ["USERPROFILE"] = os.path.join(scratch,
                                                                  "me")
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = main(argv)
        dry = dry_run_area(root)
        runs = run_files(dry)
        run = {}
        if runs:
            with io.open(runs[0], encoding="utf-8") as handle:
                run = json.load(handle)
        trials = run.get("trials", [])
        prepared = os.path.isdir(os.path.join(dry, "change-inline-1"))

        # The same round's earlier change run, planted beside this one with
        # its manifest edited, and with its block 1 started from another
        # build: each refuses the run.
        drifted = []
        for name, change in (
                ("manifest", {"manifest_sha256": "0" * 64}),
                ("block", {"blocks": {"1": "none-7"}})):
            earlier = os.path.join(scratch, "drift-" + name)
            os.makedirs(earlier)
            with io.open(os.path.join(earlier, "run-1.json"), "w",
                         encoding="utf-8") as handle:
                json.dump(dict(run, fixtures=dict(run.get("fixtures") or {},
                                                  **change)), handle)
            printed = io.StringIO()
            with contextlib.redirect_stdout(printed):
                drifted.append((main(["--root", earlier] + argv[2:]),
                                printed.getvalue()))
        os.makedirs(root, exist_ok=True)
        planted = os.path.join(root, "run-planted.json")
        write_run(planted, datetime.datetime.now().astimezone(), [])
        printed = io.StringIO()
        with contextlib.redirect_stdout(printed):
            mixed = main(argv)
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    return [
        ("a named round's change task needs no build trial of its arm",
         code == 0 and prepared
         and [trial.get("outcome") for trial in trials]
         == ["dry-run", "dry-run"]),
        ("a named round's run record names its round, registration and "
         "fixtures",
         run.get("round") == "T1"
         and run.get("registration")
         == registration_digest(REGISTRATIONS["T1"])
         and (run.get("fixtures") or {}).get("distinct") == 1
         and all(trial.get("fixture", {}).get("trial") == "none-2"
                 and trial.get("block") == 1 for trial in trials)),
        ("a named round's run refuses a root whose records name none",
         mixed == 2 and "names no round" in printed.getvalue()),
        ("a change run whose manifest or block mapping differs from the "
         "root's earlier change runs is refused",
         [code for code, _ in drifted] == [2, 2]
         and "the manifest now reads" in drifted[0][1]
         and "started block 1 from none-7" in drifted[1][1]
         and fixtures_problem(dry, dict(run.get("fixtures") or {},
                                        blocks={"1": "none-2",
                                                "2": "none-7"})) is None),
    ]


def self_test():
    """Prove the naming, isolation, outcome, resume, change and vendoring
    rules before a trial."""
    checks = (naming_checks() + environment_checks() + credential_checks()
              + credential_link_checks() + credential_rotation_checks()
              + credential_watch_checks()
              + outcome_checks() + hang_checks()
              + resume_checks() + token_checks() + change_checks()
              + dry_run_checks()
              + process_checks()
              + claim_checks() + leftover_checks() + reach_checks() + outside_checks()
              + vendor_checks() + denial_checks() + kill_checks()
              + recover_checks() + round5_checks() + spec_checks()
              + registration_checks() + pen_checks())
    for label, ok in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED"))
    passed = sum(1 for _, ok in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Run efficacy-benchmark trials.")
    parser.add_argument("--root",
                        help="where workspaces are created; MUST be outside "
                             "this repository. Required for everything but "
                             "--self-test")
    parser.add_argument("--self-test", action="store_true",
                        help="prove the environment, outcome and resume "
                             "rules; run no trial")
    parser.add_argument("--templates",
                        help="a git clone of the templates repository, "
                             "upstream or a fork; overrides %s"
                             % TEMPLATES_ENV)
    parser.add_argument("--task", choices=("build", "change"),
                        default="build",
                        help="run the build trials, or the change task: on "
                             "each scorable build trial, or for a named "
                             "round on its block's fixture")
    parser.add_argument("--round",
                        help="the registered round the run belongs to, as "
                             "C1, from %s; the run is held to its entry"
                             % ", ".join(sorted(REGISTRATIONS)))
    parser.add_argument("--fixtures",
                        help="the directory holding the fixtures' tarballs, "
                             "for a named round's change task")
    parser.add_argument("--arms",
                        help="which arms to run, as words separated by "
                             "commas, from %s; their order is block 1's. "
                             "Required for a run, so a run names the arms "
                             "it holds, unless it names a round, whose arms "
                             "it then runs" % ",".join(ARMS))
    parser.add_argument("--k", type=int, default=K_DEFAULT,
                        help="trials per arm (default %d; at most %d, the K a "
                             "round registers)" % (K_DEFAULT, ROUND5_K))
    parser.add_argument("--cli",
                        help="the Claude CLI file every trial runs, in place "
                             "of `claude` on PATH; its version is recorded "
                             "on every trial")
    parser.add_argument("--model", default="claude-sonnet-5",
                        help="exact generator model id, recorded in the report")
    parser.add_argument("--effort", default="high")
    parser.add_argument("--spec", choices=sorted(SPECS), default="normal",
                        help="the specification the build trials get as "
                             "SPEC.md (default normal)")
    parser.add_argument("--budget", type=float, default=BUDGET_USD,
                        help="dollar ceiling per trial, read against the "
                             "CLI's own cost figure (default %s)"
                        % BUDGET_USD)
    parser.add_argument("--timeout", type=int, default=TIMEOUT_S,
                        help="wall-clock ceiling per trial, in seconds "
                             "(default %s)" % TIMEOUT_S)
    parser.add_argument("--from", dest="start",
                        help="start at this trial in the interleaved order, "
                             "as short-2")
    parser.add_argument("--stop-on-block", dest="resume_after_block",
                        action="store_false",
                        help="stop the run at a blocked trial, instead of "
                             "probing until the generator answers and "
                             "re-running it in its place")
    parser.add_argument("--resume-after-block", dest="resume_after_block",
                        action="store_true", help=argparse.SUPPRESS)
    parser.set_defaults(resume_after_block=True)
    parser.add_argument("--probe-every", type=float, default=30,
                        help="minutes between probes while blocked")
    parser.add_argument("--give-up-after", type=float, default=12,
                        help="hours of probing before the run stops")
    parser.add_argument("--dry-run", action="store_true",
                        help="prepare the workspaces and print the command; "
                             "call no model")
    return parser.parse_args(argv)


def main(argv):
    options = parse_args(argv)
    if options.templates:
        os.environ[TEMPLATES_ENV] = options.templates
    if options.self_test:
        return self_test()
    if not options.root:
        print("--root is required unless --self-test is given")
        return 2

    # A refused root is a finding about the run, so it is reported and
    # exits, rather than reaching the caller as a traceback. A run with no
    # templates source cannot deny the agent the templates, so it refuses.
    try:
        templates_root()
        assert_outside_repository(options.root)
        PINNED_CLI["path"] = (os.path.abspath(options.cli) if options.cli
                              else None)
        options.cli_version = cli_version(agent_executable())
    except (TrialError, OSError, subprocess.TimeoutExpired) as error:
        print("refused: %s" % error)
        lib.print_verdict(False, "0 trial(s), 0 done, 1 refused")
        return 1
    print("CLI: %s, %s" % (agent_executable(), options.cli_version))

    # A dry run prepares its workspaces, home and record beside the root
    # rather than in it. A workspace is never reused, so one a dry run left
    # in the root would refuse the same trial when the run proper follows.
    work = options.root
    if options.dry_run:
        work = dry_run_area(options.root)
        remove_tree(work)
    os.makedirs(work, exist_ok=True)
    home = prepare_home(work)

    arms = [arm.strip() for arm in (options.arms or "").split(",")
            if arm.strip()]
    if not arms and options.round in REGISTRATIONS:
        arms = list(REGISTRATIONS[options.round]["arms"])
    unknown = [arm for arm in arms if arm not in ARMS]
    if not arms or unknown:
        print("--arms names %s; the arms are %s"
              % (", ".join(unknown) if unknown else "nothing",
                 ", ".join(ARMS)))
        return 2
    try:
        pending = pending_trials(arms, options.k, options.start)
        identity = registered_run(options, arms)
    except TrialError as error:
        print("refused: %s" % error)
        return 2
    options.arm_list = arms
    if options.task == "build" and identity is None:
        problem = spec_problem(arms, options.spec,
                               spec_digest(SPECS[options.spec]))
        if problem:
            print("refused: %s" % problem)
            return 2

    # A trial an earlier harness died under holds its slot until voided, so
    # the run that re-runs it `--from` that trial finds the slot free.
    if not options.dry_run:
        try:
            for workspace in recover(work, home):
                print("voided %s: the harness ended while it ran" % workspace)
        except (TrialError, OSError, ValueError) as error:
            print("refused: %s" % error)
            lib.print_verdict(False, "0 trial(s), 0 done, 1 refused")
            return 1

    # The change task needs its prompt and its build trials before anything
    # runs, so a design or a run root that cannot supply them refuses here.
    # A named round's change task needs its fixtures instead, every one
    # matching its hash, and none of its arm's build trials.
    builds, fixtures, prompt = {}, [], PROMPT
    if options.task == "change":
        try:
            prompt = read_change_prompt()
            if identity is None:
                builds = scorable_trials(options.root, task="build")
            else:
                fixtures, identity["fixtures"] = run_fixtures(options)
                problem = fixtures_problem(options.root, identity["fixtures"])
                if problem:
                    raise TrialError(problem)
        except TrialError as error:
            print("refused: %s" % error)
            return 2

    # One call before the first trial, because the CLI answers an
    # unauthenticated run with a result object rather than a crash: without
    # this, a whole run completes having never reached a model. A dry run
    # calls nothing by definition and is exempt.
    if not options.dry_run:
        try:
            ready = assert_authenticated(home, agent_environment,
                                         agent_executable())
        except (TrialError, subprocess.TimeoutExpired) as error:
            print("refused: %s" % error)
            lib.print_verdict(False, "0 trial(s), 0 done, 1 refused")
            return 1
        print("generator ready: %s" % ready)

        # Files in `.claude/skills/` are not skills an agent sees until the
        # CLI discovers them, so a run with an arm carrying skills proves it
        # first, for each such arm.
        for arm in arms:
            if not ARMS[arm].get("skills"):
                continue
            try:
                seen = assert_skills_discovered(
                    home, agent_environment, agent_executable(),
                    os.path.join(ARMS_DIR, ARMS[arm]["skills"]))
            except (TrialError, subprocess.TimeoutExpired) as error:
                print("refused: %s" % error)
                lib.print_verdict(False, "0 trial(s), 0 done, 1 refused")
                return 1
            print("the agent sees the %s arm's %d skills" % (arm, len(seen)))

    started_at = now()
    run_file = os.path.join(
        work, "run-%s.json" % started_at.strftime("%Y-%m-%dT%H-%M-%S"))
    records = []

    def runner(arm, trial):
        refresh_credentials(home)

        # A dry run calls no model, so it asks for no token either.
        if not options.dry_run:
            for line in fresh_token(home, options.timeout, probe):
                print("  %s" % line, flush=True)
        if options.task == "build":
            with credential_watch(home):
                return run_trial(arm, trial, work, home, options)
        if identity is not None:
            with credential_watch(home):
                return run_fixture_change_trial(arm, trial, work, home,
                                                options,
                                                fixture_for(fixtures, trial))
        name = trial_name(arm, trial)
        if name not in builds:
            raise TrialError("build trial %s has no scorable outcome, so it "
                             "has no change task" % name)
        with credential_watch(home):
            return run_change_trial(arm, trial, work, home, options,
                                    builds[name])

    def write():
        write_run(run_file, started_at, records, options.task, prompt,
                  arms, options.k, identity)

    def probe():
        refresh_credentials(home)
        return assert_authenticated(home, agent_environment,
                                    agent_executable())

    def wait():
        if not options.resume_after_block:
            print("  --stop-on-block was given")
            return False
        return wait_for_generator(probe, options.probe_every * 60,
                                  options.give_up_after * 3600)

    finished = all(run_in_place(arm, trial, runner, wait, records, write)
                   for arm, trial in pending)
    write()
    print("\nRun record: %s" % run_file)

    # A round of two tasks is complete only with both at K for every arm.
    if identity is not None:
        owed = owed_by_task(REGISTRATIONS[options.round],
                            round_records(work))
        print("round %s: %s" % (options.round, "; ".join(
            "%s owes %s" % (task, "nothing" if not blocks else
                            "blocks %s" % ", ".join(map(str, blocks)))
            for task, blocks in owed.items())))

    refused = sum(1 for r in records if r["outcome"] == "refused")
    blocked = sum(1 for r in records if r["outcome"] == "blocked")
    lost = sum(1 for r in records if r["outcome"] == "reached")
    done = sum(1 for r in records if r["outcome"]
               in ("completed", "budget", "timeout", "dry-run"))
    lib.print_verdict(refused == 0 and finished,
                      "%d trial(s), %d done, %d blocked, %d reached, "
                      "%d refused%s"
                      % (len(records), done, blocked, lost, refused,
                         "" if finished else ", run stopped"))
    return 0 if refused == 0 and finished else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
