"""Build, test and clippy checks for one crate directory, using the pinned toolchain.

Every function takes the crate directory and a log directory, writes the raw
cargo output under the names from the design reference (build.log, test.log,
clippy_rubric.log, clippy_<group>.json), and returns a plain dict.

The functions run cargo in place and `touch src/lib.rs` between clippy runs.
Callers that must not touch a directory (e.g. --check-only on committed
translations) pass a copy (mp4common.copy_crate).
"""
import collections
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402

_ERR_RE = re.compile(r"^error(\[(E\d{4})\])?: (.*)$", re.M)
_TEST_LINE_RE = re.compile(r"^test (.+?) \.\.\. (ok|FAILED|ignored)\s*$")   # names may hold spaces (doc tests)
# Output a test writes to stdout itself is not captured by libtest. libpsbt's hex printer ends without a newline,
# so it lands in front of libtest's own `test NAME ... ok` line. Such a glued line is read for benchmark names only.
_GLUED_RE = re.compile(r"test (\S+) \.\.\. (ok|FAILED|ignored)\s*$")
_STATUS_END = ("ok", "FAILED", "ignored")
_TEST_FN_RE = re.compile(r"#\s*\[\s*test\s*\]\s*(?:#\s*\[[^\]]*\]\s*)*(?:pub(?:\s*\([^)]*\))?\s+)?fn\s+([A-Za-z_]\w*)")
_RUNNING_RE = re.compile(r"^\s+Running (.+)$", re.M)
_SUMMARY_RE = re.compile(r"^warning: `[^`]+` \([^)]*\) generated \d+ warnings?.*$", re.M)


def _errors(out):
    errs = []
    for m in _ERR_RE.finditer(out):
        msg = m.group(3)
        if msg.startswith("could not compile") or msg.startswith("aborting due to"):
            continue
        errs.append({"code": m.group(2), "message": msg})
    return errs


def _first_error_block(out, limit=40):
    lines = out.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("error"):
            return "\n".join(lines[idx:idx + limit])
    return ""


def run_build(crate, log_dir):
    """`cargo build --all-targets --locked` -> build.log."""
    log = os.path.join(log_dir, "build.log")
    code, out = mc.cargo(["build", "--all-targets", "--locked"], crate, log)
    errs = _errors(out)
    return {
        "ok": code == 0,
        "exit_code": code,
        "error_count": len(errs),
        "error_codes": sorted({e["code"] for e in errs if e["code"]}),
        "errors": errs[:50],
        "first_error": _first_error_block(out),
        "log": log,
    }


def parse_test_output(out, expected=None):
    """Per-test results keyed by test name. The same name can run in several
    executables (libpsbt runs src/bin/test.rs as a bin harness and as [[test]],
    why.md H-L10): a test passes only if every execution passed.

    Only the output from cargo's first `Running` line on is read: the compile output before it can quote any
    source text, a `test x ... ok` comment included. A line that does not start with `test ` counts only when
    it ends in a result for one of the expected benchmark names (output glued in front, see _GLUED_RE)."""
    tests = collections.OrderedDict()
    first = _RUNNING_RE.search(out)
    expected = set(expected or ())
    for line in (out[first.start():] if first else "").splitlines():
        m = _TEST_LINE_RE.match(line)
        if m is None and expected and line.rstrip().endswith(_STATUS_END):
            g = _GLUED_RE.search(line)
            m = g if g and g.group(1) in expected else None
        if m is None:
            continue
        name, status = m.group(1), m.group(2)
        entry = tests.setdefault(name, {"status": status, "executions": 0, "panic": None})
        entry["executions"] += 1
        if status == "FAILED" or entry["status"] == "FAILED":
            entry["status"] = "FAILED"
    # panic text: "---- name stdout ----" sections
    for m in re.finditer(r"^---- (.+?) stdout ----\n(.*?)(?=^---- |^failures:|\Z)", out, re.M | re.S):
        name = m.group(1)
        if name in tests and tests[name]["panic"] is None:
            tests[name]["panic"] = m.group(2).strip()[:2000]
    return tests


def benchmark_tests(source):
    """Names of the #[test] fns in the benchmark's immutable test files (source/src/bin/*.rs).

    They sit at the top level of each bin target, so these are the names cargo test prints."""
    names = set()
    bin_dir = os.path.join(source, "src", "bin")
    if os.path.isdir(bin_dir):
        for p in mc.walk_files(bin_dir):
            if p.endswith(".rs"):
                names.update(_TEST_FN_RE.findall(rustlex.strip(mc.read_text(p))))
    return sorted(names)


def run_test(crate, log_dir, expected=None):
    """`cargo test --locked --no-fail-fast` -> test.log, with per-test status and panic text.

    expected: the benchmark test names (benchmark_tests()). When given, passed/failed/total count only
    those. A benchmark test with no result line (it hung until the cargo timeout, or its executable
    crashed) is listed in missing_names and is not passed. Tests the agent wrote itself are reported in
    extra_tests and never change the benchmark counts. Without expected, every test that ran counts.
    """
    log = os.path.join(log_dir, "test.log")
    code, out = mc.cargo(["test", "--locked", "--no-fail-fast"], crate, log)
    tests = parse_test_output(out, expected)
    names = list(tests) if expected is None else list(expected)
    status = {n: (tests.get(n) or {}).get("status") for n in names}
    passed = sorted(n for n in names if status[n] == "ok")
    failed = sorted(n for n in names if status[n] == "FAILED")
    ignored = sorted(n for n in names if status[n] == "ignored")
    missing = sorted(n for n in names if status[n] is None)
    return {
        "compiled": bool(_RUNNING_RE.search(out)),
        "exit_code": code,
        "timed_out": code == mc.TIMEOUT_EXIT,
        "passed": len(passed),
        "failed": len(failed),
        "ignored": len(ignored),
        "missing": len(missing),
        "total": len(names),
        "passed_names": passed,
        "failed_names": failed,
        "missing_names": missing,
        "extra_tests": {n: t["status"] for n, t in tests.items() if n not in status},
        "tests": tests,
        "executables": _RUNNING_RE.findall(out),
        "first_error": "" if _RUNNING_RE.search(out) else _first_error_block(out),
        "log": log,
    }


def run_clippy_rubric(crate, log_dir):
    """The exact rubric command -> clippy_rubric.log (text, as graders will see it)."""
    log = os.path.join(log_dir, "clippy_rubric.log")
    lib = os.path.join(crate, "src", "lib.rs")
    if os.path.exists(lib):
        mc.touch(lib)
    code, out = mc.cargo(mc.RUBRIC_CLIPPY_ARGS, crate, log)
    return {
        "exit_code": code,
        "summary_lines": _SUMMARY_RE.findall(out),
        "error_count": len(_errors(out)),
        "log": log,
    }


def _origin(file_name):
    f = (file_name or "").replace(os.sep, "/")
    if f.startswith("/") or f.startswith("~"):
        return "external"
    if any(f.startswith(p) for p in mc.HARNESS_PREFIXES):
        return "harness"
    return "agent"


def parse_clippy_json(text):
    """Unique warning sites from cargo --message-format=json output.

    A site is (lint, file, line, column). cargo reports a lib's warnings once
    per target (lib, lib test); those duplicates collapse here.
    """
    sites = collections.OrderedDict()
    errors = 0
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            d = json.loads(line)
        except ValueError:
            continue
        if d.get("reason") != "compiler-message":
            continue
        m = d.get("message") or {}
        if m.get("level") == "error":
            errors += 1
            continue
        if m.get("level") != "warning" or not m.get("code"):
            continue
        spans = [s for s in m.get("spans", []) if s.get("is_primary")] or m.get("spans", [])
        f, ln, col = (spans[0]["file_name"], spans[0]["line_start"], spans[0]["column_start"]) if spans else ("?", 0, 0)
        key = (m["code"]["code"], f, ln, col)
        if key not in sites:
            sites[key] = {"lint": key[0], "file": f, "line": ln, "column": col,
                          "origin": _origin(f), "message": m.get("message", "")}
    return list(sites.values()), errors


def run_clippy_groups(crate, log_dir):
    """Four runs `-A clippy::all -W clippy::<group>` -> clippy_<group>.json.

    Attribution by primary span path: src/bin/* = harness, else agent. Rustc
    (non-clippy) warnings are counted from the first run alongside.
    """
    lib = os.path.join(crate, "src", "lib.rs")
    result = {"groups": {}, "rustc": None, "agent_total": 0, "harness_total": 0, "errors": 0}
    for idx, group in enumerate(mc.CLIPPY_GROUPS):
        log = os.path.join(log_dir, "clippy_%s.json" % group)
        if os.path.exists(lib):
            mc.touch(lib)
        args = ["clippy", "--all-targets", "--all-features", "--message-format=json", "--",
                "-A", "clippy::all", "-W", "clippy::%s" % group]
        code, out = mc.cargo(args, crate, log)
        sites, errors = parse_clippy_json(out)
        result["errors"] = max(result["errors"], errors)
        clippy_sites = [s for s in sites if s["lint"].startswith("clippy::")]
        g = {"exit_code": code, "agent": 0, "harness": 0, "external": 0, "lints": {}, "sites": clippy_sites,
             "log": log}
        for s in clippy_sites:
            g[s["origin"]] += 1
            per = g["lints"].setdefault(s["lint"], {"agent": 0, "harness": 0, "external": 0})
            per[s["origin"]] += 1
        result["groups"][group] = g
        result["agent_total"] += g["agent"]
        result["harness_total"] += g["harness"]
        if idx == 0:
            rustc_sites = [s for s in sites if not s["lint"].startswith("clippy::")]
            r = {"agent": 0, "harness": 0, "external": 0, "lints": {}, "sites": rustc_sites}
            for s in rustc_sites:
                r[s["origin"]] += 1
                per = r["lints"].setdefault(s["lint"], {"agent": 0, "harness": 0, "external": 0})
                per[s["origin"]] += 1
            result["rustc"] = r
    result["ok"] = result["errors"] == 0
    return result


def run_all(crate, log_dir, expected_tests=None):
    """Build, test, rubric clippy, per-group clippy. Clippy is skipped when the build fails.
    expected_tests: the benchmark test names, see run_test()."""
    os.makedirs(log_dir, exist_ok=True)
    out = {"build": run_build(crate, log_dir)}
    out["test"] = run_test(crate, log_dir, expected_tests)
    if out["build"]["ok"]:
        out["clippy_rubric"] = run_clippy_rubric(crate, log_dir)
        out["clippy"] = run_clippy_groups(crate, log_dir)
    else:
        out["clippy_rubric"] = None
        out["clippy"] = None
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Run build/test/clippy checks on a crate directory (in place).")
    ap.add_argument("crate_dir")
    ap.add_argument("--log-dir", required=True)
    a = ap.parse_args()
    print(json.dumps(run_all(os.path.abspath(a.crate_dir), os.path.abspath(a.log_dir)), indent=2))
