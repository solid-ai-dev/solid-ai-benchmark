"""Read scored efficacy trials for reliability, performance and flexibility.

Seven probes, each read on the application the trial's factory returns:
fault tolerance under malformed requests, concurrent writes, latency, an
invoice of 500 lines, SQL statements per invoice line, two instances side by
side, and the same build on another Python. Each passes or fails, except the
latency, which is recorded as two repeats of its 95th percentile.

Each trial is installed into a fresh environment of its own, on the spec's
Python, and read there in one in-process run through the test client. A probe
this reader could not run is missing, never zero; one the trial kept from
running, by not installing, not booting or not signing in its administrator,
is lost, and reads failed.
"""

import argparse
import datetime
import io
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402
from harness import (LiveRunError, canonical, claim_area,  # noqa: E402
                     claim_refusal_check, release_area, remove_tree,
                     scoring_area)
from score import (create_venv, pip, python_in, run,  # noqa: E402
                   venv_version)

SCRIPT = os.path.basename(__file__)

# The probes, in the order the reading files them. The latency is a measured
# value; every other probe passes or fails.
PROBES = ("fuzz_robustness", "concurrent_writes", "latency_p95_ms",
          "capacity_500_lines", "n_plus_one", "coexistence",
          "python_portability")
MEASURED = ("latency_p95_ms",)

# The probes the one in-process run reads; portability needs an interpreter
# of its own.
IN_PROCESS = tuple(name for name in PROBES if name != "python_portability")

# The interpreter beside the spec's on the owner's machine. Its build has to
# install, boot and serve a signed-in page there too.
OTHER_PYTHON = (3, 14)
OTHER_PYTHON_COMMANDS = (["py", "-%d.%d" % OTHER_PYTHON],
                         ["python%d.%d" % OTHER_PYTHON])

# Long enough for a slow build's 500-line invoice; a run that outlasts it
# keeps what it read and loses the rest to the application.
PROBE_TIMEOUT = 900


# Runs inside the trial's fresh environment, against the application the
# factory returns, through its test client: the specification gives a
# factory, not a server, and counting SQL statements or catching an exception
# needs the application's own process. The first argument is the mode, `all`
# or `portability`; the second is the file the report is written to after
# every probe, so a run that stalls still files what it read; the third is
# where each database's folder is made, outside the workspace, so the
# reader can remove them once the interpreter has let go of their files.
#
# It signs in as the specification has the administrator do: the password
# from the environment, set before the package is imported because the seed
# may run lazily, and the sign-in form's own hidden fields. The sign-in holds
# only where the dashboard then answers 200. Every probe reads the pages
# behind that sign-in; a request it turns away, with its redirect, a 401 or
# a 403, is never measured, and the probe is lost.
QUALITY_SCRIPT = r'''
import builtins, io, json, logging, math, os, platform, re, sqlite3
import sys, tempfile, threading, time
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import url2pathname

PACKAGE = "tariff"
USERNAME = "admin"
PASSWORD = "quality-probe-5b3f-Passphrase"
REDIRECTS = (301, 302, 303, 307, 308)
MODE, PROGRESS, DATABASES = sys.argv[1], sys.argv[2], sys.argv[3]
WORKSPACE = os.path.abspath(os.getcwd())
os.environ["TARIFF_ADMIN_PASSWORD"] = PASSWORD

real_open = builtins.open
real_os_open = os.open
report = {"python": platform.python_version(), "probes": {},
          "running": "boot"}


def save():
    """The report so far, replaced whole, so a stalled run leaves a whole
    file behind."""
    with real_open(PROGRESS + ".part", "w", encoding="utf-8") as handle:
        json.dump(report, handle)
    os.replace(PROGRESS + ".part", PROGRESS)


def finish():
    report.pop("running", None)
    save()
    print(json.dumps(report))
    raise SystemExit(0)


save()


# Every statement any connection runs is counted, on every connection the
# application opens: the factory is wrapped before the package is imported,
# so a module that imports `connect` by name gets the wrapped one too.
statements = {"window": 0, "total": 0}


def traced(statement):
    statements["window"] += 1
    statements["total"] += 1


# Where the application writes while the co-existence probe watches.
watch = {"on": False, "paths": []}


def note(path):
    if watch["on"] and isinstance(path, (str, bytes, os.PathLike)):
        watch["paths"].append(os.path.abspath(os.fsdecode(path)))


real_connect = sqlite3.connect


# A database named by a `file:` URI, as `Path.as_uri()` writes one with
# `uri=True`, is read back to the path it names: its query, such as
# `?mode=rwc`, dropped, its escapes undone, and `/C:/...` read as a drive.
def database_file(target):
    """The file a connection opens, or None for a database in memory."""
    if target.startswith("file:"):
        parts = urlsplit(target)
        if "mode=memory" in parts.query:
            return None
        path = parts.path
        if parts.netloc and parts.netloc != "localhost":
            path = "//" + parts.netloc + path
        target = url2pathname(path) if path else ""
    if target in ("", ":memory:"):
        return None
    return target


def connect(*args, **kwargs):
    connection = real_connect(*args, **kwargs)
    try:
        connection.set_trace_callback(traced)
    except Exception:
        pass
    target = args[0] if args else kwargs.get("database")
    if isinstance(target, (str, bytes, os.PathLike)):
        path = database_file(os.fsdecode(target))
        if path:
            note(path)
    return connection


sqlite3.connect = connect
sqlite3.dbapi2.connect = connect


# A file opened to write, by name. Python's own bytecode cache writes through
# the interpreter's internal `open`, so the import machinery is not read.
def watched_open(file, mode="r", *args, **kwargs):
    if any(flag in mode for flag in "wax+"):
        note(file)
    return real_open(file, mode, *args, **kwargs)


WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND


def watched_os_open(path, flags, *args, **kwargs):
    if flags & WRITE_FLAGS:
        note(path)
    return real_os_open(path, flags, *args, **kwargs)


builtins.open = io.open = watched_open
os.open = watched_os_open

# Every record any logger hands to its handlers, with its traceback, so an
# error the application answered 500 for is read even where no page shows it.
records = []
original_call_handlers = logging.Logger.callHandlers


def call_handlers(self, record):
    try:
        text = record.getMessage()
    except Exception:
        text = str(record.msg)
    if record.exc_info:
        text += "\n" + logging.Formatter().formatException(record.exc_info)
    records.append(text)
    return original_call_handlers(self, record)


logging.Logger.callHandlers = call_handlers


def folder():
    return tempfile.mkdtemp(prefix="quality-probe-", dir=DATABASES)


try:
    import importlib
    package = importlib.import_module(PACKAGE)
    app = package.create_app(os.path.join(folder(), "quality-probe.sqlite"))
    client = app.test_client()
except Exception as error:
    report["error"] = repr(error)[:300]
    finish()


class Gated(Exception):
    """A request the sign-in turned away."""


class Raised(Exception):
    """The application raised out of the test client."""


class Hidden(HTMLParser):
    """Collects every hidden input, however its attributes are quoted, in
    page order, with the action of the form it sits in."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.inputs = []
        self.forms = []
        self.form = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "form":
            self.form = len(self.forms)
            self.forms.append(attributes.get("action") or "")
        elif (tag == "input" and (attributes.get("type") or "").lower()
                == "hidden" and attributes.get("name")):
            self.inputs.append((self.form, attributes["name"],
                                attributes.get("value") or ""))

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None


# A page may hold several forms, each with its own token, such as a sign-out
# form beside the one being sent. The fields sent are those of the first form
# whose action is the path posted to, read as the browser resolves it, its
# query ignored, an empty action being the page's own path. A post no form's
# action names takes every hidden field on the page, the first of each name.
# A save control's `formaction` is not read: the builder's save is sent with
# the builder form's fields by that fallback, which is how a browser sends it.
def hidden_fields(text, page_path, target):
    """The hidden fields a post to `target` carries from the page at
    `page_path`."""
    parser = Hidden()
    parser.feed(text)
    base = "http://localhost" + page_path
    wanted = urlsplit(target).path
    for form, action in enumerate(parser.forms):
        if urlsplit(urljoin(base, action or page_path)).path == wanted:
            fields = {}
            for owner, name, value in parser.inputs:
                if owner == form:
                    fields.setdefault(name, value)
            return fields
    fields = {}
    for _, name, value in parser.inputs:
        fields.setdefault(name, value)
    return fields


# A request the sign-in turns away: its redirect, a 401, or a 403 to a
# request that carried its form's token, which no CSRF check refuses. A
# request sent without a token may be refused 403 as a forgery, as the
# specification allows.
def gated(response, token=True):
    """Whether the answer refuses the request for want of a sign-in."""
    if response.status_code == 401 or (token and response.status_code == 403):
        return True
    if response.status_code not in REDIRECTS:
        return False
    return urlsplit(response.headers.get("Location", "")).path == "/sign-in"


def ask(who, method, path, data=None, headers=None):
    try:
        return who.open(path, method=method, data=data,
                        headers=headers or {})
    except Exception as error:
        raise Raised(repr(error)[:300])


def page(who, path):
    """A page behind the sign-in, or Gated."""
    answer = ask(who, "GET", path)
    if gated(answer):
        raise Gated("%s was turned away by the sign-in: %d"
                    % (path, answer.status_code))
    return answer


def form_post(who, form, path, body, method="POST", headers=None):
    """A post carrying the hidden fields of the form it is sent from, read
    afresh, since a token may change between answers."""
    data = dict(body)
    for name, value in hidden_fields(
            ask(who, "GET", form).get_data(as_text=True), form,
            path).items():
        data.setdefault(name, value)
    return ask(who, method, path, data=data, headers=headers)


def held(answer, what):
    if gated(answer):
        raise Gated("%s was turned away by the sign-in: %d"
                    % (what, answer.status_code))
    return answer


def sign_in(who):
    """Whether the seeded administrator signs in: the dashboard, which
    only a signed-in administrator is shown, then answers 200."""
    try:
        body = {"username": USERNAME, "password": PASSWORD, "next": "/"}
        answer = form_post(who, "/sign-in", "/sign-in", body)
        report.setdefault("sign_in_status", answer.status_code)
        home = ask(who, "GET", "/")
        report.setdefault("home_status", home.status_code)
        return home.status_code == 200
    except Raised as error:
        report.setdefault("sign_in_error", str(error))
        return False


def passed(ok, **detail):
    detail["passed"] = bool(ok)
    return detail


def lost(name, reason, **detail):
    """A probe the application kept from running: a pass or fail reads
    failed, the latency reads no value."""
    detail["lost"] = reason
    if name == "latency_p95_ms":
        detail["value"] = None
    else:
        detail["passed"] = False
    return detail


SKUS = ("WID-1", "GAD-2", "BOK-3", "SRV-4", "SEE-5")
WORKED = (("WID-1", 12), ("SEE-5", 7), ("BOK-3", 2), ("SRV-4", 1))


def builder_body(lines, coupons=""):
    return {"jurisdiction": "DE", "currency": "EUR", "customer": "",
            "coupon_codes": coupons, "sku": [sku for sku, _ in lines],
            "quantity": [str(quantity) for _, quantity in lines]}


def saved_page(answer):
    """The invoice page a save redirected to, or None."""
    if answer.status_code not in REDIRECTS:
        return None
    path = urlsplit(answer.headers.get("Location", "")).path
    if re.match(r"^/invoices/[^/]+$", path) and path not in (
            "/invoices/new", "/invoices/preview"):
        return path
    return None


def save_invoice(who, lines, coupons=""):
    """Save an invoice through the builder; its page, or Gated."""
    answer = held(form_post(who, "/invoices/new", "/invoices",
                            builder_body(lines, coupons)), "the save")
    path = saved_page(answer)
    if path is None:
        raise Gated("an invoice of %d lines was not saved: it answered %d"
                    % (len(lines), answer.status_code))
    return path


def ok(answer):
    return 200 <= answer.status_code < 300


def p95(times):
    """The nearest-rank 95th percentile."""
    ordered = sorted(times)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


ROUTES = ("/", "/products", "/rules", "/jurisdictions", "/customers",
          "/invoices/new")


def latency_p95_ms():
    """The 95th percentile of 30 requests over the main routes, twice."""
    invoice = save_invoice(client, WORKED, "WELCOME")
    requests = ([("GET", path) for path in ROUTES]
                + [("GET", invoice), ("GET", invoice + "/export.json"),
                   ("GET", invoice + "/export.csv"),
                   ("POST", "/invoices/preview")])

    def timed(method, path):
        data = headers = None
        if method == "POST":
            data = builder_body(WORKED, "WELCOME")
            data.update({name: value for name, value in hidden_fields(
                page(client, "/invoices/new").get_data(as_text=True),
                "/invoices/new", path).items() if name not in data})
            headers = {"HX-Request": "true"}
        start = time.perf_counter()
        answer = ask(client, method, path, data=data, headers=headers)
        elapsed = (time.perf_counter() - start) * 1000
        held(answer, "%s %s" % (method, path))
        if not ok(answer):
            raise Gated("%s %s answered %d, so its time is not the route's"
                        % (method, path, answer.status_code))
        return elapsed

    # The first answer of each route compiles its templates, which no later
    # request pays for.
    for method, path in requests:
        timed(method, path)
    repeats = []
    for _ in range(2):
        times = [timed(method, path) for _ in range(3)
                 for method, path in requests]
        repeats.append(round(p95(times), 2))
    return {"value": max(repeats), "repeats": repeats,
            "requests": len(times), "routes": [" ".join(request)
                                               for request in requests]}


def counted(path):
    """The statements one answer ran, and the answer."""
    statements["window"] = 0
    answer = page(client, path)
    return statements["window"], answer


def n_plus_one():
    """Statements for a 1-line and a 20-line invoice page."""
    one = save_invoice(client, [("WID-1", 1)])
    twenty = save_invoice(client, [(SKUS[index % len(SKUS)], index + 1)
                                   for index in range(20)])
    for path in (one, twenty):
        page(client, path)
    small, first = counted(one)
    large, second = counted(twenty)
    if not (ok(first) and ok(second)):
        return lost("n_plus_one", "an invoice page answered %d and %d"
                    % (first.status_code, second.status_code))

    # A page that runs nothing is read only where the statements are seen
    # elsewhere: then the count is real, and it did not grow.
    if not statements["total"]:
        return {"passed": None, "missing": "no SQL statement was traced on "
                "any connection, so none could be counted"}
    return passed(large <= small, one_line=small, twenty_lines=large)


def exported(path, lines):
    """The saved invoice's JSON export read against the lines saved: its
    total, or None and why it does not hold them."""
    try:
        export = json.loads(page(client, path + "/export.json").get_data(
            as_text=True))
    except ValueError:
        return None, "the saved invoice's JSON export is not JSON"
    if not isinstance(export, dict) or not isinstance(export.get("lines"),
                                                      list):
        return None, "the saved invoice's JSON export lists no lines"
    records = export["lines"]
    malformed = [index for index, line in enumerate(records)
                 if not isinstance(line, dict)
                 or not isinstance(line.get("sku"), str)
                 or type(line.get("quantity")) is not int]
    if malformed:
        return None, ("the export's line %d is not a record with a sku and "
                      "an integer quantity" % (malformed[0] + 1))
    if [(line["sku"], line["quantity"]) for line in records] != lines:
        return None, ("the export holds %d lines, not the %d saved in order"
                      % (len(records), len(lines)))
    # A total that is no finite amount, NaN or Infinity among them, is the
    # build's malformed output, so it fails rather than goes unread.
    try:
        total = Decimal(str(export.get("total")))
    except InvalidOperation:
        total = None
    if total is None or not total.is_finite():
        return None, ("the export's total, %r, is not a finite amount"
                      % (export.get("total"),))
    return total, None


# Every line is the seed's Seed pack, SEE-5, so the invoice's total scales
# with its lines: it is zero-rated, so no tax rounds per line; its one rule
# is a bulk rule read per line; a quantity of 6, 12, 18, 24 or 30 makes each
# line's net a whole multiple of 15.00; no coupon is sent; and the one rule
# over the whole invoice is a percentage. 500 lines, five times the first
# 100, then cost five times what those 100 cost, to the cent; a cent is
# allowed for rounding all the same.
LINES = [("SEE-5", 6 * (1 + index % 5)) for index in range(500)]
SAMPLE = 100
CENT = Decimal("0.01")


def saved_export(lines, steps, key):
    """Save an invoice of `lines` and read its export: the total, or None
    and why it does not hold them."""
    saved = held(form_post(client, "/invoices/new", "/invoices",
                           builder_body(lines)), "the save")
    steps["save" + key] = saved.status_code
    path = saved_page(saved)
    if path is None:
        return None, None, ("the save of %d lines did not redirect to its "
                            "page" % len(lines))
    total, reason = exported(path, lines)
    return path, total, reason


def capacity_500_lines():
    """An invoice of 500 lines previewed, saved and rendered, its export
    holding every line, and priced five times its first 100 saved alone."""
    lines = LINES
    steps = {}
    try:
        preview = held(form_post(client, "/invoices/new", "/invoices/preview",
                                 builder_body(lines),
                                 headers={"HX-Request": "true"}),
                       "the preview")
        steps["preview"] = preview.status_code
        path, total, reason = saved_export(lines, steps, "")
        if path is not None:
            rendered = page(client, path)
            steps["render"] = rendered.status_code
        if not reason:
            _, sample, sample_reason = saved_export(lines[:SAMPLE], steps,
                                                    "_%d" % SAMPLE)
    except Raised as error:
        return passed(False, steps=steps, raised=str(error))

    # The preview and the page are read for answering, never for the amounts
    # they show: what a page writes beside a total, a subtotal among them,
    # cannot be told apart from it. The amounts are the exports', in the
    # spec's fixed form.
    if path is not None and not (ok(preview) and ok(rendered)):
        return passed(False, steps=steps)

    # A build that quietly keeps fewer lines answers 2xx everywhere. The
    # export must list every line saved, in order, each a well-formed record,
    # with a finite total; a malformed one is the build's output, so it fails.
    if reason:
        return passed(False, steps=steps, reason=reason)

    # Every line is a Seed pack at a quantity of six or more, which costs
    # more than nothing under the seed's rules, so the invoice's total is
    # positive; a total of nothing scales with any count of lines.
    if total <= 0:
        return passed(False, steps=steps, total=str(total),
                      reason="500 lines that each cost more than nothing "
                             "were priced at %s" % total)

    # The total is the build's own, so a calculation that reads only the
    # first 100 lines would agree with itself everywhere. Those 100 lines,
    # saved alone, must cost a fifth of it.
    if sample_reason:
        return passed(False, steps=steps,
                      reason="the invoice of %d lines: %s"
                             % (SAMPLE, sample_reason))
    scales = abs(total - sample * len(lines) / SAMPLE) <= CENT
    return passed(scales, steps=steps, total=str(total),
                  sample_total=str(sample))


LOCKED = re.compile(r"database (table )?is locked", re.IGNORECASE)

# How long each writer is waited for. The self-test shortens it; a run
# against a build never sets it.
WRITE_SECONDS = float(os.environ.get("QUALITY_PROBE_WRITE_SECONDS") or 120)


def concurrent_writes():
    """Two clients, each saving 20 products at once."""

    # Run after the fuzzing, the writes go to an instance of their own on a
    # fresh database, so no product a malformed request stored can reach
    # their reading.
    try:
        own = package.create_app(os.path.join(folder(), "concurrent.sqlite"))
    except Exception as error:
        return passed(False, reason="a fresh instance would not boot: %s"
                      % repr(error)[:300])
    writers = [own.test_client(), own.test_client()]
    reader = own.test_client()
    if not all(sign_in(who) for who in writers + [reader]):
        return lost("concurrent_writes", "a writing client could not sign in")
    start = threading.Barrier(len(writers))
    outcomes = [[] for _ in writers]
    logged = len(records)

    def write(index):
        try:
            start.wait(timeout=60)
        except threading.BrokenBarrierError:
            return
        for number in range(20):
            sku = "QCW-%d-%02d" % (index, number)
            entry = {"sku": sku}
            try:
                answer = form_post(writers[index], "/products", "/products",
                                   {"sku": sku, "name": "Concurrent %s" % sku,
                                    "unit_price": "1.00",
                                    "tax_category": "standard"})
                entry["status"] = answer.status_code
                entry["gated"] = gated(answer)
                entry["locked"] = bool(LOCKED.search(
                    answer.get_data(as_text=True)))
            except Raised as error:
                entry["raised"] = str(error)
                entry["locked"] = bool(LOCKED.search(str(error)))
            outcomes[index].append(entry)

    threads = [threading.Thread(target=write, args=(index,), daemon=True)
               for index in range(len(writers))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=WRITE_SECONDS)
    if any(thread.is_alive() for thread in threads):
        return passed(False, hung=True, reason=(
            "a write did not finish in %g s: the application hung it"
            % WRITE_SECONDS))
    entries = [entry for outcome in outcomes for entry in outcome]
    if any(entry.get("gated") for entry in entries):
        return lost("concurrent_writes", "a write was turned away by the "
                    "sign-in")
    listing = page(reader, "/products").get_data(as_text=True)
    unsaved = [entry["sku"] for entry in entries
               if entry["sku"] not in listing]
    failed = [entry for entry in entries if entry.get("raised")
              or (entry.get("status") or 0) >= 500]
    locked = (any(entry["locked"] for entry in entries)
              or any(LOCKED.search(text) for text in records[logged:]))
    return passed(len(entries) == 40 and not unsaved and not failed
                  and not locked, written=len(entries), unsaved=unsaved,
                  failed=failed[:5], locked=locked)


def inside(path, roots):
    path = os.path.normcase(os.path.realpath(path))
    for root in roots:
        root = os.path.normcase(os.path.realpath(root))
        try:
            if os.path.commonpath([path, root]) == root:
                return True
        except ValueError:
            continue
    return False


PRODUCT = {"sku": "QCO-1", "name": "Coexistence probe", "unit_price": "2.00",
           "tax_category": "standard"}


def coexistence():
    """Two instances, each on its own database: a write through one stays
    out of the other, and neither writes outside its folder or the
    workspace."""

    # A database's sidecars, its `-wal`, `-shm` and `-journal`, sit in its
    # folder, so the two folders admit them.
    folders_given = [folder(), folder()]
    watch["paths"] = []
    watch["on"] = True
    try:
        try:
            first, second = [
                package.create_app(os.path.join(where, "coexist.sqlite"))
                for where in folders_given]
        except Exception as error:
            return passed(False, reason="a second instance would not boot: "
                          "%s" % repr(error)[:300])
        one, other = first.test_client(), second.test_client()
        if not (sign_in(one) and sign_in(other)):
            return lost("coexistence", "an instance's administrator could "
                        "not sign in")
        held(form_post(one, "/products", "/products", PRODUCT),
             "the product's post")
        stored = PRODUCT["sku"] in page(one, "/products").get_data(
            as_text=True)
        leaked = PRODUCT["sku"] in page(other, "/products").get_data(
            as_text=True)
    finally:
        watch["on"] = False
    if not stored:
        return lost("coexistence", "the product written through the first "
                    "instance was not stored")
    stray = sorted(set(path for path in watch["paths"]
                       if not inside(path, folders_given + [WORKSPACE])))
    return passed(not leaked and not stray, leaked=leaked, stray=stray[:10])


# A number past any bound a price, percentage, rate or tier can have. The
# specification sets no upper bound on a quantity, a group or an id, so one
# past what SQLite stores, or what a Decimal prices to the cent, has no
# answer it defines; those stay at a quintillion, inside both.
HUGE = "9" * 400
BIG = "1" + "0" * 18
LONG = "x" * 20000
GOOD = {"sku": "QFZ-1", "name": "Fuzz", "unit_price": "1.00",
        "tax_category": "standard"}


def product(**fields):
    return dict(GOOD, **fields)


def preview(**fields):
    body = {"jurisdiction": "DE", "currency": "EUR", "customer": "",
            "coupon_codes": "", "sku": "WID-1", "quantity": "1"}
    body.update(fields)
    return body


# Each malformed request: a label, the method, the path, the form whose
# hidden fields it carries (None for none), its body, and whether it is sent
# signed out. Every one is a request the specification defines an answer to:
# a re-rendered form, a 400, a 404 or a 405. Only these answers are read,
# never a later page after one stored an extreme value, such as a price of
# `1e999999`: the specification bounds no price's size, so it defines no
# answer for such a page, and reading one would measure that gap, not the
# build.
FUZZ = (
    ("POST /products unit_price=abc", "POST", "/products", "/products",
     product(unit_price="abc"), False),
    ("POST /products unit_price=NaN", "POST", "/products", "/products",
     product(sku="QFZ-2", unit_price="NaN"), False),
    ("POST /products unit_price=Infinity", "POST", "/products", "/products",
     product(sku="QFZ-3", unit_price="Infinity"), False),
    ("POST /products unit_price=-1", "POST", "/products", "/products",
     product(sku="QFZ-4", unit_price="-1"), False),
    ("POST /products unit_price=1e999999", "POST", "/products", "/products",
     product(sku="QFZ-5", unit_price="1e999999"), False),
    ("POST /products unit_price=<400 digits>", "POST", "/products",
     "/products", product(sku="QFZ-6", unit_price=HUGE), False),
    ("POST /products unicode", "POST", "/products", "/products",
     product(sku="ŠKU-☃-‮", name="名前 \U0001f9fe",
             tax_category="stándard"), False),
    ("POST /products null bytes", "POST", "/products", "/products",
     product(sku="QFZ\x00-7", name="nul\x00name"), False),
    ("POST /products 20000-character fields", "POST", "/products",
     "/products", product(sku=LONG, name=LONG), False),
    ("POST /products no fields", "POST", "/products", "/products", {},
     False),
    ("POST /products no unit_price", "POST", "/products", "/products",
     {"sku": "QFZ-8", "name": "Fuzz", "tax_category": "standard"}, False),
    ("POST /rules kind=bogus", "POST", "/rules", "/rules",
     {"rule_id": "qfz-1", "kind": "bogus", "sku": ""}, False),
    ("POST /rules percent=abc", "POST", "/rules", "/rules",
     {"rule_id": "qfz-2", "kind": "percentage", "sku": "", "percent": "abc"},
     False),
    ("POST /rules percent=<400 digits>", "POST", "/rules", "/rules",
     {"rule_id": "qfz-3", "kind": "percentage", "sku": "", "percent": HUGE},
     False),
    ("POST /rules buy=abc", "POST", "/rules", "/rules",
     {"rule_id": "qfz-4", "kind": "bulk", "sku": "WID-1", "buy": "abc",
      "pay": "1"}, False),
    ("POST /rules buy and pay of 19 digits", "POST", "/rules", "/rules",
     {"rule_id": "qfz-5", "kind": "bulk", "sku": "WID-1", "buy": BIG[:-1] + "1",
      "pay": BIG}, False),
    ("POST /rules tiers=1:,:5,a:b", "POST", "/rules", "/rules",
     {"rule_id": "qfz-6", "kind": "tiered", "sku": "WID-1",
      "tiers": "1:,:5,a:b"}, False),
    ("POST /rules tiers of 400 digits", "POST", "/rules", "/rules",
     {"rule_id": "qfz-7", "kind": "tiered", "sku": "WID-1",
      "tiers": "%s:1.00" % HUGE}, False),
    ("POST /rules amount=abc", "POST", "/rules", "/rules",
     {"rule_id": "qfz-8", "kind": "coupon", "sku": "", "code": "QFZ",
      "amount": "abc"}, False),
    ("POST /rules no fields", "POST", "/rules", "/rules", {}, False),
    ("POST /jurisdictions rates=standard==,=0.1,,", "POST", "/jurisdictions",
     "/jurisdictions", {"code": "QF", "name": "Fuzz", "default_rate": "0.1",
                        "rates": "standard==,=0.1,,"}, False),
    ("POST /jurisdictions default_rate=abc", "POST", "/jurisdictions",
     "/jurisdictions", {"code": "QG", "name": "Fuzz", "default_rate": "abc",
                        "rates": ""}, False),
    ("POST /jurisdictions rate of 400 digits", "POST", "/jurisdictions",
     "/jurisdictions", {"code": "QH", "name": "Fuzz", "default_rate": "0.1",
                        "rates": "standard=%s" % HUGE}, False),
    ("POST /customers email=a@@b", "POST", "/customers", "/customers",
     {"name": "Fuzz", "email": "a@@b", "address": "1 Fuzz Lane"}, False),
    ("POST /customers unicode", "POST", "/customers", "/customers",
     {"name": "Zoë ☃", "email": "zoë@exämple.test",
      "address": "Straße 1\n‮"}, False),
    ("POST /customers no fields", "POST", "/customers", "/customers", {},
     False),
    ("POST /invoices/preview quantity=abc", "POST", "/invoices/preview",
     "/invoices/new", preview(quantity="abc"), False),
    ("POST /invoices/preview quantity=<19 digits>", "POST",
     "/invoices/preview", "/invoices/new", preview(quantity=BIG), False),
    ("POST /invoices/preview quantity=-5", "POST", "/invoices/preview",
     "/invoices/new", preview(quantity="-5"), False),
    ("POST /invoices/preview two skus, one quantity", "POST",
     "/invoices/preview", "/invoices/new",
     preview(sku=["WID-1", "GAD-2"], quantity=["1"]), False),
    ("POST /invoices/preview customer=abc", "POST", "/invoices/preview",
     "/invoices/new", preview(customer="abc"), False),
    ("POST /invoices/preview customer=<19 digits>", "POST",
     "/invoices/preview", "/invoices/new", preview(customer=BIG), False),
    ("POST /invoices/preview currency=€€€", "POST",
     "/invoices/preview", "/invoices/new", preview(currency="€€€"),
     False),
    ("POST /invoices/preview coupon_codes=,,, ,nul", "POST",
     "/invoices/preview", "/invoices/new",
     preview(coupon_codes=",,, ,\x00"), False),
    ("POST /invoices quantity=abc", "POST", "/invoices", "/invoices/new",
     preview(quantity="abc"), False),
    ("POST /invoices no fields", "POST", "/invoices", "/invoices/new", {},
     False),
    ("GET /invoices/abc", "GET", "/invoices/abc", None, None, False),
    ("GET /invoices/<19 digits>", "GET", "/invoices/" + BIG, None, None,
     False),
    ("GET /invoices/-1/export.csv", "GET", "/invoices/-1/export.csv", None,
     None, False),
    ("GET /customers/<19 digits>/export.json", "GET",
     "/customers/%s/export.json" % BIG, None, None, False),
    ("POST /products/<unicode>/delete", "POST",
     "/products/%E2%98%83%00/delete", "/products", {}, False),
    ("POST /rules/<missing>/delete", "POST", "/rules/qfz-missing/delete",
     "/rules", {}, False),
    ("PUT /products", "PUT", "/products", None, product(), False),
    ("DELETE /invoices/new", "DELETE", "/invoices/new", None, None, False),
    ("GET /invoices/preview", "GET", "/invoices/preview", None, None, False),
    ("PATCH /rules", "PATCH", "/rules", None, {}, False),
    ("POST /sign-in no fields", "POST", "/sign-in", "/sign-in", {}, True),
    ("POST /sign-in unicode and null bytes", "POST", "/sign-in", "/sign-in",
     {"username": "ädmin☃", "password": "\x00\x00",
      "next": "☃"}, True),
)


def fuzz_robustness():
    """Malformed requests to the specification's routes, none answered 500
    and none raising out of the client."""
    stranger = app.test_client()
    answers = []
    for label, method, path, form, body, signed_out in FUZZ:
        who = stranger if signed_out else client
        entry = {"request": label}
        try:
            answer = (form_post(who, form, path, body, method=method)
                      if form else ask(who, method, path, data=body))
            entry["status"] = answer.status_code

            # Signed out, the sign-in's own answer may be its redirect.
            entry["gated"] = not signed_out and gated(
                answer, token=method == "GET" or form is not None)
        except Raised as error:
            entry["raised"] = str(error)
        answers.append(entry)
    asked = [entry["request"] for entry in answers if entry.get("gated")]
    if asked:
        return lost("fuzz_robustness", "%d malformed requests were turned "
                    "away by the sign-in" % len(asked), asked=asked)
    failed = [entry for entry in answers if entry.get("raised")
              or (entry.get("status") or 0) >= 500]
    return passed(not failed, requests=len(answers), failed=failed)


report["signed_in"] = sign_in(client)
if not report["signed_in"] or MODE == "portability":
    try:
        report["index_status"] = ask(client, "GET", "/").status_code
    except Raised as error:
        report["index_error"] = str(error)
    finish()

# Fuzzing comes after the readings a malformed request's leftovers could
# reach, and the concurrent writes come last of all: a writer the build hangs
# outlives its wait, and nothing may run beside it. Where one does, the run
# stops there, the readings before it kept.
PROBES = (("latency_p95_ms", latency_p95_ms), ("n_plus_one", n_plus_one),
          ("capacity_500_lines", capacity_500_lines),
          ("coexistence", coexistence),
          ("fuzz_robustness", fuzz_robustness),
          ("concurrent_writes", concurrent_writes))
for name, probe in PROBES:
    report["running"] = name
    save()
    try:
        report["probes"][name] = probe()
    except Gated as error:
        report["probes"][name] = lost(name, str(error))
    except Raised as error:
        report["probes"][name] = lost(name, "the application raised: %s"
                                      % error)
    except Exception as error:
        key = "value" if name == "latency_p95_ms" else "passed"
        report["probes"][name] = {key: None, "missing": "the reader failed: "
                                  "%s" % repr(error)[:300]}
    if report["probes"][name].get("hung"):
        break
finish()
'''


def lost_reading(name, reason):
    """A probe the trial kept from running: failed, or no latency."""
    if name in MEASURED:
        return {"value": None, "lost": reason}
    return {"passed": False, "lost": reason}


def missing_reading(name, reason):
    """A probe this reader could not run: never zero, never passed."""
    if name in MEASURED:
        return {"value": None, "missing": reason}
    return {"passed": None, "missing": reason}


def probe_results(payload, reason=None, lost=False, stalled=None):
    """Each in-process probe's reading: its own, lost with the trial's
    reason, or missing with ours.

    `reason` is why there is no report, and `lost` says the trial caused it.
    `stalled` is why a run that ran out of time stopped: what it read stands,
    and the probes it did not reach are lost to the application.
    """
    payload = payload or {}
    trial = reason if (reason and lost) else None
    if not reason:
        if "error" in payload:
            trial = "the application would not boot: %s" % payload["error"]
        elif stalled and "signed_in" not in payload:
            trial = stalled
        elif not payload.get("signed_in"):
            trial = ("the seeded administrator could not sign in; the "
                     "sign-in answered %s and / %s"
                     % (payload.get("sign_in_status"),
                        payload.get("home_status")))
    read = payload.get("probes") or {}
    readings = {}
    for name in IN_PROCESS:
        if reason and not lost:
            readings[name] = missing_reading(name, reason)
        elif trial:
            readings[name] = lost_reading(name, trial)
        elif name in read:
            readings[name] = read[name]
        elif stalled:
            readings[name] = lost_reading(name, stalled)
        else:
            readings[name] = missing_reading(
                name, "the in-process probe did not report it")
    return readings


def write_script(where):
    script = os.path.join(where, "quality-probe.py")
    with io.open(script, "w", encoding="utf-8") as handle:
        handle.write(QUALITY_SCRIPT)
    return script


def probe_runtime(python, where, mode="all", env=None, timeout=PROBE_TIMEOUT):
    """Run the in-process probes; answer the report, why there is none, and
    why the run stopped short where it did."""
    script = write_script(where)
    progress = os.path.join(where, "quality-probe-%s.json" % mode)
    if os.path.exists(progress):
        os.remove(progress)
    databases = os.path.abspath(where) + "-databases"
    remove_tree(databases)
    os.makedirs(databases)
    try:
        outcome = run([python, script, mode, progress, databases], cwd=where,
                      env=env, timeout=timeout)
    finally:
        remove_tree(databases)
    payload = None
    if os.path.isfile(progress):
        try:
            with io.open(progress, encoding="utf-8") as handle:
                payload = json.load(handle)
        except ValueError:
            payload = None
    if payload is None:
        return None, ("the quality probe produced no report: %s"
                      % (outcome["failed"] or outcome["stderr"]
                         or outcome["stdout"])[-300:]), None
    stalled = None
    if "running" in payload:
        stalled = ("the run stopped during %s: %s" % (
            payload["running"], outcome["failed"]
            or "the interpreter exited %s" % outcome["status"]))
    return payload, None, stalled


def other_interpreter(commands=OTHER_PYTHON_COMMANDS):
    """The path of the other Python, or None."""
    probe = "import sys; print(sys.executable); print(*sys.version_info[:2])"
    wanted = ["%d" % part for part in OTHER_PYTHON]
    for command in commands:
        program = shutil.which(command[0])
        if program is None:
            continue
        outcome = run([program] + list(command[1:]) + ["-c", probe],
                      timeout=120)
        lines = outcome["stdout"].splitlines()
        if (outcome["failed"] is None and outcome["status"] == 0
                and len(lines) == 2 and lines[1].split() == wanted):
            return lines[0].strip()
    return None


def portability_reading(installed, payload, reason, version):
    """python_portability from the other Python's install and its page.

    On that interpreter the install, the boot and the page are what is
    measured, so their failing fails the probe; only a run that filed no
    report is missing.
    """
    label = "Python %s" % version
    if installed["failed"] or installed["status"] != 0:
        return {"passed": False, "python": version,
                "reason": "the trial did not install on %s: %s" % (
                    label, (installed["stderr"]
                            or installed["stdout"])[-300:])}
    if payload is None:
        return missing_reading("python_portability", reason)
    if "error" in payload:
        return {"passed": False, "python": version,
                "reason": "the application would not boot on %s: %s"
                % (label, payload["error"])}
    if not payload.get("signed_in"):
        return {"passed": False, "python": version,
                "reason": "the administrator could not sign in on %s"
                % label}
    status = payload.get("index_status")
    return {"passed": status == 200, "python": version, "status": status}


def read_portability(tree, where, other):
    """Install the trial on the other Python and serve one signed-in page."""
    if other is None:
        return missing_reading("python_portability", (
            "no Python %d.%d was found" % OTHER_PYTHON))
    venv = os.path.join(where, "venv-other")
    remove_tree(venv)
    try:
        made = run([other, "-m", "venv", venv], timeout=600)
        if made["failed"] or made["status"] != 0:
            return missing_reading("python_portability", (
                "the other Python's environment was not created: %s"
                % (made["stderr"] or made["stdout"])[-300:]))
        version = venv_version(venv)
        installed = pip(venv, "install", tree, cwd=where)
        payload, reason = None, None
        if not installed["failed"] and installed["status"] == 0:
            payload, reason, _ = probe_runtime(python_in(venv), where,
                                               "portability")
        return portability_reading(installed, payload, reason, version)
    finally:

        # About 290 MB, and nothing reads it again.
        remove_tree(venv)


def read_trial(area, name, scores_file, other):
    """Every quality probe on one scored trial, read from its score file."""
    with io.open(scores_file, encoding="utf-8") as handle:
        scores = json.load(handle)
    tree = scores.get("workspace")
    result = {"name": name, "read_at": datetime.datetime.now().isoformat(
        timespec="seconds")}
    where = os.path.join(area, "quality", name)
    os.makedirs(where, exist_ok=True)
    venv = create_venv(os.path.join(where, "venv"))
    try:
        result["python"] = venv_version(venv)
        installed = pip(venv, "install", tree, cwd=where)
        if installed["failed"] or installed["status"] != 0:
            reason = ("the trial did not install: %s"
                      % (installed["stderr"] or installed["stdout"])[-300:])
            probes = probe_results(None, reason, lost=True)
        else:
            payload, reason, stalled = probe_runtime(python_in(venv), where)
            probes = probe_results(payload, reason, stalled=stalled)
    finally:

        # About 290 MB a trial, and nothing reads it again.
        remove_tree(venv)

    # A build the spec's Python could not install, boot or sign in is lost
    # on the other one too: it was never read there.
    trial = next((probe["lost"] for probe in probes.values()
                  if probe.get("lost")), None)
    if trial and all(probe.get("lost") == trial for probe in probes.values()):
        probes["python_portability"] = lost_reading("python_portability",
                                                    trial)
    elif all(probe.get("missing") for probe in probes.values()):
        probes["python_portability"] = missing_reading(
            "python_portability", "the build was not read on the spec's "
            "Python")
    else:
        probes["python_portability"] = read_portability(tree, where, other)
    result["probes"] = {name: probes[name] for name in PROBES}
    return result


# A stand-in application for the in-process probes, importable without
# Flask, on a real SQLite file, so the statement count and the database lock
# are SQLite's own. `sound` passes every probe; each other mode plants the
# fault one probe guards against and nothing else: `fragile` answers 500 on
# a price it cannot parse, `brittle` lets an id it cannot parse raise out of
# the client, `locking` writes without waiting for the lock, `lossy` drops a
# write that overlaps another, `slow` takes 20 ms over every answer,
# `cramped` refuses over 100 lines, `crowded` saves them and will not show
# them, `chatty` reads each invoice line's product on its own, `shared` keeps
# its products in one store for every instance, `stray` writes a fixed file
# outside its folder, `truncating` keeps the first 100 lines of an invoice,
# answering as if it kept them all, `nulling` exports one line as null, and
# `capped` prices the first 100 lines alone wherever it prices them, while
# it keeps and exports all; `unpriced` exports its total as NaN, `free`
# prices every line at nothing, `poisoned` stores a price it cannot then
# list, so its products page answers 500 once fuzzing has stored one, which
# is no fault of any probe's, and `hanging` holds one concurrent write,
# and its lock, for a minute. Every mode opens its database by a `file:` URI
# with a query. `bouncing` answers a price it cannot parse with the
# sign-in's redirect and `forbidding` with a 403;
# `gated` never keeps its sign-in, and `refusing` neither keeps it nor
# redirects, answering 401; `broken` will not boot, and `unportable` boots
# on no Python but the one it names. Every mode's sign-in form quotes its
# attributes with single quotes.
FAKE_APP = '''import decimal
import json
import logging
import os
import pathlib
import sqlite3
import sys
import tempfile
import threading
import time

MODE = "__MODE__"
TOKEN = '<input type="hidden" name="csrf_token" value="t">'
SIGN_IN = "<form><input type='hidden' name='csrf_token' value='t'>"
SIGN_OUT = ('<form method="post" action="/sign-out"><input type="hidden" '
            'name="csrf_token" value="other-token"></form>')


def form_page(path, body):
    """A page whose main form posts to its own route, the builder's to its
    preview, with a sign-out form carrying another token beside it: before
    the main form on the products page, after it everywhere else."""
    action = "/invoices/preview" if path == "/invoices/new" else path
    main = '<form method="post" action="%s">%s</form>' % (action, TOKEN)
    if path == "/products":
        return SIGN_OUT + body + main
    return body + main + SIGN_OUT
SKUS = {"WID-1": "10.00", "GAD-2": "24.50", "BOK-3": "12.00",
        "SRV-4": "80.00", "SEE-5": "3.75"}
LOG = logging.getLogger("tariff")
SHARED = {}
IN_FLIGHT = []
GUARD = threading.Lock()
STRAY = os.path.join(tempfile.gettempdir(), "tariff-quality-stray.log")


class Response(object):
    def __init__(self, status, body="", headers=None):
        self.status_code = status
        self.headers = dict(headers or {})
        self._body = body

    def get_data(self, as_text=False):
        return self._body if as_text else self._body.encode("utf-8")


def listed(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def summed(rows):
    if MODE == "free":
        rows = []
    total = sum((decimal.Decimal(price) * quantity
                 for _, price, quantity in rows), decimal.Decimal("0"))
    return str(total.quantize(decimal.Decimal("0.01")))


def table(rows):
    """The export's total, and the page: each line's sku and quantity, and
    the total, from (sku, unit price, quantity) rows."""
    total = summed(rows[:100] if MODE == "capped" else rows)
    return total, "<table>%s</table><p>Total %s</p>" % ("".join(
        "<tr><td>%s</td><td>%d</td></tr>" % (sku, quantity)
        for sku, _, quantity in rows), total)


def number(text):
    """An id, or None where it is none or would overflow SQLite."""
    if MODE == "brittle":
        return int(text)
    if not text.isdigit() or int(text) > 2 ** 63 - 1:
        return None
    return int(text)


class App(object):
    def __init__(self, database):
        if MODE == "stray":
            with open(STRAY, "a") as handle:
                handle.write("booted\\n")
        self.database = database
        self.products = SHARED if MODE == "shared" else None
        self.connect().executescript(
            "CREATE TABLE IF NOT EXISTS products (sku TEXT PRIMARY KEY, "
            "name TEXT, unit_price TEXT);"
            "CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY);"
            "CREATE TABLE IF NOT EXISTS lines (invoice INTEGER, position "
            "INTEGER, sku TEXT, quantity INTEGER);")
        with self.connect() as connection:
            for sku, price in SKUS.items():
                connection.execute("INSERT OR IGNORE INTO products VALUES "
                                   "(?, ?, ?)", (sku, sku, price))
        self.password = os.environ.get("TARIFF_ADMIN_PASSWORD")
        self.config = {}

    def connect(self, wait=10.0):
        uri = pathlib.Path(self.database).as_uri() + "?mode=rwc"
        return sqlite3.connect(uri, uri=True, timeout=wait)

    def test_client(self):
        return Client(self)

    def prices(self):
        """Every product's price to the cent, which no price past a
        Decimal's precision survives."""
        return [decimal.Decimal(row[0]).quantize(decimal.Decimal("0.01"))
                for row in self.connect().execute(
                    "SELECT unit_price FROM products")]

    def skus(self):
        if self.products is not None:
            return list(SKUS) + list(self.products)
        return [row[0] for row in self.connect().execute(
            "SELECT sku FROM products ORDER BY sku")]

    def add_product(self, sku, name, price):
        if self.products is not None:
            self.products[sku] = (name, price)
            return
        if MODE == "lossy":
            with GUARD:
                if IN_FLIGHT:
                    return
                IN_FLIGHT.append(sku)
            try:
                time.sleep(0.005)
                with self.connect() as connection:
                    connection.execute("INSERT INTO products VALUES "
                                       "(?, ?, ?)", (sku, name, price))
            finally:
                IN_FLIGHT.remove(sku)
            return
        hangs = MODE == "hanging" and sku == "QCW-1-00"
        wait = {"locking": 0, "hanging": 0.1}.get(MODE, 10.0)
        connection = self.connect(10.0 if hangs else wait)
        connection.isolation_level = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("INSERT INTO products VALUES (?, ?, ?)",
                               (sku, name, price))
            time.sleep(60 if hangs else 0.005)
            connection.execute("COMMIT")
        finally:
            if connection.in_transaction:
                connection.execute("ROLLBACK")
            connection.close()


class Client(object):
    def __init__(self, app):
        self.app = app
        self.signed = False

    def get(self, path, **kwargs):
        return self.open(path, method="GET", **kwargs)

    def post(self, path, **kwargs):
        return self.open(path, method="POST", **kwargs)

    def open(self, path, method="GET", data=None, headers=None,
             follow_redirects=False):
        if MODE == "slow":
            time.sleep(0.02)
        try:
            return self.dispatch(path.split("?")[0], method, data or {})
        except Exception:
            if MODE == "brittle":
                raise
            LOG.exception("unhandled")
            return Response(500, "Internal Server Error")

    def dispatch(self, path, method, data):
        if path == "/sign-in":
            if method == "GET":
                return Response(200, SIGN_IN)
            if (data.get("csrf_token") == "t"
                    and data.get("username") == "admin"
                    and data.get("password") == self.app.password):
                self.signed = MODE not in ("gated", "refusing")
                return Response(302, "", {"Location": "/"})
            return Response(200, "wrong username or password" + SIGN_IN)
        if not self.signed and MODE == "refusing":
            return Response(401, "sign in first")
        if not self.signed:
            return Response(302, "", {"Location": "/sign-in"})
        pages = ("/", "/products", "/rules", "/jurisdictions", "/customers",
                 "/invoices/new")
        posts = ("/products", "/rules", "/jurisdictions", "/customers",
                 "/invoices/preview", "/invoices")
        parts = path.strip("/").split("/")
        if method == "GET" and path in pages:
            listing = " ".join(self.app.skus()) if path == "/products" else ""
            if path == "/products" and MODE == "poisoned":
                self.app.prices()
            return Response(200, form_page(path, "<p>%s</p>" % listing))
        if method == "POST" and (path in posts or path.endswith("/delete")
                                 or path.endswith("/erase")):
            if data.get("csrf_token") != "t":
                return Response(400, "missing token")
            if path.endswith("/delete") or path.endswith("/erase"):
                return Response(404, "not found")
            if path == "/products":
                return self.create_product(data)
            if path.startswith("/invoices"):
                return self.invoice(path, data)
            return Response(200, "the form has an error" + TOKEN)
        if method == "GET" and parts[0] in ("invoices", "customers"):
            return self.show(parts)
        if path in pages or path in posts:
            return Response(405, "method not allowed")
        return Response(404, "not found")

    def create_product(self, data):
        sku = data.get("sku") or ""
        name = data.get("name") or ""
        if not sku or not name or len(sku) > 64:
            return Response(200, "sku or name is invalid" + TOKEN)
        if MODE == "fragile":
            price = decimal.Decimal(data.get("unit_price"))
        else:
            try:
                price = decimal.Decimal(data.get("unit_price") or "")
            except decimal.InvalidOperation:
                if MODE == "bouncing":
                    return Response(302, "", {"Location": "/sign-in"})
                if MODE == "forbidding":
                    return Response(403, "forbidden")
                return Response(200, "unit_price is not a number" + TOKEN)
        if not price.is_finite() or price < 0 or (
                price > 10 ** 12 and MODE != "poisoned"):
            return Response(200, "unit_price is out of range" + TOKEN)
        if sku in self.app.skus():
            return Response(200, "sku exists" + TOKEN)
        self.app.add_product(sku, name, str(price))
        return Response(302, "", {"Location": "/products"})

    def invoice(self, path, data):
        skus, quantities = listed(data.get("sku")), listed(
            data.get("quantity"))
        if len(skus) != len(quantities):
            return Response(400, "sku and quantity do not pair")
        known = self.app.skus()
        lines = []
        for sku, quantity in zip(skus, quantities):
            if sku not in known or not quantity.isdigit() or int(
                    quantity) < 1:
                return Response(400, "a line is invalid")
            lines.append((sku, int(quantity)))
        if MODE == "cramped" and len(lines) > 100:
            return Response(413, "too many lines")
        if MODE == "truncating":
            lines = lines[:100]
        if path == "/invoices/preview":
            return Response(200, table([(sku, SKUS.get(sku, "1.00"), quantity)
                                        for sku, quantity in lines])[1])
        if not lines:
            return Response(400, "no lines")
        with self.app.connect() as connection:
            invoice = connection.execute(
                "INSERT INTO invoices DEFAULT VALUES").lastrowid
            connection.executemany(
                "INSERT INTO lines VALUES (?, ?, ?, ?)",
                [(invoice, position, sku, quantity)
                 for position, (sku, quantity) in enumerate(lines)])
        return Response(302, "", {"Location": "/invoices/%d" % invoice})

    def show(self, parts):
        if parts[0] != "invoices" or len(parts) > 2 and parts[2] not in (
                "export.json", "export.csv"):
            return Response(404, "not found")
        invoice = number(parts[1]) if len(parts) > 1 else None
        if invoice is None:
            return Response(404, "not found")
        connection = self.app.connect()
        if not connection.execute("SELECT id FROM invoices WHERE id = ?",
                                  (invoice,)).fetchone():
            return Response(404, "not found")
        if MODE == "chatty":
            rows = []
            for sku, quantity in connection.execute(
                    "SELECT sku, quantity FROM lines WHERE invoice = ? "
                    "ORDER BY position", (invoice,)).fetchall():
                rows.append(connection.execute(
                    "SELECT sku, unit_price FROM products WHERE sku = ?",
                    (sku,)).fetchone() + (quantity,))
        else:
            rows = connection.execute(
                "SELECT sku, unit_price, quantity FROM lines JOIN products "
                "USING (sku) WHERE invoice = ? ORDER BY position",
                (invoice,)).fetchall()
        if MODE == "crowded" and len(rows) > 100:
            return Response(413, "too many lines to show")
        total, shown = table(rows)
        if parts[-1] == "export.json":
            records = [{"sku": sku, "quantity": quantity}
                       for sku, _, quantity in rows]
            if MODE == "nulling" and len(records) > 100:
                records[100] = None
            return Response(200, json.dumps({
                "lines": records,
                "total": "NaN" if MODE == "unpriced" else total}))
        return Response(200, shown)


def create_app(database):
    if MODE == "broken":
        raise RuntimeError("no factory today")
    if MODE == "unportable" and sys.version_info[:2] != (2, 7):
        raise RuntimeError("written for Python 2.7 only")
    return App(database)
'''

FAULTS = {"fragile": "fuzz_robustness", "brittle": "fuzz_robustness",
          "locking": "concurrent_writes", "lossy": "concurrent_writes",
          "cramped": "capacity_500_lines", "crowded": "capacity_500_lines",
          "truncating": "capacity_500_lines",
          "hanging": "concurrent_writes",
          "nulling": "capacity_500_lines", "capped": "capacity_500_lines",
          "unpriced": "capacity_500_lines", "free": "capacity_500_lines",
          "bouncing": "fuzz_robustness",
          "forbidding": "fuzz_robustness", "chatty": "n_plus_one",
          "shared": "coexistence", "stray": "coexistence"}


def fake_readings(scratch, modes, mode_arg="all"):
    """Run the in-process probes against the stand-in in each mode."""
    readings = {}
    for mode in modes:
        where = os.path.join(scratch, "%s-%s" % (mode_arg, mode))
        package = os.path.join(where, "site", "tariff")
        os.makedirs(package)
        with io.open(os.path.join(package, "__init__.py"), "w",
                     encoding="utf-8") as handle:
            handle.write(FAKE_APP.replace("__MODE__", mode))
        env = dict(os.environ, PYTHONPATH=os.path.join(where, "site"),
                   QUALITY_PROBE_WRITE_SECONDS="5")
        readings[mode] = probe_runtime(sys.executable, where, mode_arg,
                                       env=env, timeout=300)
    return readings


def failing(probes):
    """The pass/fail probes a reading fails, in order."""
    return [name for name in IN_PROCESS
            if name not in MEASURED and probes[name].get("passed") is not True]


def runtime_self_checks(scratch):
    """Each planted fault fails its own probe and no other; an app that
    keeps the probes from running loses them."""
    modes = (["sound", "slow", "poisoned", "gated", "refusing", "broken"]
             + sorted(FAULTS))
    readings = fake_readings(scratch, modes)
    probes = {mode: probe_results(*readings[mode]) for mode in modes}
    sound = probes["sound"]
    latency = sound["latency_p95_ms"]
    checks = [
        ("a sound app signs in", (readings["sound"][0] or {}).get(
            "signed_in") is True),
        ("a sign-in form quoted with single quotes signs in",
         (readings["sound"][0] or {}).get("signed_in") is True
         and "type='hidden'" in FAKE_APP),
        ("a sound app passes every probe", failing(sound) == []),
        ("a database opened by a file URI with a query stays in its folder",
         sound["coexistence"].get("passed") is True
         and sound["coexistence"].get("stray") == []
         and '.as_uri() + "?mode=rwc"' in FAKE_APP),
        ("a form's own token is posted, not one from a form before it",
         sound["concurrent_writes"].get("passed") is True
         and sound["coexistence"].get("passed") is True
         and "return SIGN_OUT + body + main" in FAKE_APP),
        ("a post no form's action names carries the page's first token",
         sound["n_plus_one"].get("passed") is True
         and sound["capacity_500_lines"].get("passed") is True
         and "return body + main + SIGN_OUT" in FAKE_APP),
        ("the latency is two repeats of 30 requests each",
         latency.get("requests") == 30
         and len(latency.get("repeats") or []) == 2
         and all(value > 0 for value in latency["repeats"])
         and latency["value"] == max(latency["repeats"])),
        ("a slowed app reads slower by its delay",
         failing(probes["slow"]) == []
         and (probes["slow"]["latency_p95_ms"].get("value") or 0) >= 20
         and probes["slow"]["latency_p95_ms"]["value"] > latency["value"]),
        ("statements are counted per page, and did not grow",
         sound["n_plus_one"].get("one_line", 0) > 0
         and sound["n_plus_one"]["twenty_lines"]
         == sound["n_plus_one"]["one_line"]),
    ]
    labels = {
        "fragile": "an app answering 500 on bad input fails fuzz_robustness",
        "brittle": "an app raising out of the client fails fuzz_robustness",
        "locking": "an app whose writes lock fails concurrent_writes",
        "lossy": "an app dropping an overlapping write fails "
                 "concurrent_writes",
        "cramped": "an app refusing 500 lines fails capacity_500_lines",
        "crowded": "an app that cannot show 500 lines fails "
                   "capacity_500_lines",
        "bouncing": "an app answering a malformed request with the sign-in's "
                    "redirect loses fuzz_robustness",
        "forbidding": "an app answering 403 to a malformed request loses "
                      "fuzz_robustness",
        "truncating": "an app keeping 100 of 500 lines fails "
                      "capacity_500_lines",
        "hanging": "a writer the app hangs fails concurrent_writes",
        "nulling": "an export with a null line fails capacity_500_lines",
        "unpriced": "an export whose total is NaN fails capacity_500_lines",
        "free": "an app pricing every line at nothing fails "
                "capacity_500_lines",
        "capped": "a total over the first 100 of 500 exported lines fails "
                  "capacity_500_lines",
        "chatty": "an app reading each line on its own fails n_plus_one",
        "shared": "instances sharing their data fail coexistence",
        "stray": "an app writing outside its folder fails coexistence",
    }
    for mode, label in sorted(labels.items()):
        checks.append(("%s, and no other probe" % label,
                       failing(probes[mode]) == [FAULTS[mode]]
                       and probes[mode][FAULTS[mode]].get("passed") is False))
    checks.extend([
        ("a product a malformed request stored does not reach the "
         "concurrent writes", failing(probes["poisoned"]) == []),
        ("a hung writer stops the run, every reading before it kept",
         "hung it" in probes["hanging"]["concurrent_writes"].get(
             "reason", "")
         and {name: probe.get("passed")
              for name, probe in probes["hanging"].items()
              if name != "concurrent_writes"}
         == {name: probe.get("passed") for name, probe in sound.items()
             if name != "concurrent_writes"}),
        ("the redirect is read as lost, not as an answer",
         "turned away by the sign-in" in probes["bouncing"][
             "fuzz_robustness"].get("lost", "")),
        ("an app answering 401 until signed in, and never signing in, loses "
         "every probe", all("could not sign in" in probe.get("lost", "")
                            for probe in probes["refusing"].values())),
        ("the locked write is read as locked",
         probes["locking"]["concurrent_writes"].get("locked") is True),
        ("the stray file is named",
         any(path.endswith("tariff-quality-stray.log") for path in
             probes["stray"]["coexistence"].get("stray", []))),
        ("an app that never keeps its sign-in loses every probe, passing "
         "none", all(probe.get("lost") and not probe.get("passed")
                     and probe.get("value") is None
                     for probe in probes["gated"].values())
         and all("could not sign in" in probe["lost"]
                 for probe in probes["gated"].values())),
        ("an app that will not boot loses every probe",
         all("would not boot" in probe.get("lost", "")
             for probe in probes["broken"].values())),
    ])
    stray = os.path.join(tempfile.gettempdir(), "tariff-quality-stray.log")
    if os.path.exists(stray):
        os.remove(stray)
    return checks


def reading_self_checks():
    """A missing report is missing, and a stalled run keeps what it read."""
    no_report = probe_results(None, "the quality probe produced no report")
    stalled = probe_results(
        {"signed_in": True, "running": "n_plus_one",
         "probes": {"latency_p95_ms": {"value": 3.0, "repeats": [3.0, 2.0]}}},
        stalled="the run stopped during n_plus_one: timed out after 900s")
    hung_boot = probe_results({"running": "boot", "probes": {}},
                              stalled="the run stopped during boot")
    return [
        ("no report from the probe is missing, not lost",
         all(probe.get("missing") and probe.get("passed") is None
             and probe.get("value") is None and not probe.get("lost")
             for probe in no_report.values())),
        ("a stalled run keeps what it read and loses the rest",
         stalled["latency_p95_ms"]["value"] == 3.0
         and all("stopped during n_plus_one" in stalled[name].get("lost", "")
                 for name in IN_PROCESS if name != "latency_p95_ms")),
        ("a run that stalled booting loses every probe",
         all("during boot" in probe.get("lost", "")
             for probe in hung_boot.values())),
    ]


def portability_self_checks(scratch):
    """The other Python's install, boot and page decide portability."""
    readings = fake_readings(scratch, ["sound", "unportable", "gated"],
                             "portability")
    good = {"failed": None, "status": 0, "stdout": "", "stderr": ""}
    refused = {"failed": None, "status": 1, "stdout": "",
               "stderr": "ERROR: Package 'tariff' requires a different "
                         "Python: 3.14.0 not in '<3.13,>=3.12'"}

    def reading(mode, installed=good):
        payload, reason, _ = readings[mode]
        return portability_reading(installed, payload, reason, "3.14.0")

    return [
        ("a build that serves its page on the other Python passes "
         "portability", reading("sound")["passed"] is True),
        ("a build that boots on its own Python only fails portability",
         reading("unportable")["passed"] is False
         and "would not boot" in reading("unportable")["reason"]),
        ("a build whose sign-in fails on the other Python fails "
         "portability", reading("gated")["passed"] is False),
        ("a build the other Python will not install fails portability",
         reading("sound", refused)["passed"] is False
         and "did not install" in reading("sound", refused)["reason"]),
        ("no other Python is missing, not passed",
         read_portability(scratch, scratch, None)["passed"] is None
         and "no Python" in read_portability(scratch, scratch,
                                             None)["missing"]),
    ]


def claim_self_checks(scratch):
    """A reading run refuses while another holds the area, and installs
    nothing."""
    root = os.path.join(scratch, "claimed")
    area = scoring_area(root)
    os.makedirs(os.path.join(area, "scores"))
    with io.open(os.path.join(area, "scores", "none-1.json"), "w",
                 encoding="utf-8") as handle:
        handle.write("{}")
    label, refused = claim_refusal_check(SCRIPT, main, root)
    return [(label, refused
             and not os.path.exists(os.path.join(area, "quality")))]


def leftover_self_checks(scratch):
    """A reading leaves no environment behind, and a trial that did not
    install loses every probe, portability too."""
    area = os.path.join(scratch, "leftover")
    tree = os.path.join(area, "tree")
    os.makedirs(tree)
    scores_file = os.path.join(area, "none-1.json")
    with io.open(scores_file, "w", encoding="utf-8") as handle:
        json.dump({"workspace": tree}, handle)
    result = read_trial(area, "none-1", scores_file, None)
    where = os.path.join(area, "quality", "none-1")
    return [
        ("a reading's environment is gone once it is read",
         not os.path.exists(os.path.join(where, "venv"))
         and not os.path.exists(os.path.join(where, "venv-other"))),
        ("a trial that did not install loses every probe",
         sorted(result["probes"]) == sorted(PROBES)
         and all("did not install" in probe.get("lost", "")
                 for probe in result["probes"].values())),
    ]


def self_test():
    """Prove each probe fails the fault it guards against, records missing
    as missing, and that a live run refuses a second."""
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-quality-self-test")
    remove_tree(scratch)
    os.makedirs(scratch)
    checks = (runtime_self_checks(scratch) + reading_self_checks()
              + portability_self_checks(scratch) + claim_self_checks(scratch)
              + leftover_self_checks(scratch))
    for label, ok in checks:
        print("  %-52s %s" % (label, "ok" if ok else "FAILED"))
    remove_tree(scratch)
    passed = sum(1 for _, ok in checks if ok)
    lib.print_verdict(passed == len(checks),
                      "%d/%d self-test checks passed" % (passed, len(checks)))
    return 0 if passed == len(checks) else 1


def existing_file(directory, name):
    """The JSON file a trial's reading is filed under, or None."""
    path = os.path.join(directory, "%s.json" % canonical(name))
    return path if os.path.isfile(path) else None


def parse_args(argv):
    parser = argparse.ArgumentParser(
        description="Read scored efficacy trials for reliability, "
                    "performance and flexibility.")
    parser.add_argument("--root", help="the harness's run root")
    parser.add_argument("--trial", action="append", default=[],
                        help="read only this trial, as none-1; repeatable")
    parser.add_argument("--reread", action="store_true",
                        help="read a trial already read; by default such a "
                             "trial is skipped")
    parser.add_argument("--self-test", action="store_true",
                        help="prove every probe against a planted app; read "
                             "no trial")
    return parser.parse_args(argv)


def main(argv):
    options = parse_args(argv)
    if options.self_test:
        return self_test()
    if not options.root:
        print("--root is required unless --self-test is given")
        return 2

    # A score is filed under its trial's name, read as the arms spell it.
    area = scoring_area(options.root)
    scores = os.path.join(area, "scores")
    scored = {canonical(os.path.splitext(entry)[0]):
              os.path.join(scores, entry)
              for entry in (sorted(os.listdir(scores))
                            if os.path.isdir(scores) else [])
              if entry.endswith(".json")}
    wanted = (sorted(canonical(name) for name in options.trial)
              if options.trial else sorted(scored))
    missing = [name for name in wanted if name not in scored]
    if not scored or missing:
        print("no build score for %s under %s; score.py writes them"
              % (", ".join(missing) or "any trial", area))
        return 2

    # A run clears each trial's environment before rebuilding it, so a second
    # run against the area deletes the one a live run is installing into.
    try:
        claim = claim_area(area, SCRIPT)
    except LiveRunError as error:
        print("refused: %s" % error)
        return 2
    try:
        return read_trials(options, area, scored, wanted)
    finally:
        release_area(claim)


def read_trials(options, area, scored, wanted):
    """Read each wanted trial not read yet; return the exit code."""
    target = os.path.join(area, "quality-scores")
    done = []
    if not options.reread:
        for name in wanted:
            written = existing_file(target, name)
            if written:
                print("%s  already read at %s; --reread to read it again"
                      % (name, written))
                done.append(name)
        wanted = [name for name in wanted if name not in done]
    if not wanted:
        lib.print_verdict(True, "0 trial(s) read, %d already read"
                          % len(done))
        return 0
    other = other_interpreter()
    os.makedirs(target, exist_ok=True)
    for name in wanted:
        print("%s  reading for quality" % name)
        result = read_trial(area, name, scored[name], other)
        with io.open(os.path.join(target, "%s.json" % name), "w",
                     encoding="utf-8") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
        print("  " + ", ".join(
            "%s %s" % (key, shown(probe))
            for key, probe in result["probes"].items()))
    lib.print_verdict(True, "%d trial(s) read, %d already read"
                      % (len(wanted), len(done)))
    return 0


def shown(probe):
    """One probe's reading in a word or a number."""
    if probe.get("missing"):
        return "missing"
    if probe.get("lost"):
        return "lost"
    if "value" in probe:
        return "%s ms" % probe["value"]
    return "passed" if probe["passed"] else "failed"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
