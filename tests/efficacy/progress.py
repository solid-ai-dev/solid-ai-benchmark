"""Show a run's progress, one bar per arm, read from its run records, and
its scoring's and judging's, read from the scoring area.

Read-only: it opens the run root's `run-*.json` and lists the scoring area,
so it can watch a live run, scoring or judging from a console of its own
without touching a trial. It redraws every `--every` seconds until stopped,
or once with `--once`.
"""

import argparse
import contextlib
import datetime
import glob
import io
import json
import os
import shutil
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402
from harness import (ROUND5_K, SCORABLE, VOIDING, LiveRunError,  # noqa: E402
                     TrialError, canonical, claim_path, now, read_claim,
                     result_of, running_as, scoring_area, split_name)
from report import ROUND5_RUN  # noqa: E402

WIDTH = 30


def runs(root):
    """Every run record in the root, in time order, whole."""
    found = []
    for file in sorted(glob.glob(os.path.join(root, "run-*.json"))):
        try:
            with io.open(file, encoding="utf-8") as handle:
                found.append(json.load(handle))
        except (OSError, ValueError):

            # The harness rewrites a record after every trial, so a read can
            # land mid-write; the next redraw reads it whole.
            continue
    return found


def records(root, runs_read=None):
    """Every build trial record in the root's run records, in time order."""
    found = []
    for run in runs(root) if runs_read is None else runs_read:

        # A trial in flight records no task of its own; the run it sits in
        # says which task it is.
        task = run.get("task", "build")
        found.extend(record for record in run.get("trials", [])
                     if record.get("task", task) == "build")
    return found


def declared_arms(runs_read):
    """The arms the build runs name from their start, each once in order:
    an arm whose first trial is still to come gets its bar all the same."""
    found = []
    for run in runs_read:
        if run.get("task", "build") != "build":
            continue
        for arm in run.get("arms") or ():
            if arm not in found:
                found.append(arm)
    return found


def arms_in(trials, declared=(), asked=()):
    """Round 5's arms, then every other arm the run records name, by a
    trial or from their start, then those asked for, each once in the order
    it first appears."""

    # A root may hold a reused round beside the one in flight, and a round
    # may run arms of its own, as `hand` and `short`. The records say which,
    # so each gets a bar from its first trial on, or from the run's start
    # where the record names its arms; none is dropped as unknown. A run
    # whose record predates that names them with --arms instead.
    found = list(ROUND5_RUN)
    named = [record.get("arm") for record in trials]
    for arm in named + list(declared) + list(asked):
        if arm and arm not in found:
            found.append(arm)
    return tuple(found)


def cost_of(record):
    """What the CLI said a finished trial cost, or 0 where it said nothing."""
    result = record.get("result")
    if not isinstance(result, dict):
        result = result_of(record.get("stdout") or "") or {}
    return result.get("total_cost_usd") or 0.0


def started(record):
    """When a trial started, or None where its record does not say in a
    known zone."""
    try:
        stamp = datetime.datetime.fromisoformat(record["started_at"])
    except (KeyError, TypeError, ValueError):
        return None

    # Records from before starts carried an offset were written in whatever
    # zone the machine was in, which nothing records; no time is read from
    # them rather than a guessed one.
    return stamp if stamp.tzinfo else None


def tally(trials, arms):
    """Per arm: trials done, voided tries, cost, and the trial running."""
    arms = {arm: {"done": set(), "voided": 0, "cost": 0.0, "running": None}
            for arm in arms}
    for record in trials:
        arm = arms.get(record.get("arm"))
        if arm is None:
            continue
        outcome = record.get("outcome")
        arm["cost"] += cost_of(record)
        if outcome in SCORABLE:
            arm["done"].add(record.get("trial"))
        elif outcome in VOIDING:
            arm["voided"] += 1
        elif outcome == "running":
            arm["running"] = record
    return arms


def bar(done, total):
    filled = WIDTH * done // total if total else 0
    return "[%s%s]" % ("#" * filled, "." * (WIDTH - filled))


def render(root, arms=None, k=ROUND5_K, moment=None, asked=()):
    """The progress screen for the run root, as lines: one bar per round-5
    arm, per other arm the run records name, and per arm asked for."""
    moment = moment or now()
    runs_read = runs(root)
    trials = records(root, runs_read)
    arms = arms or arms_in(trials, declared_arms(runs_read), asked)
    counts = tally(trials, arms)
    total = len(arms) * k
    done = sum(len(arm["done"]) for arm in counts.values())
    lines = ["%s  %s" % (root, moment.strftime("%Y-%m-%d %H:%M")), ""]
    for name in arms:
        arm = counts[name]
        line = "%-10s %s %2d/%d  $%7.2f" % (name, bar(len(arm["done"]), k),
                                           len(arm["done"]), k, arm["cost"])
        if arm["voided"]:
            line += "  %d voided" % arm["voided"]
        running = arm["running"]
        if running and started(running):
            minutes = (moment - started(running)).total_seconds() // 60
            line += "  running %s-%s, %d min" % (name, running.get("trial"),
                                                 minutes)
        lines.append(line)

    # The pace is the run's own: wall time since its first trial started,
    # over the trials done, which counts the voided tries' time too.
    starts = [stamp for stamp in map(started, trials) if stamp]
    lines.append("")
    summary = "%-10s %s %2d/%d  $%7.2f" % (
        "all", bar(done, total), done, total,
        sum(arm["cost"] for arm in counts.values()))
    if starts and done:
        elapsed = moment - min(starts)
        left = elapsed / done * (total - done)
        summary += "  %.1f h in, about %.0f h left" % (
            elapsed.total_seconds() / 3600, left.total_seconds() / 3600)
    lines.append(summary)
    return (lines + scoring_lines(root, arms, k)
            + judging_lines(root, arms, k))


def names_in(directory):
    """The trial names a directory holds a `<name>.json` for, each with when
    it was written."""
    try:
        entries = os.listdir(directory)
    except OSError:
        return {}
    return {entry[:-len(".json")]:
            os.path.getmtime(os.path.join(directory, entry))
            for entry in entries if entry.endswith(".json")}


def arm_of(name):
    """A trial name's arm, or None where the name is not a trial's."""
    try:
        return split_name(name)[0]
    except TrialError:
        return None


def blocks_of(names, arm):
    """The blocks of `arm` that `names` hold, each once however it is
    spelled: `none-01` and `none-1` are one trial."""
    found = set()
    for name in names:
        try:
            other, block = split_name(name)
        except TrialError:
            continue
        if other == arm:
            found.add(block)
    return found


def live_scorer(claim):
    """Whether the tool a marker names is still running."""
    try:
        return running_as(claim["pid"], claim.get("tool") or "score.py")
    except LiveRunError:
        return False


def started_of(claim):
    """When a marker's tool started, as a timestamp, or None where the
    marker does not say."""
    try:
        return datetime.datetime.fromisoformat(claim["started"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return None


def since(names, when):
    """The names whose file was written at `when` or later."""
    return {name: written for name, written in names.items()
            if written >= when}


def in_progress(work, written):
    """The trial a tool is working on in `work`, as (when it changed, its
    name), or None.

    A tool rebuilds a trial's directory there before it writes the trial's
    result, so the trial in hand is the newest directory changed since its
    result was last written; one never written counts as changed. A rescore
    keeps the old result until the new one is ready, so the old result's
    presence alone does not say the trial is done. Directories that are not
    a trial's, such as the scorer's tools, are never the trial in hand.
    """
    try:
        entries = [entry for entry in os.listdir(work) if arm_of(entry)]
    except OSError:
        return None
    changed = [(os.path.getmtime(os.path.join(work, entry)), entry)
               for entry in entries]
    changed = [(when, entry) for when, entry in changed
               if when > written.get(entry, 0)]
    return max(changed) if changed else None


def tool_options(module, argv):
    """A tool's command line read with its own parser, or None where the
    parser refuses it."""
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            return module.parse_args(list(argv or [])[1:])
    except SystemExit:
        return None


def whole_scoring(argv):
    """The scorer's options where its command line covers every build
    trial, or None."""

    # Imported here: the scorer's module is only needed once one runs.
    import score
    options = tool_options(score, argv)
    if options is None or options.task != "build":
        return None
    return None if options.trial or options.run else options


def plain_scoring(argv):
    """Whether a scorer's command line scores every build trial still
    without a score, read with the scorer's own parser."""
    options = whole_scoring(argv)
    return options is not None and not options.rescore


def full_rescore(argv):
    """Whether a scorer's command line scores every build trial again."""
    options = whole_scoring(argv)
    return options is not None and bool(options.rescore)


def full_reread(argv):
    """Whether a security reader's command line reads every scored trial
    again."""

    # Imported here, as the scorer's module is.
    import security
    options = tool_options(security, argv)
    return (options is not None and bool(options.reread)
            and not options.trial)


def in_hand(area, scores, readings):
    """What the live scorer is working on, as (phase, when it changed, trial
    name): the trial being scored or the one being read for security, or
    None between the two.

    The scorer scores each trial and then reads the scored ones for
    security. Whichever of the two directories changed last holds the trial
    in hand, so a refused trial's directory, left without a result, does not
    hide the readings that follow it.
    """
    scoring = in_progress(os.path.join(area, "scoring"), scores)
    reading = in_progress(os.path.join(area, "security"), readings)
    if scoring and (not reading or scoring > reading):
        return ("scoring",) + scoring
    if reading:
        return ("security",) + reading
    return None


def scoring_lines(root, arms, k, alive=live_scorer):
    """The scoring's lines: one bar per arm of trials scored, with their
    security readings, and the trial in hand on its arm's line; none before
    scoring starts."""
    area = scoring_area(root)
    if not os.path.isdir(area):
        return []
    scores = names_in(os.path.join(area, "scores"))
    readings = names_in(os.path.join(area, "security-scores"))
    claim = read_claim(claim_path(area, "score.py"))
    live = bool(claim and alive(claim))
    begun = started_of(claim) if live else None

    # A rescore replaces every score, and a reread every reading, so the
    # ones written before it began are what it is still to replace: the bars
    # count only what it has written, and fill as it goes. The trial in hand
    # is still read against every result, old ones included: a directory
    # left from the scoring before, older than its old result, is not being
    # worked on.
    hand = in_hand(area, scores, readings) if live else None
    if begun is not None and full_rescore(claim.get("argv")):
        scores = since(scores, begun)
        readings = since(readings, begun)
    reader = read_claim(claim_path(area, "security.py"))
    reread = started_of(reader) if reader and alive(reader) else None
    if reread is not None and full_reread(reader.get("argv")):
        readings = since(readings, reread)
    if hand:
        phase, changed, trial = hand
        minutes = (time.time() - changed) // 60
        if phase == "scoring":
            working = "  scoring %s, %d min" % (trial, minutes)
        else:
            working = "  reading %s for security, %d min" % (trial, minutes)
    lines = ["", "Scored"]
    total = len(arms) * k
    done = 0
    named = False
    for name in arms:
        scored = len(blocks_of(scores, name))
        read = len(blocks_of(readings, name))
        done += scored
        line = "%-10s %s %2d/%d" % (name, bar(scored, k), scored, k)
        if read:
            line += "  %d read for security" % read

        # The trial in hand sits on its arm's line, as the run's running trial
        # does, with the minutes since its directory last changed.
        if hand and arm_of(trial) == name:
            line += working
            named = True
        lines.append(line)
    summary = "%-10s %s %2d/%d" % ("all", bar(done, total), done, total)

    # A trial of an arm the records do not name has no line of its own, so
    # the summary names it.
    if hand and not named:
        summary += working
    if live:

        # The pace is this scorer's own, from the scores it wrote since it
        # started. What is left is known for a run over every trial, plain
        # or rescoring; a run of named trials or of one record holds only
        # those. The estimate covers the scoring alone, so it is shown only
        # while a trial is being scored: the security readings that follow
        # run at a pace of their own, and a refused trial leaves the bar short
        # with no scoring left to do.
        argv = claim.get("argv")
        whole = plain_scoring(argv) or full_rescore(argv)
        if begun is not None:
            fresh = len(since(scores, begun))
            elapsed = time.time() - begun
            summary += "  %.1f h in" % (elapsed / 3600)
            if (fresh and whole and hand and hand[0] == "scoring"
                    and done < total):
                left = elapsed / fresh * (total - done)
                summary += ", about %.1f h of scoring left" % (left / 3600)
    lines.extend(["", summary])
    return lines


def judgings(judging):
    """The judge's records under `judging`, as (label, record, when written);
    a record caught mid-write is skipped."""
    found = []
    for file in sorted(glob.glob(os.path.join(judging, "T*.json"))):
        try:
            with io.open(file, encoding="utf-8") as handle:
                record = json.load(handle)
            written = os.path.getmtime(file)
        except (OSError, ValueError):
            continue
        if isinstance(record, dict):
            found.append((os.path.basename(file)[:-len(".json")], record,
                          written))
    return found


def judge_in_hand(judging, begun):
    """The blind label the live judge is reading, as (when its bundle was
    built, label), or None.

    The judge builds a label's bundle and writes the label's record once the
    judging ends, so the label in hand is the newest bundle built since the
    judge began with no record yet. The bundle holds no trial name, and the
    label is all the view shows of it.
    """
    bundles = os.path.join(judging, "bundles")
    try:
        entries = [entry for entry in os.listdir(bundles)
                   if entry.startswith("T") and entry[1:].isdigit()]
    except OSError:
        return None
    waiting = []
    for entry in entries:
        if os.path.exists(os.path.join(judging, "%s.json" % entry)):
            continue
        built = os.path.getmtime(os.path.join(bundles, entry))
        if built >= begun:
            waiting.append((built, entry))
    return max(waiting) if waiting else None


def judging_lines(root, arms, k, alive=live_scorer):
    """The judging's lines: one bar per arm of judgings done, out of the
    judgings owed to its trials whose build installed, with the failures
    still owed and the label in hand; none before judging starts."""

    # Imported here, as the scorer's module is.
    import judge
    area = scoring_area(root)
    judging = os.path.join(area, "judge")
    found = judgings(judging)
    claim = read_claim(claim_path(area, "judge.py"))
    live = bool(claim and alive(claim))
    if not live and not any(record.get("outcome") == "judged"
                            for _, record, _ in found):
        return []

    # The judgings owed per trial are the live judge's `--repeat`, or the
    # judge's own default once none runs.
    argv = claim.get("argv") if live else None
    options = tool_options(judge, argv or ["judge.py"])
    repeat = options.repeat if options and options.repeat > 0 else 3

    # A score caught mid-write leaves the failed builds unknown for one
    # redraw, which then owes their judgings; the next redraw reads it whole.
    try:
        failed = judge.failed_builds(root)
    except (OSError, ValueError, KeyError):
        failed = set()
    begun = started_of(claim) if live else None

    # A trial's judged records count up to the repeat and no further: a
    # rejudge adds readings past what is owed, which would overfill the bar.
    # A failed or invalid record counts only while its trial is still short,
    # since the judge owes it again and a later run makes it good. A dry run's
    # record is neither.
    held, failures, fresh = {}, {}, 0
    for _, record, written in found:
        try:
            name = canonical(record.get("trial") or "")
        except TrialError:
            continue
        outcome = record.get("outcome")
        if outcome == "judged":
            held[name] = held.get(name, 0) + 1
            if begun is not None and written >= begun:
                fresh += 1
        elif outcome in ("failed", "invalid"):
            failures[name] = failures.get(name, 0) + 1
    lines = ["", "Judged, %d per trial" % repeat]
    total = done = 0
    for name in arms:
        owed = (k - sum(1 for trial in failed if arm_of(trial) == name)) * repeat
        counted = sum(min(count, repeat) for trial, count in held.items()
                      if arm_of(trial) == name)
        short = sum(count for trial, count in failures.items()
                    if arm_of(trial) == name and held.get(trial, 0) < repeat)
        total += owed
        done += counted
        line = "%-10s %s %2d/%d" % (name, bar(counted, owed), counted, owed)
        if short:
            line += "  %d failed" % short
        lines.append(line)
    summary = "%-10s %s %2d/%d" % ("all", bar(done, total), done, total)

    # The label in hand and the pace are the live judge's own, and only for a
    # judging of every trial: a judge of named trials owes only those, and a
    # dry run judges nothing.
    whole = (options is not None and not options.trial
             and not options.dry_run)
    if live and whole and begun is not None:
        hand = judge_in_hand(judging, begun)
        if hand:
            summary += "  judging %s, %d min;" % (
                hand[1], (time.time() - hand[0]) // 60)
        elapsed = time.time() - begun
        summary += "%s%.1f h in" % (" " if hand else "  ", elapsed / 3600)
        if fresh and done < total:
            left = elapsed / fresh * (total - done)
            summary += ", about %.1f h left" % (left / 3600)
    lines.extend(["", summary])
    return lines


def watch(root, every, asked=()):
    while True:
        lines = render(root, asked=asked)

        # The console's own clear, not an escape sequence: a Windows console
        # can take the sequence and still leave the text scrolled out of the
        # window, which then shows black.
        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        time.sleep(every)


def self_test():
    """A planted run renders each arm's count, voids, cost and running trial,
    in the order the records name the arms, and a record caught mid-write is
    skipped rather than fatal."""
    scratch = tempfile.mkdtemp(prefix="efficacy-progress-")
    moment = datetime.datetime(2026, 10, 29, 12, 0).astimezone()

    def trial(arm, block, outcome, minutes_ago, cost=None):
        record = {"arm": arm, "trial": block, "task": "build",
                  "outcome": outcome,
                  "started_at": (moment - datetime.timedelta(
                      minutes=minutes_ago)).isoformat(timespec="seconds")}
        if cost is not None:
            record["stdout"] = json.dumps({"type": "result",
                                           "total_cost_usd": cost})
        return record

    planted = [trial("none", 1, "completed", 120, 4.0),
               trial("inline", 1, "reached", 90, 10.0),
               trial("inline", 1, "completed", 60, 6.0),
               trial("hybrid", 1, "running", 15),
               trial("hand", 1, "running", 3)]
    with io.open(os.path.join(scratch, "run-1.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "build", "trials": planted}, handle)
    with io.open(os.path.join(scratch, "run-2.json"), "w",
                 encoding="utf-8") as handle:
        handle.write('{"trials": [')

    # A run that names its arms from the start, one of them with no trial
    # yet; a change run naming arms declares none for the build view.
    with io.open(os.path.join(scratch, "run-4.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "build", "arms": ["hand", "short"], "k": 15,
                   "trials": []}, handle)
    with io.open(os.path.join(scratch, "run-5.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "change", "arms": ["lazyref"], "trials": []},
                  handle)

    # A change task in flight, recorded as the harness records one: the task
    # is the run's, not the trial's.
    in_flight = trial("skills", 1, "running", 5)
    del in_flight["task"]
    with io.open(os.path.join(scratch, "run-3.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "change", "trials": [in_flight]}, handle)

    # A root from before starts carried an offset.
    legacy = os.path.join(scratch, "legacy")
    os.makedirs(legacy)
    naive = [dict(record, started_at=record["started_at"][:19])
             for record in planted]
    with io.open(os.path.join(legacy, "run-1.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "build", "trials": naive}, handle)

    def drawn(root):
        try:
            return render(root, moment=moment)
        except Exception as error:
            return ["raised %r" % error]

    empty = os.path.join(scratch, "empty")
    os.makedirs(empty)
    lines, old, bare = drawn(scratch), drawn(legacy), drawn(empty)
    asked = render(scratch, moment=moment, asked=("lazyskills", "hand"))

    # A scoring under way: two arms scored, one read for security, the
    # scorer's tools, a scored trial's directory, the trial in hand, and the
    # scorer's marker. Each file and directory is dated, newest last.
    area = scoring_area(scratch)
    clock = time.time() - 3600

    def dated(path, minutes, folder=False):
        if folder:
            os.makedirs(path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, "w").close()
        os.utime(path, (clock + minutes * 60,) * 2)

    for name, minutes in (("none-1", 5), ("inline-1", 10), ("inline-2", 30)):
        dated(os.path.join(area, "scores", "%s.json" % name), minutes)
    dated(os.path.join(area, "security-scores", "none-1.json"), 6)

    dated(os.path.join(area, "scoring", "inline-2"), 20, folder=True)
    dated(os.path.join(area, "scoring", "hybrid-1"), 40, folder=True)
    dated(os.path.join(area, "scoring", "tools"), 50, folder=True)
    started_at = datetime.datetime.now() - datetime.timedelta(hours=1)
    with io.open(claim_path(area, "score.py"), "w", encoding="utf-8") as handle:
        json.dump({"pid": 4242, "tool": "score.py",
                   "started": started_at.isoformat(timespec="seconds")}, handle)

    def scoring_now(alive=True):
        return scoring_lines(scratch, ROUND5_RUN, ROUND5_K,
                             alive=lambda claim: alive)

    live, stale = scoring_now(), scoring_now(alive=False)

    # A rescore of none-1 rebuilds its directory while its old score stays.
    dated(os.path.join(area, "scoring", "none-1"), 45, folder=True)
    rescoring = scoring_now()

    # Every trial in the scorer's directory scored; inline-1 in the security
    # reader's directory with no reading yet.
    # A refused trial, skills-1, leaves its directory without a score.
    for name, minutes in (("hybrid-1", 55), ("none-1", 56)):
        dated(os.path.join(area, "scores", "%s.json" % name), minutes)
    dated(os.path.join(area, "scoring", "skills-1"), 56.5, folder=True)
    dated(os.path.join(area, "security", "inline-1"), 57, folder=True)
    securing = scoring_now()

    # A plain run with every trial scored, as one of one arm: only the
    # security readings are left, and they have no estimate.
    all_scored = scoring_lines(scratch, ("none",), 1, alive=lambda claim: True)

    # The trial in hand belongs to an arm the records do not name.
    dated(os.path.join(area, "scoring", "hybrid-1"), 58, folder=True)
    one_arm = scoring_lines(scratch, ("none",), 1, alive=lambda claim: True)

    # A rescore of named trials keeps the scores it does not replace, so
    # what is left of it cannot be told from the area.
    with io.open(claim_path(area, "score.py"), "w", encoding="utf-8") as handle:
        json.dump({"pid": 4242, "tool": "score.py",
                   "argv": ["tests/efficacy/score.py", "--rescore",
                            "--trial", "none-1"],
                   "started": started_at.isoformat(timespec="seconds")}, handle)
    rescore_pace = scoring_now()

    # A rescore of every trial: a score and a reading from before it began
    # are the old ones it is still to replace.
    dated(os.path.join(area, "scores", "skills-1.json"), -10)
    dated(os.path.join(area, "security-scores", "inline-1.json"), -5)
    with io.open(claim_path(area, "score.py"), "w", encoding="utf-8") as handle:
        json.dump({"pid": 4242, "tool": "score.py",
                   "argv": ["tests/efficacy/score.py", "--root", "r",
                            "--rescore"],
                   "started": started_at.isoformat(timespec="seconds")}, handle)
    rescore_all = scoring_now()
    whole_rescore = {line.split()[0]: line for line in rescore_all[2:]
                     if line.strip()}

    # The same rescore just begun, with every directory older than its old
    # result: nothing is in hand yet, old results or not.
    for name, minutes in (("hybrid-1", 54), ("skills-1", -11)):
        dated(os.path.join(area, "scoring", name), minutes, folder=True)
    dated(os.path.join(area, "security", "inline-1"), -6, folder=True)
    with io.open(claim_path(area, "score.py"), "w", encoding="utf-8") as handle:
        json.dump({"pid": 4242, "tool": "score.py",
                   "argv": ["tests/efficacy/score.py", "--root", "r",
                            "--rescore"],
                   "started": datetime.datetime.now().isoformat(
                       timespec="seconds")}, handle)
    just_begun = scoring_now()

    # A security reread of every scored trial, with the scorer gone: the
    # reading from before it began is the old one.
    os.remove(claim_path(area, "score.py"))
    dated(os.path.join(area, "security-scores", "hybrid-1.json"), 58)
    reread_at = datetime.datetime.now() - datetime.timedelta(minutes=30)
    with io.open(claim_path(area, "security.py"), "w",
                 encoding="utf-8") as handle:
        json.dump({"pid": 4242, "tool": "security.py",
                   "argv": ["tests/efficacy/security.py", "--root", "r",
                            "--reread"],
                   "started": reread_at.isoformat(timespec="seconds")}, handle)
    reread_all = {line.split()[0]: line for line in scoring_now()[2:]
                  if line.strip()}

    # A judging under way on a root of its own. none-2's build did not
    # install, so none owes 14 trials. none-1 failed once and was judged four
    # times since, one past the repeat; inline-1 holds one judging and one
    # failure; hybrid-1 holds only a dry run's record; a record caught
    # mid-write sits beside them. T9's bundle is in hand; T0's is left from
    # before the judge began.
    judged_root = os.path.join(scratch, "judged")
    judged_area = scoring_area(judged_root)
    judging = os.path.join(judged_area, "judge")
    begun_at = datetime.datetime.now() - datetime.timedelta(hours=1)
    begun_clock = time.mktime(begun_at.timetuple())

    def written(path, record, minutes):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with io.open(path, "w", encoding="utf-8") as handle:
            json.dump(record, handle)
        os.utime(path, (begun_clock + minutes * 60,) * 2)

    written(os.path.join(judged_area, "scores", "none-2.json"),
            {"name": "none-2", "install": {"value": False}}, 1)
    planted_judgings = [("T1", "none-1", "failed"), ("T2", "none-1", "judged"),
                        ("T3", "none-1", "judged"), ("T4", "none-1", "judged"),
                        ("T5", "none-1", "judged"), ("T6", "inline-1", "judged"),
                        ("T7", "inline-1", "failed"),
                        ("T8", "hybrid-1", "dry-run")]
    for minutes, (label, name, outcome) in enumerate(planted_judgings, 2):
        written(os.path.join(judging, "%s.json" % label),
                {"trial": name, "blind_id": label, "outcome": outcome},
                minutes)
    with io.open(os.path.join(judging, "T10.json"), "w",
                 encoding="utf-8") as handle:
        handle.write('{"trial": ')
    dated(os.path.join(judging, "bundles", "T0"),
          (begun_clock - 600 - clock) / 60, folder=True)
    dated(os.path.join(judging, "bundles", "T8"),
          (begun_clock + 9 * 60 - clock) / 60, folder=True)
    dated(os.path.join(judging, "bundles", "T9"),
          (time.time() - 240 - clock) / 60, folder=True)

    def judging_now(argv_tail=(), alive=True):
        with io.open(claim_path(judged_area, "judge.py"), "w",
                     encoding="utf-8") as handle:
            json.dump({"pid": 4242, "tool": "judge.py",
                       "argv": ["tests/efficacy/judge.py", "--root", "r"]
                       + list(argv_tail),
                       "started": begun_at.isoformat(timespec="seconds")},
                      handle)
        return judging_lines(judged_root, ROUND5_RUN, ROUND5_K,
                             alive=lambda claim: alive)

    def by_line(drawn_lines):
        return {line.split()[0]: line for line in drawn_lines[2:]
                if line.strip()}

    judging_live = by_line(judging_now())
    judging_twice = judging_now(["--repeat", "2"])
    judging_named = judging_now(["--trial", "none-1"])
    judging_dry = judging_now(["--dry-run"])
    judging_ended = judging_now(alive=False)
    judging_header = judging_now()[1]
    os.remove(claim_path(judged_area, "judge.py"))
    unjudged_root = os.path.join(scratch, "unjudged")
    written(os.path.join(scoring_area(unjudged_root), "judge", "T1.json"),
            {"trial": "none-1", "blind_id": "T1", "outcome": "dry-run"}, 1)
    unjudged = judging_lines(unjudged_root, ROUND5_RUN, ROUND5_K)
    judging_total = " 4/%d" % ((len(ROUND5_RUN) * ROUND5_K - 1) * 3)
    shutil.rmtree(area, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)
    scored = {line.split()[0]: line for line in live[2:] if line.strip()}
    by_arm = {line.split()[0]: line for line in lines[2:] if line.strip()}
    old_by_arm = {line.split()[0]: line for line in old[2:] if line.strip()}
    bare_arms = [line.split()[0] for line in bare[2:] if line.strip()]
    checks = [
        ("round 5's arms, the arms the records add, and the run get a line",
         list(by_arm) == list(ROUND5_RUN) + ["hand", "short", "all"]),
        ("an arm a build run names from its start gets a bar before its "
         "first trial, a change run's arms do not, and an arm asked for "
         "gets one too",
         " 0/15 " in by_arm.get("short", "")
         and "lazyref" not in by_arm
         and [line.split()[0] for line in asked[2:] if line.strip()]
         == list(ROUND5_RUN) + ["hand", "short", "lazyskills", "all"]),
        ("an arm outside round 5's shows its running trial",
         "running hand-1, 3 min" in by_arm.get("hand", "")),
        ("a root with no records yet draws round 5's arms alone",
         bare_arms == list(ROUND5_RUN) + ["all"]),
        ("a completed trial counts toward its arm",
         " 1/15 " in by_arm.get("none", "")),
        ("a voided try counts as voided, its re-run as done",
         " 1/15 " in by_arm.get("inline", "")
         and "1 voided" in by_arm.get("inline", "")),
        ("a voided try's cost is the arm's too",
         "$  16.00" in by_arm.get("inline", "")),
        ("the running trial is named with its minutes",
         "running hybrid-1, 15 min" in by_arm.get("hybrid", "")),
        ("an arm with nothing yet shows an empty bar",
         " 0/15 " in by_arm.get("skills", "")),
        ("a change task in flight is not shown as a running build",
         "running" not in by_arm.get("skills", "")),
        ("the run's line counts every arm and estimates what is left",
         " 2/105 " in by_arm.get("all", "")
         and "h left" in by_arm.get("all", "")),
        ("a root without offsets draws its counts and reads no time",
         " 2/90 " in old_by_arm.get("all", "")
         and not any("min" in line or "h left" in line for line in old)),
        ("before scoring starts, no scoring lines are drawn",
         "Scored" not in lines and "Scored" not in old),
        ("each arm's scored trials count toward its bar",
         " 1/15" in scored.get("none", "") and " 2/15" in scored.get("inline", "")
         and " 0/15" in scored.get("skills", "")),
        ("an arm's security readings are counted beside it",
         "1 read for security" in scored.get("none", "")
         and "read for security" not in scored.get("inline", "")),
        ("the trial being scored is named on its arm's line, with its minutes",
         "scoring hybrid-1, 20 min" in scored.get("hybrid", "")
         and "  scoring " not in scored.get("all", "")),
        ("the scorer's tools are never named as the trial in hand",
         not any("tools" in line for line in live + rescoring + securing)),
        ("a trial being rescored is named while its old score stays",
         any(line.startswith("none") and "scoring none-1" in line
             for line in rescoring)),
        ("a refused trial's directory does not hide the security reading",
         any(line.startswith("inline") and "reading inline-1 for security, 3 min"
             in line for line in securing)
         and not any("  scoring " in line for line in securing)),
        ("a trial of an arm with no line is named on the scoring's line",
         "scoring hybrid-1" in one_arm[-1]),
        ("the security pass shows no scoring estimate, bar short or not",
         not any("left" in line for line in securing)),
        ("a rescore of named trials shows its time in and no time left",
         any(" h in" in line for line in rescore_pace)
         and not any("h left" in line for line in rescore_pace)),
        ("a rescore of every trial counts only the scores and readings "
         "written since it began, and estimates what is left",
         " 0/15" in whole_rescore.get("skills", "")
         and " 4/75" in whole_rescore.get("all", "")
         and "h of scoring left" in whole_rescore.get("all", "")
         and "1 read for security" in whole_rescore.get("none", "")
         and "read for security" not in whole_rescore.get("inline", "")),
        ("a rescore just begun names no trial in hand over the old results",
         not any("scoring " in line or "reading " in line
                 for line in just_begun)
         and " 0/75" in just_begun[-1]),
        ("a reread of every trial counts only the readings written since "
         "it began",
         "1 read for security" in reread_all.get("hybrid", "")
         and "read for security" not in reread_all.get("none", "")
         and " 5/75" in reread_all.get("all", "")),
        ("once every trial is scored, the security pass shows no time left",
         any(" h in" in line for line in all_scored)
         and not any("left" in line for line in all_scored)),
        ("only a plain scoring run, in any spelling, estimates what is left",
         plain_scoring(["score.py", "--root", "r"])
         and not any(plain_scoring(["score.py", "--root", "r"] + extra)
                     for extra in (["--rescore"], ["--trial=none-1"],
                                   ["--trial", "none-1"], ["--run=run-1.json"],
                                   ["--run", "run-1.json"],
                                   ["--task", "change"], ["--bogus"]))),
        ("the scoring's line counts every arm and estimates what is left",
         " 3/75" in scored.get("all", "")
         and "h of scoring left" in scored.get("all", "")),
        ("a scorer that has ended names no trial and no pace",
         not any("scoring " in line or " h in" in line for line in stale)),
        ("before judging starts, no judging lines are drawn, a dry run's "
         "records or not",
         not any("Judged" in line for line in lines + old + live)
         and unjudged == []),
        ("each arm's judgings count toward its bar, owed per trial whose "
         "build installed",
         " 3/42" in judging_live.get("none", "")
         and " 1/45" in judging_live.get("inline", "")
         and " 0/45" in judging_live.get("skills", "")),
        ("the judgings owed per trial are named, from the judge's repeat",
         judging_header == "Judged, 3 per trial"
         and judging_twice[1] == "Judged, 2 per trial"
         and any(line.startswith("none") and " 2/28" in line
                 for line in judging_twice)),
        ("a dry run's record and one caught mid-write count for nothing",
         " 0/45" in judging_live.get("hybrid", "")),
        ("a failure counts only while its trial is still owed a judging",
         "1 failed" in judging_live.get("inline", "")
         and "failed" not in judging_live.get("none", "")),
        ("the label in hand is named with its minutes, no trial beside it",
         "judging T9, 4 min;" in judging_live.get("all", "")
         and not any("judging " in line
                     for arm, line in judging_live.items() if arm != "all")),
        ("the judge's line counts every arm and estimates what is left",
         judging_total in judging_live.get("all", "")
         and " 1.0 h in, about " in judging_live.get("all", "")
         and "h left" in judging_live.get("all", "")),
        ("a judge of named trials, a dry run, or one ended names no label "
         "and no pace",
         not any("judging " in line or " h in" in line
                 for line in judging_named + judging_dry + judging_ended)
         and judging_total in judging_ended[-1]),
    ]
    for label, ok in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED"))
    passed = sum(1 for _, ok in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def parse_args(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", help="the run root to watch")
    parser.add_argument("--arms", default="",
                        help="arms to draw besides those the records name, "
                             "as words separated by commas; for a run whose "
                             "record predates naming its arms")
    parser.add_argument("--every", type=int, default=30,
                        help="seconds between redraws (default 30)")
    parser.add_argument("--once", action="store_true",
                        help="draw once and exit")
    parser.add_argument("--self-test", action="store_true",
                        help="render a planted run and check it")
    return parser.parse_args(argv)


def main(argv):
    options = parse_args(argv)
    if options.self_test:
        return self_test()
    if not options.root:
        print("--root is required")
        return 2
    asked = tuple(arm.strip() for arm in options.arms.split(",")
                  if arm.strip())
    if options.once:
        print("\n".join(render(options.root, asked=asked)))
        return 0
    try:
        watch(options.root, options.every, asked)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
