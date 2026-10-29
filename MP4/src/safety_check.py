"""Safety metrics for generated Rust (why.md R-T3-*-SAFETY, Z3, Z4, D6).

--tool proxy  (interim, D6): asserts `#![forbid(unsafe_code)]` is the first
              non-comment line of src/lib.rs, builds a temp copy with
              RUSTFLAGS="-D unsafe_code", and counts the four primary metrics
              with brace-tracked regexes over library code only (src/bin and
              src/interfaces are benchmark infrastructure and excluded, as in
              the handout). Regex-level by design: the course tool replaces it.
--tool course (M12): runs configs/pipeline.yaml safety.course_cmd; fails
              loudly while it is not configured.

Output schema (both tools): {tool, tool_version, unsafe_lines, unsafe_calls,
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
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402

PROXY_VERSION = "proxy-1"
COURSE_NOT_CONFIGURED = "course safety tool not configured"

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


def course(crate, raw_path=None):
    """Run the course unsafe-metrics tool. Raises SystemExit(2) while it is not configured."""
    cfg = mc.load_pipeline_config().get("safety") or {}
    cmd = cfg.get("course_cmd")
    if not cmd:
        print(COURSE_NOT_CONFIGURED + " (set safety.course_cmd in MP4/configs/pipeline.yaml)", file=sys.stderr)
        raise SystemExit(2)
    argv = shlex.split(cmd) if isinstance(cmd, str) else [str(x) for x in cmd]
    argv = [a.replace("{crate}", crate) for a in argv]
    proc = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=mc.cargo_env())
    out = proc.stdout.decode("utf-8", "replace")
    # The adapter that maps the course tool's output onto the schema is M12's job.
    res = {"tool": "course", "tool_version": cfg.get("course_version"), "unsafe_lines": None,
           "unsafe_calls": None, "unsafe_casts": None, "pointer_arithmetic": None,
           "extra": {"exit_code": proc.returncode, "raw_output": out[-20000:]}, "findings": [],
           "raw_path": raw_path}
    _write(res, raw_path)
    return res


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
    for run in sorted(d for d in os.listdir(traj) if d.startswith("run_")):
        run_dir = os.path.join(traj, run)
        for it in sorted(d for d in os.listdir(run_dir) if re.match(r"^iter_\d+", d)):
            snap = os.path.join(run_dir, it, "src_after")
            if not os.path.isdir(snap):
                continue
            if tool == "course":
                res = course(snap)
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
    ap = argparse.ArgumentParser(description="Safety metrics for generated Rust (proxy now, course tool later).")
    ap.add_argument("--tool", choices=("proxy", "course"), default="proxy")
    ap.add_argument("--project")
    ap.add_argument("--crate-dir", help="default: MP4/translations/<project>")
    ap.add_argument("--out", help="write the JSON result here")
    ap.add_argument("--all-snapshots", action="store_true", help="every iter_*/src_after/ of the project")
    ap.add_argument("--no-build", action="store_true", help="proxy: skip the -D unsafe_code build")
    a = ap.parse_args(argv)
    if a.all_snapshots:
        if not a.project:
            ap.error("--all-snapshots needs --project")
        res = all_snapshots(mc.check_project(a.project), a.tool)
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
