"""Trace every functional requirement to the self-test checks that prove it.

`docs/requirements.md` states each rule; `docs/coverage.md` gives each live
rule one row naming the self-test labels that prove it, why no script can
test it, or the issue that tracks its missing check. This reads every
self-test's output and fails on a rule with no such row, or on a label no
self-test prints.

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
COVERAGE = os.path.join(ROOT, "docs", "coverage.md")

# Every module with a self-test, by its path under tests/efficacy/. A label
# is looked up only in the output of the module its row names.
MODULES = ("harness.py", "generate_arm.py", "score.py", "judge.py",
           "report.py", "archive.py", "reuse.py", "progress.py",
           "security.py", "control/control.py")

ROW = re.compile(r"^\| (FR-(\d{2})-(\d{2})) \| (.+?) \| (.+?) \|$")
TOPIC = re.compile(r"^#{2,3} (\d{2}) ")
CITED = re.compile(r'^`([\w/]+\.py)` "(.+)"$')
ISSUE = re.compile(r"^#\d+$")
KINDS = ("Self-test", "Untestable", "Missing")


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

        # The control pads a label to a fixed width, so a long one meets its
        # first tree's column after a single space.
        if re.match(r"^ [\w-]+=", rest):
            return True
    return False


def rows(text, name, problems):
    """Each FR row of a document, as (line number, ID, second cell, third
    cell), in order, with a problem filed for each row that is malformed,
    repeated, out of order or under another topic."""
    found = []
    seen = set()
    topic = None
    last = None
    for number, line in enumerate(text.splitlines(), 1):
        heading = TOPIC.match(line)
        if heading:
            topic = heading.group(1)
            continue

        # Markdown allows a table row a few spaces either side.
        line = line.strip()

        # A rule's row that fails to parse, such as one with an empty last
        # cell, would otherwise drop out of the trace and pass unchecked.
        row = ROW.match(line)
        if not row:
            if re.match(r"^\|\s*FR-", line):
                problems.append("%s line %d: a row that does not parse: %s"
                                % (name, number, line))
            continue
        rule, rule_topic, index, second, third = row.groups()
        where = "%s line %d, %s" % (name, number, rule)

        # A cell of spaces parses as a cell, but says nothing: a reason, a
        # kind or a requirement left blank.
        second, third = second.strip(), third.strip()
        if not (second and third):
            problems.append("%s: a cell is blank" % where)
            second = third = None

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
        found.append((number, rule, second, third))
    return found


def trace(requirements, coverage, outputs):
    """The problems with the requirements and their coverage against the
    self-tests' output, and the count of covered rules of each kind.

    `outputs` maps each module to the lines its self-test printed.
    """
    problems = []
    counts = {kind: 0 for kind in KINDS}
    stated = rows(requirements, "requirements", problems)

    # A removed row keeps its ID so the number is never reused, and needs
    # no coverage.
    live = {rule for _, rule, text, _ in stated
            if text is None or not text.startswith("Removed:")}
    covered = set()
    for number, rule, kind, cell in rows(coverage, "coverage", problems):
        where = "coverage line %d, %s" % (number, rule)
        covered.add(rule)
        if rule not in live:
            problems.append("%s: no live requirement has this ID" % where)

        # A blank row is already a problem; reading it further would only
        # repeat it.
        if kind is None:
            continue
        if kind not in KINDS:
            problems.append("%s: an unknown kind, %s" % (where, kind))
            continue
        if kind == "Untestable":
            counts[kind] += 1
            continue
        if kind == "Missing":
            if ISSUE.match(cell):
                counts[kind] += 1
            else:
                problems.append("%s: a Missing row names no issue" % where)
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
            counts[kind] += 1
    for rule in sorted(live - covered):
        problems.append("%s has no coverage row" % rule)
    if not stated:
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
    """Prove the trace passes documents whose every rule is accounted for,
    and fails each way a rule can go unaccounted for."""
    outputs = {
        "a.py": ["  a planted check            ok",
                 "  a planted check, longer    ok",
                 "a label alone on its line"],
        "b/b.py": ["  ok   a mutation landed    base-1=no  improved-1=yes",
                   "  ok   a mutation past the padding base-1=yes  base-2=no"],
    }
    stated = ("| FR-01-01 | The benchmark shall do one thing. | Report |",
              "| FR-01-02 | The benchmark shall do another. | Report |",
              "| FR-01-03 | Removed: moved to FR-01-02. | - |",
              "| FR-01-04 | The benchmark shall do a third. | Owner |",
              "| FR-01-05 | The benchmark shall do a fourth. | Judge |")
    good = ('| FR-01-01 | Self-test | `a.py` "a planted check"<br>'
            '`b/b.py` "a mutation landed" |',
            '| FR-01-02 | Self-test | `a.py` "a label alone on its line" |',
            "| FR-01-04 | Untestable | No script sees it. |",
            "| FR-01-05 | Missing | #12 |")

    def document(*lines):
        return "\n".join(("### 01 Topic", "", "| ID | A | B |",
                          "| -- | - | - |") + lines) + "\n"

    def problems_of(*covering, requirements=stated):
        return trace(document(*requirements), document(*covering),
                     outputs)[0]

    def one(*covering):
        return len(problems_of(*covering, *good[len(covering):])) == 1

    found, counts = trace(document(*stated), document(*good), outputs)
    checks = [
        ("every rule accounted for passes", found == [], found),
        ("each kind of row is counted",
         counts == {"Self-test": 2, "Untestable": 1, "Missing": 1}, counts),
        ("a live rule with no coverage row fails",
         problems_of(*good[1:]) == ["FR-01-01 has no coverage row"], None),
        ("a removed rule needs no coverage row", found == [], found),
        ("a row for a removed rule fails",
         len(problems_of(good[0], good[1],
                         "| FR-01-03 | Untestable | Gone. |", *good[2:]))
         == 1, None),
        ("a label no self-test prints fails",
         one('| FR-01-01 | Self-test | `a.py` "an absent check" |'), None),
        ("the start of a longer label is not a label",
         one('| FR-01-01 | Self-test | `a.py` "a planted" |'), None),
        ("a label is looked up only in its own module",
         one('| FR-01-01 | Self-test | `b/b.py` "a planted check" |'), None),
        ("a module with no self-test fails",
         one('| FR-01-01 | Self-test | `c.py` "a planted check" |'), None),
        ("a long label meets the trees' columns after one space",
         problems_of('| FR-01-01 | Self-test | '
                     '`b/b.py` "a mutation past the padding" |', *good[1:])
         == [], None),
        ("an indented row is still traced",
         problems_of(good[0],
                     ' | FR-01-02 | Self-test | `a.py` "an absent check" |',
                     *good[2:])
         == ['coverage line 6, FR-01-02: a.py prints no check '
             '"an absent check"'], None),
        ("a row with trailing spaces is still traced",
         problems_of(good[0],
                     '| FR-01-02 | Self-test | `a.py` "an absent check" |  ',
                     *good[2:])
         == ['coverage line 6, FR-01-02: a.py prints no check '
             '"an absent check"'], None),
        ("a row naming nothing fails",
         one("| FR-01-01 | Self-test | - |"), None),
        ("a row with an empty last cell fails",
         len(problems_of(good[0], "| FR-01-02 | Self-test | |", *good[2:]))
         == 2, None),
        ("an unknown kind fails", one("| FR-01-01 | Gap | #12 |"), None),
        ("a Missing row that names no issue fails",
         len(problems_of(*good[:3], "| FR-01-05 | Missing | later |")) == 1,
         None),
        ("an Untestable row with no reason fails",
         len(problems_of(*good[:2], "| FR-01-04 | Untestable | |", good[3]))
         == 2, None),
        ("an Untestable row whose reason is spaces fails",
         problems_of(*good[:2], "| FR-01-04 | Untestable |   |", good[3])
         == ["coverage line 7, FR-01-04: a cell is blank"], None),
        ("an ID used twice fails",
         len(problems_of(good[0], *good)) == 2, None),
        ("an ID out of order fails",
         len(problems_of(good[1], good[0], *good[2:])) == 1, None),
        ("an ID under another topic fails",
         len(problems_of(requirements=(stated[0].replace("FR-01-01",
                                                         "FR-02-01"),)
                         + stated[1:])) >= 1, None),
        ("a requirement row that does not parse fails",
         len(problems_of(*good, requirements=stated
                         + ("| FR-01-06 | The benchmark shall. | |",)))
         == 1, None),
        ("a document with no requirement fails",
         "no requirement found" in trace("# Requirements\n", "", outputs)[0],
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
        description="Trace every functional requirement to the self-test "
                    "checks that prove it.")
    parser.add_argument("--outputs",
                        help="a directory holding each self-test's output as "
                             "<module>.txt; without it, every self-test runs")
    parser.add_argument("--requirements", default=REQUIREMENTS,
                        help="the requirements document")
    parser.add_argument("--coverage", default=COVERAGE,
                        help="the coverage document to trace")
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
        requirements = handle.read()
    with io.open(options.coverage, encoding="utf-8") as handle:
        coverage = handle.read()
    problems, counts = trace(requirements, coverage, outputs)
    for problem in problems:
        print("  " + problem)
    lib.print_verdict(
        not problems,
        "%d rule(s) checked by a self-test, %d untestable, %d missing a "
        "check, %d problem(s)"
        % (counts["Self-test"], counts["Untestable"], counts["Missing"],
           len(problems)))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
