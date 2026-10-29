"""Show a run's progress, one bar per arm, read from its run records.

Read-only: it opens the run root's `run-*.json` and nothing else, so it can
watch a live run from a console of its own without touching a trial. It
redraws every `--every` seconds until stopped, or once with `--once`.
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
from harness import (ROUND5_K, SCORABLE, VOIDING, arm_name,  # noqa: E402
                     now, result_of)
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
    shutil.rmtree(scratch, ignore_errors=True)
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
