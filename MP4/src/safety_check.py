"""Safety metrics for generated Rust (why.md R-T3-*-SAFETY, Z3, Z4, D6).

--tool proxy  (interim, D6): asserts `#![forbid(unsafe_code)]` is the first
              non-comment line of src/lib.rs, builds a temp copy with
              RUSTFLAGS="-D unsafe_code", and counts the four primary metrics
              with brace-tracked regexes over library code only (src/bin and
              src/interfaces are benchmark infrastructure and excluded, as in
              the handout). Regex-level by design: the course tool replaces it.
--tool course (official): runs the course's `newmetrics` tool
              (configs/pipeline.yaml safety.course_cmd, then the staff
              aggregate.py at safety.course_aggregate) on a temporary copy of
              the crate, never in the crate itself: the tool runs `cargo clean`
              and `cargo check` and writes unsafe_spans.txt, derefs.txt,
              decls.txt and summary.json into its working directory. The tool
              is not part of this repository; MP4/README.md says how to get it.
--tool both   (pipeline default): the proxy, for its build and FFI guards,
              plus the course tool. The four reported metrics are the course
              tool's; the proxy's counts are kept under extra.proxy.

  safety_check.py --project project_1 --tool course
  safety_check.py --project project_1 --official     final translation and every
              iteration snapshot with the course tool; raw outputs go to
              trajectories/<project>/official_safety/<date>/ and the totals
              into run_summary.json `official_safety`

Output schema (all tools): {tool, tool_version, unsafe_lines, unsafe_calls,
unsafe_casts, pointer_arithmetic, extra, findings[], raw_path}.

Proxy metric definitions:
  unsafe_lines        non-blank, non-comment lines inside `unsafe { }` blocks
                      and `unsafe fn` bodies (union of lines; nesting counted once)
  unsafe_calls        call expressions inside those regions
  unsafe_casts        `as *const` / `as *mut` casts and transmute/transmute_copy calls
  pointer_arithmetic  .offset/.byte_add/.byte_sub/.byte_offset/.wrapping_offset/
                      .wrapping_byte_* /.offset_from anywhere; .add/.sub/
                      .wrapping_add/.wrapping_sub inside unsafe regions or on a
                      receiver bound to a raw pointer
"""
import argparse
import datetime
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402

PROXY_VERSION = "proxy-1"
COURSE_NOT_CONFIGURED = "course safety tool not configured"
PRIMARY = ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic")
# The course tool prints one `Label: N` line per metric and compilation unit; the staff aggregate.py sums them.
COURSE_LABELS = {"pointer_arithmetic": "Pointer arithmetic", "unsafe_lines": "Unsafe lines",
                 "unsafe_calls": "Unsafe calls", "unsafe_casts": "Unsafe casts", "total_spans": "Total spans",
                 "raw_pointer_dereferences": "Raw pointer dereferences",
                 "raw_pointer_declarations": "Raw pointer declarations"}
COURSE_SIDE_FILES = ("unsafe_spans.txt", "derefs.txt", "decls.txt")
COURSE_TIMEOUT_S = 1800
AGGREGATE_TIMEOUT_S = 120
AGGREGATE_ENV = "MP4_NEWMETRICS_AGGREGATE"   # overrides safety.course_aggregate (path to the staff aggregate.py)

_UNSAFE_RE = re.compile(r"\bunsafe\b")
_CALL_RE = re.compile(r"(?<![\w!])([A-Za-z_]\w*)\s*(?:::\s*<[^<>;{}]*>)?\s*\(")
_NOT_CALLS = {"if", "while", "match", "for", "return", "loop", "in", "as", "fn", "let", "Some", "Ok", "Err",
              "unsafe", "move", "where", "impl", "mut", "ref", "else"}
_CAST_RE = re.compile(r"\bas\s*\*\s*(?:const|mut)\b")
_TRANSMUTE_RE = re.compile(r"\btransmute(?:_copy)?\s*(?:::\s*<[^;{}]*?>)?\s*\(")
_PTR_ALWAYS_RE = re.compile(r"\.\s*(offset|byte_add|byte_sub|byte_offset|wrapping_offset|wrapping_byte_add|"
                            r"wrapping_byte_sub|wrapping_byte_offset|offset_from|byte_offset_from)\s*\(")
_PTR_AMBIG_RE = re.compile(r"([A-Za-z_]\w*)\s*\.\s*(add|sub|wrapping_add|wrapping_sub)\s*\(")
_PTR_BIND_RES = [
    re.compile(r"\blet\s+(?:mut\s+)?([A-Za-z_]\w*)\s*:\s*\*\s*(?:const|mut)\b"),
    re.compile(r"\blet\s+(?:mut\s+)?([A-Za-z_]\w*)\s*(?::[^=;]*)?=\s*[^;]*?(?:\.as_ptr\(\)|\.as_mut_ptr\(\)|"
               r"as\s*\*\s*(?:const|mut)|ptr::null(?:_mut)?\(\))"),
    re.compile(r"[(,]\s*(?:mut\s+)?([A-Za-z_]\w*)\s*:\s*\*\s*(?:const|mut)\b"),
]
_EXTRA_RES = {
    "raw_pointer_types": re.compile(r"\*\s*(?:const|mut)\s+[A-Za-z_(\[]"),
    "manual_alloc": re.compile(r"\b(?:alloc::alloc|alloc::dealloc|alloc::realloc|Box::from_raw|Box::into_raw|"
                               r"mem::forget|ManuallyDrop|MaybeUninit)\b"),
    "unsafe_impl": re.compile(r"\bunsafe\s+impl\b"),
    "static_mut": re.compile(r"\bstatic\s+mut\b"),
}


def _regions(code):
    """[(open_idx, close_idx, kind)] for unsafe blocks and unsafe fn bodies in stripped code."""
    regions = []
    for m in _UNSAFE_RE.finditer(code):
        j = m.end()
        while j < len(code) and code[j].isspace():
            j += 1
        if code.startswith("{", j):
            kind, open_idx = "block", j
        elif re.match(r"(?:extern\s+\"[^\"]*\"\s*)?fn\b", code[j:]):
            k = j
            depth = 0
            open_idx = -1
            while k < len(code):
                ch = code[k]
                if ch in "([":
                    depth += 1
                elif ch in ")]":
                    depth -= 1
                elif depth == 0 and ch == ";":
                    break
                elif depth == 0 and ch == "{":
                    open_idx = k
                    break
                k += 1
            if open_idx < 0:
                continue
            kind = "fn"
        else:
            continue
        close = rustlex.match_brace(code, open_idx)
        if close > 0:
            regions.append((open_idx, close, kind))
    return regions


def _ptr_idents(code):
    names = set()
    for rx in _PTR_BIND_RES:
        names.update(m.group(1) for m in rx.finditer(code))
    return names


def count_file(code):
    """Metrics for one stripped source text."""
    regions = _regions(code)
    lines = set()
    calls = 0
    for open_idx, close, _ in regions:
        body = code[open_idx + 1:close]
        base = rustlex.line_of(code, open_idx + 1)
        for off, ln in enumerate(body.split("\n")):
            if ln.strip():
                lines.add(base + off)
    covered = sorted({(a, b) for a, b, _ in regions})
    # calls: count each call site once even when regions nest
    call_sites = set()
    for a, b in covered:
        for m in _CALL_RE.finditer(code, a + 1, b):
            if m.group(1) not in _NOT_CALLS:
                call_sites.add(m.start())
    calls = len(call_sites)

    def in_unsafe(idx):
        return any(a < idx < b for a, b in covered)

    code_no_use = re.sub(r"^\s*(?:pub\s+)?use\b[^;]*;", lambda m: " " * len(m.group(0)), code, flags=re.M)
    casts = len(_CAST_RE.findall(code_no_use)) + len(_TRANSMUTE_RE.findall(code_no_use))
    ptr_names = _ptr_idents(code)
    ptr_sites = {m.start() for m in _PTR_ALWAYS_RE.finditer(code)}
    for m in _PTR_AMBIG_RE.finditer(code):
        if in_unsafe(m.start()) or m.group(1) in ptr_names:
            ptr_sites.add(m.start())
    extra = {k: len(rx.findall(code)) for k, rx in _EXTRA_RES.items()}
    extra["unsafe_blocks"] = sum(1 for r in regions if r[2] == "block")
    extra["unsafe_fns"] = sum(1 for r in regions if r[2] == "fn")
    extra["transmute"] = len(_TRANSMUTE_RE.findall(code_no_use))
    return {"unsafe_lines": len(lines), "unsafe_calls": calls, "unsafe_casts": casts,
            "pointer_arithmetic": len(ptr_sites), "extra": extra}


def first_code_line(lib_rs_text):
    for line in rustlex.strip(lib_rs_text).splitlines():
        if line.strip():
            return " ".join(line.split())
    return ""


def count_tree(files_root, files):
    totals = {"unsafe_lines": 0, "unsafe_calls": 0, "unsafe_casts": 0, "pointer_arithmetic": 0, "extra": {}}
    per_file = {}
    for p in files:
        c = count_file(rustlex.strip(mc.read_text(p)))
        per_file[mc.rel(p, files_root)] = c
        for k in ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic"):
            totals[k] += c[k]
        for k, v in c["extra"].items():
            totals["extra"][k] = totals["extra"].get(k, 0) + v
    return totals, per_file


def proxy(crate, raw_path=None, build=True, source=None):
    """Proxy metrics for a crate directory. build=False skips the -D unsafe_code build (snapshots)."""
    findings = []
    lib = os.path.join(crate, "src", "lib.rs")
    first = first_code_line(mc.read_text(lib)) if os.path.exists(lib) else ""
    forbid_ok = first == mc.FORBID_LINE
    if not forbid_ok:
        findings.append({"kind": "forbid_missing", "file": "src/lib.rs",
                         "detail": "first code line is %r" % first[:80]})
    totals, per_file = count_tree(crate, mc.library_sources(crate))
    build_res = None
    if build:
        copy = mc.copy_crate(crate)
        try:
            code, out = mc.cargo(["build", "--lib", "--locked"], copy, env_extra={"RUSTFLAGS": "-D unsafe_code"})
        finally:
            shutil.rmtree(os.path.dirname(copy), ignore_errors=True)   # copy_crate's temp parent
        for p in sorted({os.path.realpath(copy), copy}, key=len, reverse=True):   # the temp path is noise
            out = out.replace(p, "<crate>")
        build_res = {"ok": code == 0, "exit_code": code,
                     "unsafe_code_errors": len(re.findall(r"^error: .*unsafe", out, re.M))}
        if code != 0:
            findings.append({"kind": "deny_unsafe_build_failed", "file": "", "detail": out[-1500:]})
    ffi = integrity.ffi_scan(crate, source)
    for f in ffi["findings"]:
        findings.append(dict(f))
    extra = dict(totals["extra"])
    extra.update({
        "forbid_unsafe_code_first_line": forbid_ok,
        "deny_unsafe_build": build_res,
        "ffi": sum(1 for f in ffi["findings"] if f["kind"] in ("extern_c", "link_attr", "libc", "cc_crate")),
        "build_rs": any(f["kind"] == "build_rs" for f in ffi["findings"]),
        "c_sources": sum(1 for f in ffi["findings"] if f["kind"] == "c_source"),
        "dependencies": ffi["dependencies"],
        "extra_dependencies": ffi["extra_dependencies"],
        "per_file": per_file,
    })
    for k, v in per_file.items():
        for metric in ("unsafe_lines", "unsafe_casts", "pointer_arithmetic"):
            if v[metric]:
                findings.append({"kind": metric, "file": k, "count": v[metric]})
    res = {"tool": "proxy", "tool_version": PROXY_VERSION,
           "unsafe_lines": totals["unsafe_lines"], "unsafe_calls": totals["unsafe_calls"],
           "unsafe_casts": totals["unsafe_casts"], "pointer_arithmetic": totals["pointer_arithmetic"],
           "extra": extra, "findings": findings, "raw_path": raw_path}
    _write(res, raw_path)
    return res


def parse_course_output(text):
    """Sum every `Label: N` line of the tool's output, as the staff aggregate.py does. Returns (totals, units):
    units is the number of compilation units that reported, 0 when the tool printed no metrics at all, and also
    0 when the labels were not all reported the same number of times: a unit with a metric line missing must not
    be read as that metric being 0 (review M16)."""
    totals, counts = {}, set()
    for key, label in COURSE_LABELS.items():
        hits = re.findall(r"^\s*%s:\s*(\d+)\s*$" % re.escape(label), text, re.M)
        totals[key] = sum(int(h) for h in hits)
        counts.add(len(hits))
    return totals, (counts.pop() if len(counts) == 1 else 0)


def course_config(cfg=None):
    """(argv, aggregate path or None, version) from configs/pipeline.yaml `safety`, or from cfg when given."""
    real = cfg is None
    cfg = (mc.load_pipeline_config().get("safety") or {}) if real else cfg
    cmd = cfg.get("course_cmd")
    argv = (shlex.split(cmd) if isinstance(cmd, str) else [str(x) for x in cmd]) if cmd else None
    # the environment override applies to configs/pipeline.yaml only: an explicit cfg (the self-test's) is taken
    # as given, so the self-test does not depend on the caller's environment (review M16)
    agg = (os.environ.get(AGGREGATE_ENV) if real else None) or cfg.get("course_aggregate")
    return argv, (os.path.abspath(os.path.expanduser(agg)) if agg else None), cfg.get("course_version")


def course_unavailable(cfg=None):
    """Why the course tool cannot run here, or None when it can. Checked before every `both` measurement, so a
    machine without the tool reports that plainly instead of failing inside cargo."""
    argv, agg, _ = course_config(cfg)
    if not argv:
        return COURSE_NOT_CONFIGURED + " (set safety.course_cmd in MP4/configs/pipeline.yaml)"
    path = mc.cargo_env().get("PATH")
    exe = "cargo-" + argv[1] if os.path.basename(argv[0]) == "cargo" and len(argv) > 1 else argv[0]
    if not shutil.which(exe, path=path):
        return "course safety tool not installed (%s is not on PATH; see MP4/README.md)" % exe
    return None


def _scrub_course(text, copy):
    """The temporary copy's path -> <crate> (both macOS spellings), then secrets, e-mails and home paths."""
    import scrub_secrets
    for p in sorted({os.path.realpath(copy), copy}, key=len, reverse=True):
        text = text.replace(p, "<crate>")
    return scrub_secrets.scrub_text(text)


def course(crate, raw_path=None, cfg=None, keep_dir=None, keep_tag=None):
    """Official metrics from the course tool, measured on a temporary copy of `crate` (without target/), which is
    deleted afterwards: the tool cleans, builds and writes files where it runs, and `crate` must stay untouched.

    Runs safety.course_cmd in the copy with stdout and stderr merged (the staff command's `2>&1`), sums the
    metric lines, and, when safety.course_aggregate names the staff aggregate.py, also pipes the same output
    through it (`python3 aggregate.py --out summary.json`) and requires the two to agree. When that file does not
    exist (the course repository is cloned somewhere else) the tool still runs and the summed lines are the
    result; `extra.aggregate` says which of the two happened. keep_dir/keep_tag: also
    store the scrubbed raw output as raw_<tag>.txt, summary_<tag>.json and the tool's three span files there.
    Raises SystemExit(2) when the tool is not configured or not installed."""
    why = course_unavailable(cfg)
    if why:
        print(why, file=sys.stderr)
        raise SystemExit(2)
    if not os.path.exists(os.path.join(crate, "Cargo.toml")):
        print("no crate at %s" % crate, file=sys.stderr)
        raise SystemExit(2)
    argv, agg, version = course_config(cfg)
    env = mc.cargo_env({"RUSTUP_TOOLCHAIN": mc.TOOLCHAIN})
    env.pop("RUSTC_WRAPPER", None)
    copy = mc.copy_crate(crate)
    findings, summary, side = [], None, {}
    try:
        # its own process group, like mc.cargo: on a timeout the whole tree (cargo, cargo-newmetrics, rustc) is
        # killed before the copy is removed under it
        proc = subprocess.Popen(argv, cwd=copy, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, start_new_session=True)
        try:
            raw_bytes, _ = proc.communicate(timeout=COURSE_TIMEOUT_S)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                proc.kill()
            raw_bytes, _ = proc.communicate()
            code, raw_bytes = 124, (raw_bytes or b"") + b"\n[mp4] course tool timed out\n"
        raw = raw_bytes.decode("utf-8", "replace")
        totals, units = parse_course_output(raw)
        if code != 0 or units == 0:
            findings.append({"kind": "course_tool_failed", "file": "",
                             "detail": "exit %d, %d compilation unit(s) reported" % (code, units)})
        elif agg and os.path.isfile(agg):
            try:
                agg_code = subprocess.run([sys.executable, "-I", agg, "--out", "summary.json"], cwd=copy, env=env,
                                          input=raw_bytes, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                          timeout=AGGREGATE_TIMEOUT_S).returncode
            except subprocess.TimeoutExpired:
                agg_code = 124
            try:
                with open(os.path.join(copy, "summary.json"), encoding="utf-8") as fh:
                    summary = json.load(fh)
            except (OSError, ValueError):
                summary = None
            if agg_code != 0 or not isinstance(summary, dict) or any(
                    summary.get(k) != totals[k] for k in COURSE_LABELS):
                summary = None
                findings.append({"kind": "course_tool_failed", "file": "",
                                 "detail": "aggregate.py exit %d; its summary.json does not equal the summed "
                                           "metric lines" % agg_code})
        for name in COURSE_SIDE_FILES:
            p = os.path.join(copy, name)
            if os.path.isfile(p) and not os.path.islink(p):
                side[name] = _scrub_course(mc.read_text(p), copy)
        raw = _scrub_course(raw, copy)
    finally:
        shutil.rmtree(os.path.dirname(copy), ignore_errors=True)   # copy_crate's temp parent
    ok = not findings
    metrics = {k: (totals[k] if ok else None) for k in PRIMARY}
    for k in PRIMARY:
        if ok and totals[k]:
            findings.append({"kind": k, "file": "", "count": totals[k]})
    extra = {"exit_code": code, "compilation_units": units,
             "targets": re.findall(r"^Target name: (.+)$", raw, re.M),
             "unsupported_targets": re.findall(r"^Target (\S+) is not supported$", raw, re.M),
             "aggregate": "staff aggregate.py" if summary is not None else (
                 "summed by the adapter (no aggregate.py at safety.course_aggregate)"
                 if agg and not os.path.isfile(agg) else "summed by the adapter")}
    if ok:
        extra.update({k: totals[k] for k in ("raw_pointer_dereferences", "raw_pointer_declarations", "total_spans")})
    if keep_dir:
        tag = keep_tag or "final"
        os.makedirs(keep_dir, exist_ok=True)
        files = {"raw_%s.txt" % tag: raw}
        if ok:
            # the staff summary.json when it was produced; otherwise the same fields from the summed lines
            files["summary_%s.json" % tag] = json.dumps(summary if summary is not None else totals, indent=2) + "\n"
        for name, body in side.items():
            files[name if tag == "final" else "%s.%s" % (tag, name)] = body
        for name, body in files.items():
            with open(os.path.join(keep_dir, name), "w", encoding="utf-8") as fh:
                fh.write(body)
    else:
        extra["raw_output"] = raw[-20000:]
    res = {"tool": "course", "tool_version": version, "extra": extra, "findings": findings, "raw_path": raw_path}
    res.update(metrics)
    _write(res, raw_path)
    return res


def both(crate, log_dir=None, source=None, cfg=None):
    """Proxy plus course tool (`safety.tool: both`). The four reported metrics are the course tool's. The proxy
    still runs for what the course tool does not look at: the forbid line, the `-D unsafe_code` build, FFI,
    build.rs and dependencies. Where the course tool cannot run (not installed, or it failed) the result says so
    in a finding that blocks SUCCESS, and the reported metrics fall back to the proxy's."""
    p = proxy(crate, raw_path=os.path.join(log_dir, "safety_proxy.json") if log_dir else None, source=source)
    proxy_metrics = {k: p[k] for k in PRIMARY}
    findings = list(p["findings"])
    extra = dict(p["extra"])
    extra["proxy"] = dict(proxy_metrics, tool_version=PROXY_VERSION)
    why = course_unavailable(cfg)
    c = None
    if why:
        findings.append({"kind": "course_tool_unavailable", "file": "", "detail": why})
    else:
        c = course(crate, raw_path=os.path.join(log_dir, "safety_course.json") if log_dir else None, cfg=cfg,
                   keep_dir=log_dir, keep_tag="course" if log_dir else None)
        findings += [f for f in c["findings"] if f["kind"] == "course_tool_failed"]
    official = c is not None and all(c[k] is not None for k in PRIMARY)
    if c is not None:
        extra["course"] = dict({k: c[k] for k in PRIMARY}, tool_version=c["tool_version"],
                               **{k: v for k, v in c["extra"].items() if k != "raw_output"})
    metrics = {k: c[k] for k in PRIMARY} if official else proxy_metrics
    extra["proxy_equals_course"] = (metrics == proxy_metrics) if official else None
    res = {"tool": "both" if official else "proxy",
           "tool_version": "%s + %s" % (c["tool_version"], PROXY_VERSION) if official else PROXY_VERSION,
           "extra": extra, "findings": findings,
           "raw_path": os.path.join(log_dir, "safety_course.json") if (log_dir and official) else p["raw_path"]}
    res.update(metrics)
    return res


def measure(tool, crate, log_dir=None, source=None):
    """The pipeline's safety step for the configured safety.tool."""
    if tool == "both":
        return both(crate, log_dir, source)
    return proxy(crate, raw_path=os.path.join(log_dir, "safety_proxy.json") if log_dir else None, source=source)


def snapshot_crate(project, snap, parent):
    """A buildable crate for one iteration snapshot: the benchmark skeleton's Cargo.toml and Cargo.lock with the
    snapshot (the iteration's whole src/) as its src/. Returns the crate path under parent."""
    crate = os.path.join(parent, os.path.basename(mc.translation_dir(project)))
    os.makedirs(crate)
    for name in ("Cargo.toml", "Cargo.lock"):
        src = os.path.join(mc.skeleton_dir(project), name)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(crate, name))
    shutil.copytree(snap, os.path.join(crate, "src"), symlinks=True)
    return crate


def final_run_snapshots(project):
    """(run_summary, [(iteration dir name, src_after path)]) of the project's final run, in run order."""
    traj = os.path.join(mc.TRAJECTORIES_DIR, project)
    with open(os.path.join(traj, "run_summary.json"), encoding="utf-8") as fh:
        rsum = json.load(fh)
    run_id = rsum.get("run_id")
    if not isinstance(run_id, str) or not re.match(r"^[A-Za-z0-9_.-]{1,64}$", run_id):
        raise ValueError("%s run_summary.json has no valid run_id" % project)
    run_dir = os.path.join(traj, "run_%s" % run_id)
    snaps = []
    for it in sorted((d for d in os.listdir(run_dir) if integrity._ITER_DIR_RE.match(d)), key=integrity._iter_key):
        snap = os.path.join(run_dir, it, "src_after")
        if os.path.isdir(snap):
            snaps.append((it, snap))
    return rsum, snaps


def official(project, date=None, cfg=None):
    """Measure the committed translation and every iteration snapshot of the final run with the course tool.
    Raw outputs and an index go to trajectories/<project>/official_safety/<date>/, and the totals are recorded
    in run_summary.json under `official_safety` (the run's own `final` block, measured by the proxy at run time,
    is left as it was). Nothing under MP4/translations/ is written."""
    date = date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise ValueError("date must be YYYY-MM-DD")
    why = course_unavailable(cfg)
    if why:   # before anything is touched: an earlier measurement of the same date stays as it is
        raise ValueError(why)
    traj = os.path.join(mc.TRAJECTORIES_DIR, project)
    rsum, snaps = final_run_snapshots(project)
    final_dir = os.path.join(traj, "official_safety", date)
    os.makedirs(os.path.dirname(final_dir), exist_ok=True)
    # measured into a sibling temporary directory, which replaces <date>/ only when every measurement succeeded
    out_dir = tempfile.mkdtemp(prefix=".%s.tmp_" % date, dir=os.path.dirname(final_dir))
    try:
        return _official(project, date, cfg, traj, rsum, snaps, out_dir, final_dir)
    finally:
        shutil.rmtree(out_dir, ignore_errors=True)


def _official(project, date, cfg, traj, rsum, snaps, out_dir, final_dir):
    _, _, version = course_config(cfg)

    def entry(res):
        e = {k: res[k] for k in PRIMARY}
        e.update({k: res["extra"].get(k) for k in ("raw_pointer_dereferences", "raw_pointer_declarations",
                                                   "total_spans", "compilation_units", "targets",
                                                   "unsupported_targets", "exit_code")})
        e["failed"] = any(f["kind"] == "course_tool_failed" for f in res["findings"])
        return e

    final = entry(course(mc.translation_dir(project), cfg=cfg, keep_dir=out_dir, keep_tag="final"))
    final["crate"] = mc.rel(mc.translation_dir(project), mc.REPO_DIR)
    iterations = {}
    for it, snap in snaps:
        tmp = tempfile.mkdtemp(prefix="mp4snap_")
        try:
            iterations[it] = entry(course(snapshot_crate(project, snap, tmp), cfg=cfg, keep_dir=out_dir,
                                          keep_tag=it))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
        iterations[it]["snapshot"] = mc.rel(snap, mc.REPO_DIR)
    bad = [tag for tag, e in [("final", final)] + sorted(iterations.items()) if e["failed"]]
    if bad:
        raise ValueError("the course tool failed for %s (%s); nothing was recorded, run_summary.json and %s are "
                         "unchanged" % (project, ", ".join(bad), mc.rel(final_dir, mc.REPO_DIR)))
    index = {"project": project, "run_id": rsum["run_id"], "tool": "course", "tool_version": version,
             "measured": date, "dir": mc.rel(final_dir, mc.REPO_DIR), "final": final, "iterations": iterations,
             "note": "Measured after the run, each on a temporary copy. An iteration is its src_after/ snapshot "
                     "with the benchmark's Cargo.toml and Cargo.lock. The tool rewrites its three span files for "
                     "every compilation unit, so they hold the last unit's spans only."}
    with open(os.path.join(out_dir, "official_safety.json"), "w", encoding="utf-8") as fh:
        json.dump(index, fh, indent=2)
        fh.write("\n")
    if os.path.isdir(final_dir):
        shutil.rmtree(final_dir)
    os.replace(out_dir, final_dir)
    rsum["official_safety"] = {k: index[k] for k in ("tool", "tool_version", "measured", "dir", "final")}
    rsum["official_safety"]["iterations"] = {it: {k: e[k] for k in PRIMARY} for it, e in iterations.items()}
    path = os.path.join(traj, "run_summary.json")
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(rsum, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, path)
    return index


def _write(res, raw_path):
    if raw_path:
        os.makedirs(os.path.dirname(os.path.abspath(raw_path)), exist_ok=True)
        with open(raw_path, "w", encoding="utf-8") as fh:
            json.dump(res, fh, indent=2)


def all_snapshots(project, tool):
    """Run the chosen tool over every trajectories/project_N/run_*/iter_*/src_after/ snapshot (no build)."""
    traj = os.path.join(mc.TRAJECTORIES_DIR, project)
    out = []
    if not os.path.isdir(traj):
        return out
    for run in sorted(d for d in os.listdir(traj) if d.startswith("run_") and os.path.isdir(os.path.join(traj, d))):
        run_dir = os.path.join(traj, run)   # (run_summary.json also starts with run_: review 3 D10, fixed at M16)
        for it in sorted((d for d in os.listdir(run_dir) if integrity._ITER_DIR_RE.match(d)),
                         key=integrity._iter_key):
            snap = os.path.join(run_dir, it, "src_after")
            if not os.path.isdir(snap):
                continue
            if tool == "course":
                tmp = tempfile.mkdtemp(prefix="mp4snap_")
                try:
                    res = course(snapshot_crate(project, snap, tmp))
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)
            else:
                # a snapshot is the crate's src/ only: lay it out as <tmp>/src so the same scan applies
                tmp = tempfile.mkdtemp(prefix="mp4snap_")
                try:
                    crate = os.path.join(tmp, "crate")
                    shutil.copytree(snap, os.path.join(crate, "src"))
                    res = proxy(crate, build=False)
                finally:
                    shutil.rmtree(tmp, ignore_errors=True)
            out.append({"run": run, "iter": it, "result": res})
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Safety metrics for generated Rust (interim proxy and the course tool).")
    ap.add_argument("--tool", choices=("proxy", "course", "both"), default="proxy")
    ap.add_argument("--project")
    ap.add_argument("--crate-dir", help="default: MP4/translations/<project>")
    ap.add_argument("--out", help="write the JSON result here")
    ap.add_argument("--all-snapshots", action="store_true", help="every iter_*/src_after/ of the project")
    ap.add_argument("--no-build", action="store_true", help="proxy: skip the -D unsafe_code build")
    ap.add_argument("--official", action="store_true",
                    help="course tool on the final translation and every iteration snapshot of the final run; "
                         "writes trajectories/<project>/official_safety/<date>/ and run_summary.json")
    ap.add_argument("--date", help="--official: directory name, YYYY-MM-DD (default: today, UTC)")
    a = ap.parse_args(argv)
    if a.official:
        if not a.project:
            ap.error("--official needs --project")
        try:
            res = official(mc.check_project(a.project), a.date)
        except (ValueError, OSError) as exc:
            print("safety_check: %s" % exc, file=sys.stderr)
            return 2
        print(json.dumps(res, indent=2))
        return 0
    if a.all_snapshots:
        if not a.project:
            ap.error("--all-snapshots needs --project")
        res = all_snapshots(mc.check_project(a.project), "course" if a.tool == "both" else a.tool)
        _write(res, a.out)
        print(json.dumps(res, indent=2))
        return 0
    if a.crate_dir:
        crate = os.path.abspath(a.crate_dir)
    elif a.project:
        crate = mc.translation_dir(a.project)
    else:
        ap.error("give --project or --crate-dir")
    if a.tool == "course":
        res = course(crate, a.out)
    elif a.tool == "both":
        res = both(crate, source=mc.skeleton_dir(a.project) if a.project else None)
        _write(res, a.out)
    else:
        if not os.path.exists(os.path.join(crate, "Cargo.toml")):
            print("no crate at %s" % crate, file=sys.stderr)
            return 2
        source = mc.skeleton_dir(a.project) if a.project else None
        res = proxy(crate, a.out, build=not a.no_build, source=source)
    print(json.dumps(res, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
