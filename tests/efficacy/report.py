"""Aggregate scored trials into the dated round report.

Per metric: the mean per arm, the three paired contrasts, a bias-corrected and
accelerated bootstrap interval over the paired differences, and the verdict
read against that metric's declared direction. Nothing here decides by eye,
and nothing here decides a direction either: both the direction and the
verdict rule were fixed before any trial ran.

Two properties of a small K are carried into the output rather than hidden
in it. Below six blocks every interval is labelled descriptive, because no
arrangement of so few paired differences reaches conventional significance.
And a metric whose bootstrap distribution is degenerate — every difference
identical — reports the fallback it used instead of an interval it cannot
compute.
"""

import argparse
import datetime
import fnmatch
import glob
import io
import json
import math
import os
import random
import re
import shutil
import itertools
import statistics
import sys
import tempfile
import textwrap
import xml.etree.ElementTree as ElementTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import archive  # noqa: E402
import lib  # noqa: E402
from generate_arm import GENERATED, record_path  # noqa: E402
from harness import (ARMS, ARMS_DIR, PROMPT, ROUND5_ARMS,  # noqa: E402
                     ROUND5_K, ROUND5_SPEC, ROUND5D_ARMS, ROUND5E_ARMS,
                     SCORABLE, TEMPLATES_ENV, VENDORED, VOIDING, TrialError,
                     canonical, git, reach, read_transcripts, scoring_area,
                     split_name, templates_root, transcript_files,
                     trial_name)
from harness import name_of as trial_of  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
REPOSITORY = os.path.dirname(os.path.dirname(HERE))

# The registration a run of round 5's arms is read against, relative to this
# repository. Its hypotheses bind only if they landed on the main branch before
# its first trial ran and stayed unchanged after, so a registration that landed
# later read the results first. Round 5 was stopped after its first start and
# ran again as round 5b, which changed only the prompt; round 5b was stopped in
# turn and runs again as round 5c, which changes only where a workspace sits.
ROUND5_REGISTRATION = "docs/rounds/round-5c.md"
ROUND5D_REGISTRATION = "docs/rounds/round-5d.md"
ROUND5E_REGISTRATION = "docs/rounds/round-5e.md"

# A registration counts once it is on this branch, not on a branch of its own.
REGISTRATION_BRANCH = "main"

# A round's report is its record, kept beside the templates it measured:
# under the templates source's docs/audits/. A report written to any such
# directory needs the round archived as it stands; anywhere else it is a
# draft.
AUDITS = ("docs", "audits")

# The fewest paired differences at which all of them pointing one way is
# unlikely by luck at 5 %: 2 of 64 sign patterns. Below it, no interval is
# more than a description.
FEWEST_DECIDING = 6

# Metrics withdrawn after grading, each for the grader revision found to
# measure something other than the metric. Keyed by revision rather than by
# run, so every run that grader scored loses the metric and a corrected grader
# does not.
WITHDRAWN = os.path.join(HERE, "withdrawn.json")

RESAMPLES = 10000
CONFIDENCE = 0.95

# Every contrast declared before the run, each a treatment arm against a
# baseline. A run prints the contrasts whose arms it holds; the rest are
# computed as not computed and left out of every table. Each file arm reads
# against none, and short - hand holds length fixed.
CONTRASTS = (("short", "none"), ("hybrid", "none"), ("hand", "none"),
             ("short", "hand"),

             # Round 5: each arm against none, the two
             # hypotheses' contrasts against hybrid, and skills against
             # inline, the same rules with and without the split.
             ("reference", "none"), ("inline", "none"), ("skills", "none"),
             ("skills", "hybrid"), ("reference", "hybrid"),
             ("skills", "inline"),

             # Round 5d: each templates arm against a person's file, and the
             # 40-line file against the same generation without its budget.
             ("inline", "hand"), ("hybrid", "hand"), ("reference", "hand"),
             ("skills", "hand"), ("short", "inline"),

             # Round 5e: each map arm against none, against the arm it
             # answers (H7, H9), against the other reused arms, and the skill
             # against the file (H8).
             ("lazyref", "none"), ("lazyskills", "none"),
             ("lazyref", "reference"), ("lazyskills", "skills"),
             ("lazyskills", "lazyref"),
             ("lazyref", "skills"), ("lazyskills", "reference"),
             ("lazyref", "hand"), ("lazyskills", "hand"),
             ("lazyref", "short"), ("lazyskills", "short"))

# Declared before the run. "up" improves upward, "down"
# improves downward, "neutral" is reported without a verdict.
UP, DOWN, NEUTRAL = "up", "down", "neutral"

# The primary dimensions the report leads with, owner-declared. Security and
# data protection are each read twice, by the judge and by the probes.
PROBE_RATES = ("security_probe_pass_rate", "data_protection_probe_pass_rate")
PRIMARY = ("judge_design", "judge_readability", "judge_maintainability",
           "judge_security", "judge_data_protection") + PROBE_RATES

# How a margin is measured: in the metric's own units, or as a share of the
# baseline arm's mean, so that it scales with the metric.
ABSOLUTE, RELATIVE = "absolute", "relative"

# The static-analysis counts reported per KLOC, held to one relative margin
# between them.
STATIC_PER_KLOC = ("ruff_per_kloc", "unformatted_per_kloc", "mypy_per_kloc",
                   "bandit_per_kloc", "complexity_over_15_per_kloc",
                   "unused_per_kloc")

# The non-inferiority margins, for the claim that a metric was preserved
# rather than merely not shown to differ.
MARGINS = {
    "task_success": ("2 pp", 0.02, ABSOLUTE),
    "adherence": ("5 pp", 0.05, ABSOLUTE),
    "judge_design": ("0.3 points", 0.3, ABSOLUTE),
    "judge_readability": ("0.3 points", 0.3, ABSOLUTE),
    "judge_maintainability": ("0.3 points", 0.3, ABSOLUTE),
    "judge_security": ("0.3 points", 0.3, ABSOLUTE),
    "judge_data_protection": ("0.3 points", 0.3, ABSOLUTE),
    "security_probe_pass_rate": ("2 pp", 0.02, ABSOLUTE),
    "data_protection_probe_pass_rate": ("10 pp", 0.10, ABSOLUTE),
    "churn_files": ("15 % relative", 0.15, RELATIVE),
    "churn_lines": ("15 % relative", 0.15, RELATIVE),
}
MARGINS.update((key, ("10 % relative", 0.10, RELATIVE))
               for key in STATIC_PER_KLOC)

# Round 5 holds adherence to one checklist item of thirteen rather than 5 pp.
# A pair's adherence differs by about one item from build to build, so no K
# a round can afford rules out a loss of less than one.
ROUND5_MARGINS = dict(MARGINS, adherence=("8 pp", 0.08, ABSOLUTE))

# Round 5 reads app code's size against a band rather than zero. A better
# solution is often a little bigger, with layering and error handling, so a
# rise inside the margin reads as held and only one wholly past it as worse.
ROUND5_MARGINS.update((key, ("20 % relative", 0.20, RELATIVE))
                      for key in ("app_lines", "app_files"))
BANDED = ("app_lines", "app_files")

# Round 5d adds two margins. Reliability's is one build of fifteen. Economy's
# is a quarter of the baseline's mean, so a small rise in cost reads as held.
ROUND5D_MARGINS = dict(ROUND5_MARGINS,
                       reliability=("6.7 pp", 1 / 15.0, ABSOLUTE))
ROUND5D_MARGINS.update((key, ("25 % relative", 0.25, RELATIVE))
                       for key in ("cost_usd", "turns", "output_tokens",
                                   "wall_seconds"))

# The rows round 5d reads on working builds alone. A build that does not
# install and boot counts once, against reliability, and not again against
# every row it would fail.
WORKING_ONLY = ("task_success",) + PROBE_RATES

# The size rows round 5 replaces with app code. Source lines miss templates
# and count tests kept in the package; files count docs and configuration.
# They are still printed, without a verdict, so nothing reads them twice.
SUPERSEDED_IN_ROUND5 = ("source_lines", "tracked_files")


def path(payload, *keys):
    """Follow a path through nested dicts, answering None at the first gap."""
    cursor = payload
    for key in keys:
        if not isinstance(cursor, dict) or key not in cursor:
            return None
        cursor = cursor[key]
    return cursor


def metric_value(trial, *keys):
    """A metric's value, or None where it was recorded as missing."""
    record = path(trial, "scores", *keys[:1])
    if not isinstance(record, dict) or record.get("missing"):
        return None
    return path(record, "value", *keys[1:]) if len(keys) > 1 else \
        record.get("value")


def per_kloc(trial, *keys):
    """A finding count per thousand source lines the tool actually saw."""
    count = metric_value(trial, *keys)
    lines = path(trial, "scores", keys[0], "seen", "lines")
    if count is None or not lines:
        return None
    return round(count / (lines / 1000.0), 2)


def task_success(trial):
    """The hidden suite's pass rate, and zero where nothing installed.

    A trial whose agent produced no installable workspace scores zero on
    task success rather than missing, because that is an outcome of the run
    and not a gap in the measurement.
    """
    rate = metric_value(trial, "hidden_suite")
    if rate is not None:
        return rate
    if metric_value(trial, "install") is False:
        return 0.0
    return None


def works(trial):
    """1.0 where the build installed, created its app and served `/`, 0.0
    where any of those failed, None where it was not measured."""

    # A redirect to the sign-in page is an app that serves, so any status
    # short of a server error counts as booted.
    install = metric_value(trial, "install")
    if install is False:
        return 0.0
    boot = metric_value(trial, "boot")
    if install is not True or not isinstance(boot, dict):
        return None
    status = boot.get("index_status")
    booted = (boot.get("factory") is True and isinstance(status, int)
              and status < 500)
    return 1.0 if booted else 0.0


def boolean(trial, *keys):
    value = metric_value(trial, *keys)
    return None if value is None else (1.0 if value else 0.0)


def extension_points(trial):
    axes = metric_value(trial, "structure", "extension_points")
    if not isinstance(axes, dict) or not axes:
        return None
    return sum(1 for present in axes.values() if present)


def structure_count(trial, key):
    value = metric_value(trial, "structure", key)
    return None if value is None else len(value)


def readings(trial):
    """Every completed judging of a trial, or its single judging; none for a
    build that did not install."""

    # A trial that produced no installable workspace has its quality metrics
    # recorded as missing, never scored: a judge reading an empty tree gives
    # it the lowest anchor on every row, which is a score of nothing.
    if path(trial, "scores", "install", "value") is False:
        return []
    several = trial.get("judgings")
    if several:
        return several
    return [trial["judge"]] if trial.get("judge") else []


def judge_score(trial, dimension):
    """The dimension's score, meaned over every judging of the trial.

    One call is not reproducible: six calls on one unchanged tree returned
    readability 4, 4, 4, 3, 4, 4. A round judges each trial several times and
    the mean is what a contrast is computed from. A trial judged once means
    itself, which is how the rounds before repeats were introduced read.
    """
    scores = [path(judging, "answer", "rubric", dimension, "score")
              for judging in readings(trial)]
    scores = [score for score in scores if score is not None]
    return statistics.fmean(scores) if scores else None


def pattern_count(trial, verdict):
    counts = []
    for judging in readings(trial):
        patterns = path(judging, "answer", "patterns")
        if isinstance(patterns, list):
            counts.append(sum(1 for entry in patterns
                              if entry.get("verdict") == verdict))
    return statistics.fmean(counts) if counts else None


# Every metric, its direction and where its number comes from. The direction
# column is declared before the run; an interval is read against
# it and never against "bigger is better".
METRICS = (
    ("judge_design", "Design (SOLID and patterns), 1-5", UP,
     lambda t: judge_score(t, "design")),
    ("judge_readability", "Readability, 1-5", UP,
     lambda t: judge_score(t, "readability")),
    ("judge_maintainability", "Maintainability, 1-5", UP,
     lambda t: judge_score(t, "maintainability")),
    ("judge_security", "Security, 1-5", UP,
     lambda t: judge_score(t, "security")),
    ("judge_data_protection", "Data protection, 1-5", UP,
     lambda t: judge_score(t, "data_protection")),
    ("security_probe_pass_rate", "Security probe pass rate, of eleven", UP,
     lambda t: security_value(t, "security_probe_pass_rate")),
    ("data_protection_probe_pass_rate",
     "Data-protection probe pass rate, of three", UP,
     lambda t: security_value(t, "data_protection_probe_pass_rate")),

    ("task_success", "Task success, hidden suite pass rate", UP, task_success),
    ("install", "Installs in a clean environment", UP,
     lambda t: boolean(t, "install")),
    ("reliability", "Installs and boots", UP, works),
    ("adherence", "Adherence checklist fraction", UP,
     lambda t: metric_value(t, "adherence")),

    ("judge_srp", "SRP, 1-5", UP, lambda t: judge_score(t, "srp")),
    ("judge_ocp", "OCP, 1-5", UP, lambda t: judge_score(t, "ocp")),
    ("judge_lsp", "LSP, 1-5", UP, lambda t: judge_score(t, "lsp")),
    ("judge_isp", "ISP, 1-5", UP, lambda t: judge_score(t, "isp")),
    ("judge_dip", "DIP, 1-5", UP, lambda t: judge_score(t, "dip")),
    ("judge_naming", "Naming and abstraction, 1-5", UP,
     lambda t: judge_score(t, "naming_and_abstraction")),
    ("judge_errors", "Error design, 1-5", UP,
     lambda t: judge_score(t, "error_design")),
    ("judge_tests", "Test quality, 1-5", UP,
     lambda t: judge_score(t, "test_quality")),

    ("patterns_warranted", "Patterns warranted", UP,
     lambda t: pattern_count(t, "warranted")),
    ("patterns_over_engineered", "Patterns over-engineered", DOWN,
     lambda t: pattern_count(t, "over_engineered")),
    ("patterns_missed", "Patterns missed", DOWN,
     lambda t: pattern_count(t, "missed")),

    ("coverage", "Line coverage of the trial's own tests, %", UP,
     lambda t: metric_value(t, "coverage", "line")),
    ("docstrings", "Docstring coverage, %", UP,
     lambda t: metric_value(t, "docstrings")),

    ("ruff_per_kloc", "Lint findings per KLOC", DOWN,
     lambda t: per_kloc(t, "ruff")),
    ("ruff_total", "Lint findings", DOWN, lambda t: metric_value(t, "ruff")),
    ("unformatted", "Files the formatter would change", DOWN,
     lambda t: metric_value(t, "ruff_format")),
    ("unformatted_per_kloc", "Files the formatter would change, per KLOC",
     DOWN, lambda t: per_kloc(t, "ruff_format")),
    ("mypy_errors", "Type errors under --strict", DOWN,
     lambda t: metric_value(t, "mypy")),
    ("mypy_per_kloc", "Type errors under --strict, per KLOC", DOWN,
     lambda t: per_kloc(t, "mypy")),
    ("bandit_serious", "Security findings, high and medium", DOWN,
     lambda t: metric_value(t, "bandit")),
    ("bandit_per_kloc", "Security findings, high and medium, per KLOC", DOWN,
     lambda t: per_kloc(t, "bandit")),
    ("complexity_max", "Highest cognitive complexity", DOWN,
     lambda t: metric_value(t, "complexity", "max")),
    ("complexity_over_15", "Functions over complexity 15", DOWN,
     lambda t: metric_value(t, "complexity", "over_15")),
    ("complexity_over_15_per_kloc", "Functions over complexity 15, per KLOC",
     DOWN, lambda t: per_kloc(t, "complexity", "over_15")),
    ("mean_cc", "Mean cyclomatic complexity", DOWN,
     lambda t: metric_value(t, "radon", "mean_cc")),
    ("min_mi", "Lowest maintainability index", NEUTRAL,
     lambda t: metric_value(t, "radon", "min_mi")),
    ("unused", "Unused names", DOWN, lambda t: metric_value(t, "unused")),
    ("unused_per_kloc", "Unused names per KLOC", DOWN,
     lambda t: per_kloc(t, "unused")),

    ("extension_points", "Extension axes present, of three", UP,
     extension_points),
    ("layering_violations", "Modules import tariff loads that reach Flask or "
     "the database", DOWN, lambda t: structure_count(t, "layering_violations")),
    ("money_in_routes", "Routes doing pricing arithmetic", DOWN,
     lambda t: structure_count(t, "money_in_routes")),
    ("bool_parameters", "Boolean parameters", DOWN,
     lambda t: structure_count(t, "bool_parameters")),
    ("kind_ladders", "Conditional ladders over rule kinds", DOWN,
     lambda t: structure_count(t, "kind_ladders")),
    ("surface_extra", "Public names beyond the specification", DOWN,
     lambda t: len(metric_value(t, "structure", "surface", "extra") or [])
     if metric_value(t, "structure", "surface") else None),
    ("surface_missing", "Specified names missing", DOWN,
     lambda t: len(metric_value(t, "structure", "surface", "missing") or [])
     if metric_value(t, "structure", "surface") else None),
    ("mutual_imports", "Mutually importing module pairs", DOWN,
     lambda t: metric_value(t, "structure", "graph", "mutual_import_pairs")),
    ("instability", "Mean instability of domain modules", NEUTRAL,
     lambda t: metric_value(t, "structure", "graph", "mean_instability")),

    ("xss_inert", "Stored payload renders inert", UP,
     lambda t: boolean(t, "web", "xss_inert")),
    ("csrf_refused", "A post without a token is refused", UP,
     lambda t: boolean(t, "web", "csrf_refused_without_token")),
    ("axe_violations", "Accessibility violations", DOWN,
     lambda t: path(t, "scores", "web", "accessibility", "value")),
    ("html_invalid", "HTML validity errors", DOWN,
     lambda t: path(t, "scores", "web", "html_validity", "value")),
    ("builder_bytes", "Invoice builder response size, bytes", DOWN,
     lambda t: metric_value(t, "web", "builder_bytes")),
    ("builder_subrequests", "Invoice builder subrequests", DOWN,
     lambda t: metric_value(t, "web", "builder_subrequests")),

    ("output_tokens", "Output tokens", DOWN,
     lambda t: metric_value(t, "cost", "output_tokens")),
    ("turns", "Turns", DOWN, lambda t: metric_value(t, "cost", "turns")),
    ("wall_seconds", "Wall time, seconds", DOWN,
     lambda t: metric_value(t, "cost", "elapsed_s")),
    ("cost_usd", "Cost, USD", DOWN,
     lambda t: metric_value(t, "cost", "cost_usd")),
    ("source_lines", "Source lines", DOWN,
     lambda t: metric_value(t, "scope", "source_lines")),
    ("tracked_files", "Files", DOWN,
     lambda t: metric_value(t, "scope", "tracked_files")),
    ("app_lines", "App code, lines", DOWN,
     lambda t: metric_value(t, "scope", "app_lines")),
    ("app_files", "App code, files", DOWN,
     lambda t: metric_value(t, "scope", "app_files")),
    ("test_lines", "Test code, lines", NEUTRAL,
     lambda t: metric_value(t, "scope", "test_lines")),
    ("unasked_artifacts", "Artifacts nobody asked for", DOWN,
     lambda t: metric_value(t, "scope", "unasked_artifacts")),

    ("change_success", "Change task, acceptance pass rate", UP,
     lambda t: change_success(t)),
    ("change_regression", "Change task, build suite pass rate after it", UP,
     lambda t: change_value(t, "build_suite")),
    ("churn_files", "Change task, files touched", DOWN,
     lambda t: change_value(t, "churn", "files")),
    ("churn_lines", "Change task, lines changed", DOWN,
     lambda t: change_value(t, "churn", "lines")),
    ("change_cost_usd", "Change task, cost, USD", DOWN,
     lambda t: change_value(t, "cost", "cost_usd")),
)

# The change task's rows, in the order the report prints them.
CHANGE = ("change_success", "change_regression", "churn_files", "churn_lines",
          "change_cost_usd")


def security_value(trial, key):
    """A security reading's value, or None where it was not taken."""
    return metric_value({"scores": trial.get("security") or {}}, key)


def change_value(trial, *keys):
    """A change-task metric's value, or None where it was not measured."""
    return metric_value({"scores": trial.get("change") or {}}, *keys)


def change_success(trial):
    """The change suite's pass rate, and zero where the changed tree broke."""
    rate = change_value(trial, "change_suite")
    if rate is not None:
        return rate
    if change_value(trial, "install") is False:
        return 0.0
    return None


def bca_interval(differences, seed, resamples=RESAMPLES):
    """A bias-corrected and accelerated bootstrap interval over K differences.

    Returns the interval and, where the method cannot be applied, the reason
    and the fallback used. Three identical differences make the bootstrap
    distribution a point mass: the bias correction is then infinite, and
    reporting a percentile interval with that stated is honest where
    reporting a computed BCa interval would not be.
    """
    count = len(differences)
    if count < 2:
        return {"low": None, "high": None,
                "method": "not computed: fewer than two paired differences"}
    observed = statistics.fmean(differences)
    shuffler = random.Random(seed)
    replicates = []
    for _ in range(resamples):
        sample = [differences[shuffler.randrange(count)] for _ in range(count)]
        replicates.append(statistics.fmean(sample))
    replicates.sort()

    if replicates[0] == replicates[-1]:
        return {"low": observed, "high": observed,
                "method": "degenerate: every paired difference is identical, "
                          "so every resample has the same mean"}

    normal = statistics.NormalDist()
    below = sum(1 for value in replicates if value < observed)
    share = below / resamples
    if share <= 0 or share >= 1:
        low = replicates[int((1 - CONFIDENCE) / 2 * resamples)]
        high = replicates[min(resamples - 1,
                              int((1 + CONFIDENCE) / 2 * resamples))]
        return {"low": low, "high": high,
                "method": "percentile: the bias correction is undefined "
                          "because no resample fell on one side of the mean"}

    bias = normal.inv_cdf(share)

    # Jackknife acceleration. With every difference equal the denominator is
    # zero, which the degenerate branch above has already taken.
    jackknife = [statistics.fmean(differences[:i] + differences[i + 1:])
                 for i in range(count)]
    centre = statistics.fmean(jackknife)
    deviations = [centre - value for value in jackknife]
    denominator = 6 * (sum(d * d for d in deviations) ** 1.5)
    acceleration = (sum(d ** 3 for d in deviations) / denominator
                    if denominator else 0.0)

    bounds = []
    for tail in ((1 - CONFIDENCE) / 2, (1 + CONFIDENCE) / 2):
        z = normal.inv_cdf(tail)
        adjusted = bias + (bias + z) / (1 - acceleration * (bias + z))
        position = normal.cdf(adjusted)
        index = min(resamples - 1, max(0, int(position * resamples)))
        bounds.append(replicates[index])
    return {"low": bounds[0], "high": bounds[1],
            "method": "BCa, %d resamples, %d%%" % (resamples,
                                                   int(100 * CONFIDENCE))}


# What a contrast reads as when its two arms were judged in different rounds.
# It is not a verdict, and every reader of a verdict below tests for "better"
# or "worse", so this value counts nowhere.
CROSSING_VERDICT = "no verdict: the arms were judged in different rounds"

# What a judge-row contrast reads as when the other vendor's judge reads it in
# the opposite direction. Like the crossing verdict, it counts nowhere.
DISAGREE_VERDICT = "no verdict: the two judges disagree on its direction"


def banded_verdict(interval, direction, margin):
    """Better, worse, held or no improvement shown, where a loss inside
    `margin`, in the metric's own units, reads as held rather than worse."""
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None:
        return "not computed"
    loss_low, loss_high = (-high, -low) if direction == UP else (low, high)
    if loss_high < 0:
        return "better"
    if loss_low > margin:
        return "worse"
    if loss_high <= margin:
        return "held"
    return "no improvement shown"


def verdict(interval, direction):
    """Better, worse, or no improvement shown — read against the direction."""
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None:
        return "not computed"
    if direction == NEUTRAL:
        return "reported without a verdict"
    if low <= 0 <= high:
        return "no improvement shown"
    improving = (low > 0) if direction == UP else (high < 0)
    return "better" if improving else "worse"


def non_inferior(key, interval, direction, baseline_mean=None, margins=None):
    """Whether a metric can be claimed preserved, not merely not-shown-worse.

    An interval containing zero is absence of evidence. The claim that nothing
    got worse needs the whole degradation side of the interval inside the
    margin fixed before the run: `margins`, by default the shared ones.
    """
    margins = MARGINS if margins is None else margins
    if key not in margins:
        return None
    label, margin, kind = margins[key]
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None:
        return None

    # A relative margin is a share of the baseline arm's mean. Without a
    # baseline, or against a zero one, there is nothing to take a share of.
    if kind == RELATIVE:
        if not baseline_mean:
            return None
        margin = margin * abs(baseline_mean)
    degradation = -low if direction == UP else high
    return {"margin": label, "within": degradation <= margin}


def load(root):
    """Every scored trial, with its judging attached where one exists.

    Keyed by canonical name, so a trial's score, judging and reading meet
    however each spelled it.
    """
    area = scoring_area(root)
    trials = {}
    for file in sorted(glob.glob(os.path.join(area, "scores", "*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            scores = json.load(handle)
        trials[canonical(scores["name"])] = {
            "scores": scores, "judge": None, "judgings": [], "change": None,
            "security": None}

    # A completed judging stands over any other record of the same trial,
    # such as a dry run's or a failed attempt's left beside it. A trial judged
    # more than once keeps all of them: each is a separate reading of the same
    # tree, and every score the report computes is their mean.
    for file in sorted(glob.glob(os.path.join(area, "judge", "T*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            judging = json.load(handle)
        name = canonical(judging.get("trial") or "")
        if name not in trials:
            continue
        if judging.get("outcome") == "judged":
            trials[name]["judgings"].append(judging)
            if path(trials[name], "judge", "outcome") != "judged":
                trials[name]["judge"] = judging
        elif trials[name]["judge"] is None:
            trials[name]["judge"] = judging

    # A change task sits beside its own build trial, so one whose build trial
    # was never scored has nothing to pair with and is left out.
    for file in sorted(glob.glob(os.path.join(area, "scores-change",
                                              "*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            change = json.load(handle)
        name = canonical(change.get("name") or "")
        if name in trials:
            trials[name]["change"] = change

    for file in sorted(glob.glob(os.path.join(area, "security-scores",
                                              "*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            security = json.load(handle)
        name = canonical(security.get("name") or "")
        if name in trials:
            trials[name]["security"] = security
    return trials


def arm_of(name):
    return split_name(name)[0]


def index_of(name):
    return split_name(name)[1]


def ordered(names):
    """Trial names by arm in the arms' declared order, then by block."""
    position = list(ARMS)
    return sorted(names, key=lambda name: (
        position.index(arm_of(name)) if arm_of(name) in position
        else len(position), index_of(name)))


def is_round5(trials):
    """Whether the run holds a round-5 arm, so that round's registration,
    its K and its margins, governs it."""
    return (any(arm_of(name) in ROUND5_ARMS for name in trials)
            or is_round5d(trials) or is_round5e(trials))


def is_round5d(trials):
    """Whether the run holds a round-5d arm, so that round's registration
    and its verdict rules govern it."""
    return any(arm_of(name) in ROUND5D_ARMS for name in trials)


def is_round5e(trials):
    """Whether the run holds a round-5e arm, so that round's registration
    governs it, under round 5d's verdict rules."""
    return any(arm_of(name) in ROUND5E_ARMS for name in trials)


def later_rules_of(trials):
    """Whether round 5d's verdict rules govern the run: they do from round
    5d on, so round 5e reads under them too."""
    return is_round5d(trials) or is_round5e(trials)


# The arms round 5 registers. A block is complete only when every one of
# them has its trial, so a run that lost a trial or an arm is part-run.
ROUND5_RUN = ("none", "inline", "hybrid", "reference", "skills")


def round_arms(trials):
    """The arms the run's round registers as fresh trials."""
    if is_round5e(trials):
        return ROUND5E_ARMS
    return ROUND5D_ARMS if is_round5d(trials) else ROUND5_RUN


def owed_blocks(trials):
    """The blocks of round 5's K that still miss a registered arm's trial,
    in order."""
    run = round_arms(trials)
    return [block for block in range(1, ROUND5_K + 1)
            if any(trial_name(arm, block) not in trials for arm in run)]


def blocks_named(blocks):
    """Block numbers in words, runs joined: blocks 2, 7 and 9 to 15."""
    spans = []
    for block in blocks:
        if spans and block == spans[-1][1] + 1:
            spans[-1][1] = block
        else:
            spans.append([block, block])
    parts = ["%d" % low if low == high else "%d to %d" % (low, high)
             for low, high in spans]
    words = parts[0] if len(parts) == 1 else "%s and %s" % (
        ", ".join(parts[:-1]), parts[-1])
    return ("block %s" if len(blocks) == 1 else "blocks %s") % words


def margins_of(trials):
    """The margins a run's contrasts are held against."""
    return ROUND5D_MARGINS if later_rules_of(trials) else ROUND5_MARGINS


def active_contrasts(trials):
    """The declared contrasts whose both arms the run holds, in the declared
    order."""
    present = {arm_of(name) for name in trials}
    return [pair for pair in CONTRASTS if set(pair) <= present]


def contrast_arms(active):
    """The arms the given contrasts name, in the arms' declared order."""
    named = {arm for pair in active for arm in pair}
    return [arm for arm in ARMS if arm in named]


def reused_arms(trials):
    """The arms whose trials were reused from an earlier round, with how
    many, in the arms' declared order."""
    counts = {}
    for name, trial in trials.items():
        if (trial.get("scores") or {}).get("reused_from"):
            counts[arm_of(name)] = counts.get(arm_of(name), 0) + 1
    return [(arm, counts[arm]) for arm in ARMS if arm in counts]


def arm_origins(trials):
    """Where each arm's trials ran: the root they were reused from, or None
    for an arm run in this round. A reused trial that names no root is
    told apart from a fresh one by the name its origin carries."""
    origins = {}
    for name in ordered(trials):
        source = (trials[name].get("scores") or {}).get("reused_from") or {}
        origins.setdefault(arm_of(name), source.get("root")
                           or source.get("name") or None)
    return origins


def crossing(active, origins):
    """The contrasts whose arms ran in different rounds: one reused and one
    run here, or both reused from different roots."""
    return [pair for pair in active
            if origins.get(pair[0]) != origins.get(pair[1])]


def crossed_labels(trials):
    """Every contrast label whose arms ran in different rounds."""
    return {"%s-%s" % pair
            for pair in crossing(active_contrasts(trials),
                                 arm_origins(trials))}


def collect(trials, metrics=METRICS, later_rules=None):
    """Metric values by metric, arm and trial index, read by round 5d's
    rules for a round-5d run or where `later_rules` asks for them."""
    working_only = (later_rules_of(trials) if later_rules is None
                    else later_rules)
    table = {}
    for key, label, direction, accessor in metrics:
        if key in SUPERSEDED_IN_ROUND5 or (working_only
                                           and key == "adherence"):
            direction = NEUTRAL
        row = {}
        for name, trial in sorted(trials.items()):
            try:
                value = accessor(trial)
            except (TypeError, KeyError, ValueError):
                value = None
            if working_only and key in WORKING_ONLY and works(trial) != 1.0:
                value = None
            row.setdefault(arm_of(name), {})[index_of(name)] = value
        table[key] = {"label": label, "direction": direction, "values": row}
    return table


def margined_verdict(interval, direction, margin):
    """Better or worse only where the whole interval lies past `margin`, in
    the metric's own units; held where its worse end stays within it; no
    improvement shown otherwise."""
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None:
        return "not computed"
    if direction == NEUTRAL:
        return "reported without a verdict"
    gain_low, gain_high = (low, high) if direction == UP else (-high, -low)
    if gain_low > margin:
        return "better"
    if -gain_high > margin:
        return "worse"
    if -gain_low <= margin:
        return "held"
    return "no improvement shown"


def wilson(successes, count):
    """Wilson's score interval for a share, at the report's confidence."""
    z = statistics.NormalDist().inv_cdf((1 + CONFIDENCE) / 2)
    share = successes / count
    scale = 1 + z * z / count
    centre = (share + z * z / (2 * count)) / scale
    half = z * math.sqrt(share * (1 - share) / count
                         + z * z / (4 * count * count)) / scale
    return max(0.0, centre - half), min(1.0, centre + half)


def newcombe_paired(pairs):
    """Newcombe's score interval for the difference of two shares measured
    on the same blocks (Newcombe, 1998, method 10): `pairs` holds each
    block's (treatment, baseline), each 1.0 or 0.0."""
    count = len(pairs)
    both = sum(1 for left, right in pairs if left and right)
    left_only = sum(1 for left, right in pairs if left and not right)
    right_only = sum(1 for left, right in pairs if right and not left)
    neither = count - both - left_only - right_only
    first, second = (both + left_only) / count, (both + right_only) / count
    low1, high1 = wilson(both + left_only, count)
    low2, high2 = wilson(both + right_only, count)
    product = ((both + left_only) * (right_only + neither)
               * (both + right_only) * (left_only + neither))
    phi = ((both * neither - left_only * right_only) / math.sqrt(product)
           if product else 0.0)
    below = math.sqrt(max(0.0, (first - low1) ** 2 - 2 * phi * (first - low1)
                          * (high2 - second) + (high2 - second) ** 2))
    above = math.sqrt(max(0.0, (high1 - first) ** 2 - 2 * phi * (high1 - first)
                          * (second - low2) + (second - low2) ** 2))
    difference = first - second
    return {"low": max(-1.0, difference - below),
            "high": min(1.0, difference + above),
            "method": "Newcombe's score interval, paired, %d%%"
                      % int(100 * CONFIDENCE)}


def newcombe_unpaired(left, right):
    """Newcombe's score interval for the difference of two independent
    shares (Newcombe, 1998, method 10): each list holds 1.0 or 0.0."""
    first, second = statistics.fmean(left), statistics.fmean(right)
    low1, high1 = wilson(sum(left), len(left))
    low2, high2 = wilson(sum(right), len(right))
    difference = first - second
    return {"low": difference - math.hypot(first - low1, high2 - second),
            "high": difference + math.hypot(high1 - first, second - low2),
            "method": "Newcombe's score interval, unpaired, %d%%"
                      % int(100 * CONFIDENCE)}


def clopper_pearson(successes, count):
    """The exact interval for a share (Clopper and Pearson, 1934), found by
    bisection on the binomial tail."""
    tail = (1 - CONFIDENCE) / 2

    def at_most(k, share):
        return sum(math.comb(count, i) * share ** i * (1 - share) ** (count - i)
                   for i in range(k + 1))

    def solve(falls, target):
        low, high = 0.0, 1.0
        for _ in range(60):
            middle = (low + high) / 2
            if falls(middle) > target:
                low = middle
            else:
                high = middle
        return (low + high) / 2
    lower = 0.0 if successes == 0 else solve(
        lambda share: -(1 - at_most(successes - 1, share)), -tail)
    upper = 1.0 if successes == count else solve(
        lambda share: at_most(successes, share), tail)
    return lower, upper


# The radar's full scales: the move at which a row scores ±1. Judge rows move
# on their 1-5 scale, shares in parts of one, coverage in percent; every
# other row is a count or a cost, read as a ratio on a log scale.
JUDGE_SCALE = 1.0
SHARE_SCALE = 0.20
COVERAGE_SCALE = 20.0
RATIO_SCALE = 4.0
SHARE_ROWS = ("reliability", "task_success", "install", "csrf_refused",
              "xss_inert") + PROBE_RATES

# Cost and turns are never zero in a trial that ran, so they take the plain
# ratio; a count may be zero on either side, so it is offset by one unit.
PLAIN_RATIO_ROWS = ("cost_usd", "turns", "output_tokens", "wall_seconds")


def row_size(key, interval, direction, baseline_mean):
    """How far a row moved, from -1 to +1 with + for better: the bound of
    its interval nearest zero over the row's full scale, capped; 0 for an
    interval across zero; None where it cannot be read."""
    low, high = interval.get("low"), interval.get("high")
    if low is None or high is None or direction == NEUTRAL:
        return None
    bound = 0.0 if low <= 0 <= high else (low if low > 0 else high)
    if key.startswith("judge_"):
        moved = bound / JUDGE_SCALE
    elif key in SHARE_ROWS:
        moved = bound / SHARE_SCALE
    elif key == "coverage":
        moved = bound / COVERAGE_SCALE
    else:
        if baseline_mean is None:
            return None
        offset = 0.0 if key in PLAIN_RATIO_ROWS else 1.0
        if baseline_mean + offset <= 0 or baseline_mean + bound + offset <= 0:
            return None
        moved = math.log((baseline_mean + bound + offset)
                         / (baseline_mean + offset)) / math.log(RATIO_SCALE)
    signed = moved if direction == UP else -moved
    return max(-1.0, min(1.0, signed))


def unpaired_interval(left, right, seed, resamples=RESAMPLES):
    """A bias-corrected and accelerated bootstrap interval for the
    difference of two independent means, each arm resampled on its own.

    The acceleration comes from each arm's jackknife, combined across the
    two samples (Efron and Tibshirani, 1993, ch. 14).
    """
    if len(left) < 2 or len(right) < 2:
        return {"low": None, "high": None,
                "method": "not computed: fewer than two trials in an arm"}
    observed = statistics.fmean(left) - statistics.fmean(right)
    shuffler = random.Random(seed)
    replicates = sorted(
        statistics.fmean(shuffler.choices(left, k=len(left)))
        - statistics.fmean(shuffler.choices(right, k=len(right)))
        for _ in range(resamples))
    method = "BCa, unpaired, %d resamples, %d%%" % (resamples,
                                                    int(100 * CONFIDENCE))
    if replicates[0] == replicates[-1]:
        return {"low": observed, "high": observed,
                "method": "degenerate: every trial of each arm is identical"}
    share = sum(1 for value in replicates if value < observed) / resamples
    if share <= 0 or share >= 1:
        return {"low": replicates[int((1 - CONFIDENCE) / 2 * resamples)],
                "high": replicates[min(resamples - 1, int(
                    (1 + CONFIDENCE) / 2 * resamples))],
                "method": "percentile: the bias correction is undefined "
                          "because no resample fell on one side of the mean"}
    normal = statistics.NormalDist()
    bias = normal.inv_cdf(share)
    cubes, squares = 0.0, 0.0

    # The baseline's mean enters the difference with a minus sign, so its
    # influence on the difference is the negative of its influence on its
    # own mean; the squares do not see the sign, the cubes do.
    for sample, sign in ((left, 1.0), (right, -1.0)):
        count = len(sample)
        jackknife = [statistics.fmean(sample[:i] + sample[i + 1:])
                     for i in range(count)]
        centre = statistics.fmean(jackknife)
        influence = [sign * (count - 1) * (centre - value)
                     for value in jackknife]
        cubes += sum(u ** 3 for u in influence) / count ** 3
        squares += sum(u * u for u in influence) / count ** 2
    acceleration = cubes / (6 * squares ** 1.5) if squares else 0.0
    bounds = []
    for tail in ((1 - CONFIDENCE) / 2, (1 + CONFIDENCE) / 2):
        z = normal.inv_cdf(tail)
        position = normal.cdf(bias + (bias + z)
                              / (1 - acceleration * (bias + z)))
        bounds.append(replicates[min(resamples - 1,
                                     max(0, int(position * resamples)))])
    return {"low": bounds[0], "high": bounds[1], "method": method}


def strict_contrast(key, direction, left, right, seed, margins,
                    resamples=RESAMPLES, unpaired=False):
    """One contrast read by round 5d's rules, paired by block or, with
    `unpaired`, as two independent samples.

    Better or worse needs the whole interval past the row's margin, and a
    row without one is read against zero. Reliability's interval is
    Newcombe's, as a share's. Each contrast carries its size on the radar.
    """
    observed = [value for value in right.values() if value is not None]
    baseline_mean = statistics.fmean(observed) if observed else None
    if unpaired:
        ours = [value for value in left.values() if value is not None]
        if not ours or not observed:
            return {"pairs": [], "mean": None, "size": None, "unpaired": True,
                    "interval": {"low": None, "high": None,
                                 "method": "an arm has no measured trial"},
                    "verdict": "not computed", "non_inferior": None}
        interval = (newcombe_unpaired(ours, observed) if key == "reliability"
                    else unpaired_interval(ours, observed, seed, resamples))
        mean = statistics.fmean(ours) - baseline_mean
        return dict(margined(key, direction, interval, baseline_mean,
                             margins), pairs=[], mean=round(mean, 4),
                    interval=interval, unpaired=True,
                    trials=(len(ours), len(observed)))
    measured = [(left[index], right[index])
                for index in sorted(set(left) & set(right))
                if left[index] is not None and right[index] is not None]
    if not measured:
        return {"pairs": [], "mean": None, "size": None,
                "interval": {"low": None, "high": None,
                             "method": "no complete pair was measured"},
                "verdict": "not computed", "non_inferior": None}
    pairs = [first - second for first, second in measured]
    interval = (newcombe_paired(measured) if key == "reliability"
                else bca_interval(pairs, seed, resamples))
    return dict(margined(key, direction, interval, baseline_mean, margins),
                pairs=pairs, mean=round(statistics.fmean(pairs), 4),
                interval=interval)


def margined(key, direction, interval, baseline_mean, margins):
    """An interval's verdict past the row's margin, its non-inferiority and
    its size on the radar."""
    margin = 0.0
    if key in margins:
        _, share, kind = margins[key]
        margin = (share * abs(baseline_mean or 0.0) if kind == RELATIVE
                  else share)
    return {"verdict": margined_verdict(interval, direction, margin),
            "non_inferior": non_inferior(key, interval, direction,
                                         baseline_mean, margins),
            "size": row_size(key, interval, direction, baseline_mean)}


def contrasts(table, seed, crossed=(), margins=None, strict=False,
              resamples=RESAMPLES, only=None):
    """The paired differences, their intervals and their verdicts, with
    each held against `margins`, by default the shared ones.

    `strict` reads them by round 5d's rules, as `strict_contrast` states,
    and a contrast in `crossed` unpaired. `only` limits the contrasts
    computed to the labels it names.

    A contrast in `crossed` pairs an arm judged in an earlier round with one
    judged in this one, so its difference carries the day as well as the arm.
    Such a contrast keeps its mean and interval and is given no verdict: a
    reader can see the number and what produced it, and nothing downstream
    counts it as a win, a fail or a finding.
    """
    results = {}
    for key, entry in table.items():
        per_contrast = {}
        for treatment, baseline in CONTRASTS:
            label = "%s-%s" % (treatment, baseline)
            if only and label not in only:
                continue
            left = entry["values"].get(treatment, {})
            right = entry["values"].get(baseline, {})
            # Round 5d reads a contrast with an earlier round's arm unpaired,
            # as registered: the two never ran in one block.
            if strict:
                per_contrast[label] = strict_contrast(
                    key, entry["direction"], left, right, seed,
                    margins or MARGINS, resamples, label in crossed)
                continue
            pairs = []
            for index in sorted(set(left) & set(right)):
                if left[index] is None or right[index] is None:
                    continue
                pairs.append(left[index] - right[index])
            if not pairs:
                per_contrast[label] = {
                    "pairs": [], "mean": None,
                    "interval": {"low": None, "high": None,
                                 "method": "no complete pair was measured"},
                    "verdict": "not computed", "non_inferior": None}
                continue
            interval = bca_interval(pairs, seed)
            observed = [value for value in right.values() if value is not None]
            across = label in crossed
            read = verdict(interval, entry["direction"])
            band = (margins or MARGINS).get(key)
            if key in BANDED and band and observed and statistics.fmean(
                    observed):
                read = banded_verdict(interval, entry["direction"],
                                      band[1] * abs(statistics.fmean(
                                          observed)))
            per_contrast[label] = {
                "pairs": pairs,
                "mean": round(statistics.fmean(pairs), 4),
                "interval": interval,
                "verdict": CROSSING_VERDICT if across else read,
                "non_inferior": None if across else non_inferior(
                    key, interval, entry["direction"],
                    statistics.fmean(observed) if observed else None,
                    margins),
            }
        results[key] = per_contrast
    return results


def round_contrasts(trials, table, seed):
    """`table`'s contrasts read the way the round registered: its margins,
    its crossings, and round 5d's rules for a round-5d run."""
    return contrasts(table, seed, crossed_labels(trials), margins_of(trials),
                     later_rules_of(trials))


def withdrawals(trials, path=WITHDRAWN):
    """Each withdrawn metric whose grader revision scored any of these trials.

    One trial graded by the withdrawn revision withdraws the metric for the
    run, because the contrasts pair trials and a pair measured by two graders
    compares the graders.
    """
    if not os.path.exists(path):
        return {}
    with io.open(path, encoding="utf-8") as handle:
        records = json.load(handle)
    withdrawn = {}
    for record in records:
        part = "change" if record["metric"] in CHANGE else "scores"
        graded = {(trial.get(part) or {}).get("suite_revision")
                  for trial in trials.values()}
        if record["suite_revision"] in graded:
            withdrawn[record["metric"]] = record
    return withdrawn


def withdraw(withdrawn, table, *result_sets):
    """Blank each withdrawn metric's values, intervals and verdicts in place."""
    for key in withdrawn:

        # A number left in the raw table still reads as a result, so the
        # values go as well as the verdict.
        if key in table:
            table[key]["values"] = {arm: dict.fromkeys(row) for arm, row
                                    in table[key]["values"].items()}
        for results in result_sets:
            if key in results:
                results[key] = {"%s-%s" % pair: {
                    "pairs": [], "mean": None,
                    "interval": {"low": None, "high": None,
                                 "method": "withdrawn, see Withdrawn "
                                           "measurements"},
                    "verdict": "withdrawn", "non_inferior": None}
                    for pair in CONTRASTS}


# The primary rows the judge scores, which the other vendor's judge reads too.
JUDGE_ROWS = tuple(key for key in PRIMARY if key not in PROBE_RATES)

# Two scores this close agree: the rubric anchors its 1, 3 and 5 two points
# apart, so a difference of one never crosses an anchor.
AGREE_WITHIN = 1.0


def load_cross_check(root, trials):
    """The other vendor's completed judgings under `root`, for the trials
    this round scored, keyed as `load` keys them."""
    found = {}
    pattern = os.path.join(scoring_area(root), "judge", "T*.json")
    for file in sorted(glob.glob(pattern)):
        with io.open(file, encoding="utf-8") as handle:
            judging = json.load(handle)
        name = canonical(judging.get("trial") or "")
        if name in trials and judging.get("outcome") == "judged":
            entry = found.setdefault(name, {"judge": judging, "judgings": []})
            entry["judgings"].append(judging)
    return found


def shared_judges(trials, other):
    """The judge models that read both this round and the cross-check."""
    def models(source):
        return {judging.get("model") for trial in source.values()
                for judging in readings(trial)}
    return sorted(str(model) for model in models(trials) & models(other))


def cross_check(trials, other, seed, later_rules=None):
    """How far the other vendor's judge agrees with the rounds' judge on the
    trials it read, per judge row, and the contrasts it reads itself, by
    round 5d's rules for a round-5d run or where `later_rules` asks."""
    strict = later_rules_of(trials) if later_rules is None else later_rules
    rows = {}
    for key in JUDGE_ROWS:
        dimension = key[len("judge_"):]
        differences = []
        for name in sorted(other):
            ours = judge_score(trials[name], dimension)
            theirs = judge_score(other[name], dimension)
            if ours is not None and theirs is not None:
                differences.append(theirs - ours)
        rows[key] = {
            "trials": len(differences),
            "mean_difference": (round(statistics.fmean(differences), 4)
                                if differences else None),
            "within_one": (sum(1 for difference in differences
                               if abs(difference) <= AGREE_WITHIN)
                           / len(differences) if differences else None)}
    first = other[min(other)]["judge"] if other else {}
    metrics = [metric for metric in METRICS if metric[0] in JUDGE_ROWS]
    return {"model": first.get("model"), "trials": sorted(other),
            "rows": rows,
            "results": contrasts(collect(other, metrics, strict), seed,
                                 crossed_labels(trials), None, strict),
            "disagreements": []}


def disagree(results, check):
    """Withhold the verdict of every judge-row contrast the other vendor's
    judge reads in the opposite direction; return what was withheld."""
    withheld = []
    for key in JUDGE_ROWS:
        for label, contrast in results.get(key, {}).items():
            ours = contrast["mean"]

            # A contrast the other judge's reading did not compute, as an
            # earlier round's leaves out round 5d's, has nothing to oppose.
            theirs = check["results"].get(key, {}).get(label, {}).get("mean")
            if (contrast["verdict"] not in ("better", "worse")
                    or ours is None or theirs is None):
                continue

            # Opposite signs only: a judge that reads no difference has not
            # read the other direction, and a verdict it merely fails to
            # confirm is what the rounds' judge's interval already weighs.
            if ours * theirs < 0:
                contrast["verdict"] = DISAGREE_VERDICT
                contrast["non_inferior"] = None
                withheld.append({"metric": key, "contrast": label,
                                 "ours": ours, "theirs": theirs})
    check["disagreements"] = withheld
    return withheld


def cross_check_section(check):
    """The report's lines on the other vendor's judge."""
    lines = ["## The other vendor's judge", ""]
    if not check:
        lines.append("Not run: no other vendor's judging was read for this "
                     "round, so the judge is checked only by its evidence "
                     "lines.")
        return lines
    lines.append("`%s` read %d trial(s) of this round: %s. Its scores are "
                 "never meaned with the rounds' judge's. A judge-row contrast "
                 "it reads in the opposite direction keeps its numbers and "
                 "loses its verdict."
                 % (check["model"], len(check["trials"]),
                    ", ".join(check["trials"])))
    lines.append("")
    lines.append("| Row | Trials read by both | Mean difference, other judge "
                 "minus the rounds' | Within one point |")
    lines.append("|---|---|---|---|")
    for key in JUDGE_ROWS:
        row = check["rows"][key]
        lines.append("| %s | %d | %s | %s |"
                     % (SHORT[key], row["trials"],
                        number(row["mean_difference"]),
                        "—" if row["within_one"] is None
                        else "%.0f%%" % (100 * row["within_one"])))
    lines.append("")
    if check["disagreements"]:
        lines.append("Verdicts withheld, the two judges reading opposite "
                     "directions:")
        lines.append("")
        for entry in check["disagreements"]:
            lines.append("- %s, %s: the rounds' judge %s, the other %s"
                         % (SHORT[entry["metric"]], entry["contrast"],
                            signed(entry["ours"]), signed(entry["theirs"])))
    else:
        lines.append("No verdict withheld: on every judge-row contrast both "
                     "read, the two judges agree on the direction or one of "
                     "them reads none.")
    return lines


def blocks_state(trials):
    """How far the run has come toward its registered K: the blocks it
    holds, and those that still miss a registered arm's trial."""
    return {"k": max((index_of(name) for name in trials), default=0),
            "owed_blocks": owed_blocks(trials)}


def number(value):
    """One rendering of a number, so the tables line up."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, float):
        if value == int(value):
            return "%d" % int(value)
        return "%.3f" % value if abs(value) < 1000 else "%.1f" % value
    return str(value)


def generation_records():
    """Each generated arm's record, committed beside the file it produced,
    by arm; an arm whose record is absent is left out."""
    records = {}
    for arm in GENERATED:
        path = record_path(arm)
        if os.path.exists(path):
            with io.open(path, encoding="utf-8") as handle:
                records[arm] = json.load(handle)
    return records


def run_records(root):
    """Every trial record in the root's run records, in time order."""
    sequence = []
    for file in sorted(glob.glob(os.path.join(root, "run-*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            sequence.extend(json.load(handle).get("trials", []))
    return sequence


# What marks a change task's name apart from its build trial's.
CHANGE_TASK = " (change task)"


def name_of(record):
    """A trial record's name, marking a change task apart from its build."""

    # A change task shares its build trial's name, so the task tells them
    # apart; a record written before tasks existed is a build trial.
    name = trial_of(record)
    if record.get("task", "build") == "change":
        name += CHANGE_TASK
    return name


def started(record):
    """When a trial record's trial started, as a timestamp, or None."""

    # Recorded to the second and before the CLI launched, so it never falls
    # after a transcript the trial itself wrote.
    try:
        moment = datetime.datetime.fromisoformat(record["started_at"])
    except (KeyError, TypeError, ValueError):
        return None
    return moment.timestamp()


def spec_problem(root):
    """Why the round's build trials did not all build from the spec round 5
    registers, or None when every one did."""
    registered = ROUND5_SPEC[1]
    for record in run_records(root):
        if record.get("task", "build") != "build":
            continue
        spec = record.get("spec")

        # A refused or unfinished trial built nothing, so it has no spec to
        # show; a trial with something to score has to.
        if spec is None:
            if record.get("outcome") in SCORABLE:
                return ("trial %s records no spec, so it cannot be shown to "
                        "have built from the registered one" % trial_of(record))
            continue
        if spec.get("sha256") != registered:
            return ("trial %s built from %s at sha256 %s, and round 5 "
                    "registers sha256 %s" % (trial_of(record), spec.get("file"),
                                             spec.get("sha256"), registered))
    return None


def prompt_problem(root):
    """Why one of the round's build trials was given another prompt than the
    one every arm is given, or None when none was."""

    # Read per trial, not per run: reusing a trial copies its record, with
    # its own prompt, into a run that names the current one.
    for record in run_records(root):
        if record.get("task", "build") != "build":
            continue

        # A refused or unfinished trial put nothing in front of the scorer,
        # so its prompt does not matter.
        if record.get("outcome") not in SCORABLE:
            continue
        if record.get("prompt") != PROMPT:
            return ("trial %s was given another prompt than the one every "
                    "arm is given" % trial_of(record))
    return None


def python_problem(trials):
    """Why the trials' scores were not all installed on one Python, or None.

    A score from before the scorer recorded its Python reads as unrecorded,
    so a round's old scores beside new ones are refused too."""
    found = {}
    for name, trial in trials.items():
        for part in ("scores", "change"):
            scores = trial.get(part)
            if scores is None:
                continue
            version = scores.get("python")
            minor = ".".join(version.split(".")[:2]) if version else "unrecorded"
            found.setdefault(minor, name)
    if len(found) < 2:
        return None
    return ("the trials were installed on more than one Python: %s"
            % ", ".join("%s (%s, for one)" % (minor, name)
                        for minor, name in sorted(found.items())))


def registration_of(trials):
    """The registration a run is read against: the latest round whose arm
    it holds."""
    if is_round5e(trials):
        return ROUND5E_REGISTRATION
    return ROUND5D_REGISTRATION if is_round5d(trials) else ROUND5_REGISTRATION


def registration_problem(root, registration, repository=REPOSITORY):
    """Why the round's registration does not predate its first trial, or
    None when it landed on the main branch before that trial and is
    unchanged since."""
    moments = []
    for record in run_records(root):

        # A trial reused from an earlier round ran under that round's
        # registration, so only this round's own trials have to follow its.
        if record.get("reused_from"):
            continue
        try:
            moment = datetime.datetime.fromisoformat(record["started_at"])
        except (KeyError, TypeError, ValueError):
            continue

        # A harness from before offsets were recorded wrote local time with no
        # zone, which no machine can order against a commit's date for sure.
        if moment.tzinfo is None:
            return ("trial %s started at %s, which carries no UTC offset, so "
                    "it cannot be ordered against %s"
                    % (trial_of(record), record["started_at"], registration))
        moments.append(moment)
    if not moments:
        return "no run record under %s says when the first trial ran" % root
    first = min(moments)
    if git(repository, "status", "--porcelain", "--", registration):
        return "%s has changes that are not committed" % registration
    if git(repository, "diff", "--name-only", REGISTRATION_BRANCH, "--",
           registration):
        return ("%s differs from %s's copy, so it has not landed; merge it "
                "or pull %s" % (registration, REGISTRATION_BRANCH,
                                REGISTRATION_BRANCH))

    # The first-parent line is the main branch's own history, so a merge that
    # brought the registration in is read at the merge, not at the branch
    # commit beneath it. GitHub's squash and rebase merges stamp the commit
    # with the merge time; a fast-forward pushed from a clone keeps the
    # branch commit's date, which this cannot see past.
    landed = git(repository, "log", REGISTRATION_BRANCH, "--first-parent",
                 "-1", "--format=%cI", "--", registration)
    if not landed:
        return "%s is not on %s" % (registration, REGISTRATION_BRANCH)
    if datetime.datetime.fromisoformat(landed) > first:
        return ("%s landed on %s at %s, after the first trial started at %s"
                % (registration, REGISTRATION_BRANCH, landed,
                   first.isoformat()))
    return None


def reaches(root):
    """Every scorable trial's transcript scan, as name and hits.

    Scanned here under the current rule wherever the run root still holds the
    transcripts, so a record scanned under an earlier, narrower rule is read
    again. A trial whose transcripts are gone keeps its record's own scan.
    """
    home = os.path.join(root, "home")
    scans = []
    for record in run_records(root):
        if record.get("outcome") not in SCORABLE:
            continue
        workspace = record.get("workspace") or ""
        files, calls = read_transcripts(home, workspace, started(record))
        if files:
            scan = reach(files, calls, workspace, record.get("temp"),
                         record.get("vendored"))
        else:
            scan = record.get("reach") or reach(files, calls)
        scans.append({"name": name_of(record), "hits": scan["hits"]})
    return scans


def exclude_reached(trials, scans):
    """Leave out of `trials` every trial whose scan finds a reach, in place;
    return the names left out.

    A reached build trial goes whole. A reached change task takes only its
    change reading with it, because its build trial was measured clean.
    """
    left_out = []
    for scan in scans:
        if not scan["hits"]:
            continue
        name = scan["name"]
        build = name.replace(CHANGE_TASK, "")
        if build not in trials:
            continue
        if name == build:
            del trials[name]
        elif trials[build]["change"] is not None:
            trials[build]["change"] = None
        else:
            continue
        left_out.append(name)
    return left_out


def reach_section(root, scans=None):
    """The report's lines naming every trial that reached past its own
    workspace, from `scans` where the caller has already taken them."""
    lines = ["## Trials that reached past their own workspace",
             "",
             "The shell keeps its network, and a trial's deny rules fence "
             "only the file tools, so a trial could still fetch this "
             "repository or read the hidden suite, the scoring area, or "
             "another trial's workspace, tarball or transcript through the "
             "shell. Every transcript is scanned for a tool call naming any "
             "of them. The harness voids a trial whose scan finds one and "
             "re-runs it; a trial this re-scan flags is left out of every "
             "figure above.",
             ""]
    scans = reaches(root) if scans is None else scans
    flagged = [scan for scan in scans if scan["hits"]]
    if flagged:
        lines.append("| Trial | Tool | Names | Call |")
        lines.append("|---|---|---|---|")
        for scan in flagged:
            for hit in scan["hits"]:
                call = " ".join(hit["call"].split()).replace("|", "/")
                lines.append("| %s | %s | `%s` | %s |"
                             % (scan["name"], hit["tool"], hit["term"],
                                call[:160]))
    else:
        lines.append("None: no scanned transcript names any of them.")
    unscanned = [scan["name"] for scan in scans if scan["hits"] is None]
    if unscanned:
        lines.append("")
        lines.append("Not scanned, having no transcript: %s."
                     % ", ".join(unscanned))
    return lines


def lost_trials(root):
    """Every trial the harness voided, with the outcome of what replaced it."""

    # Every run record in time order, because a voided trial is re-run either
    # in its place or by a later run started `--from` it.
    sequence = run_records(root)

    lost, recorded = [], set()
    for index, record in enumerate(sequence):
        if record.get("outcome") not in VOIDING:
            continue
        later = next((other for other in sequence[index + 1:]
                      if name_of(other) == name_of(record)), None)
        kept = path(record, "void", "dir")
        if kept:
            recorded.add(os.path.normcase(os.path.abspath(kept)))
        lost.append({"name": name_of(record),
                     "started_at": record.get("started_at"),
                     "reason": record.get("reason"),
                     "kept": kept,
                     "rerun": later.get("outcome") if later else None})
    return lost + unrecorded_voids(root, sequence, recorded)


# A voided directory is named for the workspace it held and when it was
# voided, as `change-hand-2-2026-09-16T20-29-18`.
VOIDED = re.compile(r"^(change-)?([a-z]+-\d+)-(\d{4}-\d{2}-\d{2})"
                    r"T(\d{2})-(\d{2})-(\d{2})$")


def unrecorded_voids(root, sequence, recorded):
    """Each voided workspace under `void/` that no run record names.

    A run that stops before recording a trial leaves the voided workspace as
    the only trace of the loss, so the directory is read for the trial and
    the time, and the first record for that trial started after it is the
    re-run.
    """
    voided = os.path.join(root, "void")
    entries = sorted(os.listdir(voided)) if os.path.isdir(voided) else []
    lost = []
    for entry in entries:
        kept = os.path.join(voided, entry)
        if os.path.normcase(os.path.abspath(kept)) in recorded:
            continue

        # A directory named otherwise is still a loss, listed under its own
        # name rather than skipped.
        match = VOIDED.match(entry)
        name, voided_at = entry, ""
        if match:
            name = canonical(match.group(2)) + (" (change task)"
                                                if match.group(1) else "")
            voided_at = "%sT%s:%s:%s" % match.group(3, 4, 5, 6)
        later = next((record for record in sequence
                      if name_of(record) == name
                      and (record.get("started_at") or "") >= voided_at),
                     None)
        lost.append({"name": name, "started_at": None,
                     "reason": "no run record holds it: the run stopped "
                               "before recording the trial",
                     "kept": kept,
                     "rerun": later.get("outcome") if later else None})
    return lost


def write_report(root, trials, table, results, seed, out_dir,
                 withdrawn=None, cross=None, iso=None, uses=None):
    """The dated round report, written to `out_dir`.

    The directory has no default so a shakedown of the writer renders into
    a scratch directory. A fabricated run must not be able to leave a file
    among the real audits, where its date alone would read as a result.
    `withdrawn` maps each withdrawn metric to its record, already blanked
    from `table` and `results`.
    `cross` is the other vendor's judge's reading, already applied to
    `results`.
    `iso` is the ISO reading, computed here when not given and the round
    draws that radar.
    """
    names = ordered(trials)
    arms = [arm for arm in ARMS if arm in {arm_of(name) for name in names}]
    k = max((index_of(name) for name in names), default=0)
    generation = generation_records()

    stem = "%s-efficacy" % datetime.date.today().isoformat()
    report, appendix, record = (stem + ".md", stem + "-appendix.md",
                                stem + "-record.md")
    lines = []
    lines.append("# Efficacy benchmark — %s, full record"
                 % datetime.date.today().isoformat())
    lines.append("")
    lines.append("Every number behind [the report](%s) and its [technical "
                 "appendix](%s), trial by trial." % (report, appendix))
    lines.append("")
    lines.append("Does a generated context file improve the result? The "
                 "question, the verdict rule and the metric directions were "
                 "fixed before any trial ran, in the "
                 "solid-ai-benchmark repository.")
    lines.append("")
    if k < FEWEST_DECIDING:
        lines.append("**Every interval below is descriptive.** At K = %d no "
                     "arrangement of paired differences reaches conventional "
                     "significance, which the registration states and this "
                     "report repeats rather than footnotes." % k)
    else:
        lines.append("Each interval below is a 95 %% bootstrap interval over "
                     "the paired differences of its contrast, one per block "
                     "that measured both arms: K = %d at most, and a cell "
                     "that had fewer names its count." % k)
    lines.append("")

    lost = lost_trials(root)
    scans = reaches(root)
    active = active_contrasts(trials)
    os.makedirs(out_dir, exist_ok=True)
    if iso is None and iso_rules(trials):
        iso = iso_reading(trials, seed, withdrawn or {})
    if iso:
        panels = iso_panels(table, iso[0], iso[1], active)
        draw = iso_radar_svg
    else:
        panels = radar_panels(table, results, active)
        draw = radar_svg
    radar = {}
    if panels:
        for theme in RADAR_THEMES:
            image = "%s-radar-%s.svg" % (stem, theme)
            with io.open(os.path.join(out_dir, image), "w", encoding="utf-8",
                         newline="\n") as handle:
                handle.write(draw(panels, theme))
            radar[theme] = image
    lines.extend(executive_section(trials, table, results, withdrawn or {},
                                   lost, scans, radar, iso))
    lines.append("")

    lines.extend(["## What produced these numbers", ""])
    lines.extend(provenance_lines(trials, names, arms, k, seed,
                                  generation))
    lines.append("")

    if withdrawn:
        lines.extend(withdrawn_section(withdrawn))
        lines.append("")

    lines.append("## Primary dimensions")
    lines.append("")
    lines.append("The report leads with these, declared by the owner "
                 "before the run: %s judge rows and %s probe pass rates. "
                 "Task success and cost follow."
                 % (counted(len(PRIMARY) - len(PROBE_RATES)),
                    counted(len(PROBE_RATES))))
    lines.append("")
    lines.extend(contrast_table(table, results, PRIMARY, active=active,
                                blocks=k))
    lines.append("")

    lines.extend(blocks_section(trials))
    lines.append("")

    lines.append("## Task success, adherence and cost")
    lines.append("")
    lines.extend(contrast_table(table, results,
                                ("task_success", "install", "adherence",
                                 "output_tokens", "turns", "wall_seconds",
                                 "cost_usd"), active=active, blocks=k))
    lines.append("")

    lines.append("## The change task")
    lines.append("")
    lines.append("How far each design had to be disturbed to take a change it "
                 "was not built for, read beside whether the change works and "
                 "whether the build still passes after it.")
    lines.append("")
    lines.extend(contrast_table(table, results, CHANGE, active=active,
                                blocks=k))
    lines.append("")

    lines.append("## Every other metric")
    lines.append("")
    rest = [key for key, _, _, _ in METRICS
            if key not in PRIMARY and key not in CHANGE and key not in
            ("task_success", "install", "adherence", "output_tokens", "turns",
             "wall_seconds", "cost_usd")]
    lines.extend(contrast_table(table, results, rest, active=active,
                                blocks=k))
    lines.append("")

    if is_round5(trials) and not later_rules_of(trials):
        lines.extend(round5_section(trials, table, results))
        lines.append("")
    if is_round5d(trials):
        lines.extend(round5d_section(trials, table, results, seed,
                                     margins_of(trials)))
        lines.append("")
    if is_round5e(trials):
        lines.extend(round5e_section(root, trials, table, results, seed,
                                     margins_of(trials), uses))
        lines.append("")

    lines.append("## Raw numbers, per trial")
    lines.append("")
    lines.append("| Metric | %s |" % " | ".join(names))
    lines.append("|---|%s" % ("---|" * len(names)))
    for key, label, direction, _ in METRICS:
        row = table[key]["values"]
        cells = [number(row.get(arm_of(name), {}).get(index_of(name)))
                 for name in names]
        lines.append("| %s | %s |" % (label, " | ".join(cells)))
    lines.append("")

    lines.append("## Trials, and what was measured on them")
    lines.append("")
    lines.append("| Trial | Outcome | Metrics flagged as not measured |")
    lines.append("|---|---|---|")
    for name in names:
        scores = trials[name]["scores"]
        flagged = scores.get("flagged") or []
        lines.append("| %s | %s | %s |"
                     % (name,
                        (scores.get("cost") or {}).get("value", {})
                        .get("outcome", "unknown")
                        if (scores.get("cost") or {}).get("value") else
                        "no cost record",
                        ", ".join(flagged) if flagged else "none"))
    lines.append("")

    lines.append("## Trials lost to the provider or the harness")
    lines.append("")
    if not lost:
        lines.append("None: no trial was voided.")
    else:
        lines.append("Each was voided and re-run once in its own place, as "
                     "registered before the run. A voided workspace is kept "
                     "and never scored.")
        lines.append("")
        lines.append("| Trial | Started | Why | Kept at | Re-run |")
        lines.append("|---|---|---|---|---|")
        for entry in lost:
            reason = " ".join((entry["reason"] or "—").split())
            lines.append("| %s | %s | %s | %s | %s |"
                         % (entry["name"], entry["started_at"] or "—",
                            reason.replace("|", "/")[:160],
                            "`%s`" % entry["kept"] if entry["kept"]
                            else "not moved",
                            entry["rerun"] or "not re-run"))
    lines.append("")

    lines.extend(reach_section(root, scans))
    lines.append("")

    lines.append("## The judge, and how it is checked")
    lines.append("")
    lines.append("| Trial | Blind id | Evidence lines found in the tree |")
    lines.append("|---|---|---|")
    for name in names:
        judging = trials[name]["judge"]
        if not readings(trials[name]):
            failed = path(trials[name], "scores", "install",
                          "value") is False
            lines.append("| %s | — | %s |" % (
                name, "its build did not install" if failed
                else "not judged"))
            continue
        share = path(judging, "evidence", "share")
        lines.append("| %s | %s | %s |"
                     % (name, judging.get("blind_id"),
                        "%.0f%%" % (100 * share) if share is not None
                        else "—"))
    lines.append("")
    lines.append("No person scores the judge. Each score it gives quotes an "
                 "evidence line, and the share of those lines found in the "
                 "tree they were quoted from is one check on it; the other "
                 "vendor's judge, below, is the second.")
    lines.append("")
    lines.extend(cross_check_section(cross))
    lines.append("")

    lines.extend(["## Verdict vector", ""])
    lines.extend(vector_lines(results, active))
    lines.append("")

    os.makedirs(out_dir, exist_ok=True)
    width = markdown_width()
    documents = {
        record: lines,
        appendix: appendix_lines(trials, table, results, k, seed, generation,
                                 report, record, iso),
        report: plain_report_lines(root, trials, table, results, radar,
                                   appendix, k, iso)}
    for document, text in documents.items():
        with io.open(os.path.join(out_dir, document), "w", encoding="utf-8",
                     newline="\n") as handle:
            handle.write(report_text(text, width))
    return os.path.join(out_dir, report)


def posthoc_rules_reading(trials, seed, withdrawn=None, check=None):
    """An earlier round's table and contrasts read by round 5d's rules,
    with withdrawn metrics blanked and the cross-check's disagreements
    withheld, as the registered reading has them."""
    table = collect(trials, later_rules=True)
    results = contrasts(table, seed, crossed_labels(trials), ROUND5D_MARGINS,
                        True)
    withdraw(withdrawn or {}, table, results)
    if check:
        disagree(results, check)
    return table, results


def write_posthoc_rules(trials, table, results, seed, out_dir):
    """The post-hoc page beside an earlier round's report: its trials read
    by round 5d's rules, with a radar by size. Returns its path."""
    stem = "%s-efficacy-posthoc" % datetime.date.today().isoformat()
    active = active_contrasts(trials)
    os.makedirs(out_dir, exist_ok=True)
    radar = {}
    panels = radar_panels(table, results, active)
    for theme in RADAR_THEMES if panels else ():
        image = "%s-radar-%s.svg" % (stem, theme)
        with io.open(os.path.join(out_dir, image), "w", encoding="utf-8",
                     newline="\n") as handle:
            handle.write(radar_svg(panels, theme))
        radar[theme] = image
    arms = by_cost(table, [pair[0] for pair in active if pair[1] == BARE])
    lines = ["# Efficacy benchmark — %s, a post-hoc reading"
             % datetime.date.today().isoformat(), "",
             "**Post-hoc.** These rules were registered for round 5d, after "
             "this round ran. The round's registered verdicts stand; this page "
             "shows how its trials read under the later rules, and decides "
             "nothing.", ""]
    for theme, image in sorted(radar.items()):
        lines.append("![Radar per arm, post-hoc](%s#gh-%s-mode-only)"
                     % (image, theme))
    if radar:
        lines.extend(["", RADAR_SIZE_READING, ""])
    lines.extend(radar_table(results, arms))
    lines.extend(["", "## Each arm against `%s`, post-hoc" % BARE, ""])
    for arm in arms:
        lines.append("- `%s`: %s" % (arm, "; ".join(
            "%s %s" % (axis, word)
            for axis, word in profile(results, "%s-%s" % (arm, BARE)))))
    lines.append("")
    lines.extend(round5d_section(
        trials, table, results, seed, ROUND5D_MARGINS, ROUND5_HYPOTHESES,
        "## The round's questions, read post-hoc"))

    # Every reading above rests on a row printed below: the rows each
    # question decides on, and each radar axis's rows against the bare arm.
    k = max((index_of(name) for name in trials), default=0)
    asked = [tuple(label.split("-")) for _, label, _ in ROUND5_HYPOTHESES
             if tuple(label.split("-")) in active]
    lines.extend(["", "## The numbers behind it, post-hoc", "",
                  "Each cell reads by the later rules, on working builds "
                  "where the row says so. %s" % CONTRAST_LEGEND, "",
                  DEGENERATE_NOTE.replace("`aggregate.json`",
                                          "`aggregate-posthoc.json`"),
                  "", "### The rows the questions decide on",
                  ""])
    lines.extend(contrast_table(table, results,
                                ROUND5D_ROWS + ("reliability",),
                                active=asked, blocks=k, legend=False))
    against = [pair for pair in active if pair[1] == BARE]
    for axis, keys in ROUND5D_RADAR_AXES:
        lines.extend(["", "### %s" % axis, ""])
        lines.extend(contrast_table(table, results, keys, active=against,
                                    blocks=k, legend=False))
    target = os.path.join(out_dir, stem + ".md")
    with io.open(target, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(report_text(lines, markdown_width()))
    return target


def provenance_lines(trials, names, arms, k, seed, generation):
    """What produced a round's numbers, as a table: the trials, the models,
    the blinding, the revisions, the bootstrap and each generated file."""
    any_scores = trials[names[0]]["scores"] if names else {}
    lines = []
    lines.append("| | |")
    lines.append("|---|---|")
    lines.append("| Trials | %d, arms %s, K = %d |"
                 % (len(names), ", ".join(arms), k))
    lines.append("| Generator | `%s` |" % any_scores.get("model", "unknown"))
    judgings = [t["judge"] for t in trials.values() if t["judge"]]
    if judgings:
        lines.append("| Judge | `%s` at effort `%s`, %s |"
                     % (judgings[0].get("model"), judgings[0].get("effort"),
                        judgings[0].get("cli")))
        lines.append("| Blinding | condition markers stripped, order shuffled "
                     "at seed %s |" % judgings[0].get("seed"))

        # One judging of a tree is not reproducible, so a contrast is computed
        # from the mean of several and the report says how many it had. A
        # round that judged unevenly says so rather than averaging the fact
        # away.
        counts = sorted({len(readings(trial)) for trial in trials.values()
                         if readings(trial)})
        lines.append("| Judgings per trial | %s, meaned |"
                     % (counts[0] if len(counts) == 1
                        else "%d to %d, uneven" % (counts[0], counts[-1])))
    else:
        lines.append("| Judge | not run |")
    # A trial's record names the benchmark tree that ran it under the key
    # `templates_tree`, from when the benchmark lived in the templates
    # repository; the templates an arm was made from are its generation
    # record's, in the arm rows below.
    for label, key in (("Benchmark revision, per trial", "templates_tree"),
                       ("Hidden suite", "suite_revision")):
        seen = sorted({str(trial["scores"].get(key) or "unknown")
                       for trial in trials.values()}) or ["unknown"]
        lines.append("| %s | %s |" % (label, ", ".join(
            "`%s`" % value for value in seen)))
    lines.append("| Bootstrap | %d resamples, %d%%, seed %s |"
                 % (RESAMPLES, int(100 * CONFIDENCE), seed))
    for arm in arms:
        if arm not in GENERATED:
            continue
        record = generation.get(arm)
        if record:
            made_from = (record.get("commit") or record.get("ref")
                         or "unknown")[:8]
            lines.append("| Arm %s's file | generated %s from the templates "
                         "at `%s`, %s lines, leak scan: %s |"
                         % (arm, record.get("started_at", "unknown"),
                            made_from, record.get("output_lines", "?"),
                            "clean" if not (record.get("output_leak") or {})
                            .get("hits") else "HITS"))
        else:
            lines.append("| Arm %s's file | no generation record beside it |"
                         % arm)
    return lines


def vector_lines(results, active):
    """The verdict vector: every metric's verdict in every contrast."""
    lines = ["The whole vector, which the summary's scores digest and never "
             "replace.", ""]
    header = ["%s−%s" % pair for pair in active]
    lines.append("| Metric | %s |" % " | ".join(header))
    lines.append("|---|%s" % ("---|" * len(header)))
    for key, label, direction, _ in METRICS:
        cells = [results[key]["%s-%s" % pair]["verdict"] for pair in active]
        lines.append("| %s | %s |" % (label, " | ".join(cells)))
    return lines


# Each approach as a reader knows it, in plain words.
PLAIN_ARMS = {
    "none": "no rules file: the AI gets only the specification",
    "reference": "a short file that points the AI to the templates, which "
                 "it reads itself",
    "inline": "every rule of the templates copied into one file",
    "hybrid": "the most important rules copied in, the rest pointed to",
    "skills": "a root file plus one skill per kind of task",
    "hand": "a short file a person wrote",
    "short": "the templates' rules cut down to 40 lines",
    "lazyref": "a short file that maps each kind of work to the template to "
               "read when that work starts",
    "lazyskills": "the same map, each template loaded as a skill when that "
                  "work starts",
}

# Each radar axis in plain words, as a sentence names it.
PLAIN_AXES = {
    "Reliability": "reliability",
    "Security": "security",
    "Data protection": "data protection",
    "Design": "design",
    "Maintainability": "maintainability",
    "Tests": "the tests it wrote",
    "Economy": "cost and time",
}

# The measures that decide a verdict, in plain words.
PLAIN_DECIDING = {
    "judge_design": "the AI judge's design score",
    "judge_readability": "the AI judge's readability score",
    "judge_maintainability": "the AI judge's maintainability score",
    "judge_security": "the AI judge's security score",
    "judge_data_protection": "the AI judge's data-protection score",
    "security_probe_pass_rate": "the security checks",
    "data_protection_probe_pass_rate": "the data-protection checks",
    "task_success": "the hidden tests",
}

# What the verdict looks at, said once above the approaches.
PLAIN_VERDICT_RULE = (
    "Each verdict looks only at the measures chosen before the run to decide "
    "it: the hidden tests, the security and data-protection checks, and the "
    "AI judge's scores for design, readability, maintainability, security "
    "and data protection. One of them clearly worse makes the verdict "
    "worse, whatever the rest gained.")

# Round 5's questions, as a reader would ask them.
PLAIN_QUESTIONS = {
    "skills-hybrid": "Does the skills approach do as well as the hybrid "
                     "file?",
    "reference-hybrid": "Does a file that only points to the templates do "
                        "worse than the hybrid file?",
    "hand-none": "Does a person's short file do better than no file?",
    "inline-hand": "Does the inline file do as well as a person's file?",
    "hybrid-hand": "Does the hybrid file do as well as a person's file?",
    "reference-hand": "Does the reference file do as well as a person's "
                      "file?",
    "skills-hand": "Does the skills approach do as well as a person's file?",
    "short-hand": "Does a 40-line file from the templates do as well as a "
                  "person's file of the same length?",
    "lazyref-reference": "Does a template read when the work touches its "
                         "topics do as well as the same template read "
                         "before the work starts?",
    "lazyskills-lazyref": "Does loading a template as a skill do as well as "
                          "reading it as a file, at the same moments?",
    "lazyskills-skills": "Do templates loaded whole as skills, at a named "
                         "moment, do as well as task skills offered by "
                         "description?",
}
PLAIN_ANSWERS = {"supported": "yes", "refuted": "no",
                 "inconclusive": "not settled: the runs could not tell "
                                 "either way"}


def consistency_reading(trials):
    """Round 5's consistency hypothesis: whether the skills arm's trials
    agree with each other at least as much as the hybrid arm's."""
    hybrid, _ = conventions_agreement(trials, "hybrid")
    skills, _ = conventions_agreement(trials, "skills")
    if hybrid is None or skills is None:
        return "not computed"
    if skills >= hybrid:
        return "supported"
    if hybrid - skills >= 0.15:
        return "refuted"
    return "inconclusive"


def iso_axis_moves(iso, name):
    """Each ISO axis's move for one contrast, in the radar's order, as
    the markers read it: +1 better, -1 worse, 0 within the margin, None
    where it could not be read; the shape the plain words follow."""
    moves = []
    for axis, _ in ISO_AXES:
        marker = iso_marker(iso[1].get("iso:" + axis, {}).get(name, {}))
        moves.append((axis, {"better": 1.0, "worse": -1.0,
                             "dot": 0.0}.get(marker)))
    return moves


def plain_arm_lines(trials, table, results, arm, length, iso=None):
    """One approach against the bare arm, in plain words: what it did
    better, what it did worse with the numbers a reader would ask for, and
    its verdict. With `iso`, the axes are the ISO radar's, as its markers
    read them, and the cost gets a line of its own."""
    name = "%s-%s" % (arm, BARE)
    scores = (iso_axis_moves(iso, name) if iso
              else cluster_scores(results, name))
    verdict = answer([results[key][name]["verdict"] for key in ANSWERED])
    better = [PLAIN_AXES.get(axis, axis.lower()) for axis, value in scores
              if value is not None and value > 0]
    # The runs that fell short are counted whatever the reliability axis
    # reads, because one broken build among many can leave it neutral.
    low = low_runs(table, arm)
    errors, count = boot_failures(trials, arm)
    shortfall = []
    if low:
        shortfall.append("%d of %d runs passed clearly fewer of the hidden "
                         "tests" % (len(low), count))
    if errors:
        shortfall.append("%d %s because the app would not start after a "
                         "clean install" % (len(errors), "of them" if low
                                            else "runs"))
    worse = []
    noted = False
    for axis, value in scores:
        if value is None or value >= 0:
            continue
        if axis == "Reliability":
            worse.append("reliability (%s)" % ", ".join(shortfall)
                         if shortfall else "reliability")
            noted = True
        elif axis == "Economy":
            mean = arm_mean(table, "cost_usd", arm)
            bare = arm_mean(table, "cost_usd", BARE)
            worse.append("cost and time (about $%.2f a run, against $%.2f "
                         "with no rules file)" % (mean, bare)
                         if mean is not None and bare is not None
                         else "cost and time")
        else:
            worse.append(PLAIN_AXES.get(axis, axis.lower()))
    size = ("%s lines" % format(length, ",")) if length else "no file"
    lines = ["### `%s`" % arm, "",
             "%s (%s)." % (sentence_case(PLAIN_ARMS.get(
                 arm, ARMS[arm]["label"])), size), ""]
    lines.append("- Better than no rules file at: %s."
                 % (spoken(better) if better else "nothing clearly"))
    lines.append("- Worse at: %s." % ("; ".join(worse) if worse
                                      else "nothing clearly"))

    # Cost is shown beside the ISO radar and not scored on it, so it gets a
    # line of its own rather than an axis.
    if iso:
        mean = arm_mean(table, "cost_usd", arm)
        bare = arm_mean(table, "cost_usd", BARE)
        lines.append("- Cost: %s." % (
            "about $%.2f a run, against $%.2f with no rules file"
            % (mean, bare) if mean is not None and bare is not None
            else NOT_MEASURED))
    if shortfall and not noted:
        lines.append("- Noted, though reliability was not clearly worse "
                     "overall: %s." % ", ".join(shortfall))
    lines.extend(["", plain_verdict(results, name, verdict)])
    return lines


def plain_verdict(results, name, verdict):
    """A verdict in plain words, naming the deciding measures behind it."""
    def moved(direction):
        return [PLAIN_DECIDING[key] for key in ANSWERED
                if results[key][name]["verdict"] == direction]
    if verdict == "Worse":
        return "**Verdict: worse**, because of %s." % spoken(moved("worse"))
    if verdict == "Yes":
        return ("**Verdict: better**, on %s, with none of the deciding "
                "measures worse." % spoken(moved("better")))
    if verdict == "No":
        return ("**Verdict: no clear gain.** None of the deciding measures "
                "moved clearly.")
    if any(results[key][name]["verdict"] == CROSSING_VERDICT
           for key in ANSWERED):
        return ("**Verdict: not given.** Its runs come from an earlier round, "
                "and comparing them with this round's would mix two rounds.")
    return "**Verdict: not measured.** Too few runs were scored to compare it."


def sentence_case(text):
    """Text with its first letter capital and the rest as written."""
    return text[:1].upper() + text[1:]


# Said wherever an interval is shown from fewer blocks than can decide.
DESCRIPTIVE_NOTE = ("**Every interval below is descriptive.** At K = %d no "
                    "arrangement of paired differences reaches conventional "
                    "significance, so no difference here is established.")


def runs_per_arm(trials):
    """How many scored runs each arm has, in the arms' declared order."""
    counts = {}
    for name in trials:
        counts[arm_of(name)] = counts.get(arm_of(name), 0) + 1
    return {arm: counts[arm] for arm in ARMS if arm in counts}


def times(runs, arms):
    """How many times the arms ran, as a sentence says it: 15 times, or
    between 12 and 15 times where they differ."""
    counts = sorted({runs[arm] for arm in arms if arm in runs})
    if not counts:
        return "no times"
    if len(counts) == 1:
        return "%d %s" % (counts[0], "time" if counts[0] == 1 else "times")
    return "between %d and %d times" % (counts[0], counts[-1])


def sureness_lines(trials, k):
    """The qualifications the full record states, in plain words: a round
    too small to decide anything, and a round not yet complete."""
    lines = []
    if k < FEWEST_DECIDING:
        lines.append("- With only %d runs per approach, no difference here can "
                     "be called established. Read every result as a hint."
                     % k)
    owed = owed_blocks(trials)
    if owed:
        lines.append("- The round is not complete: %s still miss a run, so "
                     "every answer here is provisional." % blocks_named(owed))
    return lines


def plain_report_lines(root, trials, table, results, radar, appendix, k,
                       iso=None):
    """The report a reader opens: the radars, each approach in plain words,
    the round's questions answered, and how sure the answers are. `iso` is
    the ISO reading where the round draws that radar."""
    names = ordered(trials)
    active = active_contrasts(trials)
    arms = by_cost(table, [pair[0] for pair in active if pair[1] == BARE])
    judgings = [trial["judge"] for trial in trials.values() if trial["judge"]]
    model = next((trial["scores"].get("model") for trial in trials.values()
                  if trial["scores"].get("model")), "unknown")
    runs = runs_per_arm(trials)
    lines = ["# Efficacy benchmark — %s" % datetime.date.today().isoformat(),
             "",
             "We asked an AI to build the same small web app %s with each "
             "approach to giving it our templates, and %s with no rules file "
             "at all (`%s`). Each radar compares one approach with `%s`."
             % (times(runs, [arm for arm in runs if arm != BARE]),
                times(runs, [BARE]), BARE, BARE), ""]
    if radar:
        for theme, image in sorted(radar.items()):
            lines.append("![Radar per approach](%s#gh-%s-mode-only)"
                         % (image, theme))
        lines.append("")
    lines.extend([ISO_PLAIN_READING if iso else
                  "How to read it: the dashed ring is `%s`. A point outside "
                  "the ring means the approach did better on that axis, "
                  "inside it means worse. Each axis groups several "
                  "measurements; the appendix lists them." % BARE, "",
                  "## Each approach", "", PLAIN_VERDICT_RULE, ""])
    for arm in arms:
        lines.extend(plain_arm_lines(trials, table, results, arm,
                                     context_lines(arm), iso))
        lines.append("")
    present = {arm_of(name) for name in trials}
    if later_rules_of(trials):
        # The latest round's questions are the run's: a round-5e root
        # holds round 5d's arms too, reused, and answers its own.
        hypotheses = (ROUND5E_HYPOTHESES if is_round5e(trials)
                      else ROUND5D_HYPOTHESES)
        lines.extend(["## The questions this round asked", ""])
        for _, label, wanted in hypotheses:
            if not set(label.split("-")) <= present:
                continue
            state, _ = round5d_hypothesis(results, label, wanted)
            lines.append("- %s **%s.**" % (PLAIN_QUESTIONS[label],
                                           sentence_case(PLAIN_ANSWERS[state])))
        lines.append("")
    elif is_round5(trials):
        lines.extend(["## The questions this round asked", ""])
        for _, label, wanted in ROUND5_HYPOTHESES:
            state, _ = hypothesis(results, label, wanted)
            lines.append("- %s **%s.**" % (PLAIN_QUESTIONS[label],
                                           sentence_case(PLAIN_ANSWERS[state])))
        state = consistency_reading(trials)
        lines.append("- Are the skills approach's runs at least as alike "
                     "each other as the hybrid file's? **%s.**"
                     % sentence_case(PLAIN_ANSWERS.get(state, state)))
        lines.append("")
    lines.extend(["## How sure we are", ""])
    lines.extend(sureness_lines(trials, k))
    lines.extend([
        "- Each approach ran %s on one small web app, built by one AI "
        "model, `%s`." % (times(runs, list(runs)), model),
        "- Automatic tests and tools measured most of it. %s"
        % ("Another AI, `%s`, read the code and scored its design, security "
           "and tests." % judgings[0].get("model") if judgings
           else "No AI read the code this round."),
        "- A difference counts only when it shows clearly across the runs. "
        "Small or mixed differences count as none."])
    lines.extend(rerun_lines(lost_trials(root)))
    lines.extend([
        "- %d runs were scored in all." % len(names), "",
        "Every number behind this page is in the [technical appendix](%s)."
        % appendix])
    return lines


def rerun_lines(lost):
    """What happened to the runs that were stopped, in plain words: those run
    again, and those still missing."""
    redone = sum(1 for entry in lost if entry.get("rerun"))
    pending = len(lost) - redone
    if not lost:
        return ["- No run had to be run again."]
    lines = []
    if redone:
        lines.append("- %d %s stopped part-way, for example by a usage "
                     "limit, and run again from the start. Only complete "
                     "runs count." % (redone, "run was" if redone == 1
                                      else "runs were"))
    if pending:
        lines.append("- %d stopped %s not been run again yet, so %s missing."
                     % (pending, "runs have" if pending != 1 else "run has",
                        "they are" if pending != 1 else "it is"))
    return lines


def appendix_lines(trials, table, results, k, seed, generation, report,
                   record, iso=None):
    """The technical appendix: what produced the results, the radar's axes
    row by row, and the verdict vector. `iso` is the ISO reading where the
    round draws that radar, whose axes come as tables of sub-scores."""
    names = ordered(trials)
    arms = [arm for arm in ARMS if arm in {arm_of(name) for name in names}]
    active = active_contrasts(trials)
    against = [pair for pair in active if pair[1] == BARE]
    lines = ["# Efficacy benchmark — %s, technical appendix"
             % datetime.date.today().isoformat(), "",
             "The numbers behind [the report](%s). Everything else, trial by "
             "trial, is in [the full record](%s)." % (report, record), ""]
    if k < FEWEST_DECIDING:
        lines.extend([DESCRIPTIVE_NOTE % k, ""])
    lines.extend(["## What produced the results", ""])
    lines.extend(provenance_lines(trials, names, arms, k, seed, generation))
    if iso:
        lines.extend(["", "## The radar's axes, row by row", "",
                      ISO_TABLE_READING, "", DEGENERATE_NOTE, ""])
        lines.extend(iso_axis_lines(trials, iso[0],
                                    [BARE] + by_cost(table, [
                                        pair[0] for pair in against]),
                                    iso[1], iso[2], k))
    else:
        lines.extend(["", "## The radar's axes, row by row", "",
                      "Each table is one axis of the radar: every "
                      "measurement it groups, each approach's mean, and each "
                      "approach against `%s`. %s" % (BARE, CONTRAST_LEGEND),
                      "", DEGENERATE_NOTE, ""])
        for axis, keys in radar_axes(results):
            lines.extend(["### %s" % axis, ""])
            lines.extend(contrast_table(table, results, keys, active=against,
                                        blocks=k, legend=False))
            lines.append("")
    lines.extend(["## The verdict vector", ""])
    lines.extend(vector_lines(results, active))
    return lines


def report_text(lines, width):
    """The report's lines as one text, wrapped to `width`, ending in exactly
    one newline."""

    # Sections each end in a blank line, so the last one would leave two
    # blank lines at the end of the file, which the templates' Markdown lint
    # refuses.
    return "\n".join(wrap_prose(lines, width)).rstrip("\n") + "\n"


def markdown_width():
    """The Markdown line width the repository declares."""
    with io.open(os.path.join(lib.ROOT, ".markdownlint.json"),
                 encoding="utf-8") as handle:
        return json.load(handle)["MD013"]["line_length"]


def wrap_prose(lines, width):
    """Each prose line wrapped to `width`; tables and headings left whole.

    The report lands among the repository's documents, whose width check
    reads every tracked Markdown file. A table row cannot wrap without
    breaking its table, and that check exempts rows and headings.
    """
    wrapped = []
    for line in lines:
        if len(line) <= width or line.startswith(("|", "#")):
            wrapped.append(line)
            continue

        # A list item's continuation is indented, so it stays in the item.
        indent = "  " if line.startswith("- ") else ""
        wrapped.extend(textwrap.wrap(line, width, subsequent_indent=indent,
                                     break_long_words=False,
                                     break_on_hyphens=False))
    return wrapped


def spoken(names):
    """Names as a sentence lists them: a, b and c."""
    return names[0] if len(names) == 1 else "%s and %s" % (
        ", ".join(names[:-1]), names[-1])


def score(wins, fails):
    """1 to 10: 1 where a side lost every metric that separated the pair,
    10 where it won every one, None where no metric separated them."""
    if not wins + fails:
        return None
    return round(1 + 9 * wins / (wins + fails), 1)


# The metrics the finding table answers from, and the words it uses.
ANSWERED = PRIMARY + ("task_success",)
SHORT = {"judge_design": "design", "judge_readability": "readability",
         "judge_maintainability": "maintainability",
         "judge_security": "security",
         "judge_data_protection": "data protection",
         "task_success": "task success",
         "security_probe_pass_rate": "security probes",
         "data_protection_probe_pass_rate": "data-protection probes"}

# The arm every file arm is read against: the bare agent.
BARE = "none"

COUNTED = ("no", "one", "two", "three", "four", "five")
NOT_MEASURED = "not measured"

# A run whose hidden-suite pass rate sits under the bare arm's mean by more
# than this is named in the finding table. It is the smallest change that
# matters for task success, as registered; nothing else reads it.
SUITE_DIP = 0.05


# Round 5's hypotheses, as registered: the primary rows H1 and H3 read, and
# the contrast each reads them on. H1 is supported when every row is held or
# better; H3 when any row is worse, and refuted, which reopens the decision
# that hybrid is the delivery floor, when every row is held or better.
ROUND5_ROWS = ("adherence",) + PROBE_RATES + ("judge_security",
                                              "judge_data_protection")

# Round 5d's primary rows are outcomes. Adherence scores the templates' own
# checklist, which only the templates arms were given, so it shows whether
# the rules arrived and decides nothing; the hidden tests decide instead.
ROUND5D_ROWS = ("task_success",) + PROBE_RATES + ("judge_security",
                                                  "judge_data_protection")
ROUND5_HYPOTHESES = (
    ("H1, skills deliver what hybrid does", "skills-hybrid", "held"),
    ("H3, a reference alone delivers less", "reference-hybrid", "worse"),
)


def conventions_agreement(trials, arm):
    """The conventions agreement for one arm, and the pairs it means: for
    each pair of the arm's trials, the share of the adherence items both
    measured on which the two give the same verdict. None with fewer than
    two trials or no pair measuring an item in common."""

    # A mean over pairs keeps its expected value as trials are added, so its
    # bar means the same at any K. The share every trial agrees on can only
    # fall with each trial added.
    sets = [path(trial, "scores", "adherence", "items") or {}
            for name, trial in trials.items() if arm_of(name) == arm]
    shares = []
    for left, right in itertools.combinations(sets, 2):
        common = [item for item in left if left[item] is not None
                  and right.get(item) is not None]
        if common:
            shares.append(sum(1 for item in common
                              if left[item] == right[item]) / len(common))
    if not shares:
        return None, 0
    return round(statistics.fmean(shares), 3), len(shares)


def jaccard(left, right):
    """The Jaccard similarity of two sets; two empty sets agree fully."""
    if not left and not right:
        return 1.0
    return len(left & right) / len(left | right)


def pairwise_agreement(sets):
    """The pairwise agreement: the mean Jaccard similarity over
    every pair of an arm's trials. None with fewer than two."""
    pairs = [jaccard(a, b) for a, b in itertools.combinations(sets, 2)]
    return round(statistics.fmean(pairs), 3) if pairs else None


def structure_sets(trials, arm):
    """Each of an arm's trials' Python file paths, where scoring recorded
    them; a trial without the record is left out."""
    found = []
    for name, trial in trials.items():
        if arm_of(name) != arm:
            continue
        files = metric_value(trial, "python_files")
        if files is not None:
            found.append(set(files))
    return found


def security_sets(trials, arm):
    """Each of an arm's trials' failed security and data-protection probes;
    a trial with a probe left unmeasured is left out, since its set would
    be incomplete."""
    found = []
    for name, trial in trials.items():
        if arm_of(name) != arm:
            continue
        probes = path(trial, "security", "probes")
        if not probes or any(probe.get("passed") is None
                             for probe in probes.values()):
            continue
        found.append({probe for probe, result in probes.items()
                      if result.get("passed") is False})
    return found


def row_outcome(contrast):
    """One row of a hypothesis: worse, held (better counts as held) or
    open, from a contrast's verdict and non-inferiority."""
    if contrast is None or contrast.get("verdict") in ("not computed",
                                                        CROSSING_VERDICT):
        return "open"
    if contrast["verdict"] == "worse":
        return "worse"
    if contrast["verdict"] == "better":
        return "held"
    held = contrast.get("non_inferior") or {}
    return "held" if held.get("within") else "open"


def hypothesis(results, label, wanted):
    """A round-5 hypothesis's reading in this block: supported, refuted or
    inconclusive, with the row outcomes it rests on."""
    rows = {key: row_outcome(results.get(key, {}).get(label))
            for key in ROUND5_ROWS}
    outcomes = set(rows.values())
    if wanted == "held":
        state = ("refuted" if "worse" in outcomes
                 else "supported" if outcomes == {"held"} else "inconclusive")
    else:
        state = ("supported" if "worse" in outcomes
                 else "refuted" if outcomes == {"held"} else "inconclusive")
    return state, rows


def context_words(arm):
    """The words an arm's trials read on every turn: its context file, and
    for the skills arm its root file alone. None where it receives none."""
    context = ARMS[arm]["context"]
    if not context:
        return None
    with io.open(os.path.join(ARMS_DIR, context), encoding="utf-8") as handle:
        return len(handle.read().split())


def round5_section(trials, table, results):
    """Round 5's answer: each arm's size, agreement and worst trial, and
    each hypothesis's reading."""
    present = {arm_of(name) for name in trials}
    arms = [arm for arm in ("none", "reference", "inline", "hybrid",
                            "skills") if arm in present]
    lines = ["## Round 5: how the rules are delivered", "",
             "Agreement is a mean over pairs of an arm's trials: conventions "
             "as the share of the adherence items both measured on which "
             "they agree, structure and security as the Jaccard similarity "
             "of their Python files and of the probes they fail. A dash is "
             "not computed. Adherence is held within %s, one checklist item."
             % ROUND5_MARGINS["adherence"][0],
             "",
             "| Arm | Words every turn | Conventions agreement (pairs) | "
             "Structure agreement | Security agreement | Task success, "
             "worst | Task success, mean |",
             "| --- | --- | --- | --- | --- | --- | --- |"]

    def shown(value):
        return "—" if value is None else "%.2f" % value
    for arm in arms:
        words = context_words(arm)
        share, items = conventions_agreement(trials, arm)
        values = [value for value in table["task_success"]["values"].get(
            arm, {}).values() if value is not None]
        lines.append("| %s | %s | %s (%d) | %s | %s | %s | %s |" % (
            arm, "—" if words is None else words, shown(share), items,
            shown(pairwise_agreement(structure_sets(trials, arm))),
            shown(pairwise_agreement(security_sets(trials, arm))),
            number(min(values)) if values else "—",
            number(statistics.fmean(values)) if values else "—"))
    lines.append("")
    for name, label, wanted in ROUND5_HYPOTHESES:
        state, rows = hypothesis(results, label, wanted)
        detail = ", ".join("%s %s" % (SHORT.get(key, key), outcome)
                           for key, outcome in rows.items())
        lines.append("- %s, %s: %s (%s)" % (name, label, state, detail))
    h2 = {"not computed": "not computed",
          "supported": "skills agrees at least as much as hybrid",
          "refuted": "refuted: skills agrees less by 0.15 or more",
          "inconclusive": "skills agrees less, by under 0.15"}[
              consistency_reading(trials)]
    lines.append("- H2, consistency: %s" % h2)
    return lines


# Round 5d's hypotheses, as registered: each contrast, and what it needs.
# H4 asks for a gain; H5 and H6 for no loss. Each reads round 5's primary
# rows, and reliability can refute any of them.
ROUND5D_HYPOTHESES = (
    ("H4, a file at all", "hand-none", "better"),
    ("H5, inline against a person's file", "inline-hand", "held"),
    ("H5, hybrid against a person's file", "hybrid-hand", "held"),
    ("H5, reference against a person's file", "reference-hand", "held"),
    ("H5, skills against a person's file", "skills-hand", "held"),
    ("H6, the templates' content at a person's length", "short-hand",
     "held"),
)

# Round 5e's hypotheses, as registered: each asks for no loss, under round
# 5d's rules. H7 and H9 cross rounds and read unpaired; H8 is paired.
ROUND5E_HYPOTHESES = (
    ("H7, on demand against up front", "lazyref-reference", "held"),
    ("H8, a skill against a file", "lazyskills-lazyref", "held"),
    ("H9, one skill per template against one skill per task",
     "lazyskills-skills", "held"),
)

# Each leave-two-out reading takes fewer resamples than the report's
# intervals, so an unpaired contrast's 435 readings stay cheap.
LEAVE_TWO_OUT_RESAMPLES = 2000


def row_reading(contrast):
    """One primary row of a round-5d hypothesis: better, held, worse or
    open."""
    verdict = (contrast or {}).get("verdict")
    return verdict if verdict in ("better", "held", "worse") else "open"


def round5d_hypothesis(results, label, wanted):
    """A round-5d hypothesis's reading, supported, refuted or inconclusive,
    with the row readings it rests on, reliability's among them."""

    # At K = 15 reliability's interval is too wide to show it held, so it
    # can refute a hypothesis and never has to hold for one.
    rows = {key: row_reading(results.get(key, {}).get(label))
            for key in ROUND5D_ROWS}
    reliability = row_reading(results.get("reliability", {}).get(label))
    outcomes = set(rows.values())

    # A hypothesis that predicts a loss, as round 5's H3 does, is supported
    # by the loss that refutes the others, reliability's among them.
    if wanted == "worse":
        state = ("supported" if "worse" in outcomes or reliability == "worse"
                 else "refuted" if outcomes <= {"better", "held"}
                 else "inconclusive")
    elif "worse" in outcomes or reliability == "worse":
        state = "refuted"
    elif wanted == "better":
        state = "supported" if "better" in outcomes else "inconclusive"
    else:
        state = ("supported" if outcomes <= {"better", "held"}
                 else "inconclusive")
    rows["reliability"] = reliability
    return state, rows


def without_trials(table, keys, dropped):
    """The rows `keys` of `table`, with the trials in `dropped`, each an
    (arm, block), left out."""
    return {key: dict(table[key], values={
        arm: {index: value for index, value in values.items()
              if (arm, index) not in dropped}
        for arm, values in table[key]["values"].items()})
        for key in keys if key in table}


def leave_two_out(table, label, wanted, seed, margins, results=None,
                  unpaired=False):
    """Robust where the hypothesis reads the same with every two blocks left
    out, or with every two trials where the contrast is `unpaired`; fragile
    where any such reading differs; None where it was not read. A verdict
    `results` withholds stays withheld in every reading."""
    keys = ROUND5D_ROWS + ("reliability",)
    crossed = (label,) if unpaired else ()
    withheld = {key: (results or {}).get(key, {}).get(label, {}).get(
        "verdict") for key in keys}
    withheld = {key: verdict for key, verdict in withheld.items()
                if verdict and verdict.startswith("no verdict")}

    def read(dropped):
        reading = contrasts(without_trials(table, keys, dropped), seed,
                            crossed, margins, True, LEAVE_TWO_OUT_RESAMPLES,
                            (label,))
        for key, verdict in withheld.items():
            reading[key][label]["verdict"] = verdict
        return round5d_hypothesis(reading, label, wanted)[0]

    # The reading every drop is compared with is the one the report prints,
    # at its full resamples, not one recomputed at fewer.
    state = (round5d_hypothesis(results, label, wanted)[0] if results
             else read(()))
    treatment, baseline = label.split("-")
    held = {(arm, index) for key in keys if key in table
            for arm in (treatment, baseline)
            for index in table[key]["values"].get(arm, {})}

    # Paired, a block drops both arms' trials; unpaired, any two trials of
    # the two arms drop, the 435 pairs of thirty.
    if unpaired:
        units = [frozenset([trial]) for trial in sorted(held)]
    else:
        units = [frozenset(trial for trial in held if trial[1] == block)
                 for block in sorted({index for _, index in held})]
    if len(units) < 3:
        return None
    for first, second in itertools.combinations(units, 2):
        if read(first | second) != state:
            return "fragile"
    return "robust"


def axis_word(results, name, keys):
    """One radar axis as the profile reads it: worse where a row is worse
    and none better, better where a row is better and none worse, held where
    every row is held, and by the axis's size where rows went both ways."""
    verdicts = [results[key][name]["verdict"] for key in keys
                if name in results.get(key, {})]
    counted = [verdict for verdict in verdicts
               if verdict in COUNTED_VERDICTS]
    if not counted:
        return "not computed"
    better, worse = "better" in counted, "worse" in counted
    if better and worse:

        # The radar's own rows: a withheld verdict's size counts nowhere.
        sizes = [results[key][name].get("size") for key in keys
                 if name in results.get(key, {})
                 and results[key][name]["verdict"] in COUNTED_VERDICTS]
        sizes = [size for size in sizes if size is not None]
        mean = statistics.fmean(sizes) if sizes else 0.0
        return "better" if mean > 0 else "worse" if mean < 0 else "unsettled"
    if worse:
        return "worse"
    if better:
        return "better"
    return "held" if set(counted) == {"held"} else "unsettled"


def profile(results, name):
    """Each radar axis's word for one contrast, in the radar's order."""
    return [(axis, axis_word(results, name, keys))
            for axis, keys in ROUND5D_RADAR_AXES]


def round5d_section(trials, table, results, seed, margins,
                    hypotheses=ROUND5D_HYPOTHESES,
                    heading="## Round 5d: a person's file and a 40-line file"):
    """Round 5d's answer: each arm's working builds with their exact
    interval, and each hypothesis's reading, confidence and profile."""
    present = {arm_of(name) for name in trials}
    lines = [heading, "",
             "A row is better or worse only where its whole interval lies "
             "past its margin. Task success and the probes are read on "
             "working builds: those that install and boot. Reliability can "
             "refute a hypothesis and never has to hold for one.", "",
             "| Arm | Working builds | 95 % exact interval |",
             "| --- | --- | --- |"]
    for arm in ARMS:
        if arm not in present:
            continue
        values = [value for value in table["reliability"]["values"].get(
            arm, {}).values() if value is not None]
        if not values:
            lines.append("| %s | — | — |" % arm)
            continue
        low, high = clopper_pearson(int(sum(values)), len(values))
        lines.append("| %s | %d of %d | %.2f to %.2f |"
                     % (arm, sum(values), len(values), low, high))
    lines.append("")
    for name, label, wanted in hypotheses:
        if not set(label.split("-")) <= present:
            continue
        state, rows = round5d_hypothesis(results, label, wanted)
        sureness = leave_two_out(
            table, label, wanted, seed, margins, results,
            any(contrast.get("unpaired") for per in results.values()
                for name, contrast in per.items() if name == label))
        detail = ", ".join("%s %s" % (SHORT.get(key, key), outcome)
                           for key, outcome in rows.items())
        lines.append("- %s, %s: %s, %s (%s)" % (
            name, label, state, sureness or "confidence not read", detail))
        lines.append("  - profile: %s" % "; ".join(
            "%s %s" % (axis, word) for axis, word in profile(results, label)))
    return lines


# The tools whose call writes a file of the trial's own, and the shell tools
# whose command may: one is a write where its text redirects, copies, moves
# or creates. A read of the map's templates before the first of them came
# before any work.
WRITES = ("Write", "Edit", "MultiEdit", "NotebookEdit")
SHELLS = ("Bash", "PowerShell")

# A shell command is read one simple command at a time: the text between
# pipes, semicolons, `&&`, `||` and line breaks. The command is its first
# word, after any variable assignments and with any directory and `.exe`
# taken off, so a word that is an argument never counts as a command.
SEGMENT = re.compile(r"\|\||&&|[|;\n]")
ASSIGNMENT = re.compile(r"^[A-Za-z_]\w*=")
WRITE_COMMANDS = ("tee", "touch", "mkdir", "cp", "mv", "new-item",
                  "set-content", "add-content", "out-file", "copy-item",
                  "move-item")
READ_COMMANDS = ("cat", "type", "head", "tail", "sed", "less", "more", "bat",
                 "grep", "rg", "awk", "get-content", "gc", "select-string")
TEMPLATE_PATH = re.compile(re.escape(VENDORED["into"] + "/")
                           + r"(templates/[\w./-]+\.md)")

# A shell operand under the vendored copy that may carry a wildcard, which
# is resolved against the map's templates rather than read as no file.
TEMPLATE_OPERAND = re.compile(re.escape(VENDORED["into"] + "/")
                              + r"(templates/[\w./*?\[\]-]+)")

# A redirection that writes no file: to the null device, or of one stream
# into another. Taken out of a command before it is read for a write.
NULL_REDIRECT = re.compile(
    r"\d?>{1,2}\s*(&\d|/dev/null|\$null|NUL\b)", re.IGNORECASE)

# Quoted text is an argument, not an operator or a command, so it is taken
# out before a command is read for a write.
QUOTED = re.compile(r"'[^']*'|\"[^\"]*\"")


# A here-document's body is data, not commands, and is taken out whole.
HEREDOC = re.compile(r"<<-?\s*(['\"]?)(\w+)\1[^\n]*\n.*?\n\s*\2\s*(?=\n|$)",
                     re.DOTALL)


def simple_commands(command, keep_quotes=False):
    """A shell command's simple commands, each as (command word, text), the
    null redirections and here-document bodies taken out and, unless asked
    to keep them, the quoted arguments too. A separator inside quotes
    separates nothing."""
    quoted = []

    def stash(match):
        quoted.append(match.group(0))
        return "\x00%d\x00" % (len(quoted) - 1)
    masked = QUOTED.sub(stash, NULL_REDIRECT.sub(" ", HEREDOC.sub(
        " ", command)))
    found = []
    for segment in SEGMENT.split(masked):
        segment = re.sub(r"\x00(\d+)\x00", lambda match: (
            quoted[int(match.group(1))] if keep_quotes else " "), segment)
        words = [word for word in segment.split()
                 if not ASSIGNMENT.match(word)]
        if not words:
            continue
        word = words[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
        if word.endswith(".exe"):
            word = word[:-len(".exe")]
        found.append((word, segment))
    return found


def first_writing_command(command):
    """The index of the first simple command that writes a file of the
    trial's own, one that redirects into a file or copies, moves or creates
    one; None where none does."""
    for index, (word, text) in enumerate(simple_commands(command)):
        if word in WRITE_COMMANDS or ">" in text:
            return index
    return None


def shell_writes(command):
    """Whether a shell command writes a file of the trial's own."""
    return first_writing_command(command) is not None


def shell_reads(command, known=()):
    """The templates a shell command reads, as (index of its simple
    command, template) in order: every one a reading command names under
    the vendored copy, a wildcard operand standing for each template of the
    map it matches."""
    found = []
    for index, (word, text) in enumerate(
            simple_commands(command, keep_quotes=True)):
        if word not in READ_COMMANDS:
            continue
        for operand in TEMPLATE_OPERAND.findall(text):
            if any(mark in operand for mark in "*?["):
                found.extend((index, template) for template in known
                             if fnmatch.fnmatchcase(template, operand))
            elif operand.endswith(".md"):
                found.append((index, operand))
    return found


def mapped_templates(arm):
    """What an arm's file points the agent at: the skills it carries, by
    name, or the templates it vendors, by path; empty for an arm with
    neither."""
    entry = ARMS.get(arm) or {}
    if entry.get("skills"):
        folder = os.path.join(ARMS_DIR, entry["skills"])
        return sorted(os.listdir(folder)) if os.path.isdir(folder) else []
    if entry.get("vendor"):
        record = generation_records().get(arm) or {}
        return list(record.get("resolved_files") or [])
    return []


# The tools that hand work to a subagent, whose transcript sits beside the
# session's. What the subagent read or wrote is charged to the turn that
# delegated it.
DELEGATIONS = ("Agent", "Task")


def tool_calls_by_turn(files, written_at=None):
    """Every tool call in the transcripts as (turn, tool, input), a turn
    being one message of the model: several lines may share a message id,
    so a new id is what counts a turn. Given a dict as `written_at`, each
    line's uuid is filed under the turn current once it was written."""
    calls = []
    turn = 0
    last_message = object()
    for file in files:
        with io.open(file, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    record = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(record, dict):
                    continue
                message = record.get("message") or {}
                if record.get("type") == "assistant" \
                        and message.get("id") != last_message:
                    last_message = message.get("id")
                    turn += 1
                if written_at is not None and record.get("uuid"):
                    written_at[record["uuid"]] = turn
                if record.get("type") != "assistant":
                    continue
                content = message.get("content")
                for block in content if isinstance(content, list) else []:
                    if isinstance(block, dict) \
                            and block.get("type") == "tool_use":
                        given = block.get("input")
                        calls.append((turn, block.get("name"),
                                      given if isinstance(given, dict)
                                      else {}))
    return calls


def delegation_turn(file, written_at, fallback):
    """The session's turn a subagent's transcript was started at: the turn
    of the session's line its first record points back to, or `fallback`
    where it points at none the session wrote."""
    with io.open(file, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            try:
                record = json.loads(line)
            except ValueError:
                continue
            if not isinstance(record, dict):
                continue
            parent = record.get("parentLastUuid") or record.get("parentUuid")
            if parent in written_at:
                return written_at[parent]
            if record.get("type") == "assistant":
                break
    return fallback


def map_use(files, arm, templates=None, delegated=()):
    """How one trial used what its file points at, from its transcripts:
    each template read from the vendored copy or loaded as a skill, as
    (turn, template) in order, the turn of the trial's first write to a
    file of its own, or None, and how many of the uses a subagent made.

    A subagent's transcript, in `delegated`, is read after the session's,
    its calls charged to the turn of the session's line it points back to,
    the moment it was started; one pointing nowhere the session wrote is
    charged to the session's first delegation.
    """
    entry = ARMS.get(arm) or {}
    known = set(mapped_templates(arm) if templates is None else templates)
    marker = VENDORED["into"] + "/"
    named = re.compile(re.escape(marker) + r"(templates/[\w./-]+\.md)")

    def mapped(templates):
        """Those of the templates that are on the arm's map."""
        return [template for template in templates
                if not known or template in known]
    written_at = {}
    own = [(turn, name, given, False)
           for turn, name, given in tool_calls_by_turn(files, written_at)]
    first_delegation = next((turn for turn, name, _, _ in own
                             if name in DELEGATIONS), None)
    calls = list(own)
    for file in delegated:
        at = delegation_turn(file, written_at, first_delegation)
        calls.extend((at if at is not None else turn, name, given, True)
                     for turn, name, given in tool_calls_by_turn([file]))
    calls.sort(key=lambda call: call[0])
    uses = []
    before = set()
    first_write = None
    by_subagent = 0
    for turn, name, given, from_subagent in calls:
        command = str(given.get("command") or "").replace("\\", "/")
        found = []
        writes_at = None

        # A shell command may read a template and write a file in one go,
        # so it is read for both, and a read in a simple command before the
        # writing one came before the write.
        if name in SHELLS and entry.get("vendor"):
            writes_at = first_writing_command(command)
            for index, template in shell_reads(command, sorted(known)):
                if template in known or not known:
                    found.append(template)
                    if first_write is None and (writes_at is None
                                                or index < writes_at):
                        before.add(template)
        elif name == "Read" and entry.get("vendor"):
            path = str(given.get("file_path") or "").replace("\\", "/")
            found = mapped(named.findall(path))
        elif name == "Skill" and entry.get("skills"):
            skill = str(given.get("skill") or "").strip()
            found = [skill] if skill in known else []
        if name not in SHELLS and first_write is None:
            before.update(found)
        if first_write is None and (name in WRITES or writes_at is not None):
            first_write = turn
        uses.extend((turn, template) for template in found)
        if from_subagent:
            by_subagent += len(found)
    return {"uses": uses, "first_write": first_write,
            "before_write": sorted(before) if first_write is not None
            else None, "by_subagent": by_subagent}


def map_uses(root, trials):
    """Every trial's map use, by name, for the arms whose file points at
    the templates and whose transcripts the root still holds."""
    home = os.path.join(root, "home")
    uses = {}
    for record in run_records(root):
        if record.get("outcome") not in SCORABLE:
            continue
        name = name_of(record)
        if name not in trials:
            continue
        arm = arm_of(name)
        templates = mapped_templates(arm)
        if not templates:
            continue
        workspace = record.get("workspace") or ""
        files = transcript_files(home, workspace, started(record))
        if files:
            uses[name] = map_use(files, arm, templates,
                                 subagent_files(home, workspace,
                                                started(record)))
    return uses


def subagent_files(home, workspace, since=None):
    """The transcripts of the subagents a session in `workspace` started,
    filed under the session's folder, left out where written before
    `since`."""
    folder = os.path.dirname(transcript_files(home, workspace)[0]) \
        if transcript_files(home, workspace) else None
    if not folder:
        return []
    files = sorted(glob.glob(os.path.join(folder, "*", "subagents",
                                          "*.jsonl")))
    if since is None:
        return files
    return [file for file in files if os.path.getmtime(file) >= since]


def mean_of(values):
    """The mean of the values, or None of none."""
    return statistics.fmean(values) if values else None


def median_of(values):
    """The median of the values, or None of none."""
    return float(statistics.median(values)) if values else None


def map_use_rows(trials, uses):
    """Per arm: trials read, templates in its map, how many each trial read
    or loaded, how many before its first write, the turn of the first, and
    how many trials read every template before writing anything."""
    rows = []
    for arm in ARMS:
        names = [name for name in ordered(trials)
                 if arm_of(name) == arm and name in uses]
        if not names:
            continue
        total = len(mapped_templates(arm))
        counts, before, firsts = [], [], []
        for name in names:
            use = uses[name]
            counts.append(len({template for _, template in use["uses"]}))

            # A trial that never wrote has no "before", and says nothing
            # about reading up front.
            if use["first_write"] is not None:
                before.append(len(use.get("before_write") or ()))
            if use["uses"]:
                firsts.append(use["uses"][0][0])
        rows.append({"arm": arm, "trials": len(names), "total": total,
                     "read": mean_of(counts), "before": mean_of(before),
                     "wrote": len(before), "first": median_of(firsts),
                     "unused": sum(1 for count in counts if not count),
                     "up_front": sum(1 for count in before
                                     if total and count >= total)})
    return rows


def map_use_detail(trials, uses):
    """Every trial's map use, one row each: the turn of its first write and
    each template with the turn it was read or loaded at."""
    lines = ["#### Per trial", "",
             "A subagent's reads are charged to the turn that delegated "
             "to it.", "",
             "| Trial | First write at turn | By a subagent "
             "| Templates, by turn |",
             "| --- | --- | --- | --- |"]
    for name in ordered(trials):
        if name not in uses:
            continue
        use = uses[name]
        reads = ", ".join("%d: %s" % (turn, template[len("templates/"):]
                                      if template.startswith("templates/")
                                      else template)
                          for turn, template in use["uses"]) or "none"
        lines.append("| %s | %s | %d | %s |" % (
            name, "—" if use["first_write"] is None else use["first_write"],
            use.get("by_subagent", 0), reads))
    return lines


def map_use_lines(trials, uses):
    """The use-of-the-map table and the note beside H7."""
    rows = map_use_rows(trials, uses)
    lines = ["### Use of the map", "",
             "From each trial's transcript: the templates it read from the "
             "vendored copy or loaded as skills, counted once each, the "
             "turn the first happened at, and how many came before the "
             "trial's first write to a file of its own.", "",
             "| Arm | Trials | Templates in the map | Read or loaded, mean "
             "| Before the first write, mean | First at turn, median "
             "| Read all before writing |",
             "| --- | --- | --- | --- | --- | --- | --- |"]

    def shown(value, places=1):
        return "—" if value is None else ("%%.%df" % places) % value
    for row in rows:
        lines.append("| %s | %d | %d | %s | %s | %s | %d of %d |" % (
            row["arm"], row["trials"], row["total"], shown(row["read"]),
            shown(row["before"]), shown(row["first"], 0), row["up_front"],
            row["wrote"]))
    for row in rows:
        if row["arm"] != "lazyref":
            continue
        lines.append("")
        if not row["wrote"]:
            lines.append("Beside H7: no `lazyref` trial's first write could "
                         "be placed, so the map's use says nothing about "
                         "whether the templates were read up front or on "
                         "demand.")
        elif row["unused"] == row["trials"]:
            lines.append("Beside H7: no `lazyref` trial read a template of "
                         "its map, so H7 compares a map ignored against "
                         "templates read up front, not on-demand reading.")
        elif row["up_front"]:
            lines.append("Beside H7: `lazyref` read every template of its map "
                         "before its first write in %d of the %d trials that "
                         "wrote. Those trials measured reading up front, not "
                         "on demand." % (row["up_front"], row["wrote"]))
        else:
            lines.append("Beside H7: no `lazyref` trial read every template "
                         "of its map before its first write, so H7 reads "
                         "on-demand reading%s." % (
                             ", and %d of %d trials read none"
                             % (row["unused"], row["trials"])
                             if row["unused"] else ""))
    lines.append("")
    lines.extend(map_use_detail(trials, uses))
    return lines


# Round 5d's screen for round 6: the candidates, read against the bare arm,
# and how many of them go on.
SCREEN_CANDIDATES = ("inline", "hybrid", "reference", "skills", "hand",
                     "short") + ROUND5E_ARMS
SCREEN_KEEPS = 4
SCREEN_ROWS = ROUND5D_ROWS + ("reliability",)


def round6_screen(trials, table, results):
    """Each candidate against the bare arm: out where a deciding row reads
    worse, the rest ranked by rows better and then by mean cost, the top
    four going on to round 6 once every candidate is read. A candidate the
    run holds no trial of is named as missing, and nothing goes on until
    it is read too."""
    rows = []
    missing = []

    # Every declared contrast has a result, computed or not, so an arm's
    # presence is read from the trials and not from the results.
    present = {arm_of(name) for name in trials}
    for arm in SCREEN_CANDIDATES:
        label = "%s-%s" % (arm, BARE)
        if arm not in present or BARE not in present:
            missing.append(arm)
            continue
        readings = {key: row_reading(results.get(key, {}).get(label))
                    for key in SCREEN_ROWS}
        rows.append({"arm": arm,
                     "worse": [key for key in SCREEN_ROWS
                               if readings[key] == "worse"],
                     "better": sum(1 for reading in readings.values()
                                   if reading == "better"),
                     "cost": arm_mean(table, "cost_usd", arm),
                     "rank": None, "round6": False})
    kept = [row for row in rows if not row["worse"]]
    kept.sort(key=lambda row: (-row["better"], row["cost"]
                               if row["cost"] is not None else float("inf")))
    for rank, row in enumerate(kept, 1):
        row["rank"] = rank
        row["round6"] = rank <= SCREEN_KEEPS and not missing
    return rows, missing


def screen_lines(trials, table, results):
    """The screen as a table, and the arms round 6 runs, or the candidates
    still to be read before it names them."""
    rows, missing = round6_screen(trials, table, results)
    lines = ["### Round 6's arms, by the screen of 13d.9", "",
             "Each candidate is read against `%s` by the rules of 13d.7. An "
             "arm worse on a deciding row is out; the rest rank by how many "
             "rows read better, then by mean cost. The screen decides which "
             "arms run again, not which arm is better." % BARE, "",
             "| Arm | Rows better | Rows worse | Mean cost | Screen |",
             "| --- | --- | --- | --- | --- |"]
    for row in rows:
        if row["worse"]:
            screen = "out: %s worse" % ", ".join(
                SHORT.get(key, key) for key in row["worse"])
        else:
            screen = "rank %d%s" % (row["rank"],
                                   ", round 6" if row["round6"] else "")
        lines.append("| %s | %d | %d | %s | %s |" % (
            row["arm"], row["better"], len(row["worse"]),
            "—" if row["cost"] is None else "$%.2f" % row["cost"], screen))
    chosen = [row["arm"] for row in sorted(
        (row for row in rows if row["round6"]), key=lambda row: row["rank"])]
    if missing:
        lines.extend(["", "The screen is partial: %s %s not in this root, so "
                      "it names no arms for round 6 yet." % (
                          spoken(["`%s`" % arm for arm in missing]),
                          "is" if len(missing) == 1 else "are")])
    else:
        lines.extend(["", "Round 6 runs `%s`%s." % (
            BARE, " and " + spoken(["`%s`" % arm for arm in chosen])
            if chosen else " alone")])
    return lines


def round5e_section(root, trials, table, results, seed, margins, uses=None):
    """Round 5e's answer: round 5d's reading of H7 to H9, how each trial
    used its map, and the screen for round 6."""
    lines = round5d_section(trials, table, results, seed, margins,
                            ROUND5E_HYPOTHESES,
                            "## Round 5e: the templates on demand")
    lines.append("")
    lines.extend(map_use_lines(
        trials, map_uses(root, trials) if uses is None else uses))
    lines.append("")
    lines.extend(screen_lines(trials, table, results))
    return lines


def round5e_checks():
    """Round 5e's rules: its arms are read under round 5d's rules and its
    own registration, its contrasts are declared, H7 to H9 read as
    registered, the map's use is counted from the transcript, and the
    screen ranks round 6's candidates as 13d.9 says."""
    checks = []
    fresh = {"lazyref-1": {}, "lazyskills-1": {}}
    earlier = {"hand-1": {}, "short-1": {}}
    got = (is_round5e(fresh), is_round5d(fresh), later_rules_of(fresh),
           round_arms(fresh) == ROUND5E_ARMS,
           margins_of(fresh) is ROUND5D_MARGINS,
           registration_of(fresh), registration_of(earlier),
           owed_blocks(fresh) == list(range(2, ROUND5_K + 1)))
    checks.append(("round 5e reads under round 5d's rules, against its own "
                   "registration, owing its own arms' blocks",
                   got == (True, False, True, True, True,
                           ROUND5E_REGISTRATION, ROUND5D_REGISTRATION, True),
                   got))

    present = {"%s-1" % arm: {} for arm in
               ("none", "reference", "skills", "hand", "short") + ROUND5E_ARMS}
    active = active_contrasts(present)
    wanted = [tuple(label.split("-")) for _, label, _ in ROUND5E_HYPOTHESES]
    against = [(arm, other) for arm in ROUND5E_ARMS
               for other in ("none", "reference", "skills", "hand", "short")]
    got = (all(pair in active for pair in wanted + against),
           all(label in PLAIN_QUESTIONS for _, label, _ in ROUND5E_HYPOTHESES))
    checks.append(("round 5e's contrasts are declared: each map arm against "
                   "none and every reused arm, and the skill against the "
                   "file", got == (True, True), got))

    # In round 5e's root, `none` and `reference` came from round 5c and
    # `hand` from round 5d, all reused: `hand − none` crosses rounds, `none`
    # against `reference` does not, and a fresh arm crosses every reused one.
    def reused(root):
        return {"scores": {"reused_from": {"root": root, "name": "x-1"}}}
    mixed = {"none-1": reused("r5c"), "reference-1": reused("r5c"),
             "hand-1": reused("r5d"), "lazyref-1": {"scores": {}}}
    crossed = crossed_labels(mixed)
    got = (sorted(crossed), arm_origins(mixed)["lazyref"])
    checks.append(("a contrast crosses rounds where its arms ran in "
                   "different roots, reused or not",
                   "hand-none" in crossed and "lazyref-none" in crossed
                   and "lazyref-hand" in crossed
                   and "reference-none" not in crossed
                   and "lazyref-reference" in crossed and got[1] is None,
                   got))

    def results_for(label, **overrides):
        readings = {key: "held" for key in SCREEN_ROWS}
        readings.update(overrides)
        return {key: {label: {"verdict": reading}}
                for key, reading in readings.items()}
    label = "lazyref-reference"
    got = [round5d_hypothesis(results_for(label), label, "held")[0],
           round5d_hypothesis(results_for(label, task_success="better"),
                              label, "held")[0],
           round5d_hypothesis(results_for(label, judge_security="worse"),
                              label, "held")[0],
           round5d_hypothesis(results_for(label, reliability="worse"),
                              label, "held")[0],
           round5d_hypothesis(results_for(label, task_success="open"),
                              label, "held")[0]]
    checks.append(("H7 to H9 are supported when every row is held or better, "
                   "refuted by any worse row, reliability's included",
                   got == ["supported", "supported", "refuted", "refuted",
                           "inconclusive"], got))

    def read_names(command, known=()):
        """The templates a shell command reads, by name alone."""
        return [template for _, template in shell_reads(command, known)]
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-map-use-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)

    def call(name, **given):
        return {"type": "tool_use", "id": "t", "name": name, "input": given}

    def line(kind, message_id, *blocks):
        return json.dumps({"type": kind,
                           "message": {"id": message_id,
                                       "content": list(blocks)}}) + "\n"
    into = VENDORED["into"]
    planted = os.path.join(scratch, "planted.jsonl")
    with io.open(planted, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(line("user", "u1", {"type": "text", "text": "go"}))
        handle.write(line("assistant", "a1", call(
            "Read", file_path="C:\\pen\\%s\\templates\\core\\quality.md"
            % into.replace("/", "\\"))))
        handle.write(line("assistant", "a1", {"type": "text", "text": "ok"}))
        handle.write(line("assistant", "a2", call(
            "Read", file_path="/pen/%s/templates/core/quality.md" % into)))
        handle.write(line("assistant", "a3", call(
            "Bash", command="ls src 2>/dev/null; pytest -q 2>&1 | tail -3")))
        handle.write(line("assistant", "a4", call(
            "Bash", command="echo x > x.py")))
        handle.write(line("assistant", "a5", call("Write", file_path="y.py")))
        handle.write(line("assistant", "a6", call(
            "Bash", command="cat %s/templates/backend/http.md | head" % into)))
        handle.write(line("assistant", "a7", call(
            "Read", file_path="/pen/%s/templates/core/oop.md" % into)))
        handle.write(line("assistant", "a8", call("Read",
                                                  file_path="/pen/x.py")))
    chain = ["templates/core/quality.md", "templates/backend/http.md"]
    reading = map_use([planted], "lazyref", chain)
    skills = os.path.join(scratch, "skills.jsonl")
    with io.open(skills, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(line("assistant", "s1", call("Skill",
                                                  skill="base-quality")))
        handle.write(line("assistant", "s2", call("Skill", skill="run")))
        handle.write(line("assistant", "s3", call("Edit", file_path="x.py"),
                          call("Skill", skill="backend-api")))
    loading = map_use([skills], "lazyskills", ["base-quality", "backend-api"])
    silent = os.path.join(scratch, "silent.jsonl")
    with io.open(silent, "w", encoding="utf-8", newline="\n") as handle:
        for index, name in enumerate(chain, 1):
            handle.write(line("assistant", "n%d" % index, call(
                "Read", file_path="/pen/%s/%s" % (into, name))))
    never_wrote = map_use([silent], "lazyref", chain)
    rows = map_use_rows(
        {"lazyref-1": {}, "lazyref-2": {}, "lazyskills-1": {}},
        {"lazyref-1": reading, "lazyref-2": never_wrote,
         "lazyskills-1": loading})
    summary = [(row["arm"], row["read"], row["before"], row["wrote"],
                row["first"], row["up_front"]) for row in rows]
    detail = "\n".join(map_use_detail({"lazyref-1": {}},
                                      {"lazyref-1": reading}))
    shutil.rmtree(scratch, ignore_errors=True)
    got = (reading, loading, never_wrote, summary)
    checks.append(("the map's use counts each template read or skill loaded, "
                   "with its turn, and those before the first write",
                   reading == {"uses": [(1, "templates/core/quality.md"),
                                        (2, "templates/core/quality.md"),
                                        (6, "templates/backend/http.md")],
                               "first_write": 4, "by_subagent": 0,
                               "before_write": ["templates/core/quality.md"]}
                   and loading == {"uses": [(1, "base-quality"),
                                            (3, "backend-api")],
                                   "first_write": 3, "by_subagent": 0,
                                   "before_write": ["base-quality"]}
                   and never_wrote["first_write"] is None
                   and summary == [("lazyref", 2.0, 1.0, 1, 1.0, 0),
                                   ("lazyskills", 2.0, 1.0, 1, 1.0, 0)],
                   got))
    checks.append(("a shell command that writes counts as the first write, "
                   "a template off the map is not counted, and a trial that "
                   "never wrote says nothing about reading up front",
                   reading["first_write"] == 4
                   and all(template != "templates/core/oop.md"
                           for _, template in reading["uses"])
                   and summary[0][3] == 1 and summary[0][5] == 0,
                   (reading, summary)))
    checks.append(("a shell read of a template counts, and a redirection to "
                   "the null device or into another stream is no write",
                   (6, "templates/backend/http.md") in reading["uses"]
                   and not shell_writes("ls src 2>/dev/null")
                   and not shell_writes("pytest 2>&1 | tail")
                   and not shell_writes("Get-Content x.py > $null")
                   and shell_writes("echo x > x.py")
                   and shell_writes("cat a >> b.txt")
                   and shell_writes("mkdir src"),
                   reading["uses"]))
    quality = "%s/templates/core/quality.md" % into
    checks.append(("quoted text is no shell operator, and a path a shell "
                   "command lists or tests is not read",
                   not shell_writes("git log --format='%h -> %s'")
                   and not shell_writes("echo 'mkdir src'")
                   and shell_writes("echo 'x' > 'my file.py'")
                   and read_names("ls %s" % quality) == []
                   and read_names("test -f %s && echo yes" % quality) == []
                   and read_names("cat %s" % quality)
                   == ["templates/core/quality.md"]
                   and read_names("sed -n 1,40p %s | head" % quality)
                   == ["templates/core/quality.md"]
                   and read_names("Get-Content %s" % quality)
                   == ["templates/core/quality.md"],
                   None))
    http = "%s/templates/backend/http.md" % into
    checks.append(("a shell command is read one simple command at a time: "
                   "every operand of a reading command counts, and a verb "
                   "in an argument is no command",
                   read_names("cat %s %s" % (quality, http))
                   == ["templates/core/quality.md",
                       "templates/backend/http.md"]
                   and read_names("cat '%s' | head" % quality)
                   == ["templates/core/quality.md"]
                   and read_names("ls %s && cat %s" % (quality, http))
                   == ["templates/backend/http.md"]
                   and not shell_writes("rg -n mkdir src")
                   and not shell_writes("echo mkdir src")
                   and shell_writes("/usr/bin/cp a b")
                   and shell_writes("FOO=1 mkdir x")
                   and shell_writes("pytest -q | tee log.txt")
                   and shell_writes("C:\\Windows\\System32\\xcopy.exe a b"
                                    " > out.txt"),
                   None))
    silent_note = "\n".join(map_use_lines({"lazyref-2": {}},
                                          {"lazyref-2": never_wrote}))
    checks.append(("with no trial that wrote, the note beside H7 withholds "
                   "the reading",
                   "says nothing about whether" in silent_note
                   and "on-demand reading" not in silent_note,
                   silent_note[-300:]))
    checks.append(("every trial's reads are listed with their turns",
                   "| lazyref-1 | 4 | 0 | 1: core/quality.md, "
                   "2: core/quality.md, 6: backend/http.md |" in detail,
                   detail))

    # A subagent read all of the map at the parent's turn 2, before the
    # parent's first write at turn 3; a wildcard stands for every template
    # of the map it matches; a map read by nobody is said to be ignored.
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-map-use-self-test")
    os.makedirs(scratch)
    parent = os.path.join(scratch, "parent.jsonl")
    with io.open(parent, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(line("assistant", "p1", call("Bash", command="ls")))
        handle.write(line("assistant", "p2", call(
            "Agent", prompt="read the templates")))
        handle.write(line("assistant", "p3", call("Write", file_path="a.py")))
    child = os.path.join(scratch, "agent.jsonl")
    with io.open(child, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(line("assistant", "c1", call(
            "Bash", command="cat %s/templates/core/*.md" % into)))
        handle.write(line("assistant", "c2", call(
            "Read", file_path="/pen/%s/templates/backend/http.md" % into)))
    chain = ["templates/core/quality.md", "templates/core/git.md",
             "templates/backend/http.md"]
    with_subagent = map_use([parent], "lazyref", chain, [child])
    delegated_rows = map_use_rows({"lazyref-1": {}},
                                  {"lazyref-1": with_subagent})
    shutil.rmtree(scratch, ignore_errors=True)
    checks.append(("a subagent's reads count at the turn that delegated, and "
                   "a wildcard stands for every template of the map it "
                   "matches",
                   with_subagent == {
                       "uses": [(2, "templates/core/git.md"),
                                (2, "templates/core/quality.md"),
                                (2, "templates/backend/http.md")],
                       "first_write": 3, "by_subagent": 3,
                       "before_write": ["templates/backend/http.md",
                                        "templates/core/git.md",
                                        "templates/core/quality.md"]}
                   and delegated_rows[0]["before"] == 3.0
                   and read_names("cat %s/templates/core/q*.md" % into,
                                   chain) == ["templates/core/quality.md"],
                   with_subagent))
    # Two delegations: each subagent is charged to the line it points back
    # to, so the second one's read at turn 3 falls after the write at turn
    # 2, and a quoted separator splits no command.
    os.makedirs(scratch)

    def stamped(kind, message_id, uuid, *blocks):
        record = json.loads(line(kind, message_id, *blocks))
        record["uuid"] = uuid
        return json.dumps(record) + "\n"
    parent = os.path.join(scratch, "parent.jsonl")
    with io.open(parent, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(stamped("assistant", "p1", "u1", call(
            "Agent", prompt="read quality")))
        handle.write(stamped("assistant", "p2", "u2", call(
            "Write", file_path="a.py")))
        handle.write(stamped("assistant", "p3", "u3", call(
            "Agent", prompt="read http")))
    children = []
    for index, (uuid, template) in enumerate(
            (("u1", "core/quality.md"), ("u3", "backend/http.md"))):
        child = os.path.join(scratch, "agent-%d.jsonl" % index)
        with io.open(child, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps({"type": "fork-context-ref",
                                     "parentLastUuid": uuid}) + "\n")
            handle.write(line("assistant", "c%d" % index, call(
                "Read", file_path="/pen/%s/templates/%s" % (into, template))))
        children.append(child)
    twice = map_use([parent], "lazyref", chain, children)
    shutil.rmtree(scratch, ignore_errors=True)
    checks.append(("each subagent is charged to the turn that started it, "
                   "and a separator inside quotes splits no command",
                   twice == {"uses": [(1, "templates/core/quality.md"),
                                      (3, "templates/backend/http.md")],
                             "first_write": 2, "by_subagent": 2,
                             "before_write": ["templates/core/quality.md"]}
                   and read_names('echo "x; cat %s"' % quality, chain) == []
                   and read_names('cat "%s"; ls' % quality, chain)
                   == ["templates/core/quality.md"]
                   and not shell_writes('echo "a > b"'),
                   twice))
    one_go = os.path.join(scratch, "one-go.jsonl")
    os.makedirs(scratch)
    heredoc = "python - <<'PY'\nprint(2 > 1)\nPY"
    with io.open(one_go, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(line("assistant", "g1", call("Bash", command=heredoc)))
        handle.write(line("assistant", "g2", call(
            "Bash", command="cat %s/%s %s/%s && mkdir -p src && cat %s/%s"
            % (into, chain[0], into, chain[1], into, chain[2]))))
    in_one_go = map_use([one_go], "lazyref", chain)
    shutil.rmtree(scratch, ignore_errors=True)
    checks.append(("a read before the writing command of one shell call "
                   "comes before the write, and a here-document body is "
                   "no command",
                   in_one_go["first_write"] == 2
                   and in_one_go["before_write"] == sorted(chain[:2])
                   and len(in_one_go["uses"]) == 3
                   and not shell_writes(heredoc)
                   and shell_writes("cat a <<'EOF'\nx\nEOF\necho y > z"),
                   in_one_go))
    ignored = map_use_lines({"lazyref-1": {}}, {"lazyref-1": {
        "uses": [], "first_write": 2, "by_subagent": 0}})
    checks.append(("a map no trial read is said to be ignored, not read on "
                   "demand",
                   "compares a map ignored" in "\n".join(ignored)
                   and "so H7 reads on-demand" not in "\n".join(ignored),
                   ignored[-6:]))
    planted_uses = {"lazyref-1": reading}
    kept = aggregate(1, {}, {}, {}, {}, None, None, planted_uses)["map_use"]
    checks.append(("the aggregate keeps each trial's map use",
                   kept == {"lazyref-1": {
                       "first_write": 4, "by_subagent": 0,
                       "before_write": ["templates/core/quality.md"],
                       "uses": [{"turn": 1,
                                 "template": "templates/core/quality.md"},
                                {"turn": 2,
                                 "template": "templates/core/quality.md"},
                                {"turn": 6,
                                 "template": "templates/backend/http.md"}]}}
                   and "map_use" not in aggregate(1, {}, {}, {}, {}, None,
                                                  None),
                   kept))
    got = (mapped_templates("none"), len(mapped_templates("lazyskills")),
           len(mapped_templates("lazyref")))
    checks.append(("an arm's map is its skills or its vendored chain, and the "
                   "bare arm has none", got == ([], 13, 13), got))

    # Two arms better on two rows, the cheaper first; one out on task
    # success; three held, by cost; the fifth in rank stays out of round 6.
    costs = {"inline": 10.0, "hybrid": 8.0, "reference": 6.0, "skills": 5.0,
             "hand": 9.0, "short": 20.0}
    table = {"cost_usd": {"values": {arm: {1: cost, 2: cost}
                                     for arm, cost in costs.items()}}}
    results = {key: {} for key in SCREEN_ROWS}
    for arm in costs:
        for key in SCREEN_ROWS:
            results[key]["%s-none" % arm] = {"verdict": "held"}
    for key in ("task_success", "judge_security"):
        results[key]["inline-none"]["verdict"] = "better"
        results[key]["hybrid-none"]["verdict"] = "better"
    results["task_success"]["reference-none"]["verdict"] = "worse"

    # Every declared contrast has a result whether its arms ran or not, so
    # the planted results carry the absent arms' labels too.
    for arm in ROUND5E_ARMS:
        for key in SCREEN_ROWS:
            results[key]["%s-none" % arm] = {"verdict": "not computed"}
    held = {"%s-1" % arm: {} for arm in list(costs) + [BARE]}
    partial_rows, missing = round6_screen(held, table, results)
    partial = {row["arm"]: (row["rank"], row["round6"], row["worse"])
               for row in partial_rows}
    checks.append(("the screen ranks what it holds and names no arm for "
                   "round 6 while a candidate is missing",
                   missing == list(ROUND5E_ARMS)
                   and partial["hybrid"] == (1, False, [])
                   and "names no arms for round 6 yet" in
                   "\n".join(screen_lines(held, table, results))
                   and "`lazyref` and `lazyskills` are not in this root"
                   in "\n".join(screen_lines(held, table, results)),
                   (partial, missing)))
    for arm in ROUND5E_ARMS:
        costs[arm] = 30.0
        held["%s-1" % arm] = {}
        table["cost_usd"]["values"][arm] = {1: 30.0, 2: 30.0}
        for key in SCREEN_ROWS:
            results[key]["%s-none" % arm] = {"verdict": "held"}
    full_rows, missing = round6_screen(held, table, results)
    screen = {row["arm"]: (row["rank"], row["round6"], row["worse"])
              for row in full_rows}
    checks.append(("the screen drops an arm worse than none on a deciding "
                   "row, ranks the rest by rows better and then by cost, "
                   "and keeps four",
                   not missing
                   and screen == {"hybrid": (1, True, []),
                                  "inline": (2, True, []),
                                  "skills": (3, True, []),
                                  "hand": (4, True, []),
                                  "short": (5, False, []),
                                  "lazyref": (6, False, []),
                                  "lazyskills": (7, False, []),
                                  "reference": (None, False,
                                                ["task_success"])},
                   screen))
    text = "\n".join(screen_lines(held, table, results))
    checks.append(("the screen names the arms round 6 runs",
                   "Round 6 runs `none` and `hybrid`, `inline`, `skills` and "
                   "`hand`." in text
                   and "out: %s worse" % SHORT["task_success"] in text,
                   text.splitlines()[-1]))

    # The plain report answers the latest round's questions: with round
    # 5e's arms present, H7 to H9, and not round 5d's.
    design = {"none": 3, "reference": 3, "skills": 3, "hand": 3,
              "lazyref": 3, "lazyskills": 3}
    run = {trial_name(arm, index): {
        "scores": ({"reused_from": {"root": "r5c", "name": "x"}}
                   if arm in ("none", "reference", "skills")
                   else {"reused_from": {"root": "r5d", "name": "x"}}
                   if arm == "hand" else {}),
        "change": None, "security": None,
        "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
        for arm, score in design.items() for index in range(1, 4)}
    plain = " ".join(rendered_plain(run, 20260912).split())
    checks.append(("the plain report asks round 5e's questions, not round "
                   "5d's",
                   PLAIN_QUESTIONS["lazyref-reference"] in plain
                   and PLAIN_QUESTIONS["lazyskills-lazyref"] in plain
                   and PLAIN_QUESTIONS["hand-none"] not in plain,
                   plain[plain.find("## The questions"):][:400]))
    return checks


def round5d_checks(seed):
    """Round 5d's rules: a working build, quality on working builds, a
    verdict only past the margin, economy's margins, reliability's interval
    and its refute-only reading, leave-two-out, the profile and the radar's
    sizes."""
    checks = []

    def boot(install, factory, status):
        return {"scores": {"install": {"value": install},
                           "boot": {"value": {"factory": factory,
                                              "index_status": status}}}}
    got = [works(boot(True, True, 302)), works(boot(True, False, None)),
           works(boot(False, False, None)), works(boot(True, True, 500))]
    checks.append(("a build works when it installs and serves short of a "
                   "server error", got == [1.0, 0.0, 0.0, 0.0], got))

    # A broken build's task success is left out in round 5d and is zero in
    # a round read by the earlier rules.
    broken = dict(boot(False, False, None)["scores"],
                  hidden_suite={"value": None, "missing": "no install"})
    working = dict(boot(True, True, 302)["scores"],
                   hidden_suite={"value": 0.9})
    run = {"hand-1": {"scores": broken}, "short-1": {"scores": working}}
    later = collect(run)
    earlier = collect({"none-1": {"scores": broken},
                       "inline-1": {"scores": working}})
    got = (later["task_success"]["values"]["hand"][1],
           later["reliability"]["values"]["hand"][1],
           earlier["task_success"]["values"]["none"][1])
    checks.append(("round 5d reads task success on working builds only",
                   got == (None, 0.0, 0.0), got))

    # Round 5d prints adherence without a verdict and decides on the hidden
    # tests; round 5 still reads adherence.
    got = (later["adherence"]["direction"], earlier["adherence"]["direction"],
           "adherence" in ROUND5D_ROWS, "task_success" in ROUND5D_ROWS)
    checks.append(("round 5d decides on outcomes, and adherence decides "
                   "nothing", got == (NEUTRAL, UP, False, True), got))

    # A judge row's margin is 0.3 points.
    readings = [margined_verdict({"low": low, "high": high}, UP, 0.3)
                for low, high in ((0.05, 0.25), (0.35, 0.6), (-0.6, -0.35),
                                  (-0.2, 0.0), (-0.4, 0.1))]
    checks.append(("a strike or a win needs the whole interval past the "
                   "margin", readings == ["held", "better", "worse", "held",
                                          "no improvement shown"],
                   readings))

    # A 10 % rise in cost on a baseline of about 11 is held within 25 %; a
    # 50 % rise is worse.
    base = {index: 10.0 + index % 3 for index in range(1, 7)}
    costs = []
    for rise in (1.1, 1.5):
        left = {index: value * rise for index, value in base.items()}
        costs.append(strict_contrast("cost_usd", DOWN, left, base, seed,
                                     ROUND5D_MARGINS)["verdict"])
    checks.append(("economy is held within 25 % of the baseline's cost",
                   costs == ["held", "worse"], costs))

    # Fifteen of fifteen on both sides: the difference spans about ±0.204,
    # and the exact interval of one arm starts at 0.782.
    unpaired = newcombe_unpaired([1.0] * 15, [1.0] * 15)
    paired = newcombe_paired([(1.0, 1.0)] * 15)
    exact = clopper_pearson(15, 15)
    got = (round(unpaired["low"], 3), round(unpaired["high"], 3),
           round(paired["low"], 3), round(exact[0], 3))
    checks.append(("reliability's interval is Newcombe's, and the arm's is "
                   "exact", got == (-0.204, 0.204, -0.204, 0.782), got))

    def planted_rows(verdicts, reliability):
        planted = {key: {"short-hand": {"verdict": verdict}}
                   for key, verdict in zip(ROUND5D_ROWS, verdicts)}
        planted["reliability"] = {"short-hand": {"verdict": reliability}}
        return planted
    held = ["held"] * len(ROUND5D_ROWS)
    got = (round5d_hypothesis(planted_rows(held, "no improvement shown"),
                              "short-hand", "held")[0],
           round5d_hypothesis(planted_rows(held, "worse"), "short-hand",
                              "held")[0],
           round5d_hypothesis(planted_rows(held, "held"), "short-hand",
                              "better")[0],
           round5d_hypothesis(planted_rows(["better"] + held[1:], "held"),
                              "short-hand", "better")[0])
    checks.append(("reliability refutes and never has to hold; H4 needs a "
                   "gain", got == ("supported", "refuted", "inconclusive",
                                   "supported"), got))

    # Six blocks, every primary row equal: held wherever two are dropped.
    # Two blocks losing a security point unsettle the row, and dropping
    # just those two settles it, so that reading is fragile.
    def table(security):
        rows = {key: {"label": key, "direction": UP, "values": {
            "short": {index: 1.0 for index in range(1, 7)},
            "hand": {index: 1.0 for index in range(1, 7)}}}
            for key in ROUND5D_ROWS + ("reliability",)}
        rows["judge_security"]["values"]["short"].update(security)
        return rows
    got = (leave_two_out(table({}), "short-hand", "held", seed,
                         ROUND5D_MARGINS),
           leave_two_out(table({1: 0.0, 2: 0.0}), "short-hand", "held",
                         seed, ROUND5D_MARGINS))
    checks.append(("leave-two-out reads robust and fragile",
                   got == ("robust", "fragile"), got))

    # Security two points worse in every block refutes in every reading;
    # withheld by the cross-check, it stays withheld, so the two blocks
    # losing task success decide, and the reading is fragile.
    planted_table = table({index: -1.0 for index in range(1, 7)})
    planted_table["task_success"]["values"]["short"].update({1: 0.0, 2: 0.0})
    shown = contrasts(planted_table, seed, (), ROUND5D_MARGINS, True,
                      only=("short-hand",))
    published = round5d_hypothesis(shown, "short-hand", "held")[0]
    shown["judge_security"]["short-hand"]["verdict"] = DISAGREE_VERDICT
    got = (published,
           leave_two_out(planted_table, "short-hand", "held", seed,
                         ROUND5D_MARGINS),
           leave_two_out(planted_table, "short-hand", "held", seed,
                         ROUND5D_MARGINS, shown))
    checks.append(("leave-two-out keeps a withheld verdict withheld",
                   got == ("refuted", "robust", "fragile"), got))

    # Every reading supports, and the report printed inconclusive: each drop
    # is compared with what the report printed, so the reading is fragile.
    printed = contrasts(table({}), seed, (), ROUND5D_MARGINS, True,
                        only=("short-hand",))
    printed["task_success"]["short-hand"]["verdict"] = "no improvement shown"
    got = (leave_two_out(table({}), "short-hand", "held", seed,
                         ROUND5D_MARGINS),
           leave_two_out(table({}), "short-hand", "held", seed,
                         ROUND5D_MARGINS, printed))
    checks.append(("leave-two-out compares with the printed reading",
                   got == ("robust", "fragile"), got))

    # One more security point in every trial: paired by block the difference
    # is exact, while unpaired it is as wide as the spread of each arm.
    left = {index: float(index) + 1.0 for index in range(1, 16)}
    right = {index: float(index) for index in range(1, 16)}
    paired_read = strict_contrast("judge_security", UP, left, right, seed,
                                  ROUND5D_MARGINS)
    unpaired_read = strict_contrast("judge_security", UP, left, right, seed,
                                    ROUND5D_MARGINS, unpaired=True)
    reliability = strict_contrast("reliability", UP, {1: 1.0, 2: 1.0},
                                  {3: 1.0, 4: 0.0}, seed, ROUND5D_MARGINS,
                                  unpaired=True)
    got = (paired_read["interval"]["high"] - paired_read["interval"]["low"],
           unpaired_read["interval"]["high"] - unpaired_read["interval"]["low"]
           > 4, unpaired_read["verdict"], reliability["interval"]["method"])
    checks.append(("a contrast across rounds is unpaired, with a verdict",
                   got[0] == 0 and got[1] and got[2] != CROSSING_VERDICT
                   and got[3].startswith("Newcombe's score interval, "
                                         "unpaired"), got))

    # A skewed baseline: the difference's acceleration takes the baseline's
    # influence with a minus sign, which leaves the interval low enough to
    # read held within 0.3 points rather than better.
    skewed = unpaired_interval([2.0] * 15, [1.0] * 14 + [3.0], 20260912)
    got = (round(skewed["low"], 4), margined_verdict(skewed, UP, 0.3))
    checks.append(("the unpaired interval signs the baseline's influence",
                   got[1] == "held" and got[0] < 0.3, got))

    # The other vendor's judge read hand-1, hand-2 and none-3: no block in
    # common, so only an unpaired reading compares them, as the main one does.
    def judged(score, reused=False):
        return {"scores": {"reused_from": {"name": "planted"}} if reused
                else {}, "change": None, "security": None,
                "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
    ours = {"hand-1": judged(3), "hand-2": judged(3), "hand-3": judged(3),
            "none-1": judged(2, True), "none-2": judged(2, True),
            "none-3": judged(2, True)}
    theirs = {name: ours[name] for name in ("hand-1", "hand-2", "none-3")}
    got = cross_check(ours, theirs, seed)["results"]["judge_design"][
        "hand-none"]["mean"]
    checks.append(("the cross-check reads a contrast across rounds unpaired",
                   got == 1.0, got))

    # The same for an earlier round read post-hoc: its reused `inline`
    # against `none`, read by the later rules.
    earlier_ours = {"inline-1": judged(3, True), "inline-2": judged(3, True),
                    "none-3": judged(2)}
    got = (cross_check(earlier_ours, earlier_ours, seed)["results"][
        "judge_design"]["inline-none"]["mean"],
           cross_check(earlier_ours, earlier_ours, seed, True)["results"][
        "judge_design"]["inline-none"]["mean"])
    checks.append(("an earlier round's cross-check is unpaired post-hoc",
                   got == (None, 1.0), got))

    # Two measured trials against fifteen: the cell says so.
    cell = contrast_cell({"interval": {"low": 0.1, "high": 0.4,
                                       "method": "BCa, unpaired"},
                          "mean": 0.2, "verdict": "held", "pairs": [],
                          "unpaired": True, "trials": (2, 15)}, full=15)
    checks.append(("an unpaired cell names each arm's trials when short",
                   cell.endswith("(2 against 15 trials)"), cell))

    # Two arms that never share a block: unpaired, every reading of the
    # thirty is supported, which a reading by blocks would never be.
    apart = {key: {"label": key, "direction": UP, "values": {
        "short": {index: 1.0 for index in range(1, 7)},
        "hand": {index: 1.0 for index in range(7, 13)}}}
        for key in ROUND5D_ROWS + ("reliability",)}
    printed_apart = contrasts(apart, seed, ("short-hand",), ROUND5D_MARGINS,
                              True, only=("short-hand",))
    got = (round5d_hypothesis(printed_apart, "short-hand", "held")[0],
           leave_two_out(apart, "short-hand", "held", seed, ROUND5D_MARGINS,
                         printed_apart, unpaired=True),
           leave_two_out(apart, "short-hand", "held", seed, ROUND5D_MARGINS,
                         printed_apart))
    checks.append(("an unpaired contrast leaves out two trials, not blocks",
                   got == ("supported", "robust", "fragile"), got))

    # Round 5d's appendix lists the rows its radar reads.
    got = [axis for axis in radar_axes(printed)] == list(ROUND5D_RADAR_AXES)
    checks.append(("round 5d's appendix and radar read round 5d's rows",
                   got and radar_axes({}) == RADAR_AXES, got))

    def planted(*pairs):
        return {key: {"x": {"verdict": verdict, "size": size}}
                for key, (verdict, size) in zip(("a", "b"), pairs)}
    got = [axis_word(planted(("better", 0.4), ("held", 0.0)), "x",
                     ("a", "b")),
           axis_word(planted(("held", 0.0), ("held", 0.0)), "x", ("a", "b")),
           axis_word(planted(("better", 0.5), ("worse", -0.1)), "x",
                     ("a", "b")),
           axis_word(planted(("no improvement shown", 0.0), ("held", 0.0)),
                     "x", ("a", "b"))]
    checks.append(("the profile names each axis better, held, worse or "
                   "unsettled", got == ["better", "held", "better",
                                        "unsettled"], got))

    # Sizes +0.1 and -0.4 read worse; a withheld +1.0 must not tip them.
    mixed = {"a": {"x": {"verdict": "better", "size": 0.1}},
             "b": {"x": {"verdict": "worse", "size": -0.4}},
             "c": {"x": {"verdict": DISAGREE_VERDICT, "size": 1.0}}}
    got = axis_word(mixed, "x", ("a", "b", "c"))
    checks.append(("the profile's sign leaves out withheld rows",
                   got == "worse", got))

    sizes = [row_size("judge_design", {"low": 0.5, "high": 0.9}, UP, 3.0),
             row_size("judge_design", {"low": -0.1, "high": 0.4}, UP, 3.0),
             row_size("task_success", {"low": 0.1, "high": 0.3}, UP, 0.8),
             row_size("mutual_imports", {"low": 3.0, "high": 5.0}, DOWN,
                      0.0),
             row_size("mutual_imports", {"low": -3.0, "high": -2.0}, DOWN,
                      3.0),
             row_size("cost_usd", {"low": 6.0, "high": 9.0}, DOWN, 2.0),
             row_size("cost_usd", {"low": 20.0, "high": 30.0}, DOWN, 2.0)]
    got = [round(size, 3) for size in sizes]
    checks.append(("the radar plots the bound nearest zero over the full "
                   "scale", got == [0.5, 0.0, 0.5, -1.0, 0.5, -1.0, -1.0],
                   got))

    # A run of `hand` and `short` renders round 5d's section, with H6's
    # reading, its confidence and its profile.
    design = {"hand": 3, "short": 4}
    run = {trial_name(arm, index): {
        "scores": {}, "change": None, "security": None,
        "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
        for arm, score in design.items() for index in range(1, 4)}
    text = rendered(run, seed, {})[2]
    section = (text.split("## Round 5d")[1].split("\n## ")[0]
               if "## Round 5d" in text else "")
    checks.append(("a round-5d run renders H6 with its confidence and "
                   "profile",
                   "H6, the templates' content at a person's length, "
                   "short-hand: inconclusive, robust" in section
                   and "profile: Reliability not computed" in section
                   and "Design better" in section, section[-600:]))

    # With round 5c's `none` reused, H4 reads `hand` against it unpaired,
    # and the report says the contrast across rounds is unpaired.
    design = {"none": 2, "hand": 3, "short": 4}
    run = {trial_name(arm, index): {
        "scores": ({"reused_from": {"name": "planted"}} if arm == "none"
                   else {}),
        "change": None, "security": None,
        "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
        for arm, score in design.items() for index in range(1, 4)}
    text = rendered(run, seed, {})[2]
    section = (text.split("## Round 5d")[1].split("\n## ")[0]
               if "## Round 5d" in text else "")
    checks.append(("a round-5d run reads H4 against a reused `none`, "
                   "unpaired",
                   "H4, a file at all, hand-none: inconclusive" in section
                   and "Compared unpaired with this round's trials, as "
                   "round 5d registered: short − none and hand − none."
                   in " ".join(text.split()), section[-600:]))
    checks.append(("round 5d's radar is explained by size, not by votes",
                   "bound nearest zero" in " ".join(text.split())
                   and "the share of them better" not in text, None))
    checks.append(("round 5d's radar names each row's full scale",
                   "1 point for a judge score, 20 pp for a share, 20 points "
                   "for coverage, and a factor of 4 for a count or a cost"
                   in " ".join(text.split()), None))

    # H3 predicts a loss: a worse row or a worse reliability supports it,
    # and every row held refutes it.
    def rows_for(verdict, reliability="held"):
        planted = {key: {"reference-hybrid": {"verdict": verdict}}
                   for key in ROUND5D_ROWS}
        planted["reliability"] = {"reference-hybrid": {
            "verdict": reliability}}
        return planted
    got = [round5d_hypothesis(rows_for(*case), "reference-hybrid",
                              "worse")[0]
           for case in (("worse",), ("held",), ("held", "worse"),
                        ("no improvement shown",))]
    checks.append(("a hypothesis that predicts a loss reads by it",
                   got == ["supported", "refuted", "supported",
                           "inconclusive"], got))

    # Round 5c read post-hoc: its own page, labelled, with H1 and H3 by the
    # later rules, while the registered reading keeps its own rules.
    design = {"none": 3, "hybrid": 3, "skills": 4, "reference": 3}
    earlier = {trial_name(arm, index): {
        "scores": {}, "change": None, "security": None,
        "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
        for arm, score in design.items() for index in range(1, 4)}
    later_table, later_results = posthoc_rules_reading(earlier, seed)

    # With the other vendor's judge, read as an earlier round's, the
    # post-hoc reading meets contrasts that judge's reading never computed.
    try:
        posthoc_rules_reading(earlier, seed, None,
                              cross_check(earlier, earlier, seed))
        crossed_ok = True
    except KeyError as error:
        crossed_ok = error
    checks.append(("the post-hoc reading takes a cross-check",
                   crossed_ok is True, crossed_ok))

    # A round read by the later rules decides on app code and prints source
    # lines without a verdict, as round 5 does.
    sized_run = {trial_name(arm, 1): {"scores": {}} for arm in ("none",
                                                                 "inline")}
    got = (collect(sized_run, later_rules=True)["app_lines"]["direction"],
           collect(sized_run, later_rules=True)["source_lines"]["direction"],
           collect(sized_run)["source_lines"]["direction"])
    checks.append(("the later rules read app code in any round",
                   got == (DOWN, NEUTRAL, NEUTRAL), got))
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-posthoc-rules")
    shutil.rmtree(scratch, ignore_errors=True)
    page = write_posthoc_rules(earlier, later_table, later_results, seed,
                               scratch)
    with io.open(page, encoding="utf-8") as handle:
        written = " ".join(handle.read().split())
    images = sorted(name for name in os.listdir(scratch)
                    if name.endswith(".svg"))
    shutil.rmtree(scratch, ignore_errors=True)
    registered = round_contrasts(earlier, collect(earlier), seed)
    checks.append(("round 5c's post-hoc page is labelled and reads H1 and "
                   "H3 by the later rules",
                   written.startswith("# Efficacy benchmark")
                   and "**Post-hoc.**" in written
                   and "registered verdicts stand" in written
                   and "H1, skills deliver what hybrid does, skills-hybrid:"
                   in written
                   and "H3, a reference alone delivers less, "
                   "reference-hybrid:" in written
                   and "### The rows the questions decide on" in written
                   and "### Economy" in written
                   and "skills−hybrid" in written
                   and "aggregate-posthoc.json" in written
                   and len(images) == 2
                   and "size" not in registered["judge_design"]["skills-none"]
                   and "size" in later_results["judge_design"]["skills-none"],
                   written[:300]))

    axes = dict(ROUND5D_RADAR_AXES)
    sized = {key: {"x": {"verdict": "better", "size": 0.25}}
             for key in axes["Economy"]}
    got = (axes["Reliability"], axes["Economy"],
           dict(cluster_scores(sized, "x"))["Economy"])
    checks.append(("round 5d's radar reads reliability, cost and turns, by "
                   "size", got == (("reliability", "task_success"),
                                   ("cost_usd", "turns"), 0.25), got))
    return checks


def round5_checks():
    """Agreement means pairs over the items both measured, adherence is
    held within one item, the run owes no escalation, and a hypothesis
    reads supported, refuted or inconclusive by its registered rule."""
    def trial(items):
        return {"scores": {"adherence": {"value": 1, "items": items}}}
    trials = {"skills-1": trial({"a": True, "b": True, "c": None}),
              "skills-2": trial({"a": True, "b": False, "c": True}),
              "skills-3": trial({"a": True, "b": True, "c": True})}

    # The pairs agree on 1 of a, b; on both of a, b; and on 2 of a, b, c.
    share, pairs = conventions_agreement(trials, "skills")
    checks = [("conventions agreement means the pairs over the items both "
               "measured", (share, pairs) == (round(13 / 18, 3), 3),
               (share, pairs))]

    # A loss of 7 pp in adherence is held within one item, not within 5 pp.
    loss = {"low": -0.07, "high": 0.02}
    got = (non_inferior("adherence", loss, UP, None, ROUND5_MARGINS),
           non_inferior("adherence", loss, UP))
    checks.append(("round 5 holds adherence within one item, 8 pp",
                   got[0]["within"] and not got[1]["within"], got))

    # Structure: {a, b}, {a, b} and {a, c} pair as 1, 1/3 and 1/3.
    for name, files in (("skills-1", ["a.py", "b.py"]),
                        ("skills-2", ["a.py", "b.py"]),
                        ("skills-3", ["a.py", "c.py"])):
        trials[name]["scores"]["python_files"] = {"value": files,
                                                  "missing": None}
    got = pairwise_agreement(structure_sets(trials, "skills"))
    checks.append(("structure agreement is the mean pairwise Jaccard of "
                   "the trials' files", got == round(5 / 9, 3), got))

    # A trial whose listing failed is missing, not empty: left out, it
    # cannot agree with anything.
    trials["skills-3"]["scores"]["python_files"] = {
        "value": None, "missing": "listing the trial's files failed"}
    got = pairwise_agreement(structure_sets(trials, "skills"))
    checks.append(("a trial whose file listing failed is left out of "
                   "structure agreement", got == 1.0, got))

    # Security: two trials failing nothing agree fully, a trial with an
    # unmeasured probe is left out, and {x} against {} agrees not at all.
    trials["skills-1"]["security"] = {"probes": {"x": {"passed": True}}}
    trials["skills-2"]["security"] = {"probes": {"x": {"passed": True}}}
    trials["skills-3"]["security"] = {"probes": {"x": {"passed": None}}}
    alike = pairwise_agreement(security_sets(trials, "skills"))
    trials["skills-2"]["security"] = {"probes": {"x": {"passed": False}}}
    none = pairwise_agreement(security_sets(trials, "skills"))
    checks.append(("security agreement counts two empty sets as agreement "
                   "and leaves out an unmeasured trial",
                   (alike, none) == (1.0, 0.0), (alike, none)))

    def results(verdict, within):
        contrast = {"verdict": verdict, "non_inferior": {"within": within}}
        return {key: {"skills-hybrid": contrast, "reference-hybrid": contrast}
                for key in ROUND5_ROWS}
    readings = [
        ("held everywhere supports H1 and refutes H3",
         results("no improvement shown", True), "supported", "refuted"),
        ("a worse row refutes H1 and supports H3",
         results("worse", False), "refuted", "supported"),
        ("an open row leaves both inconclusive",
         results("no improvement shown", False), "inconclusive",
         "inconclusive"),
    ]
    for label, planted, h1, h3 in readings:
        got = (hypothesis(planted, "skills-hybrid", "held")[0],
               hypothesis(planted, "reference-hybrid", "worse")[0])
        checks.append((label, got == (h1, h3), got))

    # A rendered five-arm run prints all three agreements for every arm.
    run = {trial_name(arm, index): {
        "scores": {"adherence": {"value": 1, "items": {"a": True}},
                   "python_files": {"value": ["app.py"], "missing": None}},
        "change": None, "judge": None,
        "security": {"probes": {"x": {"passed": True}}}}
        for arm in ("none", "reference", "inline", "hybrid", "skills")
        for index in range(1, 4)}
    _, _, text = rendered(run, 0, {})
    section = text[text.find("## Round 5"):]
    checks.append(("a five-arm report prints conventions, structure and "
                   "security agreement for every arm",
                   "Structure agreement | Security agreement" in section
                   and all("| %s |" % arm in section and
                           "1.00 (3) | 1.00 | 1.00 |" in section
                           for arm in ("none", "reference", "inline",
                                       "hybrid", "skills")),
                   section[:600]))

    # Round 5 registers its K, so a run short of it is part-run.
    runs = " ".join(text[text.find("## Runs per arm"):][:400].split())
    checks.append(("a round-5 run short of its K names the blocks still owed",
                   "## The escalation" not in text
                   and "blocks %d to %d" % (4, ROUND5_K) in runs, runs))

    # From six blocks a run's intervals are no longer only descriptions.
    longer = {trial_name(arm, index): dict(run[trial_name(arm, 1)])
              for arm in ("none", "reference", "inline", "hybrid", "skills")
              for index in range(1, FEWEST_DECIDING + 1)}
    _, _, text = rendered(longer, 0, {})
    head = text.split("\n## ")[0]
    checks.append(("from six blocks no interval is called descriptive",
                   "descriptive" not in head
                   and "95 % bootstrap interval" in head, head[-300:]))

    # Fourteen whole blocks and one trial of the fifteenth are not the
    # round: completeness is every registered arm in every block.
    almost = {trial_name(arm, index): {} for arm in ROUND5_RUN
              for index in range(1, ROUND5_K)}
    almost[trial_name("none", ROUND5_K)] = {}
    gap = dict(almost)
    del gap[trial_name("skills", 7)]
    whole = dict(almost, **{trial_name(arm, ROUND5_K): {}
                            for arm in ROUND5_RUN})
    got = [owed_blocks(run) for run in (almost, gap, whole)]
    named = blocks_section(almost)
    checks.append(("one trial of the last block leaves the round part-run",
                   got == [[ROUND5_K], [7, ROUND5_K], []]
                   and "block %d still misses" % ROUND5_K in "\n".join(named)
                   and blocks_named([2, 7, 9, 10, 11]) ==
                   "blocks 2, 7 and 9 to 11", (got, named)))

    # Fifteen runs with two under the bare arm's mean: each is named with its
    # rate, lowest first, and the finding row counts them.
    values = {"none": {index: 1.0 for index in range(1, ROUND5_K + 1)},
              "skills": {index: 1.0 for index in range(1, ROUND5_K + 1)}}
    values["skills"][3] = 0.5
    values["skills"][4] = 0.0
    planted = {"task_success": {"values": values}}
    for key in ("judge_security", "adherence", "cost_usd"):
        planted[key] = {"values": {"none": {1: 1.0}, "skills": {1: 2.0}}}
    verdicts = {key: {"skills-none": {"verdict": verdict}} for key, verdict in
                (("task_success", "worse"), ("judge_security", "better"),
                 ("adherence", "no improvement shown"), ("cost_usd", "worse"))}
    got = (low_runs(planted, "skills"),
           finding_row(planted, verdicts, "skills", "Worse", 1351),
           finding_row(planted, verdicts, "none", None, None))
    checks.append(("each low run is named, and the row counts and marks them",
                   got == ([0.0, 0.5],
                           ["`skills`", "1,351 lines", "Worse",
                            "90 % ▼ (2 runs low)", "2.0 ▲", "200 %",
                            "$2.00 ▼"],
                           ["`none`", "no file", "—", "100 %", "1.0", "100 %",
                            "$1.00"]), got))
    got = report_text(["# Report", "", "Body.", "", ""], 88)
    checks.append(("a report ends in one newline, however its last section "
                   "ends", got == "# Report\n\nBody.\n", got))
    return checks


def failed_build_checks():
    """A build that did not install reads no judge row; one that did reads
    its judgings."""
    judging = {"answer": {"rubric": {"security": {"score": 1}}}}
    failed = {"scores": {"install": {"value": False}}, "judge": judging,
              "judgings": [judging]}
    built = {"scores": {"install": {"value": True}}, "judge": judging,
             "judgings": [judging]}
    got = (judge_score(failed, "security"), judge_score(built, "security"))
    return [("a build that did not install has its judge rows missing",
             got == (None, 1), got)]


def record_checks():
    """A report into any docs/audits/ needs the round archived, and one with
    neither a templates source nor --out-dir is refused."""
    scratch = tempfile.mkdtemp(prefix="efficacy-report-record-")
    audits = os.path.join(scratch, "templates", *AUDITS)
    checks = [("any docs/audits directory is a round's record",
               is_record(audits) and not is_record(scratch), audits)]
    root = os.path.join(scratch, "run")
    scores = os.path.join(scoring_area(root), "scores")
    os.makedirs(scores)
    with io.open(os.path.join(scores, "none-1.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"name": "none-1"}, handle)

    def quietly(argv):
        saved, sys.stdout = sys.stdout, io.StringIO()
        try:
            return main(argv), sys.stdout.getvalue()
        finally:
            sys.stdout = saved
    code, printed = quietly(["--root", root, "--out-dir", audits])
    checks.append(("a report into a templates source's docs/audits needs "
                   "the stamp", code == 2 and "not been archived" in printed
                   and not os.path.exists(audits), printed[:200]))
    source = os.environ.pop(TEMPLATES_ENV, None)
    try:
        code, printed = quietly(["--root", root])
    finally:
        if source is not None:
            os.environ[TEMPLATES_ENV] = source
    checks.append(("with no templates source and no --out-dir it refuses",
                   code == 2 and "no templates source" in printed,
                   printed[:200]))
    shutil.rmtree(scratch, ignore_errors=True)
    return checks


def context_lines(arm):
    """The line count of the context file an arm's trials received, None
    where the arm receives none."""
    context = ARMS[arm]["context"]
    if not context:
        return None
    with io.open(os.path.join(ARMS_DIR, context), encoding="utf-8") as handle:
        return len(handle.read().splitlines())


def answer(verdicts):
    """One word from the verdicts of the primary dimensions and task success:
    Worse where any is worse, Yes where any is better and none worse, No
    where none is better, Not measured where none was computed."""
    if "worse" in verdicts:
        return "Worse"
    if "better" in verdicts:
        return "Yes"
    if all(verdict in ("not computed", CROSSING_VERDICT)
           for verdict in verdicts):
        return "Not measured"
    return "No"


def arm_mean(table, key, arm):
    """The mean of one arm's measured values of a metric, None where none."""
    values = [value for value in table[key]["values"].get(arm, {}).values()
              if value is not None]
    return statistics.fmean(values) if values else None


def signed(value):
    """A paired difference with its sign, to one decimal, a whole number
    printed as one: +1, -0.7."""
    text = "%+.1f" % value
    return text[:-2] if text.endswith(".0") else text


def runs(count):
    """`run` or `runs`, as a count of them reads."""
    return "run" if count == 1 else "runs"


# The finding table's measure columns: the heading, the metric, and how an
# arm's mean is printed. One primary from the judge, the suite, adherence
# and cost: the four a reader weighs a file by at a glance.
FINDING_COLUMNS = (
    ("Hidden tests passed", "task_success",
     lambda mean: "%d %%" % round(100 * mean)),
    ("Security, judge 1–5", "judge_security", lambda mean: "%.1f" % mean),
    ("Adherence", "adherence", lambda mean: "%d %%" % round(100 * mean)),
    ("Cost per trial", "cost_usd", lambda mean: "$%.2f" % mean),
)

# A verdict against the bare arm, as the mark the finding table prints.
MARKS = {"better": " ▲", "worse": " ▼"}


def low_runs(table, arm):
    """The arm's hidden-suite rates under the bare arm's mean by more than
    the practical threshold, lowest first."""
    bare = arm_mean(table, "task_success", BARE)
    if bare is None:
        return []
    values = table["task_success"]["values"].get(arm, {}).values()
    return sorted(value for value in values
                  if value is not None and value < bare - SUITE_DIP)


def finding_row(table, results, arm, answered, length):
    """One arm's cells in the finding table: its name, its file, its verdict
    and each measure's mean, marked by the verdict against the bare arm."""
    if arm == BARE:
        cells = ["`%s`" % arm, "no file", "—"]
    else:
        cells = ["`%s`" % arm,
                 "%s lines" % format(length, ",") if length else NOT_MEASURED,
                 answered]
    for _, key, show in FINDING_COLUMNS:
        mean = arm_mean(table, key, arm)
        if mean is None:
            cells.append(NOT_MEASURED)
            continue
        cell = show(mean)
        if arm != BARE:
            cell += verdict_mark(results[key]["%s-%s" % (arm, BARE)])
        if key == "task_success" and arm != BARE:
            low = low_runs(table, arm)
            if low:
                cell += " (%d %s low)" % (len(low), runs(len(low)))
        cells.append(cell)
    return cells


def reading(answers, lengths):
    """The columns read together: what the longest and the shortest measured
    file each did for quality."""
    measured = [arm for arm in answers
                if answers[arm] != "Not measured" and lengths.get(arm)]
    if len(measured) < 2:
        return NOT_MEASURED
    longer = max(measured, key=lengths.get)
    shorter = min(measured, key=lengths.get)
    if answers[shorter] == "Yes" and answers[longer] != "Yes":
        return ("length is not quality — the long file spent the agent's "
                "attention on conventions, the short one on the code")
    if answers[shorter] == "Yes":
        return "a context file adds quality, long or short"
    if answers[longer] == "Yes":
        return "the long file added quality, the short one did not"
    return "neither file added quality"


# What a why-line says a file built beyond the task, the work that took,
# the follow-up change's churn, and what the judge read — each phrase said
# only where its metric was read better or worse.
STRUCTURE = (("more files", "tracked_files"), ("more code", "source_lines"),
             ("more files", "app_files"), ("more code", "app_lines"),
             ("more public names beyond the spec", "surface_extra"))
EFFORT = (("turns", "turns"), ("tokens", "output_tokens"),
          ("time", "wall_seconds"), ("cost", "cost_usd"))
CHURN = ("churn_files", "churn_lines", "change_cost_usd")
READS = (("judge_readability", "more readable"),
         ("judge_design", "better designed"),
         ("judge_maintainability", "more maintainable"),
         ("judge_security", "more secure"),
         ("judge_data_protection", "more careful with personal data"),
         ("judge_tests", "better tested"))

# A context file of at most this many lines is one the why-line calls a few
# rules the agent could hold.
SHORT_FILE = 60


def read_as(results, name, key, verdict):
    return results.get(key, {}).get(name, {}).get("verdict") == verdict


def counted(n):
    """A small count as a word, a larger one as digits."""
    return COUNTED[n] if n < len(COUNTED) else str(n)


def boot_failures(trials, arm):
    """The recorded error of each of an arm's scored trials whose app could
    not boot, and how many scored trials the arm has."""
    errors, count = [], 0
    for name, trial in sorted(trials.items()):
        if arm_of(name) != arm or not trial["scores"]:
            continue
        count += 1
        if path(trial, "scores", "boot", "value", "factory") is False:
            errors.append(path(trial, "scores", "boot", "value",
                               "factory_error") or "no error recorded")
    return errors, count


def why_line(trials, results, arm, name, answered, length):
    """Why a file arm scored as it did, in words. Each sentence stands on a
    verdict or a record below: a clean install that could not boot, structure
    built beyond the task and the work it took, what the judge read, wins
    only a tool counts, and patterns missed. The numbers stay in the table.
    """
    sentences = []
    errors, count = boot_failures(trials, arm)
    if errors:
        # A missing module after an install that passed is a dependency the
        # project declared wrongly, not one the environment lacked.
        cause = ("declared its dependencies so that a clean install left "
                 "the app unable to boot"
                 if errors[0].startswith("ModuleNotFoundError")
                 else "left the app unable to boot (`%s`)" % errors[0])
        sentences.append("%s %s of %s %s." % (
            counted(len(errors)).capitalize(), runs(len(errors)),
            counted(count), cause))

    built = [word for word, key in STRUCTURE
             if read_as(results, name, key, "worse")]
    effort = [word for word, key in EFFORT
              if read_as(results, name, key, "worse")]
    churned = any(read_as(results, name, key, "worse") for key in CHURN)
    if built:
        text = "It built more than the task asked for: %s" % spoken(built)
        if effort:
            text += ", and took more %s to do it" % spoken(effort)
        if churned:
            text += ("; the follow-up change had to move through that "
                     "structure too")
        sentences.append(text + ".")

    judge = [words for key, words in READS
             if read_as(results, name, key, "better")]
    computed = any(not read_as(results, name, key, "not computed")
                   for key in PRIMARY)
    wins = [key for key, _, _, _ in METRICS
            if read_as(results, name, key, "better")]
    judged = [key for key in wins if key.startswith(("judge_", "patterns_"))]
    tail = []
    if wins and not judged:
        tail.append("every win is something a tool counts")
    if read_as(results, name, "patterns_missed", "worse"):
        tail.append("it missed more of the patterns the domain called for")
    if judge:
        lead = "the judge read its code as %s" % spoken(judge)
        if answered == "Yes" and length is not None and length <= SHORT_FILE:
            lead = "A few rules the agent could hold: " + lead
        if not built:
            lead += ", and its code grew no more than its size margin allows"
            if effort:
                lead += " — for more %s" % spoken(effort)
    elif computed:
        lead = ("the judge saw none of it as better design, readability, "
                "maintainability, security or data protection")
    elif not built and effort:
        lead = "it took more %s than without a file" % spoken(effort)
    else:
        lead = ""
    closing = "; ".join(part for part in (lead, spoken(tail) if tail else "")
                        if part)
    if closing:
        sentences.append(closing[0].upper() + closing[1:] + ".")
    text = " ".join(sentences) if sentences else "Nothing below separates it."
    return "**`%s`, %s.** %s" % (arm, answered, text)


# The radar's axes: the verdict vector's rows, clustered by what a reader
# asks of a build, in a fixed order. A radar's shape depends on the order of
# its axes, so the order is the code's and never the data's. Per-KLOC rows
# stand for their totals, so one measure counts once.
RADAR_AXES = (
    ("Reliability", ("task_success", "install")),
    ("Security", ("judge_security", "security_probe_pass_rate",
                  "csrf_refused", "xss_inert", "bandit_per_kloc")),
    ("Data protection", ("judge_data_protection",
                         "data_protection_probe_pass_rate")),
    ("Design", ("judge_design", "judge_srp", "judge_ocp", "judge_lsp",
                "judge_isp", "judge_dip", "judge_errors", "judge_naming",
                "patterns_missed", "layering_violations", "mutual_imports")),
    ("Maintainability", ("judge_maintainability", "judge_readability",
                         "mypy_per_kloc", "ruff_per_kloc", "complexity_max",
                         "complexity_over_15_per_kloc", "mean_cc",
                         "unused_per_kloc")),
    ("Tests", ("judge_tests", "coverage")),
    ("Economy", ("cost_usd", "output_tokens", "turns", "wall_seconds")),
)

# Round 5d's axes. Reliability reads working builds, so install gives way to
# it. Output tokens move with turns and wall time with cost, so economy keeps
# cost and turns, and the other two stay in the tables.
ROUND5D_RADAR_AXES = tuple(
    (axis, ("reliability", "task_success") if axis == "Reliability"
     else ("cost_usd", "turns") if axis == "Economy" else keys)
    for axis, keys in RADAR_AXES)

# The verdicts an axis counts: a withheld or uncomputed one is no evidence
# either way, so it is left out of the share rather than read as no change.
COUNTED_VERDICTS = ("better", "worse", "held", "no improvement shown")

# The radar's two themes, from the reference palette: GitHub shows the one
# matching the reader's theme, by the suffix on each image's address.
RADAR_THEMES = {
    "light": {"surface": "#fcfcfb", "text": "#0b0b0b", "secondary": "#52514e",
              "muted": "#898781", "grid": "#c8c7c0", "series": "#2a78d6"},
    "dark": {"surface": "#1a1a19", "text": "#f0efec", "secondary": "#c3c2b7",
             "muted": "#898781", "grid": "#55544f", "series": "#3987e5"},
}


def radar_axes(results):
    """The radar's axes for these contrasts: round 5d's where they carry a
    size, as only round 5d's do, and the earlier rounds' otherwise."""
    sized = any("size" in contrast for per in results.values()
                for contrast in per.values())
    return ROUND5D_RADAR_AXES if sized else RADAR_AXES


def cluster_scores(results, name):
    """Per radar axis, in order, from -1 to +1, or None where no row has a
    verdict: the mean of its rows' sizes where the contrasts carry them, as
    round 5d's do, and otherwise the share of its rows better than the bare
    arm minus the share worse."""
    sized = any("size" in per.get(name, {}) for per in results.values())
    scores = []
    for axis, keys in ROUND5D_RADAR_AXES if sized else RADAR_AXES:
        rows = [results[key][name] for key in keys
                      if name in results.get(key, {})]
        counted = [contrast for contrast in rows
                   if contrast["verdict"] in COUNTED_VERDICTS]
        if sized:
            sizes = [contrast["size"] for contrast in counted
                     if contrast.get("size") is not None]
            scores.append((axis, statistics.fmean(sizes) if sizes else None))
            continue
        verdicts = [contrast["verdict"] for contrast in counted]
        scores.append((axis, (verdicts.count("better") - verdicts.count("worse"))
                       / len(verdicts) if verdicts else None))
    return scores


def radar_svg(panels, theme):
    """One SVG of small radars, one per arm, two to a row: `panels` holds
    (arm, title, scores) with scores as `cluster_scores` gives them."""
    colors = RADAR_THEMES[theme]
    width, size, radius = 1000, 370, 108
    rows = (len(panels) + 1) // 2
    top = 50
    height = top + rows * size
    count = len(RADAR_AXES)

    def point(cx, cy, value, index):
        # -1 sits at the centre, 0 (the bare arm) halfway, +1 on the rim.
        angle = -math.pi / 2 + 2 * math.pi * index / count
        reach = radius * (value + 1) / 2
        return cx + reach * math.cos(angle), cy + reach * math.sin(angle)

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family="-apple-system, Segoe UI, '
           'Helvetica, Arial, sans-serif">' % (width, height, width, height),
           '<rect width="100%%" height="100%%" fill="%s"/>' % colors["surface"]]

    # One key for every panel: the dashed ring is the bare arm.
    out.append('<line x1="%d" y1="25" x2="%d" y2="25" stroke="%s" '
               'stroke-width="1.5" stroke-dasharray="4 3"/>'
               % (width / 2 - 210, width / 2 - 180, colors["secondary"]))
    out.append('<text x="%d" y="25" dominant-baseline="middle" font-size="14" '
               'fill="%s">%s, the ring at 0</text>'
               % (width / 2 - 172, colors["secondary"], BARE))
    out.append('<line x1="%d" y1="25" x2="%d" y2="25" stroke="%s" '
               'stroke-width="2"/>' % (width / 2 + 10, width / 2 + 40,
                                       colors["series"]))
    out.append('<text x="%d" y="25" dominant-baseline="middle" font-size="14" '
               'fill="%s">the arm; outside the ring is better</text>'
               % (width / 2 + 48, colors["secondary"]))
    for place, (arm, title, scores) in enumerate(panels):
        cx = (place % 2) * (width / 2) + width / 4
        cy = top + (place // 2) * size + size / 2 + 12
        out.append('<text x="%.1f" y="%.1f" text-anchor="middle" '
                   'font-size="18" font-weight="600" fill="%s">%s</text>'
                   % (cx, cy - radius - 50, colors["text"], escape(title)))
        for ring in (-0.5, 0.5, 1.0):
            ring_points = [point(cx, cy, ring, index) for index in range(count)]
            out.append('<polygon points="%s" fill="none" stroke="%s" '
                       'stroke-width="1"/>' % (" ".join(
                           "%.1f,%.1f" % xy for xy in ring_points),
                           colors["grid"]))
        for index, (axis, _) in enumerate(scores):
            x, y = point(cx, cy, 1.0, index)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                       'stroke="%s" stroke-width="1"/>'
                       % (cx, cy, x, y, colors["grid"]))
            lx, ly = point(cx, cy, 1.32, index)
            anchor = ("middle" if abs(lx - cx) < 8
                      else "start" if lx > cx else "end")
            out.append('<text x="%.1f" y="%.1f" text-anchor="%s" '
                       'dominant-baseline="middle" font-size="15" '
                       'fill="%s">%s</text>'
                       % (lx, ly, anchor, colors["secondary"], escape(axis)))

        # The bare arm is the ring at zero, dashed, so outside it is better.
        zero = [point(cx, cy, 0.0, index) for index in range(count)]
        out.append('<polygon points="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5" stroke-dasharray="4 3"/>'
                   % (" ".join("%.1f,%.1f" % xy for xy in zero),
                      colors["secondary"]))
        shape = [point(cx, cy, value if value is not None else 0.0, index)
                 for index, (_, value) in enumerate(scores)]
        out.append('<polygon points="%s" fill="%s" fill-opacity="0.22" '
                   'stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
                   % (" ".join("%.1f,%.1f" % xy for xy in shape),
                      colors["series"], colors["series"]))
        for (x, y), (_, value) in zip(shape, scores):
            out.append('<circle cx="%.1f" cy="%.1f" r="4" fill="%s" '
                       'stroke="%s" stroke-width="2"/>'
                       % (x, y, colors["surface"] if value is None
                          else colors["series"], colors["series"]))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def radar_table(results, arms):
    """The radar's scores as a table, one row per axis and a column per arm,
    with the rows each axis clusters: the radar's text view."""
    labels = {key: label for key, label, _, _ in METRICS}
    scored = {arm: dict(cluster_scores(results, "%s-%s" % (arm, BARE)))
              for arm in arms}
    lines = ["| Axis | %s | Rows |" % " | ".join("`%s`" % arm for arm in arms),
             "| --- | %s | --- |" % " | ".join("---" for _ in arms)]
    for axis, keys in radar_axes(results):
        lines.append("| %s | %s | %s |" % (
            axis, " | ".join(axis_score(scored[arm][axis]) for arm in arms),
            "; ".join(labels.get(key, key) for key in keys)))
    return lines


def axis_score(value):
    """An axis score as the radar's table prints it: signed, two places,
    zero unsigned, a dash where the axis has no verdict."""
    if value is None:
        return "—"
    return "0.00" if value == 0 else "%+.2f" % value


def escape(text):
    """Text as an SVG element holds it."""
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def by_cost(table, arms):
    """The arms from the cheapest to the dearest, any without a cost last."""
    def cost(arm):
        mean = arm_mean(table, "cost_usd", arm)
        return (mean is None, mean or 0.0)
    return sorted(arms, key=cost)


# A row's full scale in words, from the constants the radar draws with, so
# the caption can never name a scale the drawing does not use.
FULL_SCALES = (
    "%g point for a judge score, %g pp for a share, %g points for coverage, "
    "and a factor of %g for a count or a cost"
    % (JUDGE_SCALE, 100 * SHARE_SCALE, COVERAGE_SCALE, RATIO_SCALE))

# How to read a radar drawn by size, under it.
RADAR_SIZE_READING = (
    "One radar per arm, from the cheapest to the dearest. Each axis is the "
    "mean of its rows' moves against `%s`: each row's interval bound nearest "
    "zero over the row's full scale, from -1 at the centre to +1 at the rim, "
    "and 0 where the interval crosses zero. A row's full scale is %s, so a "
    "reader can work any axis out from the intervals below. The dashed ring "
    "is `%s`, so outside it is better. A hollow point is an axis with no "
    "verdict. The rows behind each axis, and every number, are in the "
    "sections below." % (BARE, FULL_SCALES, BARE))

# How to read the radar, under it.
RADAR_READING = (
    "One radar per arm, from the cheapest to the dearest. Each axis is a "
    "cluster of the verdict vector's rows: the share of them better than "
    "`%s` minus the share worse, from -1 at the centre to +1 at the rim. The "
    "dashed ring is `%s`, so outside it is better. A hollow point is an axis "
    "with no verdict. The rows behind each axis, and every number, are in "
    "the sections below." % (BARE, BARE))


def radar_panels(table, results, active):
    """The radar's panels: each file arm against the bare arm, from the
    cheapest to the dearest, with its verdict in the title."""
    arms = [pair[0] for pair in active if pair[1] == BARE]
    panels = []
    for arm in by_cost(table, arms):
        name = "%s-%s" % (arm, BARE)
        verdict = answer([results[key][name]["verdict"] for key in ANSWERED])
        panels.append((arm, "%s — %s" % (arm, verdict),
                       cluster_scores(results, name)))
    return panels


# The quality radar on ISO/IEC 25010:2023, from round 6. Eight axes in the
# standard's own order, each the share of its targets met, read against the
# bare arm. Safety, the ninth characteristic, does not apply to this backend.
# Each sub-characteristic lists its targets as (what it asks, where the value
# comes from, the pass condition): a metric row by its key, or a probe by
# `probe:<name>`. A target is met, not met, or not measured, and a
# sub-characteristic with no target reads not measured, never 0 %.
AT_LEAST, AT_MOST = ">=", "<="
ISO_AXES = (
    ("Functionality", (
        ("Functional completeness", (
            ("every specified name is exported", "surface_missing",
             AT_MOST, 0),)),
        ("Functional correctness", (
            ("the hidden suite passes at 98 % or more", "task_success",
             AT_LEAST, 0.98),)),
        ("Functional appropriateness", (
            ("nothing nobody asked for is delivered", "unasked_artifacts",
             AT_MOST, 0),)),
    )),
    ("Performance", (
        ("Time behaviour", ()),
        ("Resource utilisation", (
            ("the invoice builder answers in 100 KB or less",
             "builder_bytes", AT_MOST, 100000),
            ("the invoice builder makes at most 3 subrequests",
             "builder_subrequests", AT_MOST, 3),)),
        ("Capacity", ()),
    )),
    ("Compatibility", (
        ("Co-existence", ()),
        ("Interoperability", ()),
    )),
    ("Usability", (
        ("Appropriateness recognisability", ()),
        ("Learnability", ()),
        ("Operability", (
            ("the HTML is valid", "html_invalid", AT_MOST, 0),)),
        ("User error protection", ()),
        ("User assistance", ()),
        ("Self-descriptiveness", ()),
        ("Inclusivity", (
            ("no WCAG 2.1 AA violation", "axe_violations", AT_MOST, 0),)),
    )),
    ("Reliability", (
        ("Faultlessness", (
            ("installs and boots", "reliability", AT_LEAST, 1.0),
            ("at most 10 type errors per KLOC under --strict",
             "mypy_per_kloc", AT_MOST, 10),)),
        ("Availability", ()),
        ("Fault tolerance", (
            ("a malformed request leaks no stack trace",
             "probe:error_leakage", AT_LEAST, 1.0),)),
        ("Recoverability", ()),
    )),
    ("Security", (
        ("Confidentiality", (
            ("passwords are hashed at rest", "probe:password_at_rest",
             AT_LEAST, 1.0),
            ("sign-in does not tell an account from a stranger",
             "probe:account_enumeration", AT_LEAST, 1.0),
            ("no hard-coded secret key", "probe:secret_key", AT_LEAST, 1.0),
            ("the session cookie carries its flags", "probe:cookie_flags",
             AT_LEAST, 1.0),)),
        ("Integrity", (
            ("sign-in refuses a post without a token", "probe:sign_in_csrf",
             AT_LEAST, 1.0),
            ("a form refuses a post without a token", "csrf_refused",
             AT_LEAST, 1.0),
            ("no open redirect", "probe:open_redirect", AT_LEAST, 1.0),
            ("no SQL assembled from strings", "probe:sql_strings",
             AT_LEAST, 1.0),
            ("a stored payload renders inert", "xss_inert",
             AT_LEAST, 1.0),)),
        ("Non-repudiation", ()),
        ("Accountability", ()),
        ("Authenticity", ()),
        ("Resistance", (
            ("debug is off", "probe:debug", AT_LEAST, 1.0),
            ("the security headers are set", "probe:security_headers",
             AT_LEAST, 1.0),
            ("no vulnerable dependency", "probe:vulnerable_dependencies",
             AT_LEAST, 1.0),
            ("no high or medium bandit finding", "bandit_serious",
             AT_MOST, 0),
            ("the judge reads its security as 3 or better",
             "judge_security", AT_LEAST, 3.0),)),
        ("Data protection", (
            ("personal data stays out of the log", "probe:log_leak",
             AT_LEAST, 1.0),
            ("erasure leaves no residue", "probe:erasure_residue",
             AT_LEAST, 1.0),
            ("an export holds its own data only", "probe:export_scope",
             AT_LEAST, 1.0),
            ("the judge reads its data protection as 3 or better",
             "judge_data_protection", AT_LEAST, 3.0),)),
    )),
    ("Maintainability", (
        ("Modularity", (
            ("no module import tariff loads reaches Flask or the database",
             "layering_violations", AT_MOST, 0),
            ("no two modules import each other", "mutual_imports",
             AT_MOST, 0),
            ("the judge reads its design as 3 or better", "judge_design",
             AT_LEAST, 3.0),
            ("the judge reads its single responsibility as 3 or better",
             "judge_srp", AT_LEAST, 3.0),)),
        ("Reusability", ()),
        ("Analysability", (
            ("at most 100 lint findings per KLOC", "ruff_per_kloc",
             AT_MOST, 100),
            ("the formatter would change no file", "unformatted",
             AT_MOST, 0),
            ("no function over cognitive complexity 15",
             "complexity_over_15", AT_MOST, 0),
            ("half the definitions carry a docstring", "docstrings",
             AT_LEAST, 50),
            ("the judge reads its readability as 3 or better",
             "judge_readability", AT_LEAST, 3.0),)),
        ("Modifiability", (
            ("no conditional ladder over rule kinds", "kind_ladders",
             AT_MOST, 0),
            ("no boolean parameter", "bool_parameters", AT_MOST, 0),
            ("at most 5 unused names per KLOC", "unused_per_kloc",
             AT_MOST, 5),
            ("the judge reads its maintainability as 3 or better",
             "judge_maintainability", AT_LEAST, 3.0),
            ("the judge reads its openness to extension as 3 or better",
             "judge_ocp", AT_LEAST, 3.0),
            ("the change task passes 90 % of its checks", "change_success",
             AT_LEAST, 0.9),
            ("the change task keeps 98 % of the build suite",
             "change_regression", AT_LEAST, 0.98),)),
        ("Testability", (
            ("its own tests pass", "own_tests_pass", AT_LEAST, 1.0),
            ("its own tests cover 80 % of the lines", "coverage",
             AT_LEAST, 80),
            ("the judge reads its tests as 3 or better", "judge_tests",
             AT_LEAST, 3.0),)),
        ("Observability", ()),
    )),
    ("Flexibility", (
        ("Adaptability", ()),
        ("Scalability", ()),
        ("Installability", (
            ("pip install . succeeds in a clean environment", "install",
             AT_LEAST, 1.0),)),
        ("Replaceability", ()),
        ("Deploy and rollback", ()),
    )),
)

# A sub-characteristic with fewer targets than this is marked in its table:
# a single target swings it between 0 and 100 %.
ENOUGH_TARGETS = 3

# The axis a broken build counts against. A build that does not install or
# boot fails Reliability's first target and is left out of every other axis,
# so one failure is counted once.
BROKEN_AXIS = "Reliability"

# The ISO radar's margins, in points of an axis's share, sized before round 6
# from round 5c's trial-to-trial noise: half the pooled within-arm standard
# deviation of each axis's per-trial score over its 75 trials, rounded up to
# a whole point, and never under 5 points, so an axis the pilot's trials
# could not shake, or did not measure, still needs a visible move.
# Reliability's 7 is one build of 15, the margin round 5d gave it too.
ISO_MARGINS = {
    "Functionality": 5, "Performance": 5, "Compatibility": 5, "Usability": 5,
    "Reliability": 7, "Security": 5, "Maintainability": 5, "Flexibility": 5,
}

# The ISO radar's own colours, over each theme's palette. Better and worse
# differ in shape as well as colour, filled up and hollow down, so the chart
# reads the same printed in black and white.
ISO_COLOURS = {
    "light": {"target": "#2e7d32", "better": "#2e7d32", "worse": "#c62828",
              "bare": "#52514e", "fill": "#dbe8f8"},
    "dark": {"target": "#66bb6a", "better": "#66bb6a", "worse": "#ef5350",
             "bare": "#c3c2b7", "fill": "#2a3d5c"},
}

# The readings the ISO radar rows add to the metric rows.
ISO_EXTRA = {
    "own_tests_pass": lambda t: boolean(t, "coverage", "tests_passed"),
}


def iso_targets():
    """Every target of the ISO radar, as (axis, sub-characteristic, what it
    asks, source, condition, threshold)."""
    return [(axis, sub, asks, source, condition, threshold)
            for axis, subs in ISO_AXES for sub, targets in subs
            for asks, source, condition, threshold in targets]


def iso_value(trial, source):
    """A target's value for one trial: a metric row's reading, a probe's
    pass, or a reading of the radar's own; None where not measured."""
    if source.startswith("probe:"):
        probes = (trial.get("security") or {}).get("probes") or {}
        passed = (probes.get(source[len("probe:"):]) or {}).get("passed")
        return None if passed is None else (1.0 if passed else 0.0)
    if source in ISO_EXTRA:
        accessor = ISO_EXTRA[source]
    else:
        accessor = next((getter for key, _, _, getter in METRICS
                         if key == source), None)
        if accessor is None:
            return None
    try:
        return accessor(trial)
    except (TypeError, KeyError, ValueError):
        return None


def target_met(trial, source, condition, threshold):
    """Whether one trial meets a target: True, False, or None where its
    value was not measured."""
    value = iso_value(trial, source)
    if value is None:
        return None
    return value >= threshold if condition == AT_LEAST else value <= threshold


def iso_trial_scores(trial, withdrawn=()):
    """One trial on every axis, as {axis: {sub-characteristic: score}}.

    A sub-score is the share of its targets met, over the targets measured,
    and None where none was. A broken build is scored on Reliability alone,
    where the install target fails, and reads None on every other axis. A
    target reading a metric in `withdrawn` is not measured.
    """
    broken = works(trial) != 1.0
    scores = {}
    for axis, subs in ISO_AXES:
        per_sub = {}
        for sub, targets in subs:
            if broken and axis != BROKEN_AXIS:
                per_sub[sub] = None
                continue

            # A withdrawn metric's number is no result, on the radar as in
            # the tables, so its target drops out rather than reads as met.
            met = [target_met(trial, source, condition, threshold)
                   for _, source, condition, threshold in targets
                   if source not in withdrawn]
            measured = [outcome for outcome in met if outcome is not None]
            per_sub[sub] = (sum(measured) / len(measured) if measured
                            else None)
        scores[axis] = per_sub
    return scores


def iso_axis_score(per_sub):
    """An axis's score for one trial, in points from 0 to 100: the mean of
    its measured sub-scores, so each sub-characteristic weighs the same
    however many targets it has; None where none was measured."""
    measured = [score for score in per_sub.values() if score is not None]
    return 100.0 * statistics.fmean(measured) if measured else None


def iso_table(trials, withdrawn=()):
    """The ISO axes as rows of a table, one row per axis under the key
    `iso:<axis>`, each trial's score in points, better up, so the contrast
    machinery reads them like any other row; `withdrawn` names the metrics
    no target may read."""
    table = {}
    for axis, _ in ISO_AXES:
        table["iso:" + axis] = {"label": axis, "direction": UP, "values": {}}
    for name, trial in sorted(trials.items()):
        scores = iso_trial_scores(trial, withdrawn)
        for axis, _ in ISO_AXES:
            row = table["iso:" + axis]["values"]
            row.setdefault(arm_of(name), {})[index_of(name)] = iso_axis_score(
                scores[axis])
    return table


def iso_margins(table):
    """The ISO margins as the contrast machinery takes them, absolute, in
    points."""
    return {"iso:" + axis: ("%d points" % points, float(points), ABSOLUTE)
            for axis, points in ISO_MARGINS.items()}


def iso_contrasts(table, seed, crossed=()):
    """Each file arm's ISO rows against the bare arm: the difference of
    arm means, its interval, and its verdict past the axis's margin; paired
    within a round and unpaired across rounds."""
    labels = ["%s-%s" % (treatment, baseline)
              for treatment, baseline in CONTRASTS if baseline == BARE]
    return contrasts(table, seed, crossed, iso_margins(table), True,
                     only=labels)


def iso_marker(contrast):
    """The marker an axis carries against the bare arm: `better` past the
    margin upward, `worse` past it downward, `dot` otherwise, and None where
    the contrast could not be read."""
    verdict = contrast.get("verdict")
    if verdict == "better":
        return "better"
    if verdict == "worse":
        return "worse"
    if verdict in COUNTED_VERDICTS:
        return "dot"
    return None


def iso_panels(table, iso, results, active):
    """The ISO radar's panels, one per file arm against the bare arm, from
    the cheapest to the dearest: (arm, cost line, axes), each axis as (name,
    score, bare score, marker, difference)."""
    arms = [pair[0] for pair in active if pair[1] == BARE]
    bare_cost = arm_mean(table, "cost_usd", BARE)
    panels = []
    for arm in by_cost(table, arms):
        name = "%s-%s" % (arm, BARE)
        cost = arm_mean(table, "cost_usd", arm)
        axes = []
        for axis, _ in ISO_AXES:
            key = "iso:" + axis
            score, bare = arm_mean(iso, key, arm), arm_mean(iso, key, BARE)
            contrast = results.get(key, {}).get(name, {})
            marker = (iso_marker(contrast) if score is not None
                      and bare is not None else None)

            # The move shown is the contrast's own mean, over the blocks it
            # paired, so its sign agrees with the marker where a broken
            # build left the two arms' means over different blocks.
            axes.append((axis, score, bare, marker,
                         None if marker is None else contrast.get("mean")))
        panels.append((arm, cost_line(cost, bare_cost), axes))
    return panels


def cost_line(cost, bare_cost):
    """The cost line above a panel: dollars per run, and the multiple of the
    bare arm's; shown, never scored."""
    if cost is None:
        return "cost not measured"
    line = "$%.2f/run" % cost
    if bare_cost:
        line += ", %.1fx %s" % (cost / bare_cost, BARE)
    return line


def iso_radar_svg(panels, theme):
    """One SVG of ISO radars, one panel per file arm, two to a row, as
    `iso_panels` gives them: the target ring, the bare arm's outline, the
    arm's shape, a marker per axis and the cost line above."""
    colors = dict(RADAR_THEMES[theme], **ISO_COLOURS[theme])
    width, size, radius = 1200, 460, 120
    rows = (len(panels) + 1) // 2
    top = 60
    height = top + rows * size
    count = len(ISO_AXES)

    def point(cx, cy, share, index):
        angle = -math.pi / 2 + 2 * math.pi * index / count
        reach = radius * share
        return cx + reach * math.cos(angle), cy + reach * math.sin(angle)

    def ring(cx, cy, share):
        return " ".join("%.1f,%.1f" % point(cx, cy, share, index)
                        for index in range(count))

    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" font-family="-apple-system, Segoe UI, '
           'Helvetica, Arial, sans-serif">' % (width, height, width, height),
           '<rect width="100%%" height="100%%" fill="%s"/>' % colors["surface"]]

    # One key for every panel.
    key = [("target", "every target met", "dashed"),
           ("bare", "%s, for reference" % BARE, "line"),
           ("better", "better than %s" % BARE, "up"),
           ("worse", "worse than %s" % BARE, "down"),
           ("muted", "no difference shown", "dot")]
    x = 40
    for colour, words, shape in key:
        if shape == "dashed":
            out.append('<line x1="%d" y1="28" x2="%d" y2="28" stroke="%s" '
                       'stroke-width="1.5" stroke-dasharray="5 3"/>'
                       % (x, x + 28, colors[colour]))
        elif shape == "line":
            out.append('<line x1="%d" y1="28" x2="%d" y2="28" stroke="%s" '
                       'stroke-width="1.5"/>' % (x, x + 28, colors[colour]))
        else:
            out.append(marker_svg(x + 14, 28, shape, colors))
        out.append('<text x="%d" y="28" dominant-baseline="middle" '
                   'font-size="13" fill="%s">%s</text>'
                   % (x + 36, colors["secondary"], escape(words)))
        x += 36 + 8 * len(words) + 24

    for place, (arm, cost, axes) in enumerate(panels):
        cx = (place % 2) * (width / 2) + width / 4
        cy = top + (place // 2) * size + size / 2 + 36

        # The arm's name, then its cost, centred above the top axis's label.
        out.append('<text x="%.1f" y="%.1f" text-anchor="middle" '
                   'font-size="18" font-weight="600" fill="%s">%s</text>'
                   % (cx, cy - radius - 96, colors["text"], escape(arm)))
        out.append('<text x="%.1f" y="%.1f" text-anchor="middle" '
                   'font-size="14" font-weight="600" fill="%s">%s</text>'
                   % (cx, cy - radius - 74, colors["secondary"],
                      escape(cost)))
        for share in (0.25, 0.5, 0.75):
            out.append('<polygon points="%s" fill="none" stroke="%s" '
                       'stroke-width="1"/>' % (ring(cx, cy, share),
                                               colors["grid"]))
        for index in range(count):
            x, y = point(cx, cy, 1.0, index)
            out.append('<line x1="%.1f" y1="%.1f" x2="%.1f" y2="%.1f" '
                       'stroke="%s" stroke-width="1"/>'
                       % (cx, cy, x, y, colors["grid"]))

        # The target ring: every target met, dashed.
        out.append('<polygon points="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5" stroke-dasharray="5 3"/>'
                   % (ring(cx, cy, 1.0), colors["target"]))

        # The bare arm's outline, thin and unfilled, then the arm's shape.
        # An axis not measured gets no vertex: the shape passes it by, where
        # a measured 0 % would pull it to the centre.
        bare = [point(cx, cy, bare / 100.0, index)
                for index, (_, _, bare, _, _) in enumerate(axes)
                if bare is not None]
        out.append('<polygon points="%s" fill="none" stroke="%s" '
                   'stroke-width="1.5"/>'
                   % (" ".join("%.1f,%.1f" % xy for xy in bare),
                      colors["bare"]))
        shape = [point(cx, cy, score / 100.0, index)
                 for index, (_, score, _, _, _) in enumerate(axes)
                 if score is not None]
        out.append('<polygon points="%s" fill="%s" fill-opacity="0.6" '
                   'stroke="%s" stroke-width="2" stroke-linejoin="round"/>'
                   % (" ".join("%.1f,%.1f" % xy for xy in shape),
                      colors["fill"], colors["series"]))
        for index, (axis, score, _, marker, moved) in enumerate(axes):
            if marker and score is not None:
                x, y = point(cx, cy, score / 100.0, index)
                out.append(marker_svg(x, y, {"better": "up", "worse": "down",
                                             "dot": "dot"}[marker], colors))
            lx, ly = point(cx, cy, 1.3, index)
            anchor = ("middle" if abs(lx - cx) < 8
                      else "start" if lx > cx else "end")
            out.append('<text x="%.1f" y="%.1f" text-anchor="%s" '
                       'dominant-baseline="middle" font-size="14" '
                       'font-weight="600" fill="%s">%s</text>'
                       % (lx, ly - 9, anchor, colors["text"], escape(axis)))
            out.append('<text x="%.1f" y="%.1f" text-anchor="%s" '
                       'dominant-baseline="middle" font-size="13" '
                       'fill="%s">%s</text>'
                       % (lx, ly + 9, anchor, colors[
                           {"better": "better", "worse": "worse"}.get(
                               marker, "secondary")],
                          escape(axis_reading(score, marker, moved))))
    out.append("</svg>")
    return "\n".join(out) + "\n"


def marker_svg(x, y, shape, colors):
    """One marker at (x, y): a filled triangle up, a hollow triangle down,
    or a small dot."""
    if shape == "up":
        return ('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s"/>'
                % (x, y - 7, x - 7, y + 6, x + 7, y + 6, colors["better"]))
    if shape == "down":
        return ('<polygon points="%.1f,%.1f %.1f,%.1f %.1f,%.1f" fill="%s" '
                'stroke="%s" stroke-width="2"/>'
                % (x, y + 7, x - 7, y - 6, x + 7, y - 6, colors["surface"],
                   colors["worse"]))
    return ('<circle cx="%.1f" cy="%.1f" r="4" fill="%s"/>'
            % (x, y, colors["muted"]))


def axis_reading(score, marker, moved):
    """An axis's label line: its share, and past the margin the move
    against the bare arm with its sign."""
    if score is None:
        return NOT_MEASURED
    words = "%d %%" % round(score)
    if marker == "better":
        words += " ▲ +%d" % round(moved)
    elif marker == "worse":
        words += " ▽ −%d" % round(abs(moved))
    elif marker == "dot":
        words += " ●"
    return words


# How to read the ISO radar, under it.
ISO_READING = (
    "One radar per arm, from the cheapest to the dearest, on the eight "
    "characteristics of ISO/IEC 25010:2023 in the standard's order. Each "
    "axis is the share of its targets met: each sub-characteristic's share, "
    "averaged, then averaged over the arm's trials. The dashed ring is every "
    "target met, and the thin outline is `%s`. A filled ▲ marks an axis "
    "better than `%s` past its margin, a hollow ▽ one worse, and a dot "
    "one within it. A build that does not install or boot counts against "
    "Reliability alone. The cost above each radar is shown, not scored. The "
    "targets behind each axis, and every number, are in the appendix."
    % (BARE, BARE))


def iso_axis_lines(trials, iso, arms, results=None, withdrawn=(),
                   blocks=None):
    """One table per axis: its sub-characteristics, each arm's mean share
    of their targets met, and the targets each asks; a target reading a
    metric in `withdrawn` is not measured, and a contrast over fewer pairs
    than `blocks` names its count."""
    lines = []
    per_trial = {name: iso_trial_scores(trial, withdrawn)
                 for name, trial in trials.items()}
    for axis, subs in ISO_AXES:
        lines.extend(["### %s" % axis, ""])
        lines.append("| Sub-characteristic | %s | Targets |"
                     % " | ".join("`%s`" % arm for arm in arms))
        lines.append("| --- | %s | --- |" % " | ".join("---" for _ in arms))
        for sub, targets in subs:
            cells = []
            for arm in arms:
                shares = [per_trial[name][axis][sub]
                          for name in per_trial if arm_of(name) == arm
                          and per_trial[name][axis][sub] is not None]
                cells.append("%d %%" % round(100 * statistics.fmean(shares))
                             if shares else NOT_MEASURED)
            asks = "; ".join(asks for asks, _, _, _ in targets)
            if not targets:
                asks = NOT_MEASURED
            elif len(targets) < ENOUGH_TARGETS:
                asks += " (fewer than %d targets)" % ENOUGH_TARGETS
            lines.append("| %s | %s | %s |" % (sub, " | ".join(cells), asks))
        cells = []
        for arm in arms:
            mean = arm_mean(iso, "iso:" + axis, arm)
            cells.append("%d %%" % round(mean) if mean is not None
                         else NOT_MEASURED)
        lines.append("| **%s** | %s | the mean of the rows measured |"
                     % (axis, " | ".join("**%s**" % cell for cell in cells)))
        if results:
            cells = []
            for arm in arms:
                contrast = results.get("iso:" + axis, {}).get(
                    "%s-%s" % (arm, BARE))
                cells.append(contrast_cell(contrast, True, blocks)
                             if contrast else "—")
            lines.append("| against `%s` | %s | a marker past %d points |"
                         % (BARE, " | ".join(cells), ISO_MARGINS[axis]))
        lines.append("")
    return lines


def iso_rules(trials):
    """Whether the run is read with the ISO radar: every round after the
    pilot, whose rounds registered radars of their own."""
    return not is_round5(trials)


def aggregate(seed, trials, table, results, withdrawn, check, iso,
              uses=None):
    """What `aggregate.json` keeps beside the report: every row, contrast
    and method the documents cite, the ISO reading where the round draws
    that radar, and each trial's use of its map where the round reads it,
    so each of its cells can be checked too."""
    payload = {"seed": seed, "table": table, "results": results,
               "blocks": blocks_state(trials), "withdrawn": withdrawn,
               "cross_check": check}
    if iso:
        payload["iso"] = {"table": iso[0], "results": iso[1],
                          "withdrawn": list(iso[2])}
    if uses is not None:
        payload["map_use"] = {
            name: {"first_write": use["first_write"],
                   "before_write": use.get("before_write"),
                   "by_subagent": use.get("by_subagent", 0),
                   "uses": [{"turn": turn, "template": template}
                            for turn, template in use["uses"]]}
            for name, use in sorted(uses.items())}
    return payload


def iso_reading(trials, seed, withdrawn=()):
    """The ISO radar's table, its contrasts against the bare arm and the
    metrics withdrawn from it, as one triple, for a run read with it."""
    withdrawn = tuple(withdrawn)
    iso = iso_table(trials, withdrawn)
    return iso, iso_contrasts(iso, seed, crossed_labels(trials)), withdrawn


# How the plain report reads the ISO radar, under it.
ISO_PLAIN_READING = (
    "How to read it: each axis is one quality of the software, from the "
    "international standard for software quality, and shows how many of its "
    "targets the approach met. The dashed ring is every target met, and the "
    "thin outline is `%s`. A filled ▲ means the approach did clearly "
    "better than `%s` on that axis, a hollow ▽ clearly worse, and a dot "
    "no clear difference. The cost above each radar is what a run spent. "
    "The appendix lists every target." % (BARE, BARE))

# How the appendix's ISO tables read, above them.
ISO_TABLE_READING = (
    "Each table is one axis of the radar: its sub-characteristics from "
    "ISO/IEC 25010:2023, each approach's mean share of their targets met "
    "over its working builds, the axis as the mean of the rows measured, "
    "and each approach against `%s`: the mean difference in points, its "
    "95 %% interval, and a marker only where the whole interval lies past "
    "the axis's margin. A row with no target reads not measured, never "
    "0 %%, and one with fewer than %d targets says so, since a single "
    "target swings it between 0 and 100 %%." % (BARE, ENOUGH_TARGETS))


def executive_section(trials, table, results, withdrawn=None, lost=(),
                      scans=(), radar=None, iso=None):
    """The report's first sections: the summary, a radar per file arm read
    against no file where `radar` names its two images, light and dark;
    then the arms against no file: the finding table, one line per file on
    why it scored so, the reading, the contrasts between files scored, and
    the caveats. `iso` is the ISO reading where the round draws that radar.

    Like the score, it digests the verdict vector and decides nothing.
    """
    active = active_contrasts(trials)
    lines = ["## Executive summary", ""]
    if radar:
        for theme, image in sorted(radar.items()):
            lines.append("![Radar per arm](%s#gh-%s-mode-only)"
                         % (image, theme))
        lines.extend(["", ISO_READING if iso else RADAR_SIZE_READING
                      if radar_axes(results) is ROUND5D_RADAR_AXES
                      else RADAR_READING, ""])
    else:
        lines.extend(["No radar was drawn for this run.", ""])
    lines.extend(finding_lines(trials, table, results, active))
    scored = between_files(results, active)
    if scored:
        lines.extend(["", scored])
    lines.extend(["", caveats_line(trials, withdrawn or {}, lost, scans)])
    return lines


def finding_lines(trials, table, results, active):
    """The finding table, its why-lines and its reading."""
    names = ["%s-%s" % (treatment, baseline)
             for treatment, baseline in active if baseline == BARE]
    if not names:
        return ["## Arms against `%s`" % BARE, "",
                "No file arm has a trial to read against `%s`, which has "
                "none in this run yet." % BARE]
    arms = [name.split("-")[0] for name in names]
    lengths = {arm: context_lines(arm) for arm in arms}
    answers = {arm: answer([results[key][name]["verdict"]
                            for key in ANSWERED])
               for arm, name in zip(arms, names)}

    # One row per arm, the bare arm first as the line every other is read
    # against, then the files from the cheapest to the dearest.
    ranked = by_cost(table, arms)
    lines = ["## Arms against `%s`" % BARE, ""]
    lines.extend(radar_table(results, ranked))
    lines.extend(["",
                  "| Arm | File | Verdict vs `%s` | %s |"
                  % (BARE, " | ".join(heading
                                      for heading, _, _ in FINDING_COLUMNS)),
                  "| --- | --- | --- | %s |"
                  % " | ".join("---" for _ in FINDING_COLUMNS)])
    for arm in [BARE] + ranked:
        lines.append("| %s |" % " | ".join(
            finding_row(table, results, arm, answers.get(arm),
                        lengths.get(arm))))
    lines.append("")
    lines.append("Each mark reads an arm against `%s`. %s"
                 % (BARE, MARK_LEGEND))
    low = [(arm, low_runs(table, arm)) for arm in ranked]
    low = [(arm, rates) for arm, rates in low if rates]
    if low:
        lines.append("")
        lines.append("Runs low on the hidden tests, more than %d points under "
                     "`%s`'s mean: %s."
                     % (round(100 * SUITE_DIP), BARE, "; ".join(
                         "`%s` %s" % (arm, spoken(["%d %%" % round(100 * rate)
                                                   for rate in rates]))
                         for arm, rates in low)))
    lines.append("")
    for arm in ranked:
        name = "%s-%s" % (arm, BARE)
        lines.append(why_line(trials, results, arm, name, answers[arm],
                              lengths[arm]))
        lines.append("")

    # A column or a contrast pairing a reused trial with one run in this
    # round crosses rounds, which the report says here rather than in a
    # footnote.
    reused = reused_arms(trials)
    if reused:
        crossed = crossing(active, arm_origins(trials))
        across = ("Compared unpaired with this round's trials, as round 5d "
                  "registered" if is_round5d(trials) else
                  "Pairing them with this round's trials, across days")
        lines.append("Reused from an earlier round: %s. %s The model is "
                     "pinned by exact id; the day is the residual confound."
                     % (spoken(["%s (%d trials)" % pair for pair in reused]),
                        "%s: %s." % (across, spoken(["%s − %s" % pair
                                                     for pair in crossed]))
                        if crossed else "No contrast pairs them with this "
                        "round's trials."))
        lines.append("")
    k = max((index_of(name) for name in trials), default=0)
    lines.append("Together%s: %s. K = %d, one project: a signal, not proof."
                 % (compared(answers, lengths), reading(answers, lengths), k))
    return lines


def compared(answers, lengths):
    """Which two files the reading sets side by side, where there are more
    than two to choose from; empty where the two columns are the only ones."""
    measured = [arm for arm in answers
                if answers[arm] != "Not measured" and lengths.get(arm)]
    if len(measured) < 3:
        return ""
    longer = max(measured, key=lengths.get)
    shorter = min(measured, key=lengths.get)
    return (", reading the longest file beside the shortest (`%s`, `%s`)"
            % (longer, shorter))


def between_files(results, active):
    """One line scoring the contrasts between two files, 1 to 10 with the
    wins and the fails, or None where the run holds none.

    A score kept for the pairings the finding table has no column for. It
    digests the verdict vector and decides nothing.
    """
    parts = []
    for treatment, baseline in active:
        if baseline == BARE:
            continue
        name = "%s-%s" % (treatment, baseline)
        wins = sum(1 for key, _, _, _ in METRICS
                   if results[key][name]["verdict"] == "better")
        fails = sum(1 for key, _, _, _ in METRICS
                    if results[key][name]["verdict"] == "worse")
        value = score(wins, fails)
        parts.append("%s − %s %s (%d won, %d failed)"
                     % (treatment, baseline,
                        "unscored" if value is None else "%.1f" % value,
                        wins, fails))
    if not parts:
        return None
    return ("Between the files, 1 to 10: %s. A win or a fail is a metric "
            "whose interval separated the pair in its declared direction, "
            "each counting once; the score is 1 + 9 × wins ÷ (wins + fails), "
            "digests the verdict vector at the end, and decides nothing."
            % "; ".join(parts))


def caveats_line(trials, withdrawn, lost, scans):
    """One line of what qualifies the run: the blocks in, withdrawals, lost
    trials, reaches and the judge's check."""
    labels = {key: label for key, label, _, _ in METRICS}
    judged = [trial["judge"] for trial in trials.values() if trial["judge"]]
    reached = []
    for scan in scans:
        if scan["hits"] and scan["name"] not in reached:
            reached.append(scan["name"])
    runs = ("%d of the %d registered blocks complete"
            % (ROUND5_K - len(owed_blocks(trials)), ROUND5_K))
    caveats = ["%d trials, %d judged" % (len(trials), len(judged)),
               runs,
               "withdrawn: %s" % ("; ".join(labels.get(key, key)
                                            for key in sorted(withdrawn))
                                  or "nothing"),
               "lost and re-run: %s" % ("; ".join(
                   "%s, %s" % (entry["name"], entry["rerun"] or "never re-run")
                   for entry in lost) or "none"),
               "reached past their workspace: %s" % (spoken(reached)
                                                     if reached else "none"),
               "the judge is checked only by its evidence lines"]
    reused = reused_arms(trials)
    if reused:
        caveats.insert(1, "reused from an earlier round: %s"
                       % spoken([arm for arm, _ in reused]))
    return "Caveats: %s." % "; ".join(caveats)


def withdrawn_section(withdrawn):
    """The report's lines on each metric withdrawn from this run, and why."""
    labels = {key: label for key, label, _, _ in METRICS}
    lines = ["## Withdrawn measurements",
             "",
             "Each metric below was found, after grading, to measure something "
             "other than what it names on the grader revision given. It prints "
             "no number, interval or verdict anywhere in this report.",
             "",
             "| Metric | Grader revision | Decided | Why |",
             "|---|---|---|---|"]
    for key, record in sorted(withdrawn.items()):
        lines.append("| %s | `%s` | %s | %s |"
                     % (labels.get(key, key), record["suite_revision"][:12],
                        record.get("decided") or "—",
                        " ".join((record.get("reason") or "—").split())
                        .replace("|", "/")))
    return lines


def blocks_section(trials):
    """The report's lines on the K the round registers, and how many of its
    blocks the run holds."""
    lines = ["## Runs per arm",
             "",
             "Fixed before the run: the round runs K = %d blocks, sized from "
             "the noise of the rounds before it, and adds none once results "
             "are seen." % ROUND5_K,
             ""]
    owed = owed_blocks(trials)
    if owed:
        lines.append("**Part-run.** A block is complete when every "
                     "registered arm has its trial in it; %s still %s a "
                     "trial before any verdict below is the round's."
                     % (blocks_named(owed),
                        "misses" if len(owed) == 1 else "miss"))
    else:
        lines.append("**Complete.** Every registered arm has its trial "
                     "in all %d blocks." % ROUND5_K)
    return lines


def contrast_cell(contrast, verdicts=True, full=None):
    """One contrast, as the mean, its interval, its verdict and its method.

    Without `verdicts` the cell stops at the interval, for a row that may
    describe a run but not decide it.

    All three contrasts are printed for every metric, because B − C is the one
    an adopter asks and a table showing only B − A cannot answer it: a large
    B − A beside an equally large C − A is not a result for the templates.

    A method other than BCa is marked in the cell rather than left to a
    companion file. Three identical paired differences give a point mass, and
    an interval of zero width printed as though it were computed would be the
    most confident-looking row in the report and the least informative.
    """
    interval = contrast["interval"]
    if interval.get("low") is None:
        return interval.get("method")
    mean = contrast["mean"]
    body = "%s%s [%s, %s]" % ("+" if mean and mean > 0 else "", number(mean),
                              number(interval["low"]),
                              number(interval["high"]))
    method = interval.get("method") or ""
    if not method.startswith("BCa"):
        body += " ‡"
    if verdicts:
        body += verdict_mark(contrast)

    # A block missing either arm's measure drops out of the pair, so an
    # interval over fewer pairs than the round's blocks says how many.
    pairs = len(contrast.get("pairs") or [])
    if full and 0 < pairs < full:
        body += " (%d pairs)" % pairs

    # An unpaired contrast has no pairs; it says how many trials each arm
    # gave where either gave fewer than the round's blocks.
    counts = contrast.get("trials")
    if full and contrast.get("unpaired") and counts and min(counts) < full:
        body += " (%d against %d trials)" % tuple(counts)
    return body


def verdict_mark(contrast):
    """A contrast's verdict as the mark its cell carries; the legend under
    each table spells the marks out once."""
    verdict = contrast["verdict"]
    if verdict in MARKS:
        return MARKS[verdict]
    if verdict == "held":
        return " ="

    # Too few complete pairs for an interval is no comparison at all, not a
    # comparison that showed nothing.
    if verdict == "not computed":
        return " (not compared)"

    # A verdict withheld on purpose (a neutral row, a pair across rounds, two
    # judges that disagree) is not an inconclusive one, so it has its own
    # mark rather than none.
    if verdict == "reported without a verdict" or verdict.startswith(
            "no verdict"):
        return " ○"
    inferiority = contrast.get("non_inferior")
    if verdict == "no improvement shown" and inferiority             and inferiority["within"]:
        return " ≈"
    return ""


# The legend under a table of contrasts with verdicts.
MARK_LEGEND = (
    "▲ better and ▼ worse: the interval is clear of zero, in the metric's "
    "direction, and under round 5d's rules clear of the row's margin. = held, for a row read by its margin, and ≈ no difference "
    "shown: either way the interval's worse end stays within the row's "
    "margin, so it is no worse than the margin, which is not the same as "
    "equal. ○ no verdict, on purpose: a row reported without one, a pair "
    "across rounds, or two judges that disagree. (not compared): too few "
    "complete pairs for an interval. No mark: no difference shown, on a row "
    "with no margin or past the margin it has.")
CONTRAST_LEGEND = ("Each cell: the mean paired difference, its 95 % interval "
                   "in brackets, and a mark. " + MARK_LEGEND)


def contrast_table(table, results, keys, verdicts=True, active=None,
                   blocks=None, legend=True):
    """One table of contrasts: every metric, each arm's mean, and every
    comparison the run holds. `blocks` is the round's block count, against
    which a contrast over fewer pairs names its count."""
    active = list(CONTRASTS if active is None else active)
    arms = contrast_arms(active)
    lines = ["| Metric | Direction | Margin | %s | %s |"
             % (" | ".join(arms),
                " | ".join("%s−%s" % pair for pair in active)),
             "|---|---|---|%s|" % "|".join("---" for _ in arms + active)]
    degenerate = False
    for key in keys:
        entry = table[key]
        means = {}
        for arm in arms:
            values = [v for v in entry["values"].get(arm, {}).values()
                      if v is not None]
            means[arm] = statistics.fmean(values) if values else None
        cells = []
        for treatment, baseline in active:
            contrast = results[key]["%s-%s" % (treatment, baseline)]
            cell = contrast_cell(contrast, verdicts, blocks)
            degenerate = degenerate or "‡" in cell
            cells.append(cell)
        margins = [contrast["non_inferior"]["margin"]
                   for contrast in results[key].values()
                   if isinstance(contrast, dict)
                   and contrast.get("non_inferior")]
        lines.append("| %s | %s | %s | %s | %s |"
                     % (entry["label"], entry["direction"],
                        margins[0] if margins else "—",
                        " | ".join(number(means[arm]) for arm in arms),
                        " | ".join(cells)))
    if verdicts and legend:
        lines.extend(["", CONTRAST_LEGEND])
    if degenerate and legend:
        lines.append("")
        lines.append(DEGENERATE_NOTE)
    return lines


# The note under a table holding an interval BCa could not compute.
DEGENERATE_NOTE = ("‡ the interval was not computed by BCa: the paired "
                   "differences were identical, or the bias correction was "
                   "undefined. `aggregate.json` carries the method per row.")


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Aggregate scored efficacy trials into the report.")
    parser.add_argument("--root", help="the harness's run root")
    parser.add_argument("--seed", type=int, default=20260912,
                        help="bootstrap seed, recorded in the report")
    parser.add_argument("--out-dir",
                        help="where the report is written; default is the "
                             "templates source's docs/audits/. Any "
                             "docs/audits/ takes only a round archived as it "
                             "stands; elsewhere the report is a draft")
    parser.add_argument("--templates",
                        help="a git clone of the templates repository, "
                             "upstream or a fork; overrides %s"
                             % TEMPLATES_ENV)
    parser.add_argument("--cross-check",
                        help="a root whose scoring area holds the other "
                             "vendor's judgings of this round's trees")
    parser.add_argument("--posthoc-rules", action="store_true",
                        help="also write a post-hoc page reading the round "
                             "by round 5d's rules; its registered verdicts "
                             "stand")
    parser.add_argument("--self-test", action="store_true",
                        help="check the verdict rule against worked cases; "
                             "read no run")
    return parser.parse_args(argv)


# The registered worked table, which is what the verdict rule has to
# reproduce. The third row is the one an earlier draft read wrongly: three
# differences that all improve cannot produce an interval containing zero,
# however much the raw columns overlap.
WORKED = (
    ("every pairing improves by the same amount", [0.33, 0.33, 0.34], UP,
     "better"),
    ("every pairing improves, unstably", [0.03, 0.10, 0.12], UP, "better"),
    ("the differences change sign", [0.13, -0.06, 0.04], UP,
     "no improvement shown"),
    ("a downward metric that fell", [-12.0, -9.0, -20.0], DOWN, "better"),
    ("a downward metric that rose", [12.0, 9.0, 20.0], DOWN, "worse"),
    ("three identical differences", [0.2, 0.2, 0.2], UP, "better"),
)


def reach_checks():
    """The report names a trial whose scan hit, and no other."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-reach-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    hit = {"tool": "Bash", "term": "solid-ai-templates",
           "call": "curl https://github.com/solid-ai-dev/solid-ai-templates"}
    planted = [
        {"arm": "inline", "trial": 1, "outcome": "completed",
         "reach": {"transcripts": ["planted"], "hits": [hit]}},
        {"arm": "none", "trial": 1, "outcome": "completed",
         "reach": {"transcripts": ["planted"], "hits": []}},
        {"arm": "hand", "trial": 1, "outcome": "completed",
         "workspace": os.path.join(scratch, "hand-1")},
        {"arm": "none", "trial": 2, "outcome": "blocked",
         "reach": {"transcripts": ["planted"], "hits": [hit]}},
    ]
    with io.open(os.path.join(scratch, "run-planted.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"trials": planted}, handle)

    lines = reach_section(scratch)
    rows = [line for line in lines
            if line.startswith("| ") and not line.startswith("| Trial")]
    checks = [("the planted run record is read",
               len(run_records(scratch)) == len(planted)),
              ("a trial whose scan hit is named",
               [row.split(" | ")[0] for row in rows] == ["| inline-1"]),
              ("a trial with no transcript is not scanned",
               "Not scanned, having no transcript: hand-1." in lines)]
    shutil.rmtree(scratch, ignore_errors=True)
    return checks


def lost_checks():
    """A voided trial is listed whether or not a run record names it."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-lost-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    recorded = os.path.join(scratch, "void", "none-1-2026-09-15T10-00-00")
    unrecorded = os.path.join(scratch, "void",
                              "change-hand-2-2026-09-16T18-30-00")
    for directory in (recorded, unrecorded):
        os.makedirs(directory)

    # none-1 was blocked and recorded; the run holding change hand-2 stopped
    # before recording it, and hand-2's change task re-ran in a later run.
    runs = {
        "run-2026-09-15T09-00-00.json": [
            {"arm": "none", "trial": 1, "task": "build", "outcome": "blocked",
             "started_at": "2026-09-15T09:00:00", "reason": "planted",
             "void": {"dir": recorded}},
            {"arm": "none", "trial": 1, "task": "build",
             "outcome": "completed", "started_at": "2026-09-15T10:05:00"}],
        "run-2026-09-16T17-00-00.json": [
            {"arm": "hand", "trial": 2, "task": "build",
             "outcome": "completed", "started_at": "2026-09-16T17:00:00"}],
        "run-2026-09-16T20-00-00.json": [
            {"arm": "hand", "trial": 2, "task": "change",
             "outcome": "completed", "started_at": "2026-09-16T20:00:00"}],
    }
    for file, trials in runs.items():
        with io.open(os.path.join(scratch, file), "w",
                     encoding="utf-8") as handle:
            json.dump({"trials": trials}, handle)

    landed = (sorted(os.listdir(os.path.join(scratch, "void")))
              == ["change-hand-2-2026-09-16T18-30-00",
                  "none-1-2026-09-15T10-00-00"]
              and len(run_records(scratch)) == 4)
    lost = lost_trials(scratch)
    shutil.rmtree(scratch, ignore_errors=True)
    rows = [(entry["name"], entry["rerun"]) for entry in lost]
    unrecorded_row = [entry for entry in lost
                      if entry["name"] == "hand-2 (change task)"]
    return [("the planted voids and run records are read", landed),
            ("a voided trial is listed once, recorded or not",
             rows == [("none-1", "completed"),
                      ("hand-2 (change task)", "completed")]),
            ("an unrecorded void says no run record holds it",
             len(unrecorded_row) == 1
             and "no run record" in unrecorded_row[0]["reason"])]


def band_checks(seed):
    """App code's size reads against a band: a rise inside the margin is
    held, only one wholly past it worse; round 5 reports the rows it
    supersedes without a verdict."""

    # A margin of 20 lines: the loss side of each interval, for a metric that
    # improves downward, placed against it.
    checks = [(label, banded_verdict({"low": low, "high": high}, DOWN, 20)
               == expected, banded_verdict({"low": low, "high": high},
                                           DOWN, 20))
              for label, low, high, expected in (
                  ("a rise inside the band is held", 5, 15, "held"),
                  ("a band that holds zero is held", -5, 10, "held"),
                  ("a fall wholly below zero is better", -10, -2, "better"),
                  ("a rise wholly past the band is worse", 25, 40, "worse"),
                  ("one that straddles the band is undecided", 10, 30,
                   "no improvement shown"))]

    # Skills writes 10 % more app code than none in every block, and twice the
    # files of a tree that also holds docs.
    def trial(app, files):
        return {"scores": {"scope": {"value": {
            "app_lines": app, "app_files": 10, "source_lines": app,
            "tracked_files": files}}}}
    trials = {}
    for index in (1, 2, 3, 4, 5, 6):
        trials["none-%d" % index] = trial(1000 + index, 20)
        trials["skills-%d" % index] = trial(1100 + index + index % 2, 40)
    results = contrasts(collect(trials), seed, (), ROUND5_MARGINS)
    app = results["app_lines"]["skills-none"]["verdict"]
    files = results["tracked_files"]["skills-none"]["verdict"]
    checks.extend([
        ("round 5 reads a 10 % rise in app code as held", app == "held", app),
        ("round 5 reports the files it supersedes without a verdict",
         files == "reported without a verdict", files)])
    return checks


def spec_checks():
    """A round is refused when a trial with something to score built from
    another spec than the registered one, or records none."""
    scratch = tempfile.mkdtemp(prefix="efficacy-report-spec-")
    registered = ROUND5_SPEC[1]

    def problem_for(*trials):
        for old in glob.glob(os.path.join(scratch, "run-*.json")):
            os.remove(old)
        with io.open(os.path.join(scratch, "run-1.json"), "w",
                     encoding="utf-8") as handle:
            json.dump({"trials": list(trials)}, handle)
        return spec_problem(scratch)

    def build(arm, trial, digest="registered", outcome="completed"):
        record = {"arm": arm, "trial": trial, "task": "build",
                  "outcome": outcome}
        if digest is not None:
            record["spec"] = {"file": "SPEC.md",
                              "sha256": registered if digest == "registered"
                              else digest}
        return record

    try:
        checks = [
            ("every trial on the registered spec passes",
             problem_for(build("none", 1), build("skills", 1)) is None),
            ("a trial on another spec is refused",
             problem_for(build("none", 1), build("skills", 1, "0" * 64))
             is not None),
            ("a scorable trial recording no spec is refused",
             problem_for(build("none", 1, None)) is not None),
            ("a refused trial, which built nothing, is not read",
             problem_for(build("none", 1),
                         build("skills", 1, None, "refused")) is None),
            ("a change task, which gets no spec, is not read",
             problem_for(build("none", 1),
                         {"arm": "none", "trial": 1, "task": "change",
                          "outcome": "completed"}) is None),
        ]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return checks


def prompt_checks():
    """A round is refused when a build trial with something to score was
    given another prompt than the one every arm is given, or records none."""
    scratch = tempfile.mkdtemp(prefix="efficacy-report-prompt-")
    old_prompt = "Implement SPEC.md."

    def problem_for(*trials, run_prompt=PROMPT):
        for old in glob.glob(os.path.join(scratch, "run-*.json")):
            os.remove(old)
        with io.open(os.path.join(scratch, "run-1.json"), "w",
                     encoding="utf-8") as handle:
            json.dump({"task": "build", "prompt": run_prompt,
                       "trials": list(trials)}, handle)
        return prompt_problem(scratch)

    def trial(prompt=PROMPT, outcome="completed", task="build"):
        record = {"arm": "none", "trial": 1, "task": task, "outcome": outcome}
        if prompt is not None:
            record["prompt"] = prompt
        return record

    try:
        checks = [
            ("every trial on the one prompt passes",
             problem_for(trial(), trial()) is None),
            ("a trial on another prompt is refused",
             problem_for(trial(), trial(old_prompt)) is not None),
            ("so is one reused into a run naming the current prompt",
             problem_for(trial(old_prompt), run_prompt=PROMPT) is not None),
            ("a scorable trial recording no prompt is refused",
             problem_for(trial(None)) is not None),
            ("a refused trial, which built nothing, is not read",
             problem_for(trial(), trial(old_prompt, "refused")) is None),
            ("a change task, which has its own prompt, is not read",
             problem_for(trial(), trial("Change it.", task="change")) is None),
        ]
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    return checks


def python_checks():
    """A round is refused when its scores were installed on more than one
    Python, an unrecorded one included."""
    def trials(*versions):
        return {"none-%d" % (index + 1): {
            "scores": {} if version is None else {"python": version},
            "change": None} for index, version in enumerate(versions)}
    return [
        ("scores on one Python are read",
         python_problem(trials("3.12.10", "3.12.15")) is None),
        ("scores all unrecorded, as an old round's are, are read",
         python_problem(trials(None, None)) is None),
        ("scores on two Pythons are refused",
         "3.14" in (python_problem(trials("3.12.10", "3.14.8")) or "")),
        ("an unrecorded score beside a recorded one is refused",
         "unrecorded" in (python_problem(trials("3.12.10", None)) or "")),
    ]


def registration_checks():
    """A round is refused when its registration landed on the main branch
    after its first trial, has not landed, is changed and not committed, or
    when a trial's start carries no UTC offset."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-registration-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    repository = os.path.join(scratch, "repository")
    os.makedirs(os.path.join(repository, "docs"))
    registration = "docs/round.md"
    path = os.path.join(repository, *registration.split("/"))
    identity = ("-c", "user.name=self-test",
                "-c", "user.email=self-test@example.invalid")

    def commit(when, *args):
        env = dict(os.environ, GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        git(repository, *(identity + args), env=env)

    def write(text):
        with io.open(path, "a", encoding="utf-8") as handle:
            handle.write(text)

    def plant_run(name, moment):
        root = os.path.join(scratch, name)
        os.makedirs(root)
        with io.open(os.path.join(root, "run-planted.json"), "w",
                     encoding="utf-8") as handle:
            json.dump({"trials": [{"arm": "none", "trial": 1,
                                   "outcome": "completed",
                                   "started_at": moment}]}, handle)
        return root

    def problem(root):
        return registration_problem(root, registration, repository)

    # The registration lands at 10:00 UTC, written in a +02:00 zone. A trial
    # at 10:30 UTC follows it, though its clock reads earlier than 12:00.
    git(repository, "init", "-q", "-b", REGISTRATION_BRANCH)
    write("# Round\n")
    git(repository, "add", registration)
    commit("2026-10-01T12:00:00+02:00", "commit", "-q", "-m", "register")
    after = plant_run("after", "2026-10-01T10:30:00+00:00")
    before = plant_run("before", "2026-10-01T09:30:00+00:00")
    naive = plant_run("naive", "2026-10-01T10:30:00")
    early, late, zoneless = problem(after), problem(before), problem(naive)
    unrecorded = problem(repository)

    # An earlier round's trial reused at 09:30 ran under its own round's
    # registration, so the round's own trial at 10:30 is what is read.
    with io.open(os.path.join(after, "run-reused.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"trials": [{"arm": "none", "trial": 2,
                               "outcome": "completed",
                               "started_at": "2026-10-01T09:30:00+00:00",
                               "reused_from": {"root": "earlier"}}]}, handle)
    reused = problem(after)

    # An amendment committed on a branch at 11:00, before a trial at 12:00,
    # and merged into the main branch at 13:00, after it.
    merged = plant_run("merged", "2026-10-01T12:00:00+00:00")
    git(repository, "switch", "-q", "-c", "amend")
    write("A hypothesis.\n")
    commit("2026-10-01T11:00:00+00:00", "commit", "-q", "-am", "amend")
    unlanded = problem(merged)
    git(repository, "switch", "-q", REGISTRATION_BRANCH)
    commit("2026-10-01T13:00:00+00:00", "merge", "-q", "--no-ff", "amend",
           "-m", "merge the amendment")
    merged_late = problem(merged)
    write("A hypothesis added after the first trial.\n")
    changed = problem(after)
    shutil.rmtree(scratch, ignore_errors=True)
    return [("a registration landed before the first trial passes, across "
             "zones", early is None),
            ("one landed after the first trial is refused",
             late is not None and "after the first trial" in late),
            ("a trial start with no UTC offset is refused",
             zoneless is not None and "no UTC offset" in zoneless),
            ("a root with no run record is refused",
             unrecorded is not None and "no run record" in unrecorded),
            ("a trial reused from an earlier round is not read against it",
             reused is None),
            ("an amendment on a branch of its own is refused",
             unlanded is not None and "has not landed" in unlanded),
            ("one merged after the first trial is read at the merge",
             merged_late is not None and "T13:00:00" in merged_late),
            ("one changed and not committed is refused",
             changed is not None and "not committed" in changed)]


def rescan_checks():
    """A record scanned under an earlier rule is read again from its
    transcript."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-rescan-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    workspace = os.path.join(scratch, "none-2")
    os.makedirs(workspace)
    os.makedirs(os.path.join(scratch, "inline-1"))
    folder = "".join(char if char.isalnum() else "-"
                     for char in os.path.abspath(workspace))
    projects = os.path.join(scratch, "home", ".claude", "projects", folder)
    os.makedirs(projects)
    entry = {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "name": "Bash",
         "input": {"command": "cat ../inline-1/src/tariff/pricing.py"}}]}}
    with io.open(os.path.join(projects, "planted.jsonl"), "w",
                 encoding="utf-8") as handle:
        handle.write(json.dumps(entry) + "\n")

    # Scanned clean when it ran, as the narrower rule would have left it.
    planted = [{"arm": "none", "trial": 2, "outcome": "completed",
                "workspace": workspace,
                "reach": {"transcripts": ["planted"], "hits": []}}]
    with io.open(os.path.join(scratch, "run-planted.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"trials": planted}, handle)

    # The plant landed: the transcript is found and carries the one call.
    landed = len(read_transcripts(os.path.join(scratch, "home"),
                                  workspace)[1]) == 1
    terms = [hit["term"] for scan in reaches(scratch)
             for hit in scan["hits"] or []]
    shutil.rmtree(scratch, ignore_errors=True)
    return [("the planted transcript carries one call", landed),
            ("its record's clean scan is read again and flagged",
             terms == ["../inline-1"])]


def planted_change_run(revision):
    """K = 3 change tasks graded at `revision`, arm skills ahead on every
    row."""
    rates = {"none": 0.25, "skills": 0.75, "hybrid": 0.5}
    lines = {"none": 300, "skills": 200, "hybrid": 250}

    def change(arm, index):
        return {"suite_revision": revision,
                "change_suite": {"value": rates[arm] + index / 100.0,
                                 "missing": None},
                "churn": {"value": {"files": 10, "lines": lines[arm] - index},
                          "missing": None}}

    return {trial_name(arm, index): {"scores": {}, "judge": None,
                                    "security": None,
                                    "change": change(arm, index)}
            for arm in rates for index in range(1, 4)}


def rendered(trials, seed, withdrawn):
    """The report a planted run renders, withdrawn metrics blanked first."""
    table = collect(trials)
    results = round_contrasts(trials, table, seed)
    before = results["change_success"]["skills-none"]["verdict"]
    withdraw(withdrawn, table, results)
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-withdrawal-render")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    target = write_report(scratch, trials, table, results, seed,
                          out_dir=scratch, withdrawn=withdrawn)
    with io.open(target[:-len(".md")] + "-record.md",
                 encoding="utf-8") as handle:
        text = handle.read()
    shutil.rmtree(scratch, ignore_errors=True)
    return before, table, text


def rendered_plain(trials, seed):
    """The plain report a planted run renders, as text."""
    table = collect(trials)
    results = round_contrasts(trials, table, seed)
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-plain-render")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    target = write_report(scratch, trials, table, results, seed,
                          out_dir=scratch)
    with io.open(target, encoding="utf-8") as handle:
        text = handle.read()
    shutil.rmtree(scratch, ignore_errors=True)
    return text


def section_rows(text, heading, label):
    """The rows of one report section that start with a metric's label."""
    section = text.split(heading)[1].split("\n## ")[0] if heading in text \
        else ""
    return [line for line in section.splitlines()
            if line.startswith("| %s |" % label)]


def withdrawal_checks(seed):
    """A withdrawn metric prints only its withdrawal, and only on runs graded
    by the revision it was withdrawn for."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-withdrawal-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    record = os.path.join(scratch, "withdrawn.json")
    with io.open(record, "w", encoding="utf-8") as handle:
        json.dump([{"metric": "change_success",
                    "suite_revision": "planted-revision",
                    "decided": "2026-09-17", "reason": "planted reason"}],
                  handle)

    graded = planted_change_run("planted-revision")
    withdrawn = withdrawals(graded, record)
    other = planted_change_run("other-revision")
    spared = withdrawals(other, record)
    shutil.rmtree(scratch, ignore_errors=True)

    label = "Change task, acceptance pass rate"
    before, table, text = rendered(graded, seed, withdrawn)
    values = [value for row in table["change_success"]["values"].values()
              for value in row.values()]
    change = section_rows(text, "## The change task", label)
    raw = section_rows(text, "## Raw numbers, per trial", label)
    vector = section_rows(text, "## Verdict vector", label)
    listed = section_rows(text, "## Withdrawn measurements", label)
    churn = section_rows(text, "## The change task",
                         "Change task, lines changed")

    checks = [
        ("a record on the grading revision is read",
         sorted(withdrawn) == ["change_success"], sorted(withdrawn)),
        ("the planted row read better before withdrawal", before == "better",
         before),
        ("withdrawal blanks every value of the row",
         len(values) == 9
         and all(value is None for value in values), values),
        ("its change-task row prints no number or verdict",
         len(change) == 1 and "withdrawn" in change[0] and not any(
             word in change[0] for word in ("0.", "better", "worse")), change),
        ("its raw row prints no value",
         len(raw) == 1 and not any(char.isdigit() for char in raw[0]), raw),
        ("its verdict vector row reads withdrawn",
         vector == ["| %s | withdrawn | withdrawn | withdrawn |" % label],
         vector),
        ("the withdrawal section names it and why",
         len(listed) == 1 and "planted reason" in listed[0], listed),
        ("a metric not withdrawn keeps its verdict",
         len(churn) == 1 and "▲" in churn[0], churn),
        ("a run graded by another revision withdraws nothing", spared == {},
         sorted(spared)),
    ]

    finding = finding_of(text)
    checks.extend([
        ("the finding table opens the report, and no summary follows it",
         0 <= text.find("## Executive summary") < text.find("## What produced")
         and "## Summary" not in text, None),
        ("the line between files scores the verdicts, the withdrawn metric "
         "not among them",
         "skills − hybrid 10.0 (1 won, 0 failed)" in finding, finding),
        ("it names the withdrawal among the caveats",
         "withdrawn: %s;" % label in finding, None),
    ])

    _, _, text = rendered(other, seed, spared)
    kept = section_rows(text, "## Verdict vector", label)
    checks.append(("that run's row keeps its verdict",
                   kept == ["| %s | better | better | better |" % label]
                   and "## Withdrawn measurements" not in text, kept))
    finding = finding_of(text)
    checks.append(("that run's line between files counts the row a win",
                   "skills − hybrid 10.0 (2 won, 0 failed)" in finding
                   and "withdrawn: nothing;" in finding, finding))

    # The rule at its ends and in the middle: round 1's templates against no
    # context file won 8 and failed 11.
    checks.extend([("a pair won and failed 8 to 11 scores 4.8",
                    score(8, 11) == 4.8, score(8, 11)),
                   ("a pair lost on every separating metric scores 1",
                    score(0, 3) == 1.0, score(0, 3)),
                   ("a pair nothing separated has no score",
                    score(0, 0) is None, score(0, 0))])
    return checks


def prose_of(text, heading):
    """One report section with its wrapping undone."""
    section = text.split(heading)[1].split("\n## ")[0] if heading in text \
        else ""
    return " ".join(section.split())


def finding_of(text):
    """The report's opening section with its wrapping undone."""
    return prose_of(text, "## Arms against `none`")


def executive_checks(seed):
    """The finding table answers from the primary dimensions and task
    success, reads its two columns together, and opens the report."""
    checks = []
    shown = "no improvement shown"
    for label, verdicts, expected in (
            ("a worse primary answers Worse",
             ["better", "worse", shown, shown], "Worse"),
            ("a better primary and no worse answers Yes",
             ["better", shown, shown, shown], "Yes"),
            ("nothing separated answers No", [shown] * 4, "No"),
            ("nothing computed answers Not measured",
             ["not computed"] * 4, "Not measured")):
        got = answer(verdicts)
        checks.append((label, got == expected, got))

    # The reading sets the longer file's answer beside the shorter's.
    lengths = {"inline": 400, "hand": 40}
    for label, answers, expected in (
            ("a short Yes beside a long No reads length is not quality",
             {"inline": "No", "hand": "Yes"},
             "length is not quality — the long file spent the agent's "
             "attention on conventions, the short one on the code"),
            ("a long Yes beside a short Worse reads the long file's gain",
             {"inline": "Yes", "hand": "Worse"},
             "the long file added quality, the short one did not"),
            ("two Yes answers read long or short",
             {"inline": "Yes", "hand": "Yes"},
             "a context file adds quality, long or short"),
            ("two No answers read neither", {"inline": "No", "hand": "No"},
             "neither file added quality"),
            ("an unmeasured column reads not measured",
             {"inline": "Not measured", "hand": "Yes"}, NOT_MEASURED)):
        got = reading(answers, lengths)
        checks.append((label, got == expected, got))

    # With more than two files the reading names the two it compares; with
    # two it needs no names, since the columns are the only ones.
    four = {"inline": 391, "short": 39, "hybrid": 516, "hand": 40}
    named = compared({arm: "No" for arm in four}, four)
    checks.append(("a reading over four files names the two it compares",
                   named == ", reading the longest file beside the shortest "
                            "(`hybrid`, `short`)", named))
    checks.append(("a reading over two files names none",
                   compared({"inline": "No", "hand": "No"}, lengths) == "",
                   compared({"inline": "No", "hand": "No"}, lengths)))

    # An interval over fewer pairs than the round's blocks names its count;
    # one over every block does not.
    contrast = {"mean": 0.1, "verdict": "better", "non_inferior": None,
                "interval": {"low": 0.05, "high": 0.2, "method": "BCa"},
                "pairs": [0.1] * 14}
    short, whole = (contrast_cell(contrast, True, 15),
                    contrast_cell(dict(contrast, pairs=[0.1] * 15), True, 15))
    checks.append(("a contrast over fewer pairs than blocks names its count",
                   "(14 pairs)" in short and "pairs" not in whole,
                   (short, whole)))

    # An axis counts its rows better minus worse over the rows with a
    # verdict; a withheld or uncomputed row is left out, and an axis with
    # none reads None.
    planted = {key: {"skills-none": {"verdict": "no improvement shown"}}
               for _, keys in RADAR_AXES for key in keys}
    planted["task_success"]["skills-none"] = {"verdict": "worse"}
    planted["install"]["skills-none"] = {"verdict": "not computed"}
    planted["judge_tests"]["skills-none"] = {"verdict": "better"}
    planted["coverage"]["skills-none"] = {"verdict": "better"}
    for key in ("judge_data_protection", "data_protection_probe_pass_rate"):
        planted[key]["skills-none"] = {"verdict": CROSSING_VERDICT}
    got = dict(cluster_scores(planted, "skills-none"))
    checks.append(("an axis is better minus worse over its rows with a "
                   "verdict, None without one",
                   got["Reliability"] == -1.0 and got["Tests"] == 1.0
                   and got["Data protection"] is None
                   and got["Security"] == 0.0
                   and [axis for axis, _ in cluster_scores(planted,
                                                           "skills-none")]
                   == [axis for axis, _ in RADAR_AXES], got))

    # The radar is well-formed SVG in both themes, a titled panel per arm,
    # its axes in their fixed order, and the bare arm's ring in each.
    panels = [("reference", "reference — Worse",
               cluster_scores(planted, "skills-none")),
              ("skills", "skills — Yes", cluster_scores(planted,
                                                        "skills-none"))]
    drawn = {theme: radar_svg(panels, theme) for theme in RADAR_THEMES}
    try:
        trees = {theme: ElementTree.fromstring(svg)
                 for theme, svg in drawn.items()}
    except ElementTree.ParseError as error:
        trees = {"error": str(error)}
    space = "{http://www.w3.org/2000/svg}"
    shaped = all(
        [text.text for text in tree.iter(space + "text")
         if text.text in ("reference — Worse", "skills — Yes")]
        == ["reference — Worse", "skills — Yes"]
        and sum(1 for polygon in tree.iter(space + "polygon")
                if polygon.get("stroke-dasharray")) == len(panels)
        for tree in trees.values()) and "error" not in trees
    labels = [text.text for text in trees.get("light", ElementTree.Element(
        "svg")).iter(space + "text")]
    order = [label for label in labels if label in dict(RADAR_AXES)]
    checks.append(("the radar draws a panel per arm, with the bare ring, in "
                   "both themes",
                   shaped and drawn["light"] != drawn["dark"]
                   and order[:len(RADAR_AXES)]
                   == [axis for axis, _ in RADAR_AXES], sorted(trees)))
    checks.append(("each axis score prints signed, zero unsigned, none as a "
                   "dash",
                   [axis_score(value) for value in (0.5, -1.0, 0.0, None)]
                   == ["+0.50", "-1.00", "0.00", "—"], None))

    # Each verdict reads as its mark, once spelled out in the legend.
    marks = [verdict_mark({"verdict": verdict, "non_inferior": inferior})
             for verdict, inferior in (
                 ("better", None), ("worse", None), ("held", None),
                 ("no improvement shown", {"within": True}),
                 ("no improvement shown", {"within": False}),
                 ("reported without a verdict", None),
                 (CROSSING_VERDICT, None), (DISAGREE_VERDICT, None),
                 ("not computed", None))]
    checks.append(("each verdict reads as its mark, a withheld one apart",
                   marks == [" ▲", " ▼", " =", " ≈", "", " ○", " ○", " ○",
                             " (not compared)"], marks))

    # Every contrast in the table short of the round's blocks: the count is
    # read against the round's K, not the most pairs any contrast had.
    one_table = {"cost_usd": {"label": "Cost", "direction": "down",
                              "values": {"none": {1: 1.0}, "skills": {1: 2.0}}}}
    one_result = {"cost_usd": {"skills-none": contrast}}
    rows = contrast_table(one_table, one_result, ["cost_usd"],
                          active=[("skills", "none")], blocks=15)
    checks.append(("a table whose every contrast is short still names counts",
                   any("(14 pairs)" in row for row in rows), rows))
    got = " ".join(cross_check_section(None))
    checks.append(("no second judge is said to be unchecked, not same-vendor",
                   "checked only by its evidence lines" in got
                   and "shares a vendor" not in got, got))

    # A why-line says, in words, what stands on a record or verdict below:
    # the run that could not boot, the structure built beyond the task and
    # the work it took, what the judge read, and the patterns missed.
    trials = {"inline-1": {"scores": {"boot": {"value": {
                  "factory": False, "factory_error": "planted error"}}}},
              "inline-2": {"scores": {"boot": {"value": {"factory": True}}}},
              "none-1": {"scores": {"boot": {"value": {"factory": False}}}}}
    got = boot_failures(trials, "inline")
    checks.append(("boot failures are the arm's own, with the error",
                   got == (["planted error"], 2), got))
    planted = {key: {"inline-none": {"mean": 0.0, "verdict": shown}}
               for key, _, _, _ in METRICS}
    planted["tracked_files"]["inline-none"]["verdict"] = "worse"
    planted["turns"]["inline-none"]["verdict"] = "worse"
    planted["churn_lines"]["inline-none"]["verdict"] = "worse"
    planted["patterns_missed"]["inline-none"]["verdict"] = "worse"
    planted["judge_readability"]["inline-none"]["verdict"] = "better"
    planted["adherence"]["inline-none"]["verdict"] = "better"
    got = why_line(trials, planted, "inline", "inline-none", "No", 400)
    checks.append(("the why-line says what the records and verdicts hold",
                   got == "**`inline`, No.** One run of two left the "
                   "app unable to boot (`planted error`). It built more than "
                   "the task asked for: more files, and took more turns to "
                   "do it; the follow-up change had to move through that "
                   "structure too. The judge read its code as more "
                   "readable; it missed more of the patterns the domain "
                   "called for.", got))
    trials["inline-1"]["scores"]["boot"]["value"]["factory_error"] = \
        "ModuleNotFoundError(\"No module named 'planted'\")"
    planted["judge_readability"]["inline-none"]["verdict"] = shown
    got = why_line(trials, planted, "inline", "inline-none", "No", 400)
    checks.append(("a module missing after a clean install is a declared "
                   "dependency, and a win the judge did not give is a tool "
                   "count",
                   got.startswith("**`inline`, No.** One run of two "
                                  "declared its dependencies so that a clean "
                                  "install left the app unable to boot.")
                   and got.endswith("The judge saw none of it as better "
                                    "design, readability, maintainability, "
                                    "security or data protection; "
                                    "every win is something a tool counts "
                                    "and it missed more of the patterns the "
                                    "domain called for."), got))
    planted = {key: {"hand-none": {"mean": 0.0, "verdict": shown}}
               for key, _, _, _ in METRICS}
    for key in ("judge_readability", "judge_tests", "coverage"):
        planted[key]["hand-none"]["verdict"] = "better"
    for key in ("turns", "cost_usd", "churn_lines"):
        planted[key]["hand-none"]["verdict"] = "worse"
    got = why_line({}, planted, "hand", "hand-none", "Yes", 39)
    checks.append(("a short Yes file is a few rules the agent could hold",
                   got == "**`hand`, Yes.** A few rules the agent "
                   "could hold: the judge read its code as more readable "
                   "and better tested, and its code grew no more than its "
                   "size margin allows — for more turns and cost.", got))

    # The planted change run has no primary, suite, size or cost values, so
    # every cell reads not measured and the columns carry the arm files'
    # own line counts.
    _, _, text = rendered(planted_change_run("any-revision"), seed, {})

    def row_start(arm, verdict):
        return "| `%s` | %s lines | %s |" % (
            arm, format(context_lines(arm), ","), verdict)
    checks.extend([
        ("the finding table opens the report",
         0 <= text.find("## Executive summary")
         < text.find("## What produced"), None),
        ("the summary is the radar, one image per theme",
         all("-radar-%s.svg#gh-%s-mode-only)" % (theme, theme) in text
             for theme in RADAR_THEMES)
         and text.find("## Executive summary") < text.find("![Radar per arm]")
         < text.find("## Arms against `none`"), None),
        ("it has a row per arm, the bare arm first, with the files' lines",
         0 < text.find("| `none` | no file | — |")
         < text.find(row_start("hybrid", "Not measured"))
         and context_lines("skills") > context_lines("hybrid"),
         prose_of(text, "## Arms against `none`")),
        ("an unmeasured run answers Not measured in every cell",
         row_start("hybrid", "Not measured") + " not measured |" in text
         and row_start("skills", "Not measured") + " not measured |" in text
         and "Together: not measured. K = 3," in text,
         prose_of(text, "## Arms against `none`")),
        ("each file's why-line sits between the table and the reading",
         "▲ better and ▼ worse" in text
         and 0 < text.find("▲ better and ▼ worse")
         < text.find("**`hybrid`, Not measured.** Every win is "
                     "something a tool counts.")
         < text.find("**`skills`, Not measured.**")
         < text.find("Together:"), prose_of(text, "## Arms against `none`")),
    ])

    # A run reusing an earlier round's trials: five arms, `hybrid` and
    # `reference` reused, the judge's design score constant per arm so each
    # contrast's verdict is known. Every declared contrast is printed, one
    # column per file arm, and the reused arms and the contrasts crossing
    # rounds are named.
    design = {"none": 3, "inline": 3, "hybrid": 3, "reference": 4,
              "skills": 4}
    trials = {trial_name(arm, index): {
        "scores": ({"reused_from": {"name": "planted"}}
                   if arm in ("hybrid", "reference") else {}),
        "change": None, "security": None,
        "judge": {"answer": {"rubric": {"design": {"score": score}}}}}
        for arm, score in design.items() for index in range(1, 4)}
    _, _, text = rendered(trials, seed, {})
    finding = prose_of(text, "## Arms against `none`")

    def row_start(arm, verdict):
        return "| `%s` | %s lines | %s |" % (
            arm, format(context_lines(arm), ","), verdict)
    checks.extend([
        ("a five-arm run prints one row per arm",
         all("| `%s` |" % arm in finding
             for arm in ("none", "inline", "hybrid", "reference", "skills")),
         finding),
        ("it prints every declared contrast its arms ran",
         all("%s − %s" % pair in finding for pair in active_contrasts(trials)
             if pair[1] != BARE)
         and len(section_rows(text, "## Verdict vector",
                              "Design (SOLID and patterns), 1-5")[0]
                 .split(" | ")) == len(active_contrasts(trials)) + 1,
         finding),
        ("the reused arms and the contrasts crossing rounds are named",
         "Reused from an earlier round: hybrid (3 trials) and reference (3 "
         "trials). Pairing them with this round's trials, across days: "
         "hybrid − none, reference − none and skills − hybrid."
         in finding and "reused from an earlier round: hybrid and reference"
         in finding, finding),
        ("the reading sets the longest measured file against the shortest",
         "Together: the long file added quality, the short one did not"
         in finding
         and all(row_start(arm, verdict) in finding for arm, verdict in
                 (("hybrid", "Not measured"), ("inline", "No"),
                  ("reference", "Not measured"), ("skills", "Yes"))),
         finding),
        ("a trial's repeats are meaned, and one judging means itself",
         judge_score({"judgings": [
             {"answer": {"rubric": {"design": {"score": 4}}}},
             {"answer": {"rubric": {"design": {"score": 3}}}},
             {"answer": {"rubric": {"design": {"score": 3}}}}]},
             "design") == 10 / 3.0
         and judge_score(
             {"judge": {"answer": {"rubric": {"design": {"score": 3}}}}},
             "design") == 3, None),
        ("a contrast crossing rounds carries no verdict and counts nowhere",
         CROSSING_VERDICT in text
         and "skills − hybrid unscored (0 won, 0 failed)" in finding, finding),
        ("a three-arm run prints only its own contrasts",
         "| Metric | hybrid−none | skills−none | skills−hybrid |"
         in rendered(planted_change_run("r"), seed, {})[2], None),
    ])
    return checks


def iso_checks(seed):
    """The ISO radar's rules: a sub-score as the share of targets met, an
    empty sub-characteristic not measured, an axis as the mean of its
    sub-scores, an arm as the mean over its trials, a broken build against
    Reliability alone, a marker only past the margin, the drawing, and the
    round that draws it."""
    checks = []

    def planted(install=True, probes=None, **scores):
        """A working build, with each named probe's outcome and each named
        score's value; `install=False` plants a build that did not."""
        trial = {"scores": {"install": {"value": install},
                            "boot": {"value": {"factory": True,
                                               "index_status": 302}}},
                 "judge": None, "judgings": [], "change": None,
                 "security": {"probes": {name: {"passed": passed}
                                         for name, passed
                                         in (probes or {}).items()}}}
        for key, value in scores.items():
            trial["scores"][key] = {"value": value, "missing": None}
        return trial

    # Confidentiality asks four probes: two passed, one failed and one not
    # run read 2 of 3, and Compatibility, with no target, reads not measured.
    trial = planted(probes={"password_at_rest": True,
                            "account_enumeration": True,
                            "secret_key": False})
    scores = iso_trial_scores(trial)
    got = (round(scores["Security"]["Confidentiality"], 4),
           scores["Compatibility"]["Interoperability"],
           iso_axis_score(scores["Compatibility"]))
    checks.append(("a sub-score is the share of its measured targets met, "
                   "and one with none reads not measured",
                   got == (round(2 / 3, 4), None, None), got))

    # Each sub-characteristic weighs the same: Security at 2 of 3 on one row
    # and 0 of 1 on another reads 33, not 2 of 4.
    trial = planted(probes={"password_at_rest": True,
                            "account_enumeration": True,
                            "secret_key": False, "debug": False})
    scores = iso_trial_scores(trial)
    got = {sub: score for sub, score in scores["Security"].items()
           if score is not None}
    axis = iso_axis_score(scores["Security"])
    checks.append(("an axis is the mean of its measured sub-scores, each "
                   "weighing the same",
                   got == {"Confidentiality": 2 / 3, "Resistance": 0.0}
                   and round(axis, 4) == round(100 / 3, 4), (got, axis)))

    # An arm is the mean over its trials: 100 and 0 on Flexibility read 50.
    run = {"hybrid-1": planted(), "hybrid-2": planted(),
           "none-1": planted()}
    run["hybrid-2"]["scores"]["install"]["value"] = True
    table = iso_table(run)
    table["iso:Flexibility"]["values"]["hybrid"][2] = 0.0
    got = (arm_mean(table, "iso:Flexibility", "hybrid"),
           arm_mean(table, "iso:Flexibility", "none"))
    checks.append(("an arm is the mean over its trials", got == (50.0, 100.0),
                   got))

    # A broken build fails Reliability's install target and is left out of
    # every other axis, so it counts once.
    broken = planted(install=False, mypy=0, html_validity=0)
    broken["scores"]["mypy"]["seen"] = {"lines": 1000}
    scores = iso_trial_scores(broken)
    got = {axis: iso_axis_score(per_sub) for axis, per_sub in scores.items()}
    checks.append(("a broken build counts against Reliability only",
                   got["Reliability"] == 50.0 and all(
                       score is None for axis, score in got.items()
                       if axis != "Reliability"), got))

    # A marker turns only past the axis's margin: 3 points over a 5-point
    # margin stays a dot, 20 over turns up, 20 under turns down.
    bare = {index: 50.0 + (index % 3) for index in range(1, 16)}
    markers = []
    for shift in (3.0, 20.0, -20.0):
        table = {"iso:Security": {"label": "Security", "direction": UP,
                                  "values": {"none": bare, "hybrid": {
                                      index: value + shift
                                      for index, value in bare.items()}}}}
        results = iso_contrasts(table, seed)
        markers.append(iso_marker(results["iso:Security"]["hybrid-none"]))
    checks.append(("a marker turns only past the axis's margin",
                   markers == ["dot", "better", "worse"], markers))
    unread = iso_marker({"verdict": "not computed"})
    checks.append(("an axis that could not be read carries no marker",
                   unread is None, unread))

    # The move shown beside a marker is the contrast's mean over the blocks
    # it paired, not the difference of the arms' means over every trial: a
    # broken bare build leaves those over different blocks, with a sign of
    # their own.
    bare = {1: 40.0, 2: 40.0, 3: None}
    ours = {1: 50.0, 2: 50.0, 3: 0.0}
    iso = {"iso:Security": {"label": "Security", "direction": UP,
                            "values": {"none": bare, "hybrid": ours}}}
    for axis, _ in ISO_AXES:
        iso.setdefault("iso:" + axis, {"label": axis, "direction": UP,
                                       "values": {}})
    results = iso_contrasts(iso, seed)
    table = {"cost_usd": {"values": {"none": {1: 4.0}, "hybrid": {1: 8.0}}}}
    axes = iso_panels(table, iso, results, [("hybrid", "none")])[0][2]
    got = next((score, bare, moved) for axis, score, bare, _, moved in axes
               if axis == "Security")
    checks.append(("the move shown is the contrast's mean over the blocks "
                   "it paired", got == (100 / 3, 40.0, 10.0), got))

    # A withdrawn metric's target drops out of the radar and its tables, as
    # its row does from the contrasts.
    trial = planted(probes={"password_at_rest": True,
                            "account_enumeration": False})
    kept = iso_trial_scores(trial)["Security"]["Confidentiality"]
    dropped = iso_trial_scores(
        trial, ("probe:account_enumeration",))["Security"]["Confidentiality"]
    run = {"hybrid-1": planted(), "none-1": planted()}
    lines = iso_axis_lines(run, iso_table(run, ("install",)),
                           ["none", "hybrid"], None, ("install",))
    installability = [line for line in lines
                      if line.startswith("| Installability |")]
    checks.append(("a withdrawn metric's target is not measured",
                   kept == 0.5 and dropped == 1.0
                   and installability[0].count(NOT_MEASURED) == 2,
                   (kept, dropped, installability)))

    # A contrast over fewer pairs than the round's blocks names its count
    # in the axis's table, as the metric tables do.
    sparse = {"iso:Security": {"label": "Security", "direction": UP,
                               "values": {"none": {1: 40.0, 2: 40.0},
                                          "hybrid": {1: 50.0, 2: 60.0}}}}
    for axis, _ in ISO_AXES:
        sparse.setdefault("iso:" + axis, {"label": axis, "direction": UP,
                                          "values": {}})
    results = iso_contrasts(sparse, seed)
    lines = iso_axis_lines(run, sparse, ["none", "hybrid"], results, (), 15)
    against = [line for line in lines if line.startswith("| against `none`")]
    checks.append(("an axis contrast over fewer pairs than blocks names its "
                   "count", any("(2 pairs)" in line for line in against),
                   against[:1]))

    # The aggregate keeps the ISO reading, so a cell marked as not computed
    # by BCa leads to a method the file holds.
    payload = aggregate(seed, run, {}, {}, {}, None,
                        iso_reading(run, seed, ("install",)))
    got = (sorted(payload.get("iso", {})),
           payload.get("iso", {}).get("withdrawn"),
           "iso:Security" in payload.get("iso", {}).get("results", {}),
           "iso" in aggregate(seed, run, {}, {}, {}, None, None))
    checks.append(("the aggregate keeps the ISO reading where the round "
                   "draws it", got == (["results", "table", "withdrawn"],
                                       ["install"], True, False), got))

    # The plain words follow the ISO markers, not the pilot's axes: a
    # Functionality better and a Reliability dot read as functionality,
    # with the cost on a line of its own.
    iso_results = {"iso:" + axis: {"hybrid-none": {"verdict": "held"}}
                   for axis, _ in ISO_AXES}
    iso_results["iso:Functionality"]["hybrid-none"] = {"verdict": "better"}
    iso_results["iso:Usability"]["hybrid-none"] = {"verdict": "worse"}
    planted_results = {key: {"hybrid-none": {"verdict": "better" if key
                                             == "task_success" else "held"}}
                       for key in ANSWERED + ("reliability",)}
    for _, keys in RADAR_AXES:
        for key in keys:
            planted_results.setdefault(key, {"hybrid-none": {
                "verdict": "worse"}})
    table = {"cost_usd": {"values": {"none": {1: 4.0}, "hybrid": {1: 8.8}}},
             "task_success": {"values": {"hybrid": {1: 1.0}}},
             "install": {"values": {"hybrid": {1: 1.0}}}}
    words = plain_arm_lines({}, table, planted_results, "hybrid", 516,
                            ({}, iso_results, ()))
    checks.append(("the plain words follow the ISO markers, with the cost "
                   "on its own line",
                   "- Better than no rules file at: functionality." in words
                   and "- Worse at: usability." in words
                   and "- Cost: about $8.80 a run, against $4.00 with no "
                   "rules file." in words, words[:8]))

    # Every target reads a metric row, a probe security.py runs, or a
    # reading of the radar's own; a target pointed elsewhere would read not
    # measured for every trial without failing.
    import security
    probes = set(security.SECURITY_PROBES + security.DATA_PROTECTION_PROBES)
    keys = {key for key, _, _, _ in METRICS} | set(ISO_EXTRA)
    stray = sorted(source for _, _, _, source, _, _ in iso_targets()
                   if not (source[len("probe:"):] in probes
                           if source.startswith("probe:")
                           else source in keys))
    checks.append(("every target reads a metric row, a probe or a reading "
                   "of the radar's own", not stray, stray))
    checks.append(("every axis carries a margin",
                   set(ISO_MARGINS) == {axis for axis, _ in ISO_AXES},
                   sorted(ISO_MARGINS)))

    # The tables mark a sub-characteristic with fewer than three targets and
    # read an empty one as not measured, never 0 %.
    run = {"hybrid-1": planted(), "none-1": planted()}
    table = iso_table(run)
    lines = iso_axis_lines(run, table, ["none", "hybrid"])
    thin = [line for line in lines if line.startswith("| Installability |")]
    empty = [line for line in lines if line.startswith("| Co-existence |")]
    checks.append(("the tables mark a thin sub-characteristic and read an "
                   "empty one as not measured",
                   len(thin) == 1 and "(fewer than 3 targets)" in thin[0]
                   and "100 %" in thin[0] and len(empty) == 1
                   and empty[0].count(NOT_MEASURED) == 3
                   and "0 %" not in empty[0], thin + empty))

    # The drawing: a panel per arm with its cost line, the dashed target
    # ring and the bare outline in each, a filled triangle up for better, a
    # hollow one down for worse, a dot within the margin, in both themes.
    axes = [(axis, score, bare, marker, moved) for (axis, _), (
        score, bare, marker, moved) in zip(ISO_AXES, [
            (95.0, 95.0, "dot", 0.0), (70.0, 80.0, "worse", -10.0),
            (None, None, None, None), (60.0, 45.0, "better", 15.0),
            (75.0, 85.0, "worse", -10.0), (90.0, 60.0, "better", 30.0),
            (80.0, 55.0, "better", 25.0), (55.0, 55.0, "dot", 0.0)])]
    panels = [("hybrid", "$9.30/run, 2.2x none", axes),
              ("inline", "$14.18/run, 3.3x none", axes)]
    drawn = {theme: iso_radar_svg(panels, theme) for theme in RADAR_THEMES}
    try:
        trees = {theme: ElementTree.fromstring(svg)
                 for theme, svg in drawn.items()}
    except ElementTree.ParseError as error:
        trees = {"error": str(error)}
    space = "{http://www.w3.org/2000/svg}"

    def shapes(tree):
        polygons = list(tree.iter(space + "polygon"))
        triangles = [polygon for polygon in polygons
                     if len(polygon.get("points").split()) == 3]
        return {
            "target rings": sum(1 for polygon in polygons
                                if polygon.get("stroke-dasharray")),
            "filled up": sum(1 for polygon in triangles
                             if polygon.get("stroke") is None),
            "hollow down": sum(1 for polygon in triangles
                               if polygon.get("stroke") is not None),
            "dots": sum(1 for _ in tree.iter(space + "circle")),
            "costs": [text.text for text in tree.iter(space + "text")
                      if text.text and text.text.endswith("x none")],
            "labels": [text.text for text in tree.iter(space + "text")
                       if text.text in dict(ISO_AXES)]}
    got = {theme: shapes(tree) for theme, tree in trees.items()
           if theme != "error"}
    expected = {"target rings": 2, "filled up": 6 + 1, "hollow down": 4 + 1,
                "dots": 4 + 1, "costs": [panel[1] for panel in panels],
                "labels": [axis for axis, _ in ISO_AXES] * 2}
    checks.append(("the ISO radar draws a panel per arm with its cost, the "
                   "target ring, the markers by shape, in both themes",
                   "error" not in trees and drawn["light"] != drawn["dark"]
                   and all(shape == expected for shape in got.values()),
                   got))

    # An axis not measured gets no vertex, so the shapes have one point per
    # measured axis, seven of eight here, and a measured 0 % still has its
    # point at the centre.
    light = trees.get("light", ElementTree.Element("svg"))
    filled = [polygon for polygon in light.iter(space + "polygon")
              if polygon.get("fill-opacity")]
    outlines = [polygon for polygon in light.iter(space + "polygon")
                if polygon.get("stroke") == ISO_COLOURS["light"]["bare"]]
    zeroed = [(axis, 0.0 if axis == "Compatibility" else score, bare,
               marker, moved) for axis, score, bare, marker, moved in axes]
    zero_tree = ElementTree.fromstring(iso_radar_svg(
        [("hybrid", "$1.00/run", zeroed)], "light"))
    zero_filled = [polygon for polygon in zero_tree.iter(space + "polygon")
                   if polygon.get("fill-opacity")]
    got = ([len(polygon.get("points").split()) for polygon in filled],
           [len(polygon.get("points").split()) for polygon in outlines],
           [len(polygon.get("points").split()) for polygon in zero_filled])
    checks.append(("an axis not measured leaves no vertex, unlike a "
                   "measured 0 %", got == ([7, 7], [7, 7], [8]), got))

    # Every axis label fits inside the image and clear of the other panel,
    # at about 8 pixels a character for the bold label.
    labels = [(float(text.get("x")), text.get("text-anchor"), text.text)
              for text in light.iter(space + "text")
              if text.text in dict(ISO_AXES)]
    width = float(light.get("width"))
    extents = [(x - 8 * len(text), x) if anchor == "end"
               else (x, x + 8 * len(text)) if anchor == "start"
               else (x - 4 * len(text), x + 4 * len(text))
               for x, anchor, text in labels]
    left = [right for left_, right in extents if left_ < width / 2]
    right = [left_ for left_, right_ in extents if left_ >= width / 2]
    checks.append(("every axis label fits inside the image and clear of "
                   "the other panel",
                   len(labels) == 2 * len(ISO_AXES)
                   and all(0 <= left_ and right_ <= width
                           for left_, right_ in extents)
                   and max(left) < min(right), (min(extents), max(extents))))
    readings = [axis_reading(score, marker, moved)
                for score, marker, moved in ((90.0, "better", 30.0),
                                             (70.0, "worse", -10.0),
                                             (95.0, "dot", 0.0),
                                             (None, None, None))]
    checks.append(("an axis label reads its share and its move past the "
                   "margin",
                   readings == ["90 % ▲ +30", "70 % ▽ −10",
                                "95 % ●", NOT_MEASURED], readings))

    # A round after the pilot is read with the ISO radar; a pilot round
    # keeps the radar it registered.
    later = {"none-1": planted(), "hybrid-1": planted()}
    got = (iso_rules(later), iso_rules(planted_change_run("any")),
           iso_rules({"hand-1": planted(), "none-1": planted()}))
    checks.append(("a round after the pilot draws the ISO radar, and the "
                   "pilot its own", got == (True, False, False), got))

    # Rendered: the summary reads the ISO radar, the plain report its plain
    # words, the appendix one table per axis, and the images hold the ring.
    for name, trial in later.items():
        trial["scores"]["cost"] = {"value": {"cost_usd": 4.0}}
    later["hybrid-1"]["scores"]["cost"]["value"]["cost_usd"] = 8.8
    table = collect(later)
    results = round_contrasts(later, table, seed)
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-iso-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    target = write_report(scratch, later, table, results, seed,
                          out_dir=scratch)
    stem = target[:-len(".md")]
    texts = {}
    for suffix in ("", "-appendix", "-record", "-radar-light.svg"):
        with io.open(stem + suffix if suffix.endswith(".svg")
                     else stem + suffix + ".md", encoding="utf-8") as handle:
            texts[suffix] = handle.read()
    shutil.rmtree(scratch, ignore_errors=True)
    got = {"summary": ISO_READING[:60] in texts["-record"],
           "plain": ISO_PLAIN_READING[:60] in texts[""],
           "appendix": ISO_TABLE_READING[:60] in texts["-appendix"]
           and all("### %s" % axis in texts["-appendix"]
                   for axis, _ in ISO_AXES)
           and "| Sub-characteristic | `none` | `hybrid` | Targets |"
           in texts["-appendix"],
           "image": "stroke-dasharray" in texts["-radar-light.svg"]
           and "$8.80/run, 2.2x none" in texts["-radar-light.svg"]}
    checks.append(("a later round's report, appendix and images carry the "
                   "ISO radar", all(got.values()), got))
    return checks


def exclusion_checks():
    """A trial the re-scan flags is left out of the figures; a flagged change
    task takes only its change reading; a reached trial is a lost one."""
    def planted():
        return {name: {"scores": {"name": name}, "change": {"name": name}}
                for name in ("none-1", "inline-1", "hand-1")}

    hit = [{"tool": "Bash", "term": "hidden-suite", "call": "planted"}]
    trials = planted()
    left_out = exclude_reached(trials, [
        {"name": "inline-1", "hits": hit},
        {"name": "hand-1" + CHANGE_TASK, "hits": hit},
        {"name": "none-1", "hits": []},
        {"name": "short-1", "hits": hit}])
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-exclusion-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    with io.open(os.path.join(scratch, "run-planted.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"trials": [
            {"arm": "inline", "trial": 1, "task": "build",
             "outcome": "reached", "reason": "planted",
             "started_at": "2026-10-15T10:00:00"},
            {"arm": "inline", "trial": 1, "task": "build",
             "outcome": "completed",
             "started_at": "2026-10-15T11:00:00"}]}, handle)
    lost = lost_trials(scratch)
    shutil.rmtree(scratch, ignore_errors=True)
    return [
        ("a reached build trial is left out whole",
         "inline-1" not in trials and "none-1" in trials, sorted(trials)),
        ("a reached change task takes only its change reading",
         trials["hand-1"]["change"] is None
         and trials["hand-1"]["scores"] == {"name": "hand-1"},
         trials.get("hand-1")),
        ("only what was flagged and held is named as left out",
         left_out == ["inline-1", "hand-1" + CHANGE_TASK], left_out),
        ("a reached trial is listed among the lost, with its re-run",
         [(entry["name"], entry["rerun"]) for entry in lost]
         == [("inline-1", "completed")], lost),
    ]


def cross_checks(seed):
    """The other vendor's judge withholds a verdict it reads the other way,
    leaves one it agrees with, and its agreement is counted per row."""
    def judged(model, design, readability):
        judging = {"outcome": "judged", "model": model,
                   "answer": {"rubric": {"design": {"score": design},
                                         "readability":
                                             {"score": readability}}}}
        return {"scores": {}, "judge": judging, "judgings": [judging],
                "change": None, "security": None}

    # The rounds' judge reads inline better on both rows. The other reads full
    # worse on design and better on readability.
    ours, theirs = {}, {}
    for index, (treated_design, other_design, treated_reads, other_reads) in \
            enumerate(((4, 2, 4, 4), (4, 2, 5, 4), (5, 1, 4, 5)), 1):
        ours["none-%d" % index] = judged("ours", 2, 3)
        ours["inline-%d" % index] = judged("ours", treated_design, treated_reads)
        theirs["none-%d" % index] = judged("theirs", 4, 3)
        theirs["inline-%d" % index] = judged("theirs", other_design,
                                           other_reads)
    results = contrasts(collect(ours), seed)
    before = (results["judge_design"]["inline-none"]["verdict"],
              results["judge_readability"]["inline-none"]["verdict"])
    check = cross_check(ours, theirs, seed)
    withheld = disagree(results, check)
    text = "\n".join(cross_check_section(check))

    # Only the none trials read: the inline-none contrast has no other reading,
    # so the rounds' judge's verdict stands.
    unread = contrasts(collect(ours), seed)
    partial = cross_check(ours, {name: trial for name, trial
                                 in theirs.items() if name.startswith("none")},
                          seed)
    disagree(unread, partial)
    return [
        ("the planted rounds' judge reads inline better on both rows",
         before == ("better", "better"), before),
        ("a direction the other judge reverses loses its verdict",
         results["judge_design"]["inline-none"]["verdict"] == DISAGREE_VERDICT
         and [entry["metric"] for entry in withheld] == ["judge_design"],
         results["judge_design"]["inline-none"]["verdict"]),
        ("a direction both judges read keeps its verdict",
         results["judge_readability"]["inline-none"]["verdict"] == "better",
         results["judge_readability"]["inline-none"]["verdict"]),
        ("agreement is counted per row over the trials both read",
         check["rows"]["judge_design"] == {"trials": 6,
                                           "mean_difference": -0.3333,
                                           "within_one": 0.0}
         and check["rows"]["judge_readability"]["within_one"] == 1.0,
         check["rows"]),
        ("the section names the model and the withheld verdict",
         "`theirs` read 6 trial(s)" in text and "- design, inline-none" in text,
         text[:200]),
        ("a contrast the other judge did not read keeps its verdict",
         unread["judge_design"]["inline-none"]["verdict"] == "better",
         unread["judge_design"]["inline-none"]["verdict"]),
        ("a root with no judgings yields no cross-check",
         load_cross_check(os.path.join(HERE, "no-such-root"), ours) == {},
         None),
        ("the rounds' own judge is caught posing as the other",
         shared_judges(ours, ours) == ["ours"]
         and shared_judges(ours, theirs) == [],
         shared_judges(ours, ours)),
    ]


def documents_checks(seed):
    """A run writes three documents: a plain report with the radars and a
    verdict per approach naming its deciding measures, an appendix of three
    sections, and the full record; each holds the declared width."""
    trials = planted_change_run("any-revision")
    table = collect(trials)
    results = contrasts(table, seed, crossed_labels(trials))
    results["task_success"]["skills-none"]["verdict"] = "worse"
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-report-documents-self-test")
    shutil.rmtree(scratch, ignore_errors=True)
    os.makedirs(scratch)
    target = write_report(scratch, trials, table, results, seed,
                          out_dir=scratch)
    stem = target[:-len(".md")]
    texts = {}
    for suffix in ("", "-appendix", "-record"):
        with io.open(stem + suffix + ".md", encoding="utf-8") as handle:
            texts[suffix] = handle.read()
    shutil.rmtree(scratch, ignore_errors=True)
    report, appendix = texts[""], texts["-appendix"]
    width = markdown_width()
    over = [line for text in texts.values() for line in text.splitlines()
            if len(line) > width and not line.startswith(("|", "#"))]
    sections = [line for line in appendix.splitlines()
                if line.startswith("## ")]
    return [
        ("the report names each approach and its verdict in plain words",
         "### `skills`" in report and "### `hybrid`" in report
         and "**Verdict: worse**, because of the hidden tests." in report
         and PLAIN_VERDICT_RULE[:40] in report, report[:400]),
        ("the judge is checked by its evidence, not a person",
         "No person scores the judge." in texts["-record"]
         and "holdout" not in texts["-record"].lower(), None),
        ("the report links its appendix, and the appendix the record",
         "-appendix.md)" in report and "-record.md)" in appendix, None),
        ("the appendix holds what produced the results, the radar's axes "
         "and the verdict vector, and nothing else",
         sections == ["## What produced the results",
                      "## The radar's axes, row by row",
                      "## The verdict vector"]
         and all("### %s" % axis in appendix for axis, _ in RADAR_AXES),
         sections),
        ("every document holds the declared width", over == [], over),
        ("a round too small to decide says so in the report and the "
         "appendix", "can be called established" in report
         and "Every interval below is descriptive." in appendix, None),
        ("a comparison across rounds reads as not given, not too few runs",
         plain_verdict({key: {"inline-none": {"verdict": CROSSING_VERDICT}}
                        for key in ANSWERED}, "inline-none", "Not measured")
         .startswith("**Verdict: not given.**"), None),
        ("a round 5 run short of its last block says it is provisional",
         any("block %d still miss a run" % ROUND5_K in line
             for line in sureness_lines(
                 {trial_name(arm, block): {} for arm in ROUND5_RUN
                  for block in range(1, ROUND5_K)}, ROUND5_K - 1)), None),
        ("a run stopped and not yet run again is counted as missing",
         rerun_lines([{"rerun": "completed"}, {"rerun": None}])
         == ["- 1 run was stopped part-way, for example by a usage limit, "
             "and run again from the start. Only complete runs count.",
             "- 1 stopped run has not been run again yet, so it is missing."],
         rerun_lines([{"rerun": "completed"}, {"rerun": None}])),
        ("a broken build is named even where reliability reads neutral",
         any(line.startswith("- Noted, though reliability")
             for line in plain_arm_lines(
                 {"inline-1": {"scores": {"boot": {"value": {
                     "factory": False}}}}, "inline-2": {"scores": {}}},
                 {"task_success": {"values": {"none": {1: 1.0, 2: 1.0},
                                              "inline": {1: 0.0, 2: 1.0}}},
                  "cost_usd": {"values": {"none": {1: 1.0}, "inline": {1: 1.0}}}},
                 {key: {"inline-none": {"verdict": "no improvement shown"}}
                  for _, keys in RADAR_AXES for key in keys}
                 | {key: {"inline-none": {"verdict": "no improvement shown"}}
                    for key in ANSWERED}, "inline", 391)), None),
        ("run counts come from the runs scored, a spread where they differ",
         times({"none": 15, "skills": 12, "hybrid": 15},
               ["skills", "hybrid"]) == "between 12 and 15 times"
         and times({"none": 15}, ["none"]) == "15 times", None),
    ]


def self_test(seed):
    """Check the verdict rule, the relative margin, the withdrawal of a
    metric and the reach section."""
    checks = []
    for label, differences, direction, expected in WORKED:
        interval = bca_interval(list(differences), seed)
        got = verdict(interval, direction)
        checks.append(("%s -> %s" % (label, expected), got == expected, got))

    # A relative margin is a share of the baseline arm's mean: 15 % of a
    # baseline of 100 lines admits 10 lines more churn and refuses 20, and
    # 10 % of 20 type errors per KLOC admits 1.5 more and refuses 3.
    margins = (
        ("10 more lines on 100 is preserved", "churn_lines",
         {"low": -5.0, "high": 10.0}, 100.0, True),
        ("20 more lines on 100 is not", "churn_lines",
         {"low": 5.0, "high": 20.0}, 100.0, False),
        ("no baseline makes no relative claim", "churn_lines",
         {"low": -5.0, "high": 10.0}, None, None),
        ("1.5 more per KLOC on 20 is preserved", "mypy_per_kloc",
         {"low": -1.0, "high": 1.5}, 20.0, True),
        ("3 more per KLOC on 20 is not", "mypy_per_kloc",
         {"low": 0.5, "high": 3.0}, 20.0, False),
    )
    for label, key, interval, baseline, expected in margins:
        answer = non_inferior(key, interval, DOWN, baseline)
        got = None if answer is None else answer["within"]
        checks.append((label, got == expected, got))

    # Every per-KLOC row is a static-analysis count, so each carries the one
    # registered margin; a row added without it fails here.
    per_kloc_rows = {key for key, _, _, _ in METRICS
                     if key.endswith("_per_kloc")}
    covered = all(MARGINS.get(key, (None,))[0] == "10 % relative"
                  for key in per_kloc_rows)
    checks.append(("every per-KLOC row carries the static margin",
                   covered and per_kloc_rows == set(STATIC_PER_KLOC),
                   sorted(per_kloc_rows)))

    # A primary the judge asks for and the report does not lead with, or one
    # without its margin, its threshold or its words, would be read nowhere
    # or crash the finding table; a row added to one side only fails here.
    import judge
    judged = {"judge_" + name for name in judge.PRIMARY}
    metric_keys = {key for key, _, _, _ in METRICS}
    worded = {key for key, _ in READS}
    lacking = sorted(key for key in PRIMARY
                     if not (key in MARGINS and key in SHORT
                             and key in metric_keys
                             and (key in worded or key in PROBE_RATES)))
    unmatched = sorted(judged.symmetric_difference(
        key for key in PRIMARY if key not in PROBE_RATES))
    checks.append(("every primary the judge asks for is led with, worded "
                   "and given its margins",
                   not lacking and not unmatched,
                   {"lacking": lacking, "unmatched": unmatched}))

    # A probe rate is read from the reading security.py files under the same
    # name; a row pointed at a name it never files would read missing for
    # every trial, and the primary would decide nothing without failing.
    import security
    filed = {name: {"value": 0, "missing": None}
             for name in security.STATIC_PROBES + ("debug",)}
    security.add_probes(filed, None, "the planted trial did not boot",
                        lost=True)
    rows = {key: getter for key, _, _, getter in METRICS}
    unread = sorted(key for key in PROBE_RATES
                    if rows[key]({"security": filed}) is None
                    or rows[key]({"security": filed})
                    != filed[key]["value"])
    checks.append(("every probe rate reads the rate security.py files",
                   not unread, unread))

    # A nested count divides by the lines its own tool saw.
    planted = {"scores": {"complexity": {"value": {"over_15": 3},
                                         "missing": None,
                                         "seen": {"lines": 1500}}}}
    got = per_kloc(planted, "complexity", "over_15")
    checks.append(("a nested count is taken per KLOC", got == 2.0, got))
    checks.extend(withdrawal_checks(seed))
    checks.extend(executive_checks(seed))
    checks.extend(documents_checks(seed))
    checks.extend(cross_checks(seed))
    checks.extend(exclusion_checks())
    checks.extend(round5_checks())
    checks.extend(round5d_checks(seed))
    checks.extend(round5e_checks())
    checks.extend(iso_checks(seed))
    checks.extend(band_checks(seed))
    checks.extend(failed_build_checks())
    checks.extend(record_checks())
    checks.extend((label, ok, ok) for label, ok in reach_checks())
    checks.extend((label, ok, ok) for label, ok in lost_checks())
    checks.extend((label, ok, ok) for label, ok in rescan_checks())
    checks.extend((label, ok, ok) for label, ok in registration_checks())
    checks.extend((label, ok, ok) for label, ok in spec_checks())
    checks.extend((label, ok, ok) for label, ok in prompt_checks())
    checks.extend((label, ok, ok) for label, ok in python_checks())
    for label, ok, got in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED, got %r"
                              % (got,)))
    passed = sum(1 for _, ok, _ in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed"
                      % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def audits_dir():
    """The templates source's docs/audits/, where a round's report lands."""
    return os.path.join(templates_root(), *AUDITS)


def is_record(out_dir):
    """Whether a report written to `out_dir` is a round's record."""
    parts = os.path.normcase(os.path.abspath(out_dir)).split(os.sep)
    return parts[-len(AUDITS):] == list(AUDITS)


def main(argv):
    options = parse_args(argv)
    if options.templates:
        os.environ[TEMPLATES_ENV] = options.templates
    if options.self_test:
        return self_test(options.seed)
    if not options.root:
        print("--root is required unless --self-test is given")
        return 2

    trials = load(options.root)
    if not trials:
        print("no scores under %s; score.py writes them"
              % scoring_area(options.root))
        return 2

    out_dir = options.out_dir
    if out_dir is None:
        try:
            out_dir = audits_dir()
        except TrialError as error:
            print("refused: %s, or name --out-dir for a draft" % error)
            return 2

    # A report under docs/audits/ is the round's record, so it is written only
    # from a round archived as it stands; anywhere else it is a draft.
    if is_record(out_dir):
        problem = archive.stamp_problem(options.root)
        if problem:
            print("refused: %s" % problem)
            return 2

    # A hypothesis registered or changed after the round's first trial could
    # have been written to fit what that trial showed, so the round is refused
    # rather than read against it.
    if is_round5(trials):
        try:
            problem = registration_problem(
                options.root, registration_of(trials))
        except TrialError as error:
            problem = str(error)
        if problem:
            print("refused: %s" % problem)
            return 2

        # Two specifications in one round would read as one arm's effect, so
        # a round whose trials did not all get the registered one is refused.
        problem = spec_problem(options.root)
        if problem:
            print("refused: %s" % problem)
            return 2

        # The same holds for the prompt: trials given two prompts would read
        # as one arm's effect.
        problem = prompt_problem(options.root)
        if problem:
            print("refused: %s" % problem)
            return 2

    # Scores installed on two Pythons would read the interpreter as an arm's
    # effect, so a round's scores have to share one.
    problem = python_problem(trials)
    if problem:
        print("refused: %s" % problem)
        return 2

    # A trial that read past its workspace measures what it read, not its
    # arm; the harness voids one its own scan catches, and this re-scan, under
    # the current rule, leaves out any it missed.
    for name in exclude_reached(trials, reaches(options.root)):
        print("left out, having reached past its workspace: %s" % name)
    if not trials:
        print("no trial is left to report once the reached ones are out")
        return 2

    # A round registers its K and goes no further, so a run past it is
    # refused rather than reported as though the bound held.
    k = max(index_of(name) for name in trials)
    if k > ROUND5_K:
        print("refused: the run holds K = %d, past the registered K = %d"
              % (k, ROUND5_K))
        return 2
    table = collect(trials)
    results = round_contrasts(trials, table, options.seed)
    withdrawn = withdrawals(trials)
    withdraw(withdrawn, table, results)

    # A cross-check named and then found empty would print as "no verdict
    # withheld", which reads as agreement; it is refused instead.
    check = None
    if options.cross_check:
        other = load_cross_check(options.cross_check, trials)
        if not other:
            print("refused: no completed judging under %s names a trial of "
                  "this round" % scoring_area(options.cross_check))
            return 2

        # A root restored from the round's archive carries the rounds' own
        # judgings; read as the other vendor, they would agree with
        # themselves.
        shared = shared_judges(trials, other)
        if shared:
            print("refused: %s judged both this round and the cross-check; "
                  "remove the restored root's judge/ before judging it"
                  % ", ".join(shared))
            return 2
        check = cross_check(trials, other, options.seed)
        disagree(results, check)
    iso = (iso_reading(trials, options.seed, withdrawn) if iso_rules(trials)
           else None)
    uses = map_uses(options.root, trials) if is_round5e(trials) else None
    target = write_report(options.root, trials, table, results, options.seed,
                          out_dir, withdrawn, check, iso, uses)

    with io.open(os.path.join(scoring_area(options.root), "aggregate.json"),
                 "w", encoding="utf-8") as handle:
        json.dump(aggregate(options.seed, trials, table, results, withdrawn,
                            check, iso, uses), handle, indent=2,
                  sort_keys=True)
    print("Report: %s" % target)

    # An earlier round read by round 5d's rules is post-hoc: its own page,
    # beside the registered report, which it leaves as it was.
    if options.posthoc_rules and not later_rules_of(trials):
        # The other judge is read by the same rules, so a contrast across
        # rounds is unpaired on both sides before their signs are compared.
        later = posthoc_rules_reading(
            trials, options.seed, withdrawn,
            cross_check(trials, other, options.seed, True) if check else None)
        print("Post-hoc: %s" % write_posthoc_rules(
            trials, later[0], later[1], options.seed, out_dir))
        with io.open(os.path.join(scoring_area(options.root),
                                  "aggregate-posthoc.json"),
                     "w", encoding="utf-8") as handle:
            json.dump({"seed": options.seed, "rules": "round 5d, post-hoc",
                       "table": later[0], "results": later[1]},
                      handle, indent=2, sort_keys=True)
    judged = sum(1 for trial in trials.values() if trial["judge"])
    lib.print_verdict(True, "%d trial(s) aggregated, %d judged"
                      % (len(trials), judged))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
