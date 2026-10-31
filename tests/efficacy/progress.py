"""Show a run's progress, one bar per arm, read from its run records, and
its scoring's, read from the scoring area.

Read-only: it opens the run root's `run-*.json` and lists the scoring area,
so it can watch a live run or a live scoring from a console of its own
without touching a trial. It redraws every `--every` seconds until stopped,
or once with `--once`.
"""

import argparse
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
                     TrialError, arm_name, claim_path, now, read_claim,
                     result_of, running_as, scoring_area, split_name)
from report import ROUND5_RUN  # noqa: E402

WIDTH = 30


def records(root):
    """Every build trial record in the root's run records, in time order."""
    found = []
    for file in sorted(glob.glob(os.path.join(root, "run-*.json"))):
        try:
            with io.open(file, encoding="utf-8") as handle:
                run = json.load(handle)
        except (OSError, ValueError):

            # The harness rewrites a record after every trial, so a read can
            # land mid-write; the next redraw reads it whole.
            continue

        # A trial in flight records no task of its own; the run it sits in
        # says which task it is.
        task = run.get("task", "build")
        found.extend(record for record in run.get("trials", [])
                     if record.get("task", task) == "build")
    return found


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
        arm = arms.get(arm_name(record.get("arm")))
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


def render(root, arms=ROUND5_RUN, k=ROUND5_K, moment=None):
    """The progress screen for the run root, as lines."""
    moment = moment or now()
    trials = records(root)
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
    return lines + scoring_lines(root, arms, k)


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


def live_scorer(claim):
    """Whether the scorer a marker names is still running."""
    try:
        return running_as(claim["pid"], "score.py")
    except LiveRunError:
        return False


def in_progress(work, written):
    """The trial a tool is working on in `work`, or None.

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
    return max(changed)[1] if changed else None


def scoring_lines(root, arms, k, alive=live_scorer):
    """The scoring's lines: one bar per arm of trials scored, with their
    security readings, and the trial being scored; none before scoring
    starts."""
    area = scoring_area(root)
    if not os.path.isdir(area):
        return []
    scores = names_in(os.path.join(area, "scores"))
    readings = names_in(os.path.join(area, "security-scores"))
    lines = ["", "Scored"]
    total = len(arms) * k
    done = 0
    for name in arms:
        scored = sum(1 for trial in scores if arm_of(trial) == name)
        read = sum(1 for trial in readings if arm_of(trial) == name)
        done += scored
        line = "%-10s %s %2d/%d" % (name, bar(scored, k), scored, k)
        if read:
            line += "  %d read for security" % read
        lines.append(line)
    summary = "%-10s %s %2d/%d" % ("all", bar(done, total), done, total)

    # The scorer marks the area while it runs, scores each trial and then
    # reads the scored ones for security; the pace is this scorer's own, from
    # the scores it wrote since it started.
    claim = read_claim(claim_path(area, "score.py"))
    if claim and alive(claim):
        scoring = in_progress(os.path.join(area, "scoring"), scores)
        reading = in_progress(os.path.join(area, "security"), readings)
        if scoring:
            summary += "  scoring %s" % scoring
        elif reading:
            summary += "  reading %s for security" % reading
        try:
            begun = datetime.datetime.fromisoformat(claim["started"])
        except (KeyError, TypeError, ValueError):
            begun = None
        if begun is not None:
            fresh = sum(1 for written in scores.values()
                        if written >= begun.timestamp())
            elapsed = time.time() - begun.timestamp()
            summary += "  %.1f h in" % (elapsed / 3600)
            if fresh:
                left = elapsed / fresh * (total - done)
                summary += ", about %.1f h left" % (left / 3600)
    lines.extend(["", summary])
    return lines


def watch(root, every):
    while True:
        lines = render(root)

        # The console's own clear, not an escape sequence: a Windows console
        # can take the sequence and still leave the text scrolled out of the
        # window, which then shows black.
        os.system("cls" if os.name == "nt" else "clear")
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        time.sleep(every)


def self_test():
    """A planted run renders each arm's count, voids, cost and running trial,
    and a record caught mid-write is skipped rather than fatal."""
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
               trial("hybrid", 1, "running", 15)]
    with io.open(os.path.join(scratch, "run-1.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"task": "build", "trials": planted}, handle)
    with io.open(os.path.join(scratch, "run-2.json"), "w",
                 encoding="utf-8") as handle:
        handle.write('{"trials": [')

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

    lines, old = drawn(scratch), drawn(legacy)

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
    for name, minutes in (("hybrid-1", 55), ("none-1", 56)):
        dated(os.path.join(area, "scores", "%s.json" % name), minutes)
    dated(os.path.join(area, "security", "inline-1"), 57, folder=True)
    securing = scoring_now()
    shutil.rmtree(area, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)
    scored = {line.split()[0]: line for line in live[2:] if line.strip()}
    by_arm = {line.split()[0]: line for line in lines[2:] if line.strip()}
    old_by_arm = {line.split()[0]: line for line in old[2:] if line.strip()}
    checks = [
        ("every arm and the whole run get a line",
         sorted(by_arm) == sorted(list(ROUND5_RUN) + ["all"])),
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
         " 2/75 " in by_arm.get("all", "")
         and "h left" in by_arm.get("all", "")),
        ("a root without offsets draws its counts and reads no time",
         " 2/75 " in old_by_arm.get("all", "")
         and not any("min" in line or "h left" in line for line in old)),
        ("before scoring starts, no scoring lines are drawn",
         "Scored" not in lines and "Scored" not in old),
        ("each arm's scored trials count toward its bar",
         " 1/15" in scored.get("none", "") and " 2/15" in scored.get("inline", "")
         and " 0/15" in scored.get("skills", "")),
        ("an arm's security readings are counted beside it",
         "1 read for security" in scored.get("none", "")
         and "read for security" not in scored.get("inline", "")),
        ("the trial being scored is named, not one already scored",
         "scoring hybrid-1" in scored.get("all", "")),
        ("the scorer's tools are never named as the trial in hand",
         not any("tools" in line for line in live + rescoring + securing)),
        ("a trial being rescored is named while its old score stays",
         any("scoring none-1" in line for line in rescoring)),
        ("once every trial is scored, the one read for security is named",
         any("reading inline-1 for security" in line for line in securing)
         and not any("scoring " in line for line in securing)),
        ("the scoring's line counts every arm and estimates what is left",
         " 3/75" in scored.get("all", "") and "h left" in scored.get("all", "")),
        ("a scorer that has ended names no trial and no pace",
         not any("scoring " in line or " h in" in line for line in stale)),
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
    if options.once:
        print("\n".join(render(options.root)))
        return 0
    try:
        watch(options.root, options.every)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
