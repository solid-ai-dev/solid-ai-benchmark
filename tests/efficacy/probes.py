"""Structural and web-quality probes for one frozen efficacy trial.

`score.py` owns the backbone — install, hidden suite, static battery, scope
and cost — and calls in here for the two families of measurement that need to
reach inside the trial's own interpreter: the structural design probes,
and the web-quality probes beside them.

Both run as one script inside the trial's environment, because `grimp`, the
application factory and the browser all live there. A probe that cannot run
returns a missing metric naming what was absent; it never returns zero.

    py tests/efficacy/probes.py --self-test
"""

import argparse
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402

# The package and the factory the specification fixes. Everything in here
# reaches the trial only through those two names and the routes, never through
# a module path the arm was free to choose.
PACKAGE = "tariff"

# The names the spec requires. A name missing from a trial is a finding; a
# name the trial adds is reported as extra rather than as wrong.
REQUIRED_NAMES = ("Product", "Catalog", "InvoiceLine", "Invoice",
                  "Jurisdiction", "PercentageRule", "BulkRule", "TieredRule",
                  "CouponRule", "price", "TariffError")


class Context(object):
    """What a probe needs from the scorer, passed rather than imported.

    `score.py` already owns the command runner and the missing-vs-zero
    constructors, and importing them back from here would make the two
    modules circular.
    """

    def __init__(self, run, measured, absent, python, script):
        self.run = run
        self.measured = measured
        self.absent = absent
        self.python = python
        self.script = script


# Runs inside the trial's environment and prints one JSON object. Kept as a
# script rather than an import because the interpreter that must answer is the
# trial's, not the scorer's.
STRUCTURE_SCRIPT = r'''
import ast, json, os, sys

PACKAGE = "tariff"
REQUIRED = %(required)r
ROOTS = json.loads(sys.argv[1])

report = {}


def source_files(roots):
    found = []
    for root in roots:
        if os.path.isfile(root) and root.endswith(".py"):
            found.append(root)
            continue
        for base, _, names in os.walk(root):
            if "__pycache__" in base:
                continue
            for name in names:
                if name.endswith(".py"):
                    found.append(os.path.join(base, name))
    return found


FILES = source_files(ROOTS)
TREES = {}
for path in FILES:
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            TREES[path] = ast.parse(handle.read(), filename=path)
    except SyntaxError as error:
        report.setdefault("unparsed", []).append([path, str(error)])


def imported_names(tree):
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module.split(".")[0])
    return names


# Role assignment by what a module imports, because the arms name their
# modules freely. A module that imports flask is web; one that imports a
# database driver is persistence; the rest is domain, which is what the
# layering contract is about.
WEB = {"flask", "werkzeug", "jinja2"}
STORE = {"sqlite3", "sqlalchemy"}
roles = {}
for path, tree in TREES.items():
    imports = imported_names(tree)
    if imports & WEB:
        roles[path] = "web"
    elif imports & STORE:
        roles[path] = "persistence"
    else:
        roles[path] = "domain"
report["roles"] = {os.path.basename(p): r for p, r in roles.items()}



# The contract the specification states in its own words: `import tariff`
# works without Flask and without touching the database. So the modules that
# import loads, the package's `__init__` and every module it reaches through
# the package's own imports, may import neither. A role says nothing here: a
# module that imports Flask is web by that fact, so asking whether a domain
# module imports Flask asks nothing.
def never_on_import(node):
    """An `if` whose body never runs on import: `if TYPE_CHECKING:`, which
    only a type checker reads, and `if __name__ == "__main__":`, which runs
    only for a script. Both are read by name, as a build writes them."""
    test = node.test
    if isinstance(test, ast.Name) and test.id == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING":
        return True
    if isinstance(test, ast.Compare) and len(test.ops) == 1 and isinstance(
            test.ops[0], ast.Eq):
        sides = [test.left] + list(test.comparators)
        names = [side.id for side in sides if isinstance(side, ast.Name)]
        values = [side.value for side in sides
                  if isinstance(side, ast.Constant)]
        return "__name__" in names and "__main__" in values
    return False


def import_time(tree):
    """The nodes that run when the module is imported. A function body does
    not, so an import inside one, the factory's lazy `from . import web` the
    specification allows, is not what `import tariff` loads; nor is an import
    under a guard that never holds on import."""
    pending = list(ast.iter_child_nodes(tree))
    while pending:
        node = pending.pop()
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.Lambda)):
            continue
        if isinstance(node, ast.If) and never_on_import(node):
            pending.extend(node.orelse)
            continue
        yield node
        pending.extend(ast.iter_child_nodes(node))


def import_time_names(tree):
    """The top-level names a module imports at import time. A relative
    import names the package's own module, whatever it is called, and is
    followed by `package_imports` instead."""
    names = set()
    for node in import_time(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names.add(node.module.split(".")[0])
    return names


def resolve(base, parts):
    """The files Python runs to import `parts` under `base`: each package
    initializer on the way, then the module or its own initializer."""
    found = []
    for depth in range(1, len(parts)):
        initializer = os.path.join(base, *(parts[:depth] + ["__init__.py"]))
        if initializer in TREES:
            found.append(initializer)
    # A package wins over a module of the same name, as Python's finder has
    # it.
    stem = os.path.join(base, *parts) if parts else base
    for candidate in (os.path.join(stem, "__init__.py"), stem + ".py"):
        if candidate in TREES:
            found.append(candidate)
            break
    return found


def package_imports(path, tree):
    found = []
    here = os.path.dirname(path)
    top = os.path.dirname(ENTRY)
    for node in import_time(tree):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                base = here
                for _ in range(node.level - 1):
                    base = os.path.dirname(base)
                parts = node.module.split(".") if node.module else []
            elif node.module and node.module.split(".")[0] == PACKAGE:
                base, parts = top, node.module.split(".")[1:]
            else:
                continue
            found.extend(resolve(base, parts))
            for alias in node.names:
                found.extend(resolve(base, parts + [alias.name]))
        elif isinstance(node, ast.Import):
            for alias in node.names:
                parts = alias.name.split(".")
                if parts[0] == PACKAGE:
                    found.extend(resolve(top, parts[1:]))
    return found


def under_package(path):
    """A file's path from the package's parent, with forward slashes, so two
    initializers are told apart."""
    relative = os.path.relpath(path, os.path.dirname(os.path.dirname(ENTRY)))
    return relative.replace(os.sep, "/")


ENTRY = None
for path in TREES:
    if os.path.basename(path) == "__init__.py" and os.path.basename(
            os.path.dirname(path)) == PACKAGE:
        ENTRY = path
if ENTRY is None:
    for path in TREES:
        if os.path.basename(path) == PACKAGE + ".py":
            ENTRY = path
if ENTRY is None:
    report["layering_violations"] = None
    report["import_closure"] = None
else:
    closure, queue = [], [ENTRY]
    while queue:
        path = queue.pop(0)
        if path in closure:
            continue
        closure.append(path)
        queue.extend(package_imports(path, TREES[path]))
    violations = []
    for path in closure:
        for name in sorted(import_time_names(TREES[path]) & (WEB | STORE)):
            violations.append([under_package(path), name])
    report["layering_violations"] = violations
    report["import_closure"] = [under_package(path) for path in closure]


def is_route(node):
    for decorator in getattr(node, "decorator_list", []):
        target = decorator.func if isinstance(decorator, ast.Call) else decorator
        attribute = getattr(target, "attr", None)
        if attribute in ("route", "get", "post", "put", "delete"):
            return True
    return False


# Pricing arithmetic inside a route is the concrete form of the layering
# question: a route that multiplies Decimals is doing the domain's work.
money_in_routes = []
for path, tree in TREES.items():
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if not is_route(node):
            continue
        for inner in ast.walk(node):
            if isinstance(inner, ast.BinOp) and isinstance(
                    inner.op, (ast.Mult, ast.Div, ast.Sub, ast.Add)):
                segment = ast.dump(inner)
                if "Decimal" in segment or "unit_price" in segment:
                    money_in_routes.append([os.path.basename(path), node.name])
                    break
report["money_in_routes"] = money_in_routes

# A boolean parameter is a branch the caller cannot name, which `oop.md`
# treats as a smell rather than a style preference.
bool_parameters = []
for path, tree in TREES.items():
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        arguments = list(node.args.args) + list(node.args.kwonlyargs)
        for argument in arguments:
            annotation = getattr(argument, "annotation", None)
            if isinstance(annotation, ast.Name) and annotation.id == "bool":
                bool_parameters.append(
                    [os.path.basename(path), node.name, argument.arg])
        for default in list(node.args.defaults) + list(
                node.args.kw_defaults or []):
            if isinstance(default, ast.Constant) and isinstance(
                    default.value, bool):
                bool_parameters.append(
                    [os.path.basename(path), node.name, "default"])
report["bool_parameters"] = bool_parameters


# The extension axes the change task will exercise. Each is scored present or
# absent on the property, not on a pattern's name: an abstract base, a typed
# protocol or a registry all answer "a new kind needs no edit to an existing
# one".
def has_abstraction(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                label = getattr(base, "id", getattr(base, "attr", ""))
                if label in ("Protocol", "ABC"):
                    return True
            for decorator in node.decorator_list:
                if getattr(decorator, "id", "") == "runtime_checkable":
                    return True
        if isinstance(node, ast.FunctionDef):
            for decorator in node.decorator_list:
                target = (decorator.func if isinstance(decorator, ast.Call)
                          else decorator)
                if getattr(target, "attr", "") in ("register", "registry"):
                    return True
    return False


def mentions(tree, words):
    dumped = ast.dump(tree)
    return any(word in dumped for word in words)


axes = {}
for label, words in (("rule_kinds", ["Rule", "rule_kind", "KINDS"]),
                     ("jurisdictions", ["Jurisdiction", "rates"]),
                     ("export_formats", ["export", "Export", "csv", "json"])):
    present = False
    for path, tree in TREES.items():
        if mentions(tree, words) and has_abstraction(tree):
            present = True
            break
    axes[label] = present
report["extension_points"] = axes

# A conditional ladder over rule kinds is the missed-Strategy signal the judge
# is asked to score; counting the widest one here gives it a number to quote.
ladders = []
for path, tree in TREES.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            depth, cursor = 1, node
            while cursor.orelse and len(cursor.orelse) == 1 and isinstance(
                    cursor.orelse[0], ast.If):
                cursor = cursor.orelse[0]
                depth += 1
            if depth >= 3 and mentions(node, ["kind", "Rule", "percent"]):
                ladders.append([os.path.basename(path), depth])
report["kind_ladders"] = ladders

# Public surface, against the names the spec requires.
try:
    import importlib
    module = importlib.import_module(PACKAGE)
    exported = list(getattr(module, "__all__", []) or
                    [n for n in dir(module) if not n.startswith("_")])
    report["surface"] = {
        "missing": [n for n in REQUIRED if not hasattr(module, n)],
        "extra": [n for n in exported if n not in REQUIRED],
        "exported": len(exported),
    }
except Exception as error:
    report["surface"] = {"error": repr(error)[:300]}

# IO isolation: `price` takes values, so no parameter of it may be annotated
# as a connection, a cursor, a row or a request.
try:
    import inspect
    import importlib
    module = importlib.import_module(PACKAGE)
    price = getattr(module, "price", None)
    if price is None:
        report["io_isolation"] = {"error": "no price function is exported"}
    else:
        signature = inspect.signature(price)
        leaked = [name for name, parameter in signature.parameters.items()
                  if any(token in str(parameter.annotation).lower()
                         for token in ("connection", "cursor", "row",
                                       "request", "session", "engine"))]
        report["io_isolation"] = {
            "parameters": list(signature.parameters),
            "leaked": leaked,
            "clean": not leaked,
        }
except Exception as error:
    report["io_isolation"] = {"error": repr(error)[:300]}

# Cycles, fan-in and fan-out, from the import graph rather than from names.
try:
    import grimp
    graph = grimp.build_graph(PACKAGE)
    modules = sorted(graph.modules)
    cycles = 0
    instability = {}
    for name in modules:
        outward = len(graph.find_modules_directly_imported_by(name))
        inward = len(graph.find_modules_that_directly_import(name))
        total = outward + inward
        instability[name] = round(outward / total, 3) if total else None
    for name in modules:
        for other in graph.find_modules_directly_imported_by(name):
            if name in graph.find_modules_directly_imported_by(other):
                cycles += 1
    domain = [v for k, v in instability.items()
              if v is not None and "web" not in k and "app" not in k]
    report["graph"] = {
        "modules": len(modules),
        "mutual_import_pairs": cycles // 2,
        "mean_instability": (round(sum(domain) / len(domain), 3)
                             if domain else None),
    }
except Exception as error:
    report["graph"] = {"error": repr(error)[:300]}

# The four facts the adherence checklist needs and no tool reports: what the
# library writes to the host's streams, whether a comment cites a ticket
# number, and whether one error hierarchy covers every raised type.
prints, citations, raises, bases = [], [], [], []
for path, tree in TREES.items():
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(
                node.func, "id", "") == "print":
            prints.append([os.path.basename(path), node.lineno])
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                label = getattr(base, "id", getattr(base, "attr", ""))
                if label in ("Exception", "BaseException", "ValueError",
                             "TypeError", "RuntimeError"):
                    bases.append([os.path.basename(path), node.name, label])
report["print_calls"] = prints
report["exception_bases"] = bases

CITATION = None
try:
    import re as _re
    CITATION = _re.compile(r"#\s?\d{2,}|ADR-\d+|PR\s?#\d+")
except Exception:
    CITATION = None
if CITATION is not None:
    for path in FILES:
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                for number, line in enumerate(handle, 1):
                    stripped = line.strip()
                    if stripped.startswith("#") and CITATION.search(stripped):
                        citations.append([os.path.basename(path), number])
        except OSError:
            continue
report["citations"] = citations

# A library writes nothing to the host's streams: where logging is used at
# all, a NullHandler is what makes that true. Where it is not used the
# question does not arise, which is a third answer and not a pass.
uses_logging, null_handler = False, False
for path, tree in TREES.items():
    if "logging" in imported_names(tree):
        uses_logging = True
    if "NullHandler" in ast.dump(tree):
        null_handler = True
report["logging"] = {"used": uses_logging, "null_handler": null_handler}

report["files_parsed"] = len(TREES)
print(json.dumps(report))
'''


# Runs inside the trial's environment against the application the factory
# returns. Every probe here is one the specification already fixes: the
# routes, the CSRF refusal, the escaping of what a form stored.
WEB_SCRIPT = r'''
import json, os, re, sys, tempfile
from urllib.parse import urlsplit

PACKAGE = "tariff"
USERNAME = "admin"
PASSWORD = "web-probe-4d2a-Passphrase"
REDIRECTS = (301, 302, 303, 307, 308)
report = {"unread": {}, "lost": {}}

# The seed reads the administrator's password from the environment, and may
# seed lazily, so it is set before the package is imported.
os.environ["TARIFF_ADMIN_PASSWORD"] = PASSWORD

try:
    import importlib
    package = importlib.import_module(PACKAGE)
    database = os.path.join(tempfile.mkdtemp(), "web-probe.sqlite")
    app = package.create_app(database)
    app.config["WTF_CSRF_ENABLED"] = app.config.get("WTF_CSRF_ENABLED", True)
    client = app.test_client()
except Exception as error:
    print(json.dumps({"error": repr(error)[:300]}))
    raise SystemExit(0)


def hidden_fields(html):
    """Every hidden input in the page, which is where a CSRF token hides.

    The field's name is the arm's choice -- the specification fixes the
    visible fields and leaves the rest -- so the probe carries whatever the
    form carries rather than guessing a name.
    """
    fields = {}
    for match in re.finditer(r'<input[^>]*type="hidden"[^>]*>', html,
                             re.IGNORECASE):
        tag = match.group(0)
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            fields[name.group(1)] = value.group(1) if value else ""
    return fields


def gated(response):
    """Whether the answer is the redirect to the sign-in form, which is
    the sign-in's page and not the one asked for."""
    if response.status_code not in REDIRECTS:
        return False
    return urlsplit(response.headers.get("Location", "")).path == "/sign-in"


def unread(rows, reason):
    for row in rows:
        report["unread"][row] = reason


def lost(rows, reason):
    """Rows the application kept the probe from reading. A pass/fail row
    reads failed, since a probe the application blocks is not one it
    passes; a measured row stays unread, with the reason."""
    for row in rows:
        report["lost"][row] = reason
        if row in FORM_ROWS:
            report[row] = False
        else:
            report["unread"][row] = reason


PAYLOAD = "<script>alert(1)</script>"
FORM_ROWS = ("csrf_refused_without_token", "xss_inert")
PRODUCT = {"unit_price": "1.00", "tax_category": "standard"}


def listed(sku):
    """Whether a product shows on the pages that list products."""
    return any(sku in client.get(path).get_data(as_text=True)
               for path in ("/products", "/invoices/new"))


# Every page the probe reads sits behind the sign-in, so it signs in first,
# the way the specification has the administrator do: the seeded account,
# and the sign-in form's own hidden fields. The sign-in is the
# specification's, so one that does not hold is the application's doing.
try:
    form = client.get("/sign-in").get_data(as_text=True)
    body = {"username": USERNAME, "password": PASSWORD, "next": "/"}
    body.update({name: value for name, value in hidden_fields(form).items()
                 if name not in body})
    report["sign_in_status"] = client.post("/sign-in", data=body).status_code
    report["signed_in"] = not gated(client.get("/"))
except Exception as error:
    report["signed_in"] = False
    report["sign_in_error"] = repr(error)[:300]


def form_probe():
    """The CSRF and stored-payload readings, from the products form."""
    page = client.get("/products")
    report["products_status"] = page.status_code
    if gated(page):
        lost(FORM_ROWS, "the products page asked for a sign-in")
        return
    token = hidden_fields(page.get_data(as_text=True))

    # A post with the form's own token has to be stored first: only then
    # does a refused post without one say anything about the token.
    body = dict(PRODUCT, sku="XSS-1", name=PAYLOAD)
    body.update(token)
    created = client.post("/products", data=body, follow_redirects=True)
    report["create_status"] = created.status_code
    if not listed("XSS-1"):
        lost(FORM_ROWS, "a product posted with its token was not stored: %d"
             % created.status_code)
        return

    # The payload must come back inert on every page that can show a product
    # name. A page that renders it raw is the finding, not the one that
    # escapes it.
    raw_pages = [path for path in ("/products", "/invoices/new")
                 if PAYLOAD in client.get(path).get_data(as_text=True)]
    report["xss_raw_pages"] = raw_pages
    report["xss_inert"] = not raw_pages

    # CSRF: the same post without the hidden fields must be refused, with a
    # status the specification names, and must store nothing.
    bare = client.post("/products", data=dict(PRODUCT, sku="CSRF-1",
                                              name="no token"))
    report["csrf_status"] = bare.status_code
    report["csrf_refused_without_token"] = (bare.status_code in (400, 403)
                                            and not listed("CSRF-1"))


try:
    form_probe()
except Exception as error:
    lost(FORM_ROWS, "the application raised: %s" % repr(error)[:300])

BUILDER_ROWS = ("builder_bytes", "builder_subrequests")

try:
    builder = client.get("/invoices/new")
    html = builder.get_data(as_text=True)
    report["builder_status"] = builder.status_code
    if gated(builder):
        lost(BUILDER_ROWS, "the invoice builder asked for a sign-in")
    else:
        report["builder_bytes"] = len(builder.get_data())

        # Subresources the builder asks the browser to fetch. The
        # specification allows one vendored script and no bundler, so this
        # is a number with a stated expectation rather than a bare count.
        requests = re.findall(r'(?:src|href)="(?!http|//|#|mailto)([^"]+)"',
                              html)
        assets = [r for r in requests if not r.endswith("/")
                  and "." in os.path.basename(r)]
        report["builder_subrequests"] = len(assets)
        report["builder_assets"] = assets[:20]
except Exception as error:
    lost(BUILDER_ROWS, "the application raised: %s" % repr(error)[:300])

# Saved HTML for the validator and axe, which run outside this interpreter.
# The pages are saved only when every one of them is the page itself: one
# that is the sign-in's redirect would be read in place of the app.
PAGES = (("index", "/"), ("products", "/products"), ("rules", "/rules"),
         ("jurisdictions", "/jurisdictions"), ("builder", "/invoices/new"))
try:
    answers = [(label, client.get(path)) for label, path in PAGES]
    report["page_statuses"] = {label: response.status_code
                               for label, response in answers}
    asked = [label for label, response in answers if gated(response)]
    if asked:
        report["saved_pages"] = False
        report["save_error"] = ("pages asked for a sign-in: %s"
                                % ", ".join(asked))
    else:
        target = sys.argv[1]
        os.makedirs(target, exist_ok=True)
        for label, response in answers:
            with open(os.path.join(target, label + ".html"), "wb") as handle:
                handle.write(response.get_data())
        report["saved_pages"] = True
except Exception as error:
    report["saved_pages"] = False
    report["save_error"] = repr(error)[:300]

print(json.dumps(report))
'''


def structure(ctx, workspace, roots, seen):
    """The structural design measures, as one probe inside the trial's venv."""
    if not roots:
        return ctx.absent("no source roots were discovered", seen=seen)
    script = os.path.join(workspace, ".score-structure.py")
    with io.open(script, "w", encoding="utf-8") as handle:
        handle.write(STRUCTURE_SCRIPT % {"required": list(REQUIRED_NAMES)})
    outcome = ctx.run([ctx.python, script, json.dumps(roots)], cwd=workspace)
    if outcome["failed"]:
        return ctx.absent("the structure probe %s" % outcome["failed"],
                          seen=seen, invocation=outcome["argv"])
    try:
        payload = json.loads(outcome["stdout"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        return ctx.absent("the structure probe produced no JSON: %s"
                          % (outcome["stderr"] or outcome["stdout"])[:300],
                          seen=seen, invocation=outcome["argv"])
    if not payload.get("files_parsed"):
        return ctx.absent("the structure probe parsed no files", seen=seen,
                          invocation=outcome["argv"])
    return ctx.measured(payload, seen=seen, invocation=outcome["argv"])


# HTMX's attributes are not in the HTML standard, so the validator rejects
# every one, and `SPEC.md` requires HTMX of every arm. Counted, they would
# measure how much HTMX a trial uses rather than how much of its HTML is
# invalid. The quotes are left open because the validator prints ASCII or
# typographic ones depending on its flags.
IGNORED_HTML_ERRORS = r"Attribute .hx-[\w:.-]+. not allowed on element "


def html_errors(report):
    """A validator JSON report's error count, less the ignored errors.

    Returns None where the text is not the validator's report, which is one
    object carrying a `messages` list.
    """
    try:
        payload = json.loads(report)
    except ValueError:
        return None
    messages = payload.get("messages") if isinstance(payload, dict) else None
    if not isinstance(messages, list):
        return None
    errors = [message.get("message") or "" for message in messages
              if isinstance(message, dict) and message.get("type") == "error"]
    ignored = [text for text in errors if re.search(IGNORED_HTML_ERRORS, text)]
    return {"errors": len(errors) - len(ignored), "ignored": len(ignored),
            "messages": len(messages)}


def html_validity(ctx, pages, unsaved=None):
    """HTML validity over the pages the web probe saved.

    The validator needs a Java runtime. Where the machine has none the metric
    is missing and says so, which is the difference between valid HTML and
    unchecked HTML.
    """
    if unsaved:
        return ctx.absent(unsaved)
    binary = ctx.script("html5validator")
    if binary is None:
        return ctx.absent("html5validator is not installed")
    saved = (sorted(name for name in os.listdir(pages) if name.endswith(".html"))
             if os.path.isdir(pages) else [])
    if not saved:
        return ctx.absent("the web probe saved no pages to validate")
    outcome = ctx.run([binary, "--root", pages, "--format", "json"],
                      cwd=pages)
    if outcome["failed"]:
        return ctx.absent("html5validator %s" % outcome["failed"])
    text = outcome["stdout"] + outcome["stderr"]
    if "java" in text.lower() and "not" in text.lower() and not \
            outcome["stdout"].strip():
        return ctx.absent("no Java runtime, so validity was not checked")
    extra = {"pages": len(saved), "ignore_pattern": IGNORED_HTML_ERRORS}

    # A clean run prints nothing and exits zero. Only that pair is a zero: a
    # validator that stopped before reading a page prints nothing too.
    if not outcome["stdout"].strip():
        if outcome["status"] == 0:
            return ctx.measured(0, ignored=0, **extra)
        return ctx.absent("html5validator exited %s with no report: %s"
                          % (outcome["status"], outcome["stderr"][:300]))
    counted = html_errors(outcome["stdout"])
    if counted is not None:
        return ctx.measured(counted["errors"], ignored=counted["ignored"],
                            total=counted["messages"], **extra)

    # The validator prints one message per line when it is not given a
    # parseable format; counting those lines is still a measurement. Output
    # naming no page is not a report at all.
    lines = [line for line in text.splitlines() if ".html" in line]
    if not lines:
        return ctx.absent("html5validator printed no report the probe can "
                          "read: %s" % outcome["stdout"][:300])
    kept = [line for line in lines if not re.search(IGNORED_HTML_ERRORS, line)]
    return ctx.measured(len(kept), ignored=len(lines) - len(kept),
                        raw=kept[:20], **extra)


# The rules of WCAG 2.1 at levels A and AA, by axe's tags. axe also runs its
# best-practice rules by default, which are not WCAG and which every page
# without a landmark fails; they are kept in the record and not counted.
WCAG_TAGS = ("wcag2a", "wcag2aa", "wcag21a", "wcag21aa")


# Runs inside the trial's environment, over the saved pages; it prints every
# rule each page violates, with the rule's tags, so the counting stays here.
AXE_SCRIPT = r'''
import glob, json, os, sys
try:
    from playwright.sync_api import sync_playwright
    from axe_playwright_python.sync_playwright import Axe
except Exception as error:
    print(json.dumps({'error': repr(error)[:200]}))
    raise SystemExit(0)
results = {}
try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page = browser.new_page()
        axe = Axe()
        for path in sorted(glob.glob(os.path.join(sys.argv[1], '*.html'))):
            page.goto('file://' + os.path.abspath(path))
            report = axe.run(page)
            results[os.path.basename(path)] = [
                [rule['id'], rule['tags']]
                for rule in report.response['violations']]
        browser.close()
except Exception as error:
    print(json.dumps({'error': repr(error)[:200]}))
    raise SystemExit(0)
print(json.dumps({'violations': results}))
'''


def wcag_violations(found):
    """Per page, the violated rules that are WCAG 2.1 A or AA, and the rest.

    `found` maps a page to axe's violations, each its rule id and tags.
    """
    counted, ignored = {}, {}
    for page, violations in sorted(found.items()):
        counted[page] = sorted(rule for rule, tags in violations
                               if set(tags) & set(WCAG_TAGS))
        ignored[page] = sorted(rule for rule, tags in violations
                               if not set(tags) & set(WCAG_TAGS))
    return counted, ignored


def accessibility(ctx, workspace, pages, unsaved=None):
    """axe-core violations at WCAG 2.1 AA, over the saved pages.

    Needs a browser binary. Absent one, the row is missing rather than clean:
    an accessibility score nobody measured is not a passing score.
    """
    if unsaved or not os.path.isdir(pages):
        return ctx.absent(unsaved or "the web probe saved no pages to scan")
    script = os.path.join(workspace, ".score-axe.py")
    with io.open(script, "w", encoding="utf-8") as handle:
        handle.write(AXE_SCRIPT)
    outcome = ctx.run([ctx.python, script, pages], cwd=workspace)
    try:
        payload = json.loads(outcome["stdout"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        return ctx.absent("the accessibility probe produced no JSON: %s"
                          % (outcome["stderr"] or outcome["stdout"])[:200])
    if "error" in payload:
        return ctx.absent("axe could not run: %s" % payload["error"])
    found = payload.get("violations", {})
    if not found:
        return ctx.absent("axe scanned no pages")
    counted, ignored = wcag_violations(found)
    return ctx.measured(sum(len(rules) for rules in counted.values()),
                        per_page={page: len(rules)
                                  for page, rules in counted.items()},
                        rules=counted, best_practice=ignored)


def web_quality(ctx, workspace):
    """The web-quality family: escaping, CSRF, weight, validity, axe."""
    pages = os.path.join(workspace, ".score-pages")
    script = os.path.join(workspace, ".score-web.py")
    with io.open(script, "w", encoding="utf-8") as handle:
        handle.write(WEB_SCRIPT)
    outcome = ctx.run([ctx.python, script, pages], cwd=workspace)
    if outcome["failed"]:
        return ctx.absent("the web probe %s" % outcome["failed"],
                          invocation=outcome["argv"])
    try:
        payload = json.loads(outcome["stdout"].strip().splitlines()[-1])
    except (ValueError, IndexError):
        return ctx.absent("the web probe produced no JSON: %s"
                          % (outcome["stderr"] or outcome["stdout"])[:300],
                          invocation=outcome["argv"])
    if "error" in payload:
        return ctx.absent("the application would not boot for the web probe: "
                          "%s" % payload["error"], invocation=outcome["argv"])
    unsaved = None
    if not payload.get("saved_pages"):
        unsaved = "the web probe saved no pages: %s" % payload.get(
            "save_error", "no reason given")
    return ctx.measured(payload, invocation=outcome["argv"],
                        html_validity=html_validity(ctx, pages, unsaved),
                        accessibility=accessibility(ctx, workspace, pages,
                                                    unsaved))


# A build planted with one finding per design probe, so each probe's answer
# can be checked against what was planted. `web.py` names Flask but is never
# imported at import time, so the plant needs nothing installed, and it lies
# outside what `import tariff` loads though the factory imports it lazily;
# `db.py` is persistence by its imports and lies outside too; `data/store.py`
# names Flask and the web module under `if TYPE_CHECKING:`, which loads
# neither, and sqlite3 under an inverted main guard, which does run on
# import, and imports the package's own `data/sqlalchemy.py` relatively;
# `__init__.py` names Werkzeug under a main guard; `data.py`
# loses to the `data` package of the same name, as in Python;
# `data/__init__.py` lies inside, as the initializer on the way to a module an
# absolute import names; `broken.py` does not parse.
PLANTED_BUILD = {
    "tariff/__init__.py": '''\
"""A planted build."""
import logging
from decimal import Decimal

from .rules import BulkRule, CouponRule, PercentageRule, Rule, TieredRule
from .rules import load

__all__ = ["Product", "Catalog", "InvoiceLine", "Invoice", "Jurisdiction",
           "PercentageRule", "BulkRule", "TieredRule", "CouponRule", "price",
           "TariffError", "Extra"]

log = logging.getLogger(__name__)


class TariffError(Exception):
    pass


class Product:
    pass


class Catalog:
    pass


class InvoiceLine:
    pass


class Invoice:
    pass


class Extra:
    pass


def price(invoice, connection: "sqlite3.Connection" = None):
    # see #123 for the rounding rule
    return Decimal("0")


def apply(rule, verbose: bool = False):
    if verbose:
        print("applying", rule)
    return load(rule)


def create_app(database):
    from . import web
    return web.app


if __name__ == "__main__":
    import werkzeug  # noqa: F401
''',
    "tariff/rules.py": '''\
from abc import ABC

from tariff.data.store import load  # noqa: F401


class Rule(ABC):
    kind = "rule"


class PercentageRule(Rule):
    kind = "percent"


class BulkRule(Rule):
    kind = "bulk"


class TieredRule(Rule):
    kind = "tiered"


class CouponRule(Rule):
    kind = "coupon"


def rate_for(rule):
    if rule.kind == "percent":
        return 1
    elif rule.kind == "bulk":
        return 2
    elif rule.kind == "tiered":
        return 3
    return 0
''',
    "tariff/db.py": "import sqlite3\n\n\ndef connect():\n"
                    "    return sqlite3.connect(':memory:')\n",
    "tariff/data.py": "import jinja2  # noqa: F401\n",
    "tariff/data/__init__.py": "import sqlite3  # noqa: F401\n",
    "tariff/data/store.py": '''\
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask  # noqa: F401
    from tariff import web  # noqa: F401

if __name__ != "__main__":
    import sqlite3  # noqa: F401

from .sqlalchemy import nothing  # noqa: E402, F401


def load(rule):
    return rule
''',
    "tariff/data/sqlalchemy.py": "nothing = None\n",
    "tariff/web.py": '''\
from decimal import Decimal

import flask

app = flask.Flask(__name__)


@app.route("/total")
def total():
    return str(Decimal("2") * Decimal("3"))
''',
    "tariff/broken.py": "def broken(:\n",
}


# A stand-in application for the web probe, importable without Flask. Every
# page but the sign-in form sits behind the sign-in, as the specification
# has it. `gated` signs in the seeded administrator, refuses a post without
# its token and escapes what it shows; `locked` never signs anyone in, so
# every page is the sign-in's redirect; `raw` signs in, takes a post without
# a token and shows a stored name as it came; `unstored` signs in and
# refuses every post, the one with its token too.
FAKE_WEB_APP = '''import os

MODE = "__MODE__"
TOKEN = '<input type="hidden" name="csrf_token" value="t">'
PAGE = ('<!doctype html><html lang="en"><head><title>%s</title></head>'
        '<body><main><h1>%s</h1>%s</main></body></html>')


def escape(text):
    return (text.replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


class Response(object):
    def __init__(self, status, body="", location=None):
        self.status_code = status
        self.headers = {"Location": location} if location else {}
        self._body = body

    def get_data(self, as_text=False):
        return self._body if as_text else self._body.encode("utf-8")


class Client(object):
    def __init__(self, app):
        self.app = app
        self.signed = False

    def get(self, path):
        if path == "/sign-in":
            return Response(200, PAGE % ("Sign in", "Sign in", "<form>"
                                         + TOKEN + "</form>"))
        if not self.signed:
            return Response(302, location="/sign-in?next=" + path)
        names = "".join("<li>%s %s</li>" % (sku, name if MODE == "raw"
                                             else escape(name))
                        for sku, name in self.app.products)
        return Response(200, PAGE % (path, path, "<ul>%s</ul><form>%s</form>"
                                     % (names, TOKEN)))

    def post(self, path, data=None, follow_redirects=False):
        data = data or {}
        if path == "/sign-in":
            if data.get("csrf_token") != "t":
                return Response(400, "missing token")
            if MODE != "locked" and data.get("password") == self.app.password:
                self.signed = True
                return Response(302, location=data.get("next") or "/")
            return Response(200, "wrong username or password")
        if not self.signed:
            return Response(302, location="/sign-in")
        if MODE != "raw" and data.get("csrf_token") != "t":
            return Response(400, "missing token")
        if MODE == "unstored":
            return Response(400, "invalid")
        self.app.products.append((data["sku"], data["name"]))
        if follow_redirects:
            return self.get("/products")
        return Response(302, location="/products")


class App(object):
    def __init__(self, database):
        self.password = os.environ.get("TARIFF_ADMIN_PASSWORD")
        self.products = []
        self.config = {}

    def test_client(self):
        return Client(self)


def create_app(database):
    return App(database)
'''


def web_readings(scratch):
    """Run the web probe against the stand-in application in every mode."""
    readings = {}
    for mode in ("gated", "locked", "raw", "unstored"):
        workspace = os.path.join(scratch, "web-" + mode)
        package = os.path.join(workspace, "tariff")
        os.makedirs(package)
        with io.open(os.path.join(package, "__init__.py"), "w",
                     encoding="utf-8") as handle:
            handle.write(FAKE_WEB_APP.replace("__MODE__", mode))
        reading = web_quality(planted_context(), workspace)
        pages = os.path.join(workspace, ".score-pages")
        saved = {}
        if os.path.isdir(pages):
            for name in sorted(os.listdir(pages)):
                with io.open(os.path.join(pages, name),
                             encoding="utf-8") as handle:
                    saved[name] = handle.read()
        readings[mode] = (reading, saved)
    return readings


def web_checks(scratch):
    """The web probe reads the pages behind the sign-in, or nothing."""
    readings = web_readings(scratch)
    gated, gated_pages = readings["gated"]
    locked, locked_pages = readings["locked"]
    raw, _ = readings["raw"]
    values = {mode: reading.get("value") or {}
              for mode, (reading, _) in readings.items()}
    rows = ("csrf_refused_without_token", "xss_inert", "builder_bytes",
            "builder_subrequests")
    counted, ignored = wcag_violations({
        "a.html": [["region", ["cat.keyboard", "best-practice"]],
                   ["landmark-one-main", ["cat.semantics", "best-practice"]],
                   ["image-alt", ["cat.text-alternatives", "wcag2a"]]],
        "b.html": [["color-contrast", ["cat.color", "wcag2aa"]]],
        "c.html": []})
    return [
        ("the web probe signs in and reads the pages behind it",
         values["gated"].get("builder_status") == 200
         and values["gated"].get("csrf_refused_without_token") is True
         and values["gated"].get("xss_inert") is True
         and sorted(gated_pages) == ["builder.html", "index.html",
                                     "jurisdictions.html", "products.html",
                                     "rules.html"]
         and all("<main>" in page for page in gated_pages.values())),
        ("a post without a token and a raw name are findings once signed in",
         values["raw"].get("csrf_refused_without_token") is False
         and values["raw"].get("xss_inert") is False
         and raw["missing"] is None),
        ("a refusal says nothing about the token until a post with it is "
         "stored",
         values["unstored"].get("csrf_refused_without_token") is False
         and values["unstored"].get("xss_inert") is False
         and "was not stored" in values["unstored"].get("lost", {}).get(
             "csrf_refused_without_token", "")),
        ("a sign-in that does not hold fails the form rows and measures "
         "nothing",
         values["locked"].get("signed_in") is False
         and values["locked"].get("csrf_refused_without_token") is False
         and values["locked"].get("xss_inert") is False
         and sorted(values["locked"].get("lost", {})) == sorted(rows)
         and all(row not in values["locked"] for row in rows[2:])
         and sorted(values["locked"].get("unread", {})) == sorted(rows[2:])
         and not locked_pages
         and "asked for a sign-in" in (locked["accessibility"]["missing"]
                                       or "")
         and "asked for a sign-in" in (locked["html_validity"]["missing"]
                                       or "")),
        ("axe counts the WCAG 2.1 A and AA rules, not its best practice",
         counted == {"a.html": ["image-alt"], "b.html": ["color-contrast"],
                     "c.html": []}
         and ignored["a.html"] == ["landmark-one-main", "region"]),
    ]


def planted_context(python=None, failing=None):
    """A scorer's context for the self-test: a real subprocess runner, or one
    that reports every command failed with `failing`."""

    def run(argv, cwd=None):
        if failing:
            return {"failed": failing, "argv": argv, "stdout": "",
                    "stderr": "", "status": 1}
        finished = subprocess.run(argv, cwd=cwd, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, encoding="utf-8",
                                  errors="replace")
        return {"failed": None, "argv": argv, "stdout": finished.stdout,
                "stderr": finished.stderr, "status": finished.returncode}

    def measured(value, **extra):
        return dict({"value": value, "missing": None}, **extra)

    def absent(reason, **extra):
        return dict({"value": None, "missing": reason}, **extra)

    return Context(run=run, measured=measured, absent=absent,
                   python=python or sys.executable, script=lambda name: None)


def self_test():
    """Prove each design probe reads what the planted build holds, and that a
    probe which cannot run leaves its metric missing, never zero."""
    workspace = tempfile.mkdtemp(prefix="efficacy-probes-")
    try:
        for name, text in PLANTED_BUILD.items():
            path = os.path.join(workspace, *name.split("/"))
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with io.open(path, "w", encoding="utf-8") as handle:
                handle.write(text)
        roots = [os.path.join(workspace, "tariff")]
        seen = {"files": 9}
        metric = structure(planted_context(), workspace, roots, seen)
        headless = structure(planted_context(), workspace,
                             [os.path.join(workspace, "tariff", "rules.py")],
                             seen)
        rootless = structure(planted_context(), workspace, [], seen)
        broken = structure(planted_context(failing="exited 1"), workspace,
                           roots, seen)
        web = web_checks(workspace)
    finally:
        shutil.rmtree(workspace, ignore_errors=True)
    facts = metric.get("value") or {}
    surface = facts.get("surface") or {}
    isolation = facts.get("io_isolation") or {}
    graph = facts.get("graph") or {}
    probes = ("roles", "layering_violations", "money_in_routes",
              "bool_parameters", "extension_points", "kind_ladders",
              "surface", "io_isolation", "graph", "print_calls",
              "exception_bases", "citations", "logging")
    checks = [
        ("every design probe answers in the one structure report",
         metric["missing"] is None and all(key in facts for key in probes)),
        ("a module's role follows what it imports",
         facts.get("roles", {}).get("web.py") == "web"
         and facts.get("roles", {}).get("db.py") == "persistence"
         and facts.get("roles", {}).get("rules.py") == "domain"),
        ("a module import tariff loads that reaches the store is a violation",
         ["tariff/data/__init__.py", "sqlite3"]
         in (facts.get("layering_violations") or [])),
        ("an inverted main guard runs on import, so its import counts",
         ["tariff/data/store.py", "sqlite3"]
         in (facts.get("layering_violations") or [])),
        ("a relative import names the package's module, not a driver",
         "tariff/data/sqlalchemy.py" in (facts.get("import_closure") or [])
         and not any(name == "sqlalchemy" for _, name in
                     facts.get("layering_violations") or [])),
        ("an initializer on the way to an imported module is loaded too",
         "tariff/data/__init__.py" in facts.get("import_closure", [])
         and "tariff/data/store.py" in facts.get("import_closure", [])),
        ("an import inside a function is outside what import tariff loads",
         facts.get("import_closure")
         == ["tariff/__init__.py", "tariff/rules.py", "tariff/data/__init__.py",
             "tariff/data/store.py", "tariff/data/sqlalchemy.py"]),
        ("an import under if TYPE_CHECKING loads nothing",
         not any(name == "flask" for _, name in
                 facts.get("layering_violations") or [])
         and "tariff/web.py" not in (facts.get("import_closure") or [])),
        ("an import under a main guard loads nothing",
         not any(name == "werkzeug" for _, name in
                 facts.get("layering_violations") or [])),
        ("a package wins over a module of its name, as in Python",
         "tariff/data.py" not in (facts.get("import_closure") or [])
         and not any(name == "jinja2" for _, name in
                     facts.get("layering_violations") or [])),
        ("without a package entry the layering reading is missing, not zero",
         (headless.get("value") or {}).get("layering_violations") is None
         and (headless.get("value") or {}).get("files_parsed") == 1),
        ("Decimal arithmetic inside a route is money in a route",
         facts.get("money_in_routes") == [["web.py", "total"]]),
        ("a bool parameter is named by file, function and argument",
         ["__init__.py", "apply", "verbose"] in facts.get("bool_parameters", [])),
        ("an abstract base over rule kinds is an extension point",
         facts.get("extension_points", {}).get("rule_kinds") is True
         and facts.get("extension_points", {}).get("export_formats") is False),
        ("a three-deep conditional on a rule's kind is a kind ladder",
         facts.get("kind_ladders") == [["rules.py", 3]]),
        ("the public surface is read against the names the spec requires",
         surface.get("missing") == ["Jurisdiction"]
         and surface.get("extra") == ["Extra"]),
        ("a price parameter annotated as a connection leaks IO",
         isolation.get("leaked") == ["connection"]
         and isolation.get("clean") is False),
        ("the import graph is a measurement or a named absence",
         ("modules" in graph) != ("error" in graph)),
        ("a print call, a ticket citation and an exception base are findings",
         facts.get("print_calls") == [["__init__.py", 46]]
         and facts.get("citations") == [["__init__.py", 40]]
         and facts.get("exception_bases")
         == [["__init__.py", "TariffError", "Exception"]]),
        ("logging without a NullHandler is reported as used and unhandled",
         facts.get("logging") == {"used": True, "null_handler": False}),
        ("a file that does not parse is named, and the rest are read",
         [entry[0] for entry in facts.get("unparsed", [])]
         == [os.path.join(workspace, "tariff", "broken.py")]
         and facts.get("files_parsed") == 8),
        ("without source roots the structure metric is missing, not zero",
         rootless["value"] is None and "no source roots" in rootless["missing"]),
        ("a probe that fails leaves its metric missing, with the command",
         broken["value"] is None and "exited 1" in broken["missing"]
         and broken.get("invocation")),
    ] + web
    for label, ok in checks:
        print("  %-62s %s" % (label, "ok" if ok else "FAILED"))
    passed = sum(1 for _, ok in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true",
                        help="probe a planted build and check each answer; "
                             "read no trial")
    options = parser.parse_args(argv)
    if options.self_test:
        return self_test()
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
