"""Read scored efficacy trials for reliability, performance and flexibility.

Seven probes, each read on the application the trial's factory returns:
fault tolerance under malformed requests, concurrent writes, latency, an
invoice of 500 lines, SQL statements per invoice line, two instances side by
side, and the same build on another Python. Each passes or fails, except the
latency, which is recorded as two repeats of its 95th percentile. A change
task's tree is read on the same probes and on one more, the data upgrade: a
database its fixture seeded, opened by the changed tree with nothing lost.

Each trial is installed into a fresh environment of its own, on the spec's
Python, and read there in one in-process run through the test client. A probe
this reader could not run is missing, never zero; one the trial kept from
running, by not installing, not booting or not signing in its administrator,
is lost, and reads failed.
"""

import argparse
import datetime
import hashlib
import io
import json
import os
import shutil
import sqlite3
import sys
import tarfile
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import lib  # noqa: E402
from harness import (LiveRunError, canonical, claim_area,  # noqa: E402
                     claim_refusal_check, release_area, remove_tree,
                     scoring_area, task_folder)
from score import (create_venv, pip, python_in, run,  # noqa: E402
                   venv_version)

SCRIPT = os.path.basename(__file__)

# The probes, in the order the reading files them. The latency is a measured
# value; every other probe passes or fails.
PROBES = ("fuzz_robustness", "concurrent_writes", "latency_p95_ms",
          "capacity_500_lines", "n_plus_one", "coexistence",
          "python_portability")
MEASURED = ("latency_p95_ms",)

# The probe a change task's tree is read on besides: the database the
# fixture saved, opened by the changed tree with nothing lost.
CHANGE_PROBES = ("data_upgrade",)

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
import builtins, csv, html, io, json, logging, math, os, platform, re, sqlite3
import sys, tempfile, threading, time
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from urllib.parse import parse_qs, urljoin, urlsplit
from urllib.request import url2pathname

PACKAGE = "tariff"
USERNAME = "admin"
PASSWORD = "quality-probe-5b3f-Passphrase"
REDIRECTS = (301, 302, 303, 307, 308)
MODE, PROGRESS, DATABASES = sys.argv[1], sys.argv[2], sys.argv[3]
WORKSPACE = os.path.abspath(os.getcwd())
os.environ["TARIFF_ADMIN_PASSWORD"] = PASSWORD

# The standard library tries its temporary folder with a scratch file the
# first time any code asks for it; asked here, before the watch below, that
# try is not read as the build's write.
tempfile.gettempdir()

real_open = builtins.open
real_os_open = os.open
report = {"python": platform.python_version(), "probes": {},
          "running": "boot"}


SAVING = threading.Lock()


def save():
    """The report so far, replaced whole, so a stalled run leaves a whole
    file behind."""
    with SAVING:
        with real_open(PROGRESS + ".part", "w", encoding="utf-8") as handle:
            json.dump(report, handle)
        os.replace(PROGRESS + ".part", PROGRESS)


def finish():
    report.pop("running", None)
    if "leaked" in report["probes"].get("coexistence", {}):
        settle_coexistence(report["probes"]["coexistence"])
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


# Every file the application opens to write, by name, for the whole run.
# The watch is in place before the package is imported, so a handle opened
# at import and written to later is seen. Every database of every probe sits
# in a folder under the reader's own root, so the workspace and that root
# are the only places a build may write; a database's sidecars, its `-wal`,
# `-shm` and `-journal`, sit beside it. A write anywhere else is filed the
# moment it is seen, so a run killed later cannot lose it.
def note(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        return
    path = os.path.abspath(os.fsdecode(path))
    stray = report.setdefault("stray", [])
    if not inside(path, [DATABASES, WORKSPACE]) and path not in stray:
        stray.append(path)
        save()


real_connect = sqlite3.connect


# A database named by a `file:` URI, as `Path.as_uri()` writes one with
# `uri=True`, is read back to the path it names: its query, such as
# `?mode=rwc`, dropped, its escapes undone, and `/C:/...` read as a drive.
# Opened with `mode=ro`, it is read and never written, so it is no write.
def database_file(target):
    """The file a connection may write, or None for a database in memory
    or one opened read-only."""
    if target.startswith("file:"):
        parts = urlsplit(target)
        mode = parse_qs(parts.query).get("mode", [""])[-1]
        if mode in ("memory", "ro"):
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


# The data upgrade names the database the application opens: the one the
# fixture seeds, and then a copy of it for the changed tree. Every other mode
# starts on an empty one of its own.
try:
    import importlib
    package = importlib.import_module(PACKAGE)
    app = package.create_app(os.environ.get("QUALITY_DATABASE")
                             or os.path.join(folder(), "quality-probe.sqlite"))
    client = app.test_client()
except Exception as error:
    report["error"] = repr(error)[:300]
    finish()


class Gated(Exception):
    """A request the sign-in turned away."""


class Raised(Exception):
    """The application raised out of the test client."""


class Hidden(HTMLParser):
    """Collects every form's action and id, every hidden input and every
    submit control's `formaction`, however their attributes are quoted, in
    page order, each with the form it belongs to."""

    def __init__(self):
        HTMLParser.__init__(self)
        self.forms = []
        self.inputs = []
        self.controls = []
        self.form = None

    def owner(self, attributes):
        """The form a control belongs to: the one its `form` attribute names
        by id, else the one it sits in."""
        named = attributes.get("form")
        return ("id", named) if named else self.form

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        kind = (attributes.get("type") or "").lower()
        if tag == "form":
            self.form = len(self.forms)
            self.forms.append((attributes.get("action") or "",
                               attributes.get("id")))
        elif tag == "input" and kind == "hidden" and attributes.get("name"):
            self.inputs.append((self.owner(attributes), attributes["name"],
                                attributes.get("value") or ""))
        if ((tag == "button" and kind in ("", "submit"))
                or (tag == "input" and kind in ("submit", "image"))) \
                and attributes.get("formaction") is not None:
            self.controls.append((self.owner(attributes),
                                  attributes["formaction"]))

    def handle_endtag(self, tag):
        if tag == "form":
            self.form = None

    def resolved(self, owner):
        """A form's index from an owner, an index or an id."""
        if isinstance(owner, tuple):
            return next((index for index, (_, ident) in enumerate(self.forms)
                         if ident == owner[1]), None)
        return owner


# A page may hold several forms, each with its own token, such as a sign-out
# form beside the one being sent. The fields sent are those of the first form
# that posts to the path posted to: by its action, or by a submit control's
# `formaction`, as the builder's save sends the builder form to `/invoices`;
# a control outside the form, linked by its `form` attribute, counts too.
# Each is read as the browser resolves it, its query ignored, an empty one
# being the page's own path. A post no form sends takes every hidden field
# on the page, the first of each name.
def hidden_fields(text, page_path, target):
    """The hidden fields a post to `target` carries from the page at
    `page_path`."""
    parser = Hidden()
    parser.feed(text)
    base = "http://localhost" + page_path
    wanted = urlsplit(target).path

    def path_of(address):
        return urlsplit(urljoin(base, address or page_path)).path

    for form, (action, _) in enumerate(parser.forms):
        sends = {path_of(action)} | {
            path_of(address) for owner, address in parser.controls
            if parser.resolved(owner) == form}
        if wanted in sends:
            fields = {}
            for owner, name, value in parser.inputs:
                if parser.resolved(owner) == form:
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
    return location(response) == "/sign-in"


# A redirect may name its target relative to the request, as `invoices/1`
# after a post to `/invoices`; it is resolved against the path the answer
# was asked on, as a browser resolves it.
def location(response):
    """The path a redirect sends to, resolved against its request's."""
    asked = getattr(response, "asked_path", None) or "/"
    return urlsplit(urljoin("http://localhost" + asked,
                            response.headers.get("Location", ""))).path


def ask(who, method, path, data=None, headers=None):
    try:
        answer = who.open(path, method=method, data=data,
                          headers=headers or {})
    except Exception as error:
        raise Raised(repr(error)[:300])
    answer.asked_path = urlsplit(path).path
    return answer


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
    path = location(answer)
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
    answer = page(client, path + "/export.json")
    if not ok(answer):
        return None, ("the saved invoice's JSON export answered %d"
                      % answer.status_code)
    try:
        export = json.loads(answer.get_data(as_text=True))
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


PRODUCT = {"sku": "QCO-1", "name": "Coexistence probe", "unit_price": "2.00",
           "tax_category": "standard"}


def coexistence():
    """Two instances, each on its own database: a write through one stays
    out of the other, and neither writes outside its folder or the
    workspace."""

    folders_given = [folder(), folder()]
    try:
        first, second = [
            package.create_app(os.path.join(where, "coexist.sqlite"))
            for where in folders_given]
    except Exception as error:
        return passed(False, reason="a second instance would not boot: "
                      "%s" % repr(error)[:300])
    one, other = first.test_client(), second.test_client()
    if not (sign_in(one) and sign_in(other)):
        return lost("coexistence", "an instance's administrator could not "
                    "sign in")
    held(form_post(one, "/products", "/products", PRODUCT),
         "the product's post")
    listed, other_listed = page(one, "/products"), page(other, "/products")

    # A list that does not answer cannot show the product, so its absence
    # there says nothing about isolation.
    if not (ok(listed) and ok(other_listed)):
        return passed(False, reason=(
            "the instances' product lists answered %d and %d, so neither's "
            "contents could be read" % (listed.status_code,
                                        other_listed.status_code)))
    stored = PRODUCT["sku"] in listed.get_data(as_text=True)
    leaked = PRODUCT["sku"] in other_listed.get_data(as_text=True)
    if not stored:
        return lost("coexistence", "the product written through the first "
                    "instance was not stored")
    return settle_coexistence({"leaked": leaked})


def settle_coexistence(reading):
    """The co-existence reading with every write outside the places a build
    may write, so far."""
    stray = report.get("stray") or []
    reading["stray"] = sorted(stray)[:10]
    reading["passed"] = not reading["leaked"] and not stray
    return reading


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


# Each case is sent to an instance of its own, on a fresh database and
# signed in afresh, so no case meets what another stored. A case sent with
# its form's token needs that form first: a form page that does not answer
# 200 gives no token, and a refusal for want of one would read as handled,
# so the case fails as its form not reached. A case sent without a token on
# purpose fetches no form.
def fuzz_case(method, path, form, body, signed_out):
    """One malformed request's outcome, on a fresh instance."""
    entry = {}
    try:
        own = package.create_app(os.path.join(folder(), "fuzz.sqlite"))
    except Exception as error:
        entry["reason"] = "a fresh instance would not boot: %s" % (
            repr(error)[:200])
        return entry
    who = own.test_client()
    if not signed_out and not sign_in(who):
        entry["gated"] = True
        return entry
    try:
        data = body
        if form:
            sent_from = ask(who, "GET", form)
            if not signed_out and gated(sent_from):
                entry["gated"] = True
                return entry
            if sent_from.status_code != 200:
                entry["reason"] = ("the form could not be reached: %s "
                                   "answered %d"
                                   % (form, sent_from.status_code))
                return entry
            data = dict(body)
            for name, value in hidden_fields(
                    sent_from.get_data(as_text=True), form, path).items():
                data.setdefault(name, value)
        answer = ask(who, method, path, data=data)
        entry["status"] = answer.status_code

        # Signed out, the sign-in's own answer may be its redirect.
        entry["gated"] = not signed_out and gated(
            answer, token=method == "GET" or form is not None)
    except Raised as error:
        entry["raised"] = str(error)
    return entry


def fuzz_robustness():
    """Malformed requests to the specification's routes, each reaching
    its route, none answered 500 and none raising out of the client."""
    answers = []
    for label, method, path, form, body, signed_out in FUZZ:
        entry = {"request": label}
        entry.update(fuzz_case(method, path, form, body, signed_out))
        answers.append(entry)
    asked = [entry["request"] for entry in answers if entry.get("gated")]
    if asked:
        return lost("fuzz_robustness", "%d malformed requests were turned "
                    "away by the sign-in" % len(asked), asked=asked)
    failed = [entry for entry in answers if entry.get("raised")
              or entry.get("reason") or (entry.get("status") or 0) >= 500]
    return passed(not failed, requests=len(answers), failed=failed,
                  statuses=[entry.get("status") for entry in answers])


# An amount as a page may write it, which the data upgrade reads an old
# invoice's price back by: grouped by thousands with a comma, a point, a
# space, a no-break or narrow no-break space, or an apostrophe, and two
# decimals after a point or a comma. The page is read with its character
# references resolved, so `&nbsp;` and `&#8239;` group as the characters do.
AMOUNT = re.compile(r"(?<![\d.,])(\d{1,3}(?:[,.\u00a0\u202f' ]\d{3})+"
                    r"|\d+)[.,](\d{2})(?!\d)")


def shows_total(answer, total, tolerance=Decimal("0")):
    """Whether a page shows an amount within `tolerance` of `total`, however
    it is grouped and whatever currency sign stands beside it."""
    return any(abs(Decimal(re.sub(r"\D", "", whole) + "." + cents) - total)
               <= tolerance for whole, cents in AMOUNT.findall(
                   html.unescape(answer.get_data(as_text=True))))


# What the data upgrade seeds through the fixture's own application: a
# product of each rated category, a customer, a rule of three kinds over the
# new products, a jurisdiction of its own, and invoices that read all of
# them, one billed to the customer and one on the seed's own data.
UPGRADE_PRODUCTS = (
    {"sku": "UPG-1", "name": "Upgrade lamp", "unit_price": "7.50",
     "tax_category": "standard"},
    {"sku": "UPG-2", "name": "Upgrade manual", "unit_price": "15.00",
     "tax_category": "reduced"})
UPGRADE_CUSTOMER = {"name": "Ada Upgrade", "email": "ada.upgrade@example.test",
                    "address": "1 Upgrade Street\n10115 Berlin"}
UPGRADE_RULES = (
    {"rule_id": "u-pct-lamp", "kind": "percentage", "sku": "UPG-1",
     "percent": "12"},
    {"rule_id": "u-bulk-manual", "kind": "bulk", "sku": "UPG-2", "buy": "3",
     "pay": "2"},
    {"rule_id": "u-coupon", "kind": "coupon", "sku": "", "code": "UPGRADE",
     "amount": "5.00"})
UPGRADE_JURISDICTION = {"code": "UP", "name": "Upgradia",
                        "default_rate": "0.2",
                        "rates": "standard=0.2,reduced=0.05"}
CUSTOMER_LINK = re.compile(r"/customers/(\d+)(?![\d/])")


def upgrade_body(jurisdiction, customer, lines, coupons):
    return {"jurisdiction": jurisdiction, "currency": "EUR",
            "customer": customer, "coupon_codes": coupons,
            "sku": [sku for sku, _ in lines],
            "quantity": [str(quantity) for _, quantity in lines]}


def text_of(answer):
    return html.unescape(answer.get_data(as_text=True))


def created(path, body):
    """Post one record through its form; Gated where it is turned away."""
    answer = held(form_post(client, path, path, body), "the post to " + path)
    return answer.status_code


def customer_id(email):
    """The id the customer list links to for `email`, read from each linked
    customer's export."""
    for found in sorted(set(CUSTOMER_LINK.findall(
            text_of(page(client, "/customers")))), key=int):
        try:
            export = json.loads(page(client, "/customers/%s/export.json"
                                     % found).get_data(as_text=True))
        except ValueError:
            continue
        if isinstance(export, dict) and export.get("email") == email:
            return found
    return None


def listed_on():
    """What each list page must show of the records seeded."""
    return {
        "/products": [value for item in UPGRADE_PRODUCTS
                      for value in (item["sku"], item["name"])],
        "/customers": [UPGRADE_CUSTOMER["name"], UPGRADE_CUSTOMER["email"]],
        "/rules": [item["rule_id"] for item in UPGRADE_RULES],
        "/jurisdictions": [UPGRADE_JURISDICTION["code"],
                           UPGRADE_JURISDICTION["name"]]}


def invoice_reading(path):
    """A saved invoice as other software reads it: its page's status, its
    JSON export parsed, and its CSV export's text."""
    shown = page(client, path)
    export = page(client, path + "/export.json")
    csv_text = page(client, path + "/export.csv")
    try:
        parsed = json.loads(export.get_data(as_text=True))
    except ValueError:
        parsed = None
    return {"status": shown.status_code, "export_status": export.status_code,
            "export": parsed, "csv_status": csv_text.status_code,
            "csv": csv_text.get_data(as_text=True)}


# The kinds of element a page may write a record's row as, outermost first:
# a page is read by the first kind it holds, so a paragraph inside a table
# cell stays part of its row.
ROW_KINDS = ("tr", "li", "p")
ROW_TAG = re.compile(r"<(tr|li|p)\b", re.IGNORECASE)

# What a row's text is split into whole values on: white space and the
# separators a page writes a list in, so `standard=0.2` stays one value.
TOKEN_SPLIT = re.compile(r"[\s,;|]+")


class Rows(HTMLParser):
    """The text of each outermost `kind` element on a page, every tag inside
    it included, a `kind` nested inside it part of it."""

    def __init__(self, kind):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.kind, self.depth, self.rows = kind, 0, []

    def handle_starttag(self, tag, attrs):
        if tag == self.kind:
            if not self.depth:
                self.rows.append([])
            self.depth += 1
        if self.depth:
            self.rows[-1].append(" ")

    def handle_endtag(self, tag):
        if self.depth:
            self.rows[-1].append(" ")
        if tag == self.kind and self.depth:
            self.depth -= 1

    def handle_data(self, data):
        if self.depth:
            self.rows[-1].append(data)


def row_tokens(text, key):
    """The whole values the first row a page shows `key` in writes, in
    order, a row being the outermost of a table row, a list item or a
    paragraph the page holds, however its cells are marked up; None where
    no row shows it."""
    present = {tag.lower() for tag in ROW_TAG.findall(text)}
    kind = next((kind for kind in ROW_KINDS if kind in present), None)
    if kind is None:
        return None
    parser = Rows(kind)
    parser.feed(text)
    parser.close()
    for row in parser.rows:
        tokens = [token for token in TOKEN_SPLIT.split("".join(row)) if token]
        if key in tokens:
            return tokens
    return None


def row_keys():
    """The value each seeded record's row is found by, on each list page."""
    return {
        "/products": [item["sku"] for item in UPGRADE_PRODUCTS],
        "/customers": [UPGRADE_CUSTOMER["email"]],
        "/rules": [item["rule_id"] for item in UPGRADE_RULES],
        "/jurisdictions": [UPGRADE_JURISDICTION["code"]]}


def shown_rows():
    """Every seeded record's row as its list page shows it: each field the
    page writes, its price, rate or kind among them, by page and key."""
    rows = {}
    for path, keys in row_keys().items():
        text = page(client, path).get_data(as_text=True)
        rows[path] = {key: row_tokens(text, key) for key in keys}
    return rows


def seed_upgrade():
    """Seed the records through the fixture's forms and read each back as
    the fixture shows it; the readings, or why the fixture could not."""
    for item in UPGRADE_PRODUCTS:
        created("/products", item)
    created("/customers", UPGRADE_CUSTOMER)
    for item in UPGRADE_RULES:
        created("/rules", item)
    created("/jurisdictions", UPGRADE_JURISDICTION)
    customer = customer_id(UPGRADE_CUSTOMER["email"])
    if customer is None:
        return None, "the seeded customer is not listed with its export"
    bodies = (upgrade_body("UP", customer, (("UPG-1", 3), ("UPG-2", 4)),
                           "UPGRADE"),
              upgrade_body("DE", "", WORKED, "WELCOME"))
    invoices = []
    for body in bodies:
        answer = held(form_post(client, "/invoices/new", "/invoices", body),
                      "the save")
        path = saved_page(answer)
        if path is None:
            return None, "an invoice was not saved: it answered %d" % (
                answer.status_code)
        reading = invoice_reading(path)
        if not (200 <= reading["status"] < 300
                and 200 <= reading["export_status"] < 300
                and isinstance(reading["export"], dict)
                and 200 <= reading["csv_status"] < 300):
            return None, "the fixture does not show the invoice it saved"
        preview = held(form_post(client, "/invoices/new",
                                 "/invoices/preview", body,
                                 headers={"HX-Request": "true"}),
                       "the preview")
        try:
            total = Decimal(str(reading["export"].get("total")))
        except InvalidOperation:
            total = None

        # A preview is read against the old total only where the fixture's
        # own preview shows it.
        reading.update(body=body, path=path,
                       total=None if total is None else str(total),
                       previewed=bool(total is not None and ok(preview)
                                      and shows_total(preview, total)))
        invoices.append(reading)
    pages = listed_on()
    for path, values in pages.items():
        shown = text_of(page(client, path))
        missing = [value for value in values if value not in shown]
        if missing:
            return None, "%s does not list %s" % (path, missing[0])
    export = page(client, "/customers/%s/export.json" % customer)
    if not ok(export):
        return None, "the seeded customer's export answered %d" % (
            export.status_code)
    try:
        customer_export = json.loads(export.get_data(as_text=True))
    except ValueError:
        return None, "the seeded customer's export is not JSON"
    return {"invoices": invoices, "pages": pages, "rows": shown_rows(),
            "customer": {"id": customer, "export": customer_export}}, None


# A currency a page may write before an amount, as a sign or a code.
CURRENCY = re.compile(r"^(?:€|\$|£|EUR|USD|GBP)\s*", re.IGNORECASE)


def same_token(old, new):
    """Whether a value a page wrote reads as another: equal as text, or as
    amounts once a leading currency is set aside, `50.00` as `€50`; a
    `key=value` reads so only with the same key and a value that does."""
    if old == new:
        return True
    if "=" in old and "=" in new:
        old_key, _, old_value = old.partition("=")
        new_key, _, new_value = new.partition("=")
        return old_key == new_key and same_token(old_value, new_value)
    try:
        return Decimal(CURRENCY.sub("", old)) == Decimal(CURRENCY.sub("", new))
    except (InvalidOperation, ValueError):
        return False


def has_token(tokens, wanted):
    """Whether a row's values hold one that reads as `wanted`."""
    return any(same_token(wanted, token) for token in tokens)


def unkept(old, new, where="$"):
    """The first place `new` no longer holds what `old` did, or None: every
    key `old` had with the same value, a list as long, item by item. A key
    only `new` has is the change's own, and is no loss."""
    if isinstance(old, dict):
        if not isinstance(new, dict):
            return where
        for key, value in old.items():
            if key not in new:
                return "%s.%s" % (where, key)
            found = unkept(value, new[key], "%s.%s" % (where, key))
            if found:
                return found
        return None
    if isinstance(old, list):
        if not isinstance(new, list) or len(new) != len(old):
            return where
        for index, (before, after) in enumerate(zip(old, new)):
            found = unkept(before, after, "%s[%d]" % (where, index))
            if found:
                return found
        return None
    return None if old == new else where


def csv_unkept(old, new):
    """Where a CSV export no longer holds an old column's values, or None.
    A column only the new export has is the change's own."""
    before = list(csv.DictReader(io.StringIO(old)))
    after = list(csv.DictReader(io.StringIO(new)))
    if len(before) != len(after):
        return "it holds %d rows, not %d" % (len(after), len(before))
    for index, (row, now) in enumerate(zip(before, after)):
        for column, value in row.items():
            if now.get(column) != value:
                return "row %d's %s reads %r, not %r" % (
                    index + 1, column, now.get(column), value)
    return None


def data_upgrade(seeded):
    """The changed tree on a copy of the fixture's database: every record
    seeded is still there and reads the same, every old invoice opens and
    prices as it did, and the upgraded database takes new records."""
    failures, unfound = [], []
    for path, values in seeded["pages"].items():
        answer = page(client, path)
        shown = text_of(answer)
        if not ok(answer):
            failures.append("%s answered %d" % (path, answer.status_code))
            continue
        failures += ["%s no longer lists %s" % (path, value)
                     for value in values if value not in shown]

        # Each value the fixture's page wrote of a seeded record, its price
        # or rate as much as its name, still shows whole in that record's
        # row, never only inside a longer one; a value the change adds is
        # its own, and is no loss.
        # A row neither page marks so it can be found by its key leaves the
        # values unread, never kept; a key gone from the page is a loss, as
        # the listing above reads it.
        text = answer.get_data(as_text=True)
        for key, tokens in (seeded.get("rows") or {}).get(path, {}).items():
            now = row_tokens(text, key)
            if tokens is None or (now is None and key in shown):
                unfound.append(key)
                continue
            if now is None:
                continue
            failures += ["%s no longer shows %r for %s" % (path, token, key)
                         for token in tokens if not has_token(now, token)]
    for old in seeded["invoices"]:
        now = invoice_reading(old["path"])
        if not 200 <= now["status"] < 300:
            failures.append("%s answered %d" % (old["path"], now["status"]))
            continue
        # An export is read only where it answers as a success; a body
        # served with an error is no export, whatever it holds.
        if not 200 <= now["export_status"] < 300:
            failures.append("%s/export.json answered %d" % (
                old["path"], now["export_status"]))
        else:
            place = unkept(old["export"], now["export"])
            if place:
                failures.append("%s/export.json no longer reads the same at "
                                "%s" % (old["path"], place))
        if not 200 <= now["csv_status"] < 300:
            failures.append("%s/export.csv answered %d" % (
                old["path"], now["csv_status"]))
        else:
            place = csv_unkept(old["csv"], now["csv"])
            if place:
                failures.append("%s/export.csv: %s" % (old["path"], place))
        if old["previewed"]:
            preview = held(form_post(client, "/invoices/new",
                                     "/invoices/preview", old["body"],
                                     headers={"HX-Request": "true"}),
                           "the preview")
            if not (ok(preview) and shows_total(preview,
                                                Decimal(old["total"]))):
                failures.append("the old invoice %s no longer prices at %s"
                                % (old["path"], old["total"]))
    customer = seeded["customer"]
    answer = page(client, "/customers/%s/export.json" % customer["id"])
    try:
        export = json.loads(answer.get_data(as_text=True))
    except ValueError:
        export = None
    place = unkept(customer["export"], export)
    if not ok(answer):
        failures.append("the customer's export answered %d"
                        % answer.status_code)
    elif place:
        failures.append("the customer's export no longer reads the same at %s"
                        % place)

    # The new schema has to take new rows on the old file too, not only read
    # the old ones: a column added for new tables alone fails here. The old
    # invoice is saved again first, before a new rule can reprice it.
    saved = saved_page(held(form_post(client, "/invoices/new", "/invoices",
                                      seeded["invoices"][0]["body"]),
                            "the save"))
    if saved is None:
        failures.append("an invoice saved after the upgrade has no page")
    else:
        again = invoice_reading(saved)
        total = (again["export"] or {}).get("total") if isinstance(
            again["export"], dict) else None
        if str(total) != str(seeded["invoices"][0]["export"].get("total")):
            failures.append("the first invoice saved again totals %r, not %r"
                            % (total, seeded["invoices"][0]["export"].get(
                                "total")))
    written = (("/jurisdictions", "code", {
        "code": "U2", "name": "Upgradia Nova", "default_rate": "0.1",
        "rates": "standard=0.1"}, ()),
        ("/rules", "rule_id", {"rule_id": "u-pct-after",
                               "kind": "percentage", "sku": "UPG-2",
                               "percent": "3"}, ()),

        # And through the fields the change added, which a schema changed
        # for new files alone refuses on an old one, or drops. Each must be
        # read back whole in the record's row, as any of the ways a page
        # may write it.
        ("/jurisdictions", "code", {
            "code": "U3", "name": "Upgradia Capped", "default_rate": "0.2",
            "rates": "standard=0.2,reduced=0.05", "caps": "reduced=50.00"},
         ("reduced=50.00", "50.00")),
        ("/rules", "rule_id", {"rule_id": "u-threshold",
                               "kind": "threshold", "sku": "",
                               "percent": "5", "minimum": "200.00"},
         ("200.00",)))
    for path, key, body, shown_as in written:
        created(path, body)
        text = text_of(page(client, path))
        if body[key] not in text:
            failures.append("a record posted to %s after the upgrade is not "
                            "listed" % path)
            continue
        if not shown_as:
            continue
        tokens = row_tokens(page(client, path).get_data(as_text=True),
                            body[key])
        if tokens is None:
            unfound.append(body[key])
        elif not any(has_token(tokens, token) for token in shown_as):
            failures.append("%s lists %s without the %s it was posted with"
                            % (path, body[key], shown_as[0]))
    if not failures and unfound:
        return {"passed": None,
                "missing": "row for %s not found" % unfound[0]}
    return passed(not failures, failures=failures[:20])


report["signed_in"] = sign_in(client)
if not report["signed_in"] or MODE == "portability":
    try:
        report["index_status"] = ask(client, "GET", "/").status_code
    except Raised as error:
        report["index_error"] = str(error)
    finish()

# The data upgrade's two halves each run alone: the fixture seeds and reads
# back, and the changed tree reads the copy of what it seeded.
if MODE in ("seed", "upgrade"):
    report["running"] = MODE
    save()
    try:
        if MODE == "seed":
            report["seeded"], report["seed_error"] = seed_upgrade()
        else:
            with real_open(os.environ["QUALITY_SEEDED"],
                           encoding="utf-8") as handle:
                report["probes"]["data_upgrade"] = data_upgrade(
                    json.load(handle))
    except Gated as error:
        report["gated"] = str(error)
    except Raised as error:
        report["raised"] = str(error)
    except Exception as error:
        report["reader_error"] = repr(error)[:300]
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


# The stray writes are filed apart from the probe that reads them, so a run
# killed after one keeps it; the reader folds them into co-existence again.
def stray_read(reading, stray):
    """A co-existence reading with `stray` writes counted against it."""
    reading["stray"] = sorted(stray)[:10]
    reading["passed"] = not reading["leaked"] and not stray
    return reading


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
    if payload.get("stray") and "leaked" in readings["coexistence"]:
        stray_read(readings["coexistence"], payload["stray"])
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


def read_trial(area, name, scores_file, other, task="build"):
    """Every quality probe on one scored trial of `task`, read from its score
    file; a change task's adds the data upgrade."""
    with io.open(scores_file, encoding="utf-8") as handle:
        scores = json.load(handle)
    tree = scores.get("workspace")
    result = {"name": name, "read_at": datetime.datetime.now().isoformat(
        timespec="seconds")}

    # An archived round drops its extracted trees. With no tree there is
    # nothing to install, which is no fault of the build's, so nothing is
    # measured; the tree is not restored here.
    if not tree or not os.path.isdir(tree):
        reason = "source tree not present: %s" % tree
        result["probes"] = {probe: missing_reading(probe, reason)
                            for probe in PROBES + (
                                CHANGE_PROBES if task == "change" else ())}
        return result
    where = os.path.join(area, task_folder("quality", task), name)
    os.makedirs(where, exist_ok=True)

    # The fixture seeds first, in an environment of its own that is gone
    # before the changed tree's is made.
    seeded = reason = None
    if task == "change":
        seeded, reason = seed_fixture(scores, where)
    upgrade = None
    venv = create_venv(os.path.join(where, "venv"))
    try:
        result["python"] = venv_version(venv)
        installed = pip(venv, "install", tree, cwd=where)
        if installed["failed"] or installed["status"] != 0:
            reason_lost = ("the trial did not install: %s"
                           % (installed["stderr"]
                              or installed["stdout"])[-300:])
            probes = probe_results(None, reason_lost, lost=True)
            if task == "change" and seeded:
                upgrade = dict(lost_reading("data_upgrade", reason_lost),
                               **provenance(scores, seeded))
        else:
            payload, why, stalled = probe_runtime(python_in(venv), where)
            probes = probe_results(payload, why, stalled=stalled)
            if task == "change" and seeded:
                upgrade = upgrade_with(python_in(venv), where, seeded,
                                       dict(os.environ),
                                       provenance(scores, seeded))
    finally:

        # About 290 MB a trial, and nothing reads it again.
        remove_tree(venv)
    if task == "change" and upgrade is None:
        upgrade = dict(missing_reading("data_upgrade", reason),
                       **provenance(scores, None))

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
    if task == "change":
        result["probes"]["data_upgrade"] = upgrade
    return result


def fixture_tree(scores, where):
    """The tree the change task started from, out of the changed tree's own
    history: its starting commit, as the agent was handed it."""
    tree, base = scores.get("workspace"), scores.get("base")
    if not base:
        return None, "the change names no starting commit"
    target = os.path.join(where, "fixture")
    remove_tree(target)
    os.makedirs(target)
    archive = os.path.join(os.path.abspath(where), "fixture.tar")
    made = run(["git", "-C", tree, "archive", "--format=tar", "-o", archive,
                base], timeout=300)
    if made["failed"] or made["status"] != 0:
        return None, ("git could not read the starting commit %s: %s"
                      % (base, (made["failed"] or made["stderr"])[-300:]))
    with tarfile.open(archive) as handle:
        handle.extractall(target, filter="data")
    os.remove(archive)
    return target, None


def folder_digest(folder):
    """The sha256 over a folder's files, by name and content."""
    digest = hashlib.sha256()
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if os.path.isfile(path):
            digest.update(name.encode("utf-8") + b"\0")
            with io.open(path, "rb") as handle:
                digest.update(handle.read())
    return digest.hexdigest()


def seed_fixture(scores, where):
    """Seed a database through the fixture's own application, installed on
    the spec's Python; the seeding, or None and why it is missing."""
    tree, reason = fixture_tree(scores, where)
    if reason:
        return None, reason
    venv = create_venv(os.path.join(where, "venv-fixture"))
    try:
        installed = pip(venv, "install", tree, cwd=where)
        if installed["failed"] or installed["status"] != 0:
            return None, ("the fixture did not install: %s"
                          % (installed["stderr"]
                             or installed["stdout"])[-300:])
        return seed_with(python_in(venv), where, dict(os.environ))
    finally:

        # The fixture's environment, as large as the trial's, is not read
        # again once it has seeded.
        remove_tree(venv)
        remove_tree(tree)


# Where the fixture's database is seeded, and where the changed tree's copy
# of it is, each a folder of its own so a database's sidecars go with it.
SEEDED, UPGRADED, DATABASE = "seeded", "upgraded", "upgrade.sqlite"


def seed_with(python, where, env):
    """Seed through the application `python` imports; the seeding, or None
    and why. A fixture that cannot seed leaves the upgrade unread, never
    failed: it is no arm's."""
    folder = os.path.join(where, SEEDED)
    remove_tree(folder)
    os.makedirs(folder)
    env = dict(env, QUALITY_DATABASE=os.path.join(folder, DATABASE))
    payload, reason, stalled = probe_runtime(python, where, "seed", env=env)
    if reason:
        return None, reason
    if "error" in payload:
        return None, "the fixture would not boot: %s" % payload["error"]
    if not payload.get("signed_in"):
        return None, "the fixture's administrator could not sign in"
    if not payload.get("seeded"):
        return None, "the fixture could not be seeded: %s" % (
            payload.get("seed_error") or payload.get("gated")
            or payload.get("raised") or payload.get("reader_error")
            or stalled)
    readings = os.path.join(where, "seeded.json")
    with io.open(readings, "w", encoding="utf-8") as handle:
        json.dump(payload["seeded"], handle, indent=2, sort_keys=True)
    return {"folder": folder, "readings": readings,
            "sha256": folder_digest(folder),
            "python": payload.get("python")}, None


def provenance(scores, seeded):
    """What a data upgrade was read against: the fixture by its hash, the
    commit the change started from, and the database it seeded."""
    fixture = scores.get("fixture") or {}
    return {"fixture": fixture.get("trial"),
            "fixture_sha256": fixture.get("sha256"),
            "base": scores.get("base"),
            "seeded_sha256": (seeded or {}).get("sha256")}


def upgrade_with(python, where, seeded, env, origin):
    """The changed tree, as `python` imports it, on a copy of the seeded
    database: the data upgrade's reading, beside where it came from."""
    copy = os.path.join(where, UPGRADED)
    remove_tree(copy)
    shutil.copytree(seeded["folder"], copy)
    env = dict(env, QUALITY_DATABASE=os.path.join(copy, DATABASE),
               QUALITY_SEEDED=seeded["readings"])
    payload, reason, stalled = probe_runtime(python, where, "upgrade",
                                             env=env)
    if reason:
        return dict(missing_reading("data_upgrade", reason), **origin)

    # A changed tree that will not open, sign in on or answer from the
    # database its fixture saved has lost that data to its users.
    if "error" in payload:
        return dict(lost_reading("data_upgrade", (
            "the changed tree would not open the fixture's database: %s"
            % payload["error"])), **origin)
    if not payload.get("signed_in"):
        return dict(lost_reading("data_upgrade", (
            "the administrator could not sign in on the fixture's "
            "database")), **origin)
    probe = (payload.get("probes") or {}).get("data_upgrade")
    if probe is not None:
        return dict(probe, **origin)
    trouble = payload.get("gated") or payload.get("raised") or stalled
    if trouble:
        return dict(lost_reading("data_upgrade", trouble), **origin)
    return dict(missing_reading("data_upgrade", payload.get(
        "reader_error") or "the upgrade did not report"), **origin)


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
# outside its folder through a handle opened at import, `truncating` keeps
# the first 100 lines of an invoice, answering as if it kept them all,
# `nulling` exports one line as null, `capped` prices the first 100 lines
# alone wherever it prices them while it keeps and exports all, `unpriced`
# exports its total as NaN, `free` prices every line at nothing,
# `unexported` answers its export with a 500 and the JSON all the same,
# `unformed` answers 500 on its rules page, `unlisted` answers 500 on the
# product list of the third instance made, the second co-existence's, and
# `hanging` holds one concurrent write, and its lock, for a minute;
# `late-stray` writes outside on its first malformed request, then hangs.
# `reader` reads a database outside its folder, opened read-only, and
# `relative` answers a save with a location relative to `/invoices`, which
# are no faults.
# `poisoned` stores a price it cannot then list, so its products page
# answers 500 once fuzzing has stored one, which is no fault of any probe's;
# `detached` and `plain-save` place the builder's save control and the
# sign-out form otherwise, which is none either. Every mode opens its
# database by a `file:` URI with a query, and puts a sign-out form carrying
# another token on its pages. `bouncing`
# answers a price it cannot parse with the sign-in's redirect and
# `forbidding` with a 403; `gated` never keeps its sign-in, and `refusing`
# neither keeps it nor redirects, answering 401; `broken` will not boot, and
# `unportable` boots on no Python but the one it names. Every mode's sign-in
# form quotes its attributes with single quotes.
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
    preview with a save control sending it to `/invoices`, and a sign-out
    form carrying another token before it. `plain-save` has no save control
    and puts the sign-out form after; `detached` puts the save control
    after the builder form, linked to it by its id."""
    action = "/invoices/preview" if path == "/invoices/new" else path
    save = control = ""
    if path == "/invoices/new" and MODE == "detached":
        control = ('<button form="builder" formaction="/invoices">Save'
                   '</button>')
    elif path == "/invoices/new" and MODE != "plain-save":
        save = '<button type="submit" formaction="/invoices">Save</button>'
    main = ('<form id="builder" method="post" action="%s">%s%s</form>%s'
            % (action, TOKEN, save, control))
    if MODE == "plain-save":
        return body + main + SIGN_OUT
    return SIGN_OUT + body + main
SKUS = {"WID-1": "10.00", "GAD-2": "24.50", "BOK-3": "12.00",
        "SRV-4": "80.00", "SEE-5": "3.75"}
LOG = logging.getLogger("tariff")
SHARED = {}
IN_FLIGHT = []
GUARD = threading.Lock()
STRAY = os.path.join(tempfile.gettempdir(), "tariff-quality-stray.log")
HANDLE = open(STRAY, "a") if MODE == "stray" else None
LATE = os.path.join(tempfile.gettempdir(), "tariff-quality-late.log")
REFERENCE = os.path.join(tempfile.gettempdir(),
                         "tariff-quality-reference.sqlite")
INSTANCES = []


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
        INSTANCES.append(self)
        self.number = len(INSTANCES)
        if MODE == "reader":
            uri = pathlib.Path(REFERENCE).as_uri() + "?mode=ro"
            sqlite3.connect(uri, uri=True).execute(
                "SELECT COUNT(*) FROM rates").fetchone()
        if HANDLE is not None:
            HANDLE.write("booted\\n")
            HANDLE.flush()
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
            if (path == "/products" and MODE == "unlisted"
                    and self.app.number == 3):
                raise RuntimeError("the second instance's list is broken")
            if path == "/products" and MODE == "poisoned":
                self.app.prices()
            if path == "/rules" and MODE == "unformed":
                raise RuntimeError("the rules page is broken")
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
                if MODE == "late-stray":
                    with open(LATE, "a") as handle:
                        handle.write("late\\n")
                    time.sleep(600)
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
        target = ("invoices/%d" if MODE == "relative"
                  else "/invoices/%d") % invoice
        return Response(302, "", {"Location": target})

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
            export = json.dumps({
                "lines": records,
                "total": "NaN" if MODE == "unpriced" else total})
            return Response(500 if MODE == "unexported" else 200, export)
        return Response(200, shown)


def create_app(database):
    if MODE == "broken":
        raise RuntimeError("no factory today")
    if MODE == "unportable" and sys.version_info[:2] != (2, 7):
        raise RuntimeError("written for Python 2.7 only")
    return App(database)
'''

# A stand-in for the data upgrade, a fixture at version 1 and a changed
# tree at version 2 of one application on a real SQLite file: version 2 adds
# a cap to each jurisdiction and a minimum to each rule, shows the cap in its
# JSON and CSV exports, and adds the columns to an old file. `sound` does
# all of that. Each other mode plants one fault in version 2 alone:
# `unmigrated` adds the columns to new files only and then reads them,
# `dropping` rebuilds an old file empty, `rewriting` migrates and resets every
# jurisdiction's rate, rows all kept, `rerating` migrates and clears every
# jurisdiction's listed rates, which no invoice prices with and only its page
# shows, `extending` appends a digit to them, the old rates still inside the
# new, `fresh` adds the columns to new files alone and reads an old one
# without them, silently dropping the field a new record sets, `fragile`
# cannot read an old
# jurisdiction's empty cap, so old invoices break while new ones open, and
# `refusing` will not open an old file at all. At version 1, `unlisting`
# links no customer, so nothing can be seeded. `items`, at either version,
# lists jurisdictions as list items rather than table rows, and is sound. A
# mode ending `+divs` lists its records in bare `<div>`s, which no row is
# found in, one ending `+pcells` wraps each table cell in a paragraph, one
# ending `+terse` writes the minimum as 200, each price after the euro's
# sign and the cap as euro 50, and one
# ending `+erring` answers its JSON export 500 with a whole body.
UPGRADE_APP = '''import decimal
import json
import os
import sqlite3

VERSION = __VERSION__
MODE, _, MARKUP = "__MODE__".partition("+")
TOKEN = '<input type="hidden" name="csrf_token" value="t">'
CENT = decimal.Decimal("0.01")
SEED = (("WID-1", "Widget", "10.00", "standard"),
        ("GAD-2", "Gadget", "24.50", "standard"),
        ("BOK-3", "Handbook", "12.00", "reduced"),
        ("SRV-4", "Support hour", "80.00", "standard"),
        ("SEE-5", "Seed pack", "3.75", "zero"))
TABLES = ("products", "customers", "rules", "jurisdictions", "invoices",
          "lines")
ADDED = (("rules", "minimum"), ("jurisdictions", "caps"))


class Response(object):
    def __init__(self, status, body="", headers=None):
        self.status_code = status
        self.headers = dict(headers or {})
        self._body = body

    def get_data(self, as_text=False):
        return self._body if as_text else self._body.encode("utf-8")


def terse(value):
    """A value as a terse page writes it: the minimum without its trailing
    zeros, a price after the euro's sign, a cap with it."""
    text = str(value)
    if text == "200.00":
        return "200"
    if text.replace(".", "", 1).isdigit() and "." in text:
        return "\u20ac" + text
    return text.replace("=50.00", "=\u20ac50")


def form(action, body=""):
    return ('%s<form method="post" action="%s">%s</form>'
            % (body, action, TOKEN))


def columns(connection, table):
    return [row[1] for row in connection.execute(
        "PRAGMA table_info(%s)" % table)]


class App(object):
    def __init__(self, database):
        self.database = database
        connection = self.connect()
        old = "jurisdictions" in [row[0] for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'")]
        stale = old and VERSION == 2 and "caps" not in columns(
            connection, "jurisdictions")
        if stale and MODE == "refusing":
            raise RuntimeError("this database is from an older version")
        if stale and MODE == "dropping":
            for table in TABLES:
                connection.execute("DROP TABLE %s" % table)
        added = ", minimum TEXT" if VERSION == 2 else ""
        capped = ", caps TEXT" if VERSION == 2 else ""
        connection.executescript(
            "CREATE TABLE IF NOT EXISTS admin (password TEXT);"
            "CREATE TABLE IF NOT EXISTS products (sku TEXT PRIMARY KEY, "
            "name TEXT, unit_price TEXT, tax_category TEXT);"
            "CREATE TABLE IF NOT EXISTS customers (id INTEGER PRIMARY KEY, "
            "name TEXT, email TEXT, address TEXT);"
            "CREATE TABLE IF NOT EXISTS rules (rule_id TEXT PRIMARY KEY, "
            "kind TEXT, sku TEXT, detail TEXT%s);"
            "CREATE TABLE IF NOT EXISTS jurisdictions (code TEXT PRIMARY "
            "KEY, name TEXT, default_rate TEXT, rates TEXT%s);"
            "CREATE TABLE IF NOT EXISTS invoices (id INTEGER PRIMARY KEY, "
            "jurisdiction TEXT, customer TEXT, coupons TEXT);"
            "CREATE TABLE IF NOT EXISTS lines (invoice INTEGER, position "
            "INTEGER, sku TEXT, quantity INTEGER);" % (added, capped))
        if stale and MODE not in ("unmigrated", "dropping", "fresh"):
            for table, column in ADDED:
                connection.execute("ALTER TABLE %s ADD COLUMN %s TEXT"
                                   % (table, column))
            if MODE == "rewriting":
                connection.execute("UPDATE jurisdictions SET "
                                   "default_rate = '0'")
            if MODE == "rerating":
                connection.execute("UPDATE jurisdictions SET rates = ''")
            if MODE == "extending":
                connection.execute("UPDATE jurisdictions SET rates = rates "
                                   "|| '1' WHERE rates != ''")
        if not connection.execute("SELECT * FROM admin").fetchone():
            connection.execute("INSERT INTO admin VALUES (?)", (
                os.environ.get("TARIFF_ADMIN_PASSWORD"),))
        if not connection.execute("SELECT * FROM products").fetchone():
            connection.executemany("INSERT INTO products VALUES "
                                   "(?, ?, ?, ?)", SEED)
            for code, rate in (("DE", "0.19"), ("IE", "0.23")):
                self.add_jurisdiction(connection, code, code, rate, "")
        connection.commit()
        connection.close()

    def connect(self):
        return sqlite3.connect(self.database)

    def add_jurisdiction(self, connection, code, name, rate, rates,
                         caps=None):
        names, values = ["code", "name", "default_rate", "rates"], [
            code, name, rate, rates]
        if VERSION == 2 and "caps" in columns(connection, "jurisdictions"):
            names.append("caps")
            values.append(caps or "{}")
        connection.execute("INSERT INTO jurisdictions (%s) VALUES (%s)" % (
            ", ".join(names), ", ".join("?" for _ in names)), values)

    def test_client(self):
        return Client(self)


def listed(value):
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


class Client(object):
    def __init__(self, app):
        self.app = app
        self.signed = False

    def open(self, path, method="GET", data=None, headers=None):
        connection = self.app.connect()
        try:
            answer = self.dispatch(connection, path.split("?")[0], method,
                                   data or {})
            connection.commit()
            return answer
        except Exception as error:
            return Response(500, "Internal Server Error: %r" % error)
        finally:
            connection.close()

    def dispatch(self, connection, path, method, data):
        if path == "/sign-in":
            if method == "GET":
                return Response(200, form("/sign-in"))
            stored = connection.execute("SELECT password FROM admin")
            if (data.get("csrf_token") == "t"
                    and data.get("username") == "admin"
                    and data.get("password") == stored.fetchone()[0]):
                self.signed = True
                return Response(302, "", {"Location": "/"})
            return Response(200, "wrong" + form("/sign-in"))
        if not self.signed:
            return Response(302, "", {"Location": "/sign-in"})
        if method == "POST" and data.get("csrf_token") != "t":
            return Response(400, "missing token")
        parts = path.strip("/").split("/")
        if path == "/":
            return Response(200, "dashboard")
        if parts[0] in ("products", "rules", "jurisdictions") \\
                and len(parts) == 1:
            if method == "POST":
                return self.create(connection, parts[0], data)
            return Response(200, form(path, self.listing(connection,
                                                          parts[0])))
        if parts[0] == "customers":
            return self.customers(connection, parts, method, data)
        if parts[0] == "invoices":
            return self.invoices(connection, parts, method, data)
        return Response(404, "not found")

    def listing(self, connection, table):
        if table == "products":
            rows = connection.execute("SELECT sku, name, unit_price FROM "
                                      "products")
        elif table == "rules" and VERSION == 2 and "minimum" in columns(
                connection, "rules"):
            rows = connection.execute("SELECT rule_id, kind, minimum FROM "
                                      "rules")
        elif table == "rules":
            rows = connection.execute("SELECT rule_id, kind FROM rules")
        elif VERSION == 2 and "caps" in columns(connection, "jurisdictions"):
            rows = connection.execute("SELECT code, name, default_rate, "
                                      "rates, caps FROM jurisdictions")
        else:
            rows = connection.execute("SELECT code, name, default_rate, "
                                      "rates FROM jurisdictions")
        if MARKUP == "terse":
            rows = [tuple(terse(value) for value in row) for row in rows]
        if MARKUP == "divs":
            return "".join("<div>%s</div>" % " ".join(str(value)
                                                    for value in row)
                           for row in rows)
        if MODE == "items":
            return "<ul>%s</ul>" % "".join(
                "<li>%s</li>" % " ".join(str(value) for value in row)
                for row in rows)
        cell = "<td><p>%s</p></td>" if MARKUP == "pcells" else "<td>%s</td>"
        return "<table>%s</table>" % "".join(
            "<tr>%s</tr>" % "".join(cell % value for value in row)
            for row in rows)

    def create(self, connection, table, data):
        if table == "products":
            connection.execute("INSERT INTO products VALUES (?, ?, ?, ?)", (
                data["sku"], data["name"], data["unit_price"],
                data["tax_category"]))
        elif table == "rules":
            detail = json.dumps({key: data.get(key) for key in (
                "percent", "buy", "pay", "code", "amount")})
            names, values = ["rule_id", "kind", "sku", "detail"], [
                data["rule_id"], data["kind"], data.get("sku"), detail]
            if VERSION == 2 and "minimum" in columns(connection, "rules"):
                names.append("minimum")
                values.append(data.get("minimum"))
            connection.execute("INSERT INTO rules (%s) VALUES (%s)" % (
                ", ".join(names), ", ".join("?" for _ in names)), values)
        else:
            self.app.add_jurisdiction(connection, data["code"], data["name"],
                                      data["default_rate"],
                                      data.get("rates") or "",
                                      data.get("caps"))
        return Response(302, "", {"Location": "/" + table})

    def customers(self, connection, parts, method, data):
        if len(parts) == 1 and method == "POST":
            connection.execute("INSERT INTO customers (name, email, address) "
                               "VALUES (?, ?, ?)", (data["name"],
                                                    data["email"],
                                                    data["address"]))
            return Response(302, "", {"Location": "/customers"})
        if len(parts) == 1:
            rows = connection.execute("SELECT id, name, email FROM customers")
            return Response(200, form("/customers", "".join(
                ("<p>%s %s</p>" if MODE == "unlisting"
                 else '<p><a href="/customers/%d">%s</a> %s</p>') % row
                for row in rows)))
        row = connection.execute("SELECT id, name, email, address FROM "
                                 "customers WHERE id = ?",
                                 (parts[1],)).fetchone()
        if row is None:
            return Response(404, "not found")
        invoices = [found[0] for found in connection.execute(
            "SELECT id FROM invoices WHERE customer = ? ORDER BY id",
            (str(row[0]),))]
        return Response(200, json.dumps({
            "customer_id": row[0], "name": row[1], "email": row[2],
            "address": row[3], "invoices": invoices}))

    def priced(self, connection, jurisdiction, coupons, lines):
        found = connection.execute("SELECT * FROM jurisdictions WHERE code "
                                   "= ?", (jurisdiction,)).fetchone()
        if found is None:
            raise LookupError(jurisdiction)
        rate = decimal.Decimal(found[2])
        if VERSION == 2:
            caps = found[4] if len(found) > 4 else "{}"
            json.loads(caps if MODE == "fragile" else caps or "{}")
        rules = [(kind, sku, json.loads(detail)) for kind, sku, detail
                 in connection.execute("SELECT kind, sku, detail FROM rules")]
        net = []
        for sku, quantity in lines:
            price = connection.execute("SELECT unit_price FROM products "
                                       "WHERE sku = ?", (sku,)).fetchone()
            amount = decimal.Decimal(price[0]) * quantity
            for kind, scope, detail in rules:
                if kind == "percentage" and scope == sku:
                    amount -= amount * decimal.Decimal(detail["percent"]) / 100
            net.append((sku, quantity, amount.quantize(CENT)))
        subtotal = sum((amount for _, _, amount in net),
                       decimal.Decimal("0"))
        for kind, _, detail in rules:
            if (kind == "coupon" and detail.get("code") in coupons
                    and detail.get("amount")):
                subtotal -= decimal.Decimal(detail["amount"])
        total = (subtotal * (1 + rate)).quantize(CENT)
        return net, str(total)

    def invoices(self, connection, parts, method, data):
        if parts[1:] in (["preview"], []) and method == "POST":
            lines = [(sku, int(quantity)) for sku, quantity in zip(
                listed(data.get("sku")), listed(data.get("quantity")))]
            coupons = (data.get("coupon_codes") or "").split(",")
            _, total = self.priced(connection, data["jurisdiction"], coupons,
                                   lines)
            if parts[1:] == ["preview"]:
                return Response(200, "<p>Total %s</p>" % total)
            invoice = connection.execute(
                "INSERT INTO invoices (jurisdiction, customer, coupons) "
                "VALUES (?, ?, ?)", (data["jurisdiction"],
                                     data.get("customer") or "",
                                     data.get("coupon_codes") or "")
            ).lastrowid
            connection.executemany("INSERT INTO lines VALUES (?, ?, ?, ?)",
                                   [(invoice, position, sku, quantity)
                                    for position, (sku, quantity)
                                    in enumerate(lines)])
            return Response(302, "", {"Location": "/invoices/%d" % invoice})
        if parts[1:] == ["new"]:
            return Response(200, form("/invoices/preview"))
        row = connection.execute("SELECT jurisdiction, coupons FROM invoices "
                                 "WHERE id = ?", (parts[1],)).fetchone()
        if row is None:
            return Response(404, "not found")
        lines = connection.execute("SELECT sku, quantity FROM lines WHERE "
                                   "invoice = ? ORDER BY position",
                                   (parts[1],)).fetchall()
        net, total = self.priced(connection, row[0], row[1].split(","),
                                 lines)
        if parts[2:] == ["export.json"]:
            export = {"invoice_id": int(parts[1]), "jurisdiction": row[0],
                      "lines": [{"sku": sku, "quantity": quantity,
                                 "net": str(amount)}
                                for sku, quantity, amount in net],
                      "total": total}
            if VERSION == 2:
                export["caps"] = {}
            return Response(500 if MARKUP == "erring" else 200,
                            json.dumps(export))
        if parts[2:] == ["export.csv"]:
            head = "sku,quantity,net" + (",cap" if VERSION == 2 else "")
            return Response(200, "\\n".join([head] + [
                "%s,%d,%s" % (sku, quantity, amount)
                + ("," if VERSION == 2 else "")
                for sku, quantity, amount in net]) + "\\n")
        return Response(200, "<p>Invoice %s</p><p>Total %s</p>"
                        % (parts[1], total))


def create_app(database):
    return App(database)
'''

# The faults the data upgrade must catch at version 2, and what each loses.
UPGRADE_FAULTS = ("unmigrated", "dropping", "rewriting", "rerating",
                  "extending", "fresh", "fragile", "refusing")


def plant_upgrade(where, version, mode):
    """The stand-in at `version` in `mode`, importable from its own folder;
    the environment that imports it."""
    site = os.path.join(where, "site-%d" % version)
    package = os.path.join(site, "tariff")
    os.makedirs(package)
    with io.open(os.path.join(package, "__init__.py"), "w",
                 encoding="utf-8") as handle:
        handle.write(UPGRADE_APP.replace("__VERSION__", str(version))
                     .replace("__MODE__", mode))
    return dict(os.environ, PYTHONPATH=site)


def upgrade_reading(scratch, fixture, changed):
    """The data upgrade of a version 2 in mode `changed` over a version 1
    in mode `fixture`: the reading, or why seeding left it missing."""
    where = os.path.join(scratch, "upgrade-%s-%s" % (fixture, changed))
    os.makedirs(where)
    seeded, reason = seed_with(sys.executable, where,
                               plant_upgrade(where, 1, fixture))
    if seeded is None:
        return dict(missing_reading("data_upgrade", reason))
    return upgrade_with(sys.executable, where, seeded,
                        plant_upgrade(where, 2, changed),
                        {"seeded_sha256": seeded["sha256"]})


def upgrade_self_checks(scratch):
    """A sound upgrade passes; each planted fault fails or loses the probe;
    a fixture that cannot seed leaves it missing."""
    sound = upgrade_reading(scratch, "sound", "sound")
    faults = {mode: upgrade_reading(scratch, "sound", mode)
              for mode in UPGRADE_FAULTS}
    unseeded = upgrade_reading(scratch, "unlisting", "sound")
    items = upgrade_reading(scratch, "items", "items")
    hidden = upgrade_reading(scratch, "sound+divs", "rerating+divs")
    wrapped = upgrade_reading(scratch, "sound+pcells", "sound+pcells")
    rewrapped = upgrade_reading(scratch, "sound+pcells", "rerating+pcells")
    terse_read = upgrade_reading(scratch, "sound", "sound+terse")
    erring = upgrade_reading(scratch, "sound", "sound+erring")
    failed = sorted(mode for mode, reading in faults.items()
                    if reading.get("passed") is False)
    return [
        ("a version 2 that migrates the old database keeps every record",
         sound.get("passed") is True and not sound.get("failures")
         and len(sound.get("seeded_sha256") or "") == 64),
        ("a schema change shipped without a migration fails the upgrade",
         faults["unmigrated"].get("passed") is False
         and any("/jurisdictions" in failure for failure in
                 faults["unmigrated"].get("failures") or [])),
        ("an old database rebuilt empty fails the upgrade",
         faults["dropping"].get("passed") is False
         and any("no longer lists" in failure for failure in
                 faults["dropping"].get("failures") or [])),
        ("rows all kept with their values changed fail the upgrade",
         faults["rewriting"].get("passed") is False
         and any("no longer reads the same" in failure for failure in
                 faults["rewriting"].get("failures") or [])),
        ("a listed field changed by the migration, no invoice priced by it, "
         "fails the upgrade",
         faults["rerating"].get("passed") is False
         and faults["rerating"].get("failures") == [
             "/jurisdictions no longer shows 'standard=0.2' for UP",
             "/jurisdictions no longer shows 'reduced=0.05' for UP"]),
        ("a listed field kept only inside a longer one fails the upgrade",
         faults["extending"].get("passed") is False
         and faults["extending"].get("failures") == [
             "/jurisdictions no longer shows 'reduced=0.05' for UP"]),
        ("a table row whose cells are paragraphs is read whole: kept when "
         "sound, its cleared values named",
         wrapped.get("passed") is True
         and rewrapped.get("passed") is False
         and rewrapped.get("failures") == [
             "/jurisdictions no longer shows 'standard=0.2' for UP",
             "/jurisdictions no longer shows 'reduced=0.05' for UP"]),
        ("a value written as another amount, a sign before it or no "
         "trailing zeros, reads as the same value",
         terse_read.get("passed") is True and not terse_read.get("failures")),
        ("an export answering an error fails the upgrade, naming its status",
         erring.get("passed") is False
         and erring.get("failures") == [
             "/invoices/1/export.json answered 500",
             "/invoices/2/export.json answered 500"]),
        ("a row found by no key leaves the upgrade missing, never passed",
         hidden.get("passed") is None
         and hidden.get("missing", "").startswith("row for ")
         and hidden["missing"].endswith(" not found")),
        ("a list-item row with a value the change adds keeps every old one",
         items.get("passed") is True and not items.get("failures")),
        ("a schema changed for new files alone fails on the change's own "
         "fields",
         faults["fresh"].get("passed") is False
         and faults["fresh"].get("failures") == [
             "/jurisdictions lists U3 without the reduced=50.00 it was "
             "posted with",
             "/rules lists u-threshold without the 200.00 it was posted "
             "with"]),
        ("old invoices that break on the new field fail the upgrade",
         faults["fragile"].get("passed") is False
         and any("/invoices/" in failure for failure in
                 faults["fragile"].get("failures") or [])),
        ("a version 2 that will not open the old database loses the upgrade",
         faults["refusing"].get("passed") is False
         and bool(faults["refusing"].get("lost"))),
        ("every planted upgrade fault fails",
         failed == sorted(UPGRADE_FAULTS)),
        ("a fixture that cannot seed leaves the upgrade missing, not failed",
         unseeded.get("passed") is None and bool(unseeded.get("missing"))),
    ]


FAULTS = {"fragile": "fuzz_robustness", "brittle": "fuzz_robustness",
          "locking": "concurrent_writes", "lossy": "concurrent_writes",
          "cramped": "capacity_500_lines", "crowded": "capacity_500_lines",
          "truncating": "capacity_500_lines",
          "hanging": "concurrent_writes", "unformed": "fuzz_robustness",
          "unexported": "capacity_500_lines", "unlisted": "coexistence",
          "nulling": "capacity_500_lines", "capped": "capacity_500_lines",
          "unpriced": "capacity_500_lines", "free": "capacity_500_lines",
          "bouncing": "fuzz_robustness",
          "forbidding": "fuzz_robustness", "chatty": "n_plus_one",
          "shared": "coexistence", "stray": "coexistence"}


def fake_readings(scratch, modes, mode_arg="all", timeout=300):
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
                                       env=env, timeout=timeout)
    return readings


def failing(probes):
    """The pass/fail probes a reading fails, in order."""
    return [name for name in IN_PROCESS
            if name not in MEASURED and probes[name].get("passed") is not True]


def runtime_self_checks(scratch):
    """Each planted fault fails its own probe and no other; an app that
    keeps the probes from running loses them."""
    reference = os.path.join(tempfile.gettempdir(),
                             "tariff-quality-reference.sqlite")
    connection = sqlite3.connect(reference)
    connection.execute("CREATE TABLE IF NOT EXISTS rates (code TEXT)")
    connection.commit()
    connection.close()
    modes = (["sound", "slow", "poisoned", "detached", "plain-save", "reader",
              "relative",
              "gated", "refusing", "broken"]
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
        ("a save sent by its control's formaction carries its form's token",
         sound["n_plus_one"].get("passed") is True
         and sound["capacity_500_lines"].get("passed") is True
         and 'formaction="/invoices"' in FAKE_APP),
        ("a save control outside its form, linked by its id, carries that "
         "form's token", failing(probes["detached"]) == []),
        ("a post no form's action names carries the page's first token",
         failing(probes["plain-save"]) == []),
        ("the latency is two repeats of 30 requests each",
         latency.get("requests") == 30
         and len(latency.get("repeats") or []) == 2
         and all(value > 0 for value in latency["repeats"])
         and latency["value"] == max(latency["repeats"])),
        # Each answer is delayed 20 ms, so each repeat's p95 is at least
        # that whatever the machine's load; a comparison with the sound
        # run's would read the load instead.
        ("a slowed app reads slower by its delay",
         failing(probes["slow"]) == []
         and len(probes["slow"]["latency_p95_ms"].get("repeats") or []) == 2
         and min(probes["slow"]["latency_p95_ms"]["repeats"]) >= 20),
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
        "unformed": "an app whose form page answers 500 fails "
                    "fuzz_robustness",
        "unexported": "an export answered 500 fails capacity_500_lines",
        "unlisted": "a second instance whose product list answers 500 fails "
                    "coexistence",
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
        ("a value one malformed request stored reaches no other case",
         probes["poisoned"]["fuzz_robustness"].get("passed") is True
         and len(sound["fuzz_robustness"].get("statuses") or [])
         == sound["fuzz_robustness"].get("requests", 0) > 0
         and [index for index, (poisoned, clean) in enumerate(zip(
             probes["poisoned"]["fuzz_robustness"].get("statuses") or [],
             sound["fuzz_robustness"]["statuses"]))
             if poisoned == 400 and clean != 400] == []),
        ("a form that cannot be reached is no handled request",
         any("could not be reached" in entry.get("reason", "")
             for entry in probes["unformed"]["fuzz_robustness"].get(
                 "failed", []))),
        ("a save redirected to a relative location reads as the sound "
         "app's", failing(probes["relative"]) == []
         and probes["relative"]["latency_p95_ms"].get("value") is not None
         and all(probes["relative"][name].get("passed")
                 is sound[name].get("passed") is True
                 for name in ("capacity_500_lines", "n_plus_one"))),
        ("a database outside, opened read-only, is no stray write",
         failing(probes["reader"]) == []
         and probes["reader"]["coexistence"].get("stray") == []),
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

    # The first malformed request writes outside and then hangs, so the run
    # is killed in its fuzzing, long after co-existence passed.
    payload, reason, stalled = fake_readings(scratch, ["late-stray"],
                                             timeout=40)["late-stray"]
    late = probe_results(payload, reason, stalled=stalled)
    checks.append((
        "a write outside before a hang still fails coexistence, the path kept",
        late["coexistence"].get("passed") is False
        and any(path.endswith("tariff-quality-late.log")
                for path in late["coexistence"].get("stray", []))
        and "stopped during fuzz_robustness" in late["fuzz_robustness"].get(
            "lost", "")))
    for name in ("tariff-quality-stray.log", "tariff-quality-late.log",
                 "tariff-quality-reference.sqlite"):
        path = os.path.join(tempfile.gettempdir(), name)
        if os.path.exists(path):
            os.remove(path)
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


def absent_tree_self_checks(scratch):
    """A trial whose tree is gone has nothing measured, and installs
    nothing."""
    area = os.path.join(scratch, "absent")
    os.makedirs(area)
    scores_file = os.path.join(area, "none-1.json")
    with io.open(scores_file, "w", encoding="utf-8") as handle:
        json.dump({"workspace": os.path.join(area, "dropped")}, handle)
    result = read_trial(area, "none-1", scores_file, None)
    return [("a trial whose source tree is gone is missing, not lost",
             sorted(result["probes"]) == sorted(PROBES)
             and all("source tree not present" in (probe.get("missing") or "")
                     and not probe.get("lost")
                     for probe in result["probes"].values())
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
    ] + change_reading_checks(area, tree)


def change_reading_checks(area, tree):
    """A change task is read from its own scores into its own folders, adds
    the data upgrade, and loses it with a changed tree that will not
    install; with no fixture to seed, the upgrade is missing."""
    scores_file = os.path.join(area, "scores-change", "none-1.json")
    os.makedirs(os.path.dirname(scores_file))
    with io.open(scores_file, "w", encoding="utf-8") as handle:
        json.dump({"workspace": tree, "fixture": {"trial": "none-2",
                                                  "sha256": "f" * 64}},
                  handle)
    unseeded = read_trial(area, "none-1", scores_file, None, "change")

    # A fixture that seeded, as the reading takes it, over the same tree.
    saved = globals()["seed_fixture"]
    globals()["seed_fixture"] = lambda scores, where: (
        {"sha256": "a" * 64, "folder": where, "readings": None}, None)
    try:
        seeded = read_trial(area, "none-1", scores_file, None, "change")
    finally:
        globals()["seed_fixture"] = saved
    upgrade = seeded["probes"]["data_upgrade"]
    return [
        ("a change task is read from its own scores into "
         "quality-scores-change",
         sorted(scored_trials(area, "change")) == ["none-1"]
         and readings_folder(area, "change")
         == os.path.join(area, "quality-scores-change")
         and os.path.isdir(os.path.join(area, "quality-change", "none-1"))),
        ("a change task with no starting commit leaves the upgrade missing",
         sorted(unseeded["probes"]) == sorted(PROBES + CHANGE_PROBES)
         and "starting commit" in (unseeded["probes"]["data_upgrade"]
                                   .get("missing") or "")),
        ("a changed tree that does not install loses the upgrade, its "
         "fixture named",
         "did not install" in (upgrade.get("lost") or "")
         and upgrade.get("passed") is False
         and upgrade.get("fixture_sha256") == "f" * 64
         and upgrade.get("seeded_sha256") == "a" * 64),
    ]


def self_test():
    """Prove each probe fails the fault it guards against, records missing
    as missing, and that a live run refuses a second."""
    scratch = os.path.join(tempfile.gettempdir(), "efficacy-quality-self-test")
    remove_tree(scratch)
    os.makedirs(scratch)
    checks = (runtime_self_checks(scratch) + reading_self_checks()
              + portability_self_checks(scratch) + claim_self_checks(scratch)
              + absent_tree_self_checks(scratch)
              + leftover_self_checks(scratch) + upgrade_self_checks(scratch))
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
    parser.add_argument("--task", choices=("build", "change"),
                        default="build",
                        help="read the build trials' trees, or the trees the "
                             "change tasks left, with the data upgrade")
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

    area = scoring_area(options.root)
    scored = scored_trials(area, options.task)
    wanted = (sorted(canonical(name) for name in options.trial)
              if options.trial else sorted(scored))
    missing = [name for name in wanted if name not in scored]
    if not scored or missing:
        print("no %s score for %s under %s; score.py writes them"
              % (options.task, ", ".join(missing) or "any trial", area))
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


def scored_trials(area, task):
    """Every score of `task` in the scoring area, by the trial's name as the
    arms spell it."""
    scores = os.path.join(area, task_folder("scores", task))
    return {canonical(os.path.splitext(entry)[0]): os.path.join(scores, entry)
            for entry in (sorted(os.listdir(scores))
                          if os.path.isdir(scores) else [])
            if entry.endswith(".json")}


def readings_folder(area, task):
    """Where the quality readings of `task` are filed."""
    return os.path.join(area, task_folder("quality-scores", task))


def read_trials(options, area, scored, wanted):
    """Read each wanted trial not read yet; return the exit code."""
    target = readings_folder(area, options.task)
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
        result = read_trial(area, name, scored[name], other, options.task)
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
