"""Bring an earlier round's trials into a run root, scored and judged as
they were.

Round 5d reuses round 5c's trials rather than running them again. This
module copies what the report reads for a trial — its run record, frozen
tarball, transcripts, score, judging, and security and quality readings —
from the earlier root and scoring area into the new ones, and marks each copy
with where it came from. The earlier root is never touched, and nothing
copied is scored or judged again: the scorer, the judge and the security and
quality readers skip a trial whose result is already there.
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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402
from harness import (ARMS, PROMPT, REGISTRATIONS, TrialError,  # noqa: E402
                     assert_outside_repository, canonical, identity_problem,
                     now, project_folder, read_change_prompt, recorded_round,
                     registration_digest, remove_tree, scorable_trials,
                     scoring_area, task_folder, write_run)

# The scoring area's per-trial readings, each a JSON file named for the
# trial, that a reused trial brings with it; a reused change task brings the
# same readings of its own, from beside the build's.
KINDS = ("scores", "security-scores", "quality-scores")
READINGS = KINDS
CHANGE_READINGS = tuple(task_folder(kind, "change") for kind in KINDS)


def existing_file(directory, name):
    """The JSON file a trial's reading is filed under, or None."""
    path = os.path.join(directory, "%s.json" % canonical(name))
    return path if os.path.isfile(path) else None


def select(source, arms):
    """The earlier root's scorable build trials of the given arms, by
    canonical name."""
    offered = scorable_trials(source, task="build")
    chosen = {name: record for name, record in offered.items()
              if record.get("arm") in arms}
    for arm in arms:
        if not any(record.get("arm") == arm for record in chosen.values()):
            raise TrialError("no scorable build trial of arm %s in %s"
                             % (arm, source))
    return chosen


def copy_file(source, target):
    os.makedirs(os.path.dirname(target), exist_ok=True)
    shutil.copyfile(source, target)


def annotated(source, target, updates):
    """Copy a JSON reading, with its trial named as the target names it and
    its origin recorded."""
    with io.open(source, encoding="utf-8") as handle:
        data = json.load(handle)
    data.update(updates)
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with io.open(target, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)


def judgings_of(area, name, task="build"):
    """Every completed judging of a trial's `task` in a scoring area, by
    file."""
    found = {}
    for file in sorted(glob.glob(os.path.join(area, task_folder("judge", task),
                                              "T*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            record = json.load(handle)
        try:
            same = canonical(record.get("trial") or "") == name
        except TrialError:
            same = False
        if same and record.get("outcome") == "judged":
            found[file] = record
    return found


def reuse_trial(name, record, source, target, identity=None, task="build"):
    """Copy one trial's artifacts of `task` into the target root and scoring
    area; `identity` names the round and registration it ran under, if
    named.

    Returns the run record to write for it and the blind label its judging
    carries, None where it was never judged.
    """
    tarball = (record.get("frozen") or {}).get("tarball")
    if not tarball or not os.path.isfile(tarball):
        raise TrialError("%s has no frozen tarball at %s" % (name, tarball))
    # A trial copied on from a root that itself reused it keeps its first
    # origin: the root it ran in is what decides which trials it pairs with.
    origin = record.get("reused_from") or {
        "root": os.path.abspath(source),
        "name": os.path.splitext(os.path.basename(tarball))[0],
        "tarball": tarball}

    # The origin names its round, so a reader can tell a trial copied within
    # one named round, which pairs with the trials run here, from one carried
    # over from another.
    if identity:
        origin = dict(origin, **identity)

    copied = dict(record)
    copied["reused_from"] = origin
    frozen = name if task == "build" else "change-%s" % name
    copied["frozen"] = dict(record["frozen"],
                            tarball=os.path.join(target, "%s.tar" % frozen))
    copy_file(tarball, copied["frozen"]["tarball"])

    # The transcripts, filed under the workspace the trial ran in, which the
    # record keeps naming: the report's re-scan reads them from there.
    if record.get("workspace"):
        folder = project_folder(record["workspace"])
        transcripts = os.path.join(source, "home", ".claude", "projects",
                                   folder)
        if os.path.isdir(transcripts):
            shutil.copytree(transcripts,
                            os.path.join(target, "home", ".claude",
                                         "projects", folder),
                            dirs_exist_ok=True)

    from_area, to_area = scoring_area(source), scoring_area(target)
    updates = {"name": name, "arm": copied["arm"], "reused_from": origin}
    for kind in READINGS if task == "build" else CHANGE_READINGS:
        found = existing_file(os.path.join(from_area, kind), name)
        if found:
            annotated(found, os.path.join(to_area, kind, "%s.json" % name),
                      updates)

    label = None
    for file, judging in judgings_of(from_area, name, task).items():
        label = judging.get("blind_id")
        annotated(file, os.path.join(to_area, task_folder("judge", task),
                                     os.path.basename(file)),
                  {"trial": name, "reused_from": origin})
    return copied, label


def read_map(area, task="build"):
    """The scoring area's unblinding map of `task`, empty where there is
    none."""
    path = os.path.join(area, task_folder("judge", task), "map.json")
    if not os.path.isfile(path):
        return {"blind": {}}
    with io.open(path, encoding="utf-8") as handle:
        return json.load(handle)


def write_map(area, mapping, task="build"):
    path = os.path.join(area, task_folder("judge", task), "map.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with io.open(path, "w", encoding="utf-8") as handle:
        json.dump(mapping, handle, indent=2, sort_keys=True)


def reuse(source, target, arms):
    """Copy the chosen arms' trials from `source` into `target`; return the
    names copied."""
    source, target = os.path.abspath(source), os.path.abspath(target)
    if source == target:
        raise TrialError("the source and the target are the same root")
    assert_outside_repository(target)
    chosen = select(source, arms)

    # A named round's trials go on as that round's: their copy's run record
    # names it, and they join no root of another round or of none, which
    # would read them under rules their round never registered.
    named, problem = recorded_round(source)
    identity = None
    if named is not None and not problem:
        identity = {"round": named,
                    "registration": registration_digest(REGISTRATIONS[named])}
        problem = identity_problem(target, named, identity["registration"])
    elif not problem:
        problem = identity_problem(target)
    if problem:
        raise TrialError(problem)

    # A trial the target already offers would then be offered twice, which
    # the scorer refuses; better refused here, before anything is copied.
    try:
        held = scorable_trials(target, task="build")
    except TrialError:
        held = {}
    clash = sorted(set(chosen) & set(held))
    if clash:
        raise TrialError("%s already offers %s" % (target, ", ".join(clash)))
    changes, fixtures = change_tasks(source, arms)
    try:
        held = scorable_trials(target, task="change")
    except TrialError:
        held = {}
    clash = sorted(set(changes) & set(held))
    if clash:
        raise TrialError("%s already offers the change tasks of %s"
                         % (target, ", ".join(clash)))

    # One ruler for both rounds: the earlier round's tool lock goes with its
    # trials, and a target already holding a different one is another run.
    from_lock = os.path.join(scoring_area(source), "tool-lock.txt")
    to_lock = os.path.join(scoring_area(target), "tool-lock.txt")
    if os.path.isfile(from_lock):
        if os.path.isfile(to_lock):
            with io.open(from_lock, encoding="utf-8") as handle:
                theirs = handle.read()
            with io.open(to_lock, encoding="utf-8") as handle:
                ours = handle.read()
            if theirs != ours:
                raise TrialError("%s holds a tool lock that differs from %s; "
                                 "the rounds would be measured with two "
                                 "rulers" % (to_lock, from_lock))
        else:
            copy_file(from_lock, to_lock)

    started_at = now()
    os.makedirs(target, exist_ok=True)
    stamp = started_at.strftime("%Y-%m-%dT%H-%M-%S")
    run_file = os.path.join(target, "run-%s-reused.json" % stamp)
    records = copy_trials(chosen, source, target, identity, "build")
    write_run(run_file, started_at, records, "build", PROMPT,
              identity=identity)

    # A change task comes with its arm's build trials, in a run record of its
    # own; a named round's names the fixtures its change runs took.
    if changes:
        change_identity = identity
        if identity and fixtures:
            change_identity = dict(identity, fixtures=fixtures)
        records = copy_trials(changes, source, target, identity, "change")
        write_run(os.path.join(target, "run-%s-reused-change.json" % stamp),
                  started_at, records, "change", read_change_prompt(),
                  identity=change_identity)
    return sorted(chosen), run_file


def copy_trials(chosen, source, target, identity, task):
    """Copy each chosen trial of `task` with its labels; return the run
    records to write for them."""
    mapping = read_map(scoring_area(target), task)
    if "seed" not in mapping:
        mapping["seed"] = read_map(scoring_area(source), task).get("seed")
    taken = {label: name for name, label in mapping["blind"].items()}
    records, labels = [], {}
    for name in sorted(chosen):
        copied, label = reuse_trial(name, chosen[name], source, target,
                                    identity, task)
        records.append(copied)
        if label:
            if label in taken and taken[label] != name:
                raise TrialError("blind label %s is already %s's in %s"
                                 % (label, taken[label], target))
            labels[name] = label
    mapping["blind"].update(labels)
    if labels:
        write_map(scoring_area(target), mapping, task)
    return records


def change_tasks(source, arms):
    """The earlier root's scorable change tasks of the given arms, by name,
    and the fixtures its change runs took; none where it ran none."""
    chosen = {name: record for name, record
              in scorable_trials(source, task="change").items()
              if record.get("arm") in arms}
    fixtures = None
    for file in sorted(glob.glob(os.path.join(source, "run-*.json"))):
        with io.open(file, encoding="utf-8") as handle:
            run = json.load(handle)
        if run.get("task") == "change" and run.get("fixtures"):
            fixtures = run["fixtures"]
            break
    return chosen, fixtures


def plant_source(scratch, name="earlier", identity=None, changes=False):
    """A source root of an earlier round: one trial per arm, each scored,
    judged and read for security, with a transcript and a lock; a named
    round's where `identity` names one."""
    source = os.path.join(scratch, name)
    area = scoring_area(source)
    records = []
    for arm, index in (("none", 1), ("inline", 1), ("hand", 1)):
        old = "%s-%d" % (arm, index)
        workspace = os.path.join(source, old)
        tarball = os.path.join(source, "%s.tar" % old)
        os.makedirs(workspace)
        with io.open(tarball, "wb") as handle:
            handle.write(b"frozen " + old.encode())
        records.append({"arm": arm, "trial": index, "task": "build",
                        "outcome": "completed", "workspace": workspace,
                        "frozen": {"head": "abc", "tarball": tarball}})
        folder = os.path.join(source, "home", ".claude", "projects",
                              project_folder(workspace))
        os.makedirs(folder)
        with io.open(os.path.join(folder, "planted.jsonl"), "w",
                     encoding="utf-8") as handle:
            handle.write("{}\n")

        # Each reading the scoring area holds, named here rather than taken
        # from what a reuse copies, so a kind it stops copying shows.
        for kind in ("scores", "security-scores", "quality-scores"):
            os.makedirs(os.path.join(area, kind), exist_ok=True)
            with io.open(os.path.join(area, kind, "%s.json" % old), "w",
                         encoding="utf-8") as handle:
                json.dump({"name": old, "arm": arm, "trial": index,
                           "suite_revision": "planted"}, handle)
    write_run(os.path.join(source, "run-planted.json"),
              datetime.datetime(2026, 9, 15, 12, 0, 0), records,
              identity=identity)
    os.makedirs(os.path.join(area, "judge"))
    blind = {"hand-1": "T1", "inline-1": "T2", "none-1": "T3"}
    for old, label in blind.items():
        with io.open(os.path.join(area, "judge", "%s.json" % label), "w",
                     encoding="utf-8") as handle:
            json.dump({"trial": old, "blind_id": label, "outcome": "judged",
                       "answer": {"rubric": {}}}, handle)
    write_map(area, {"seed": 1, "blind": blind})
    with io.open(os.path.join(area, "tool-lock.txt"), "w",
                 encoding="utf-8") as handle:
        handle.write("ruler==1.0\n")
    if changes:
        plant_changes(source, identity)
    return source


def plant_changes(source, identity):
    """A change task of arms none and inline in `source`, each scored, read
    for security and quality and judged, in a change run of its own."""
    area = scoring_area(source)
    records = []
    for arm in ("none", "inline"):
        name = "%s-1" % arm
        tarball = os.path.join(source, "change-%s.tar" % name)
        with io.open(tarball, "wb") as handle:
            handle.write(b"changed " + name.encode())
        records.append({"arm": arm, "trial": 1, "task": "change",
                        "outcome": "completed",
                        "frozen": {"head": "def", "tarball": tarball}})
        for kind in CHANGE_READINGS:
            os.makedirs(os.path.join(area, kind), exist_ok=True)
            with io.open(os.path.join(area, kind, "%s.json" % name), "w",
                         encoding="utf-8") as handle:
                json.dump({"name": name, "arm": arm, "trial": 1}, handle)
    header = (dict(identity, fixtures={"manifest_sha256": "f" * 64})
              if identity else None)
    write_run(os.path.join(source, "run-planted-change.json"),
              datetime.datetime(2026, 9, 16, 12, 0, 0), records, "change",
              read_change_prompt(), identity=header)
    os.makedirs(os.path.join(area, "judge-change"))
    with io.open(os.path.join(area, "judge-change", "T1.json"), "w",
                 encoding="utf-8") as handle:
        json.dump({"trial": "inline-1", "blind_id": "T1",
                   "outcome": "judged", "answer": {"rubric": {}}}, handle)
    write_map(area, {"seed": 1, "blind": {"inline-1": "T1"}}, "change")


def change_checks(scratch):
    """A change task comes with its arm's build trials, with every reading
    and judging of its own, in a change run naming its round's fixtures."""
    digest = registration_digest(REGISTRATIONS["C1"])
    identity = {"round": "C1", "registration": digest}
    source = plant_source(scratch, "changed", identity, changes=True)
    target = os.path.join(scratch, "changed-later")
    area = scoring_area(target)
    reuse(source, target, ["inline", "hand"])
    runs = [os.path.join(target, entry) for entry in os.listdir(target)
            if entry.endswith("-reused-change.json")]
    with io.open(runs[0] if runs else os.devnull, encoding="utf-8") as handle:
        header = json.load(handle) if runs else {}
    copied = [os.path.join(area, kind, "inline-1.json")
              for kind in CHANGE_READINGS]
    return [
        ("a change task comes with its arm's build trials, in a change run "
         "naming its round's fixtures",
         len(runs) == 1 and header.get("task") == "change"
         and header.get("round") == "C1"
         and header.get("fixtures") == {"manifest_sha256": "f" * 64}
         and sorted(scorable_trials(target, task="change")) == ["inline-1"]
         and os.path.isfile(os.path.join(target, "change-inline-1.tar"))),
        ("a change task's score, security and quality readings and "
         "judgings come along under their own folders",
         all(os.path.isfile(path) for path in copied)
         and not os.path.exists(os.path.join(area, "scores-change",
                                             "none-1.json"))
         and os.path.isfile(os.path.join(area, "judge-change", "T1.json"))
         and read_map(area, "change")["blind"] == {"inline-1": "T1"}
         and read_map(area)["blind"] == {"inline-1": "T2", "hand-1": "T1"}),
    ]


def self_test():
    """Prove a reuse copies the chosen arms' trials, and only those, under
    the words, and refuses to offer a trial twice."""
    scratch = os.path.join(tempfile.gettempdir(),
                           "efficacy-reuse-self-test")
    remove_tree(scratch)
    source = plant_source(scratch)
    target = os.path.join(scratch, "later")
    area = scoring_area(target)

    def loaded(*parts):
        with io.open(os.path.join(*parts), encoding="utf-8") as handle:
            return json.load(handle)

    names, run_file = reuse(source, target, ["inline", "hand"])
    records = {r["arm"] + "-" + str(r["trial"]): r
               for r in loaded(run_file)["trials"]}
    checks = [
        ("the chosen arms' trials are copied under the words, and no other",
         names == ["hand-1", "inline-1"]
         and sorted(os.listdir(target)) == ["hand-1.tar", "home",
                                            "inline-1.tar",
                                            os.path.basename(run_file)]
         and sorted(records) == ["hand-1", "inline-1"]),
        ("each record names the arm's word, its origin and its copied tarball",
         records["inline-1"]["arm"] == "inline"
         and records["inline-1"]["reused_from"]["name"] == "inline-1"
         and records["inline-1"]["frozen"]["tarball"]
         == os.path.join(target, "inline-1.tar")
         and io.open(os.path.join(target, "inline-1.tar"), "rb").read()
         == b"frozen inline-1"),
        ("the transcripts come along under the workspace's folder",
         os.path.isfile(os.path.join(
             target, "home", ".claude", "projects",
             project_folder(records["hand-1"]["workspace"]),
             "planted.jsonl"))),
        ("the readings are filed under the word and name their origin",
         all(loaded(area, kind, "%s.json" % name)["name"] == name
             and loaded(area, kind, "%s.json" % name)["reused_from"]["name"]
             == old
             for kind in READINGS
             for name, old in (("inline-1", "inline-1"), ("hand-1", "hand-1")))
         and not os.path.exists(os.path.join(area, "scores",
                                             "none-1.json"))),
        ("the quality readings come along beside the security readings",
         all(os.path.isfile(os.path.join(area, kind, "%s.json" % name))
             for kind in ("security-scores", "quality-scores")
             for name in ("inline-1", "hand-1"))),
        ("the judgings keep their labels and the map is theirs alone",
         loaded(area, "judge", "T2.json")["trial"] == "inline-1"
         and loaded(area, "judge", "T1.json")["trial"] == "hand-1"
         and not os.path.exists(os.path.join(area, "judge", "T3.json"))
         and loaded(area, "judge", "map.json")["blind"]
         == {"inline-1": "T2", "hand-1": "T1"}),
        ("the earlier round's tool lock comes along",
         io.open(os.path.join(area, "tool-lock.txt"),
                 encoding="utf-8").read() == "ruler==1.0\n"),
        ("the target offers the copied trials for scoring under the words",
         sorted(scorable_trials(target)) == ["hand-1", "inline-1"]),
    ]
    try:
        reuse(source, target, ["inline"])
        checks.append(("a trial the target already offers is refused",
                       False))
    except TrialError:
        checks.append(("a trial the target already offers is refused", True))
    try:
        reuse(source, os.path.join(scratch, "other"), ["short"])
        checks.append(("an arm the source never ran is refused", False))
    except TrialError:
        checks.append(("an arm the source never ran is refused", True))

    # Copied on from the target, a trial still names the root it ran in.
    _, onward = reuse(target, os.path.join(scratch, "onward"), ["inline"])
    carried = {r["arm"] + "-" + str(r["trial"]): r
               for r in loaded(onward)["trials"]}["inline-1"]
    checks.append(("a trial copied on keeps the root it ran in as its origin",
                   carried["reused_from"]["root"] == os.path.abspath(source)
                   and carried["reused_from"]["name"] == "inline-1"))

    # A named round's trials keep their round in the copy's header, and go
    # into no root of none.
    digest = registration_digest(REGISTRATIONS["C1"])
    named = plant_source(scratch, "named",
                         {"round": "C1", "registration": digest})
    _, kept = reuse(named, os.path.join(scratch, "named-later"), ["inline"])
    header = loaded(kept)
    checks.append(("a named round's trials copied on keep its round in the "
                   "run record's header",
                   header.get("round") == "C1"
                   and header.get("registration") == digest
                   and recorded_round(os.path.dirname(kept)) == ("C1", None)))
    origin = loaded(scoring_area(os.path.dirname(kept)), "scores",
                    "inline-1.json")["reused_from"]
    checks.append(("a trial copied within a named round names that round in "
                   "its origin",
                   origin.get("round") == "C1"
                   and origin.get("registration") == digest
                   and origin.get("root") == os.path.abspath(named)))
    joined = []
    for origin, into in ((named, target),
                         (source, os.path.dirname(kept))):
        try:
            reuse(origin, into, ["none"])
            joined.append(True)
        except TrialError:
            joined.append(os.path.exists(os.path.join(into, "none-1.tar")))
    checks.append(("a reuse never mixes a named round's trials with others",
                   joined == [False, False]))
    checks += change_checks(scratch)

    for label, ok in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED"))
    remove_tree(scratch)
    passed = sum(1 for _, ok in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Bring an earlier round's trials into a run root.")
    parser.add_argument("--from", dest="source",
                        help="the earlier round's run root")
    parser.add_argument("--into", dest="target",
                        help="the run root to copy into; MUST be outside "
                             "this repository")
    parser.add_argument("--arms",
                        help="which arms to bring, as words separated by "
                             "commas: none,inline")
    parser.add_argument("--self-test", action="store_true",
                        help="prove a reuse copies the chosen trials and "
                             "only those; copy nothing")
    return parser.parse_args(argv)


def main(argv):
    options = parse_args(argv)
    if options.self_test:
        return self_test()
    if not (options.source and options.target and options.arms):
        print("--from, --into and --arms are required")
        return 2
    arms = [arm.strip() for arm in options.arms.split(",") if arm.strip()]
    unknown = [arm for arm in arms if arm not in ARMS]
    if not arms or unknown:
        print("--arms names %s; the arms are %s"
              % (", ".join(unknown) if unknown else "nothing",
                 ", ".join(ARMS)))
        return 2
    try:
        names, run_file = reuse(options.source, options.target, arms)
    except TrialError as error:
        print("refused: %s" % error)
        lib.print_verdict(False, "0 trial(s) reused, 1 refused")
        return 1
    for name in names:
        print("%s  reused" % name)
    print("\nRun record: %s" % run_file)
    lib.print_verdict(True, "%d trial(s) reused" % len(names))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
