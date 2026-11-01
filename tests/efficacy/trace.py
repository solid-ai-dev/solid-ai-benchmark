"""Trace every requirement to the self-test checks that prove it.

Each row of `docs/requirements.md` names, in its last cell, either the
self-test labels that prove the rule, why no script can test it, or the issue
that tracks its missing check. This reads every self-test's output and fails
on a rule that names none of the three, or on a label no self-test prints.

    py tests/efficacy/trace.py
    py tests/efficacy/trace.py --outputs <directory of saved self-test output>
    py tests/efficacy/trace.py --self-test
"""

import argparse
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(HERE))

import lib  # noqa: E402

REQUIREMENTS = os.path.join(ROOT, "docs", "requirements.md")

# Every module with a self-test, by its path under tests/efficacy/. A label
# is looked up only in the output of the module its row names.
MODULES = ("harness.py", "generate_arm.py", "score.py", "judge.py",
           "report.py", "archive.py", "reuse.py", "progress.py",
           "security.py", "control/control.py")

ROW = re.compile(r"^\| (FR-(\d{2})-(\d{2})) \| (.+?) \| (.+?) \|$")
TOPIC = re.compile(r"^## (\d{2}) ")
CITED = re.compile(r'^`([\w/]+\.py)` "(.+)"$')
GAP = re.compile(r"^Gap: #\d+$")
UNTESTABLE = re.compile(r"^Untestable: \S")


def saved_name(module):
    """The file a module's saved self-test output is read from."""
    return os.path.basename(module)[:-len(".py")] + ".txt"


def printed(lines, label):
    """True when `label` is the whole label of one of the check lines.

    A check line is the label alone, or the label padded before `ok`, or
    `ok` before the label and the trees' columns after it. A label that is
    only the start of a longer one does not count.
    """
    for line in lines:
        text = line.strip()
        if text.startswith("ok "):
            text = text[len("ok "):].lstrip()
        if not text.startswith(label):
            continue
        rest = text[len(label):]
        if rest == "" or re.match(r"^\s+ok$", rest) or rest.startswith("  "):
            return True
    return False


def trace(text, outputs):
    """The problems with a requirements document against the self-tests'
    output, and the count of rows of each kind.

    `outputs` maps each module to the lines its self-test printed.
    """
    problems = []
    counts = {"checked": 0, "untestable": 0, "gap": 0}
    seen = set()
    topic = None
    last = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = TOPIC.match(line)
        if heading:
            topic = heading.group(1)
            continue
        row = ROW.match(line)
        if not row:
            continue
        rule, rule_topic, index, _, cell = row.groups()
        where = "line %d, %s" % (number, rule)

        # An ID is cited from other documents, so it must be unique, sit
        # under its own topic, and keep the order a reader looks it up by.
        if rule in seen:
            problems.append("%s: the ID is used twice" % where)
        seen.add(rule)
        if rule_topic != topic:
            problems.append("%s: listed under topic %s" % (where, topic))
        if last and (rule_topic, index) <= last:
            problems.append("%s: out of order" % where)
        last = (rule_topic, index)

        if UNTESTABLE.match(cell):
            counts["untestable"] += 1
            continue
        if GAP.match(cell):
            counts["gap"] += 1
            continue
        if cell.startswith(("Gap", "Untestable")):
            problems.append("%s: a gap names no issue, or an untestable rule "
                            "no reason" % where)
            continue
        good = True
        for item in cell.split("<br>"):
            cited = CITED.match(item.strip())
            if not cited:
                problems.append("%s: not a cited check: %s" % (where, item))
                good = False
                continue
            module, label = cited.groups()
            if module not in outputs:
                problems.append("%s: no self-test named %s" % (where, module))
                good = False
            elif not printed(outputs[module], label):
                problems.append('%s: %s prints no check "%s"'
                                % (where, module, label))
                good = False
        if good:
            counts["checked"] += 1
    if not seen:
        problems.append("no requirement found")
    return problems, counts


def run_self_tests():
    """Each module's self-test output, by module, running each in turn."""
    outputs = {}

    # A label is matched as text, so every child writes the encoding this
    # reads, whatever the console's code page.
    environment = dict(os.environ, PYTHONIOENCODING="utf-8")
    for module in MODULES:
        finished = subprocess.run(
            [sys.executable, os.path.join(HERE, module), "--self-test"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            env=environment, encoding="utf-8", errors="replace")
        if finished.returncode != 0:
            raise SystemExit("%s --self-test failed:\n%s"
                             % (module, finished.stdout))
        outputs[module] = finished.stdout.splitlines()
    return outputs


def saved_outputs(directory):
    """Each module's self-test output, read from files saved beforehand."""
    outputs = {}
    for module in MODULES:
        path = os.path.join(directory, saved_name(module))
        if os.path.exists(path):
            with io.open(path, encoding="utf-8", errors="replace") as handle:
                outputs[module] = handle.read().splitlines()
    return outputs


def self_test():
    """Prove the trace passes a document whose every rule is accounted for,
    and fails each way a rule can go unaccounted for."""
    outputs = {
        "a.py": ["  a planted check            ok",
                 "  a planted check, longer    ok",
                 "a label alone on its line"],
        "b/b.py": ["  ok   a mutation landed    base-1=no  improved-1=yes"],
    }

    def document(*rows):
        return "\n".join(("## 01 Topic", "", "| ID | Rule | Checked by |",
                          "|---|---|---|") + rows) + "\n"

    def problems_of(*rows):
        return trace(document(*rows), outputs)[0]

    good = (
        '| FR-01-01 | A rule. | `a.py` "a planted check"<br>'
        '`b/b.py` "a mutation landed" |',
        '| FR-01-02 | A rule. | `a.py` "a label alone on its line" |',
        "| FR-01-04 | A rule. | Untestable: no script sees it. |",
        "| FR-01-05 | A rule. | Gap: #12 |",
    )
    found, counts = trace(document(*good), outputs)
    checks = [
        ("every rule accounted for passes", found == [], found),
        ("each kind of row is counted",
         counts == {"checked": 2, "untestable": 1, "gap": 1}, counts),
        ("a label no self-test prints fails",
         len(problems_of('| FR-01-01 | A rule. | `a.py` "an absent check" |'))
         == 1, None),
        ("the start of a longer label is not a label",
         len(problems_of('| FR-01-01 | A rule. | `a.py` "a planted" |')) == 1,
         None),
        ("a label is looked up only in its own module",
         len(problems_of('| FR-01-01 | A rule. | `b/b.py` "a planted check" |'))
         == 1, None),
        ("a module with no self-test fails",
         len(problems_of('| FR-01-01 | A rule. | `c.py` "a planted check" |'))
         == 1, None),
        ("a rule naming nothing fails",
         len(problems_of("| FR-01-01 | A rule. | - |")) == 1, None),
        ("a gap that names no issue fails",
         len(problems_of("| FR-01-01 | A rule. | Gap: later |")) == 1, None),
        ("an untestable rule with no reason fails",
         len(problems_of("| FR-01-01 | A rule. | Untestable: |")) == 1, None),
        ("an ID used twice fails",
         len(problems_of(good[0], good[0])) == 2, None),
        ("an ID out of order fails",
         len(problems_of(good[1], good[0])) == 1, None),
        ("an ID under another topic fails",
         len(problems_of(good[0].replace("FR-01-01", "FR-02-01"))) == 1,
         None),
        ("a document with no requirement fails",
         trace("# Requirements\n", outputs)[0] == ["no requirement found"],
         None),
    ]
    for label, ok, got in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED: %r" % (got,)))
    passed = sum(1 for _, ok, _ in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Trace every requirement to the self-test checks that "
                    "prove it.")
    parser.add_argument("--outputs",
                        help="a directory holding each self-test's output as "
                             "<module>.txt; without it, every self-test runs")
    parser.add_argument("--requirements", default=REQUIREMENTS,
                        help="the requirements document to trace")
    parser.add_argument("--self-test", action="store_true",
                        help="prove the trace on planted documents; run no "
                             "self-test of another module")
    return parser.parse_args(argv)


def main(argv):
    options = parse_args(argv)
    if options.self_test:
        return self_test()
    outputs = (saved_outputs(options.outputs) if options.outputs
               else run_self_tests())
    with io.open(options.requirements, encoding="utf-8") as handle:
        problems, counts = trace(handle.read(), outputs)
    for problem in problems:
        print("  " + problem)
    lib.print_verdict(
        not problems,
        "%d rule(s) checked, %d untestable, %d gap(s), %d problem(s)"
        % (counts["checked"], counts["untestable"], counts["gap"],
           len(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
