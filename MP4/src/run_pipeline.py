"""MP4 C-to-Rust agentic translation pipeline — entry point.

Usage:
  python3 -I MP4/src/run_pipeline.py --project project_N --check-only [--crate-dir DIR] [--out FILE]

--check-only reruns every measurement without a model, on a temp copy of the
crate (default MP4/translations/project_N), and writes
MP4/results/project_N.check.json plus its logs next to it. It never modifies
the crate it measures.

--dry-run prints the exact claude argv and the composed iteration-1 prompt
(no model call). --smoke runs the two isolation smoke calls (D7 allows 3 in
total, counted in docs/programs/mp4/evidence/smoke/calls.log) and writes the
evidence there.

Without a mode flag it runs the iteration loop: workspace init, then per
iteration prompt -> agent -> integrity/checks/safety/interface/hard-coding ->
snapshot and summary -> stop or relaunch. Stop conditions: SUCCESS,
MAX_ITERATIONS, NO_PROGRESS (score not improved for loop.no_progress_rounds
iterations), ABORT (integrity violations in two consecutive iterations),
ABORT_ISOLATION, AUTH_ERROR. A usage-limit rejection pauses until resets_at
(rate_limit.mode wait) or exits 75 with the --resume-run command (exit), and
redoes the iteration as iter_KK_attemptN. --resume-run re-enters at the step
recorded in run_state.json. A real run asks for confirmation unless --yes.
"""
import argparse
import datetime
import difflib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent_runner  # noqa: E402
import check_interface  # noqa: E402
import checks  # noqa: E402
import config  # noqa: E402
import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import prompt_builder  # noqa: E402
import safety_check  # noqa: E402
import scrub_secrets  # noqa: E402

SMOKE_DIR = os.path.join(mc.REPO_DIR, "docs", "programs", "mp4", "evidence", "smoke")
SMOKE_BUDGET = 3          # D7: at most 3 smoke calls in total
SMOKE_MAX_TURNS = 2       # D7: --max-turns <= 2 per smoke call
SMOKE_CALLS = [
    ("a", "List every tool you have, your permission mode, and any project instructions or memory you were given."),
    ("b", "Run `cargo +nightly-2025-05-13 --version` and then `git status`, each as its own Bash call, "
          "and report both outputs."),
]
# Distinctive phrases from the owner's ~/.claude/CLAUDE.md, the repo CLAUDE.md and auto-memory. None may
# appear in an isolated agent's answer (C4, C9). Not the repo name: it is part of the --add-dir path the
# agent legitimately sees (smoke 2026-10-29 false positive).
LEAK_MARKERS = ["Working agreement", "Build forward", "program-builder", "commit-only", "mp4-program",
                "one phase per session", "MP4 group and framework", "forum post", "owner gate",
                "MP1-MP3", "Jacob and Ross"]


def build_parser():
    ap = argparse.ArgumentParser(
        prog="run_pipeline.py",
        description="MP4 agentic C-to-Rust translation pipeline (Group 1: satc = project_1, libpsbt = project_2).")
    ap.add_argument("--project", required=True, choices=mc.PROJECTS, help="which assigned project")
    ap.add_argument("--check-only", action="store_true",
                    help="no model: rerun build/test/clippy/safety/interface/integrity checks and write "
                         "MP4/results/<project>.check.json")
    ap.add_argument("--crate-dir", help="with --check-only: crate to measure (default MP4/translations/<project>)")
    ap.add_argument("--out", help="with --check-only: output JSON path (default MP4/results/<project>.check.json)")
    ap.add_argument("--yes", action="store_true", help="start a real run without the confirmation prompt")
    ap.add_argument("--dry-run", action="store_true",
                    help="print the agent command line and the iteration-1 prompt; no model call")
    ap.add_argument("--smoke", action="store_true",
                    help="two isolation smoke calls, at most 2 turns each (counted against the smoke budget)")
    ap.add_argument("--resume-run", metavar="RUN_ID", help="continue an interrupted or paused run at its recorded step")
    ap.add_argument("--run-id", metavar="ID", help="run id for a new run (default: UTC timestamp)")
    ap.add_argument("--smoke-probe", action="store_true",
                    help="one permission-probe call (counted against the smoke budget)")
    ap.add_argument("--claude-bin", help="override agent.claude_bin (tests)")
    return ap


def _toolchain_version():
    code, out = mc.cargo(["--version"], mc.MP4_DIR, timeout=60)
    return out.strip() if code == 0 else None


def _scrub_paths(text, work, log_dir=None, crate_label="<crate>"):
    """Crate path -> crate_label, log dir -> its repo-relative path, then secrets, e-mails and home paths (Z10).
    macOS reports a temp dir both as /var/... and as /private/var/..., so both spellings are replaced."""
    for path, label in ((work, crate_label), (log_dir, mc.rel(log_dir, mc.REPO_DIR) if log_dir else None)):
        if path:
            for p in sorted({os.path.realpath(path), path}, key=len, reverse=True):
                text = text.replace(p, label)
    return scrub_secrets.scrub_text(text)


def _scrub_logs(log_dir, work, names=None, crate_label="<crate>"):
    """Rewrite the logs measure_crate wrote (cargo output carries absolute paths) through _scrub_paths."""
    for name in names if names is not None else os.listdir(log_dir):
        p = os.path.join(log_dir, name)
        if os.path.isfile(p):
            body = mc.read_text(p)
            new = _scrub_paths(body, work, log_dir, crate_label)
            if new != body:
                with open(p, "w", encoding="utf-8") as fh:
                    fh.write(new)


def check_only(project, crate, out_path):
    source = mc.skeleton_dir(project)
    out_path = os.path.abspath(out_path)
    log_dir = out_path[:-5] + ".logs" if out_path.endswith(".json") else out_path + ".logs"
    if os.path.isdir(log_dir):
        shutil.rmtree(log_dir)
    os.makedirs(log_dir)
    tmp = tempfile.mkdtemp(prefix="mp4check_")
    try:
        work = mc.copy_crate(crate, tmp)
        res = {
            "project": project,
            "crate": mc.rel(crate, mc.REPO_DIR),
            "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "toolchain": _toolchain_version(),
            "subjects_checksums_ok": not integrity.verify_subjects(source),
        }
        res.update(measure_crate(work, source, log_dir))
        _scrub_logs(log_dir, work)
        text = _scrub_paths(json.dumps(res, indent=2), work, log_dir)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text + "\n")
    return json.loads(text)


def summarize(res):
    clippy = res.get("clippy") or {}
    groups = clippy.get("groups") or {}
    t = res["test"]
    return {
        "compiles": res["build"]["ok"],
        "build_error_codes": res["build"]["error_codes"],
        "tests_passed": t["passed"],
        "tests_total": t["total"],
        "clippy_agent": {g: groups[g]["agent"] for g in groups},
        "clippy_harness": {g: groups[g]["harness"] for g in groups},
        "clippy_agent_total": clippy.get("agent_total"),
        "safety": {k: res["safety"][k]
                   for k in ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic")},
        "safety_tool": res["safety"]["tool"],
        "interface_missing": res["interface"]["missing"],
        "interface_changed": res["interface"]["changed"],
        "integrity_violations": len(res["integrity"]["violations"]),
        "hardcode_hits": len(res["hardcode_hits"]),
    }


def dry_run(project, claude_bin=None):
    cfg = config.load(project)
    argv = agent_runner.build_argv(cfg, claude_bin=claude_bin)
    print("# config_hash %s" % cfg["config_hash"])
    print("# cwd %s" % mc.rel(cfg["workspace"], mc.REPO_DIR))
    print("# env %s" % " ".join("%s=%s" % kv for kv in sorted(cfg["pipeline"]["agent"]["env"].items())))
    print("# argv")
    print(scrub_secrets.scrub_text(" ".join(shlex.quote(a) for a in argv)))
    print("# prompt (stdin), iteration 1")
    print(scrub_secrets.scrub_text(prompt_builder.build_initial(cfg)))
    return 0


def _smoke_spent():
    log = os.path.join(SMOKE_DIR, "calls.log")
    if not os.path.exists(log):
        return 0
    with open(log, encoding="utf-8") as fh:
        return sum(1 for line in fh if "\tspent\t" in line)


def _assistant_text(stream_path):
    texts = []
    with open(stream_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "assistant":
                for c in (ev.get("message") or {}).get("content") or []:
                    if c.get("type") == "text":
                        texts.append(c.get("text", ""))
    return "\n".join(texts)


def _model_used(res, stream_path):
    """True if the call reached the model. Locally generated replies (model "<synthetic>", e.g. an auth
    failure) and calls killed at init report zero API time and zero tokens."""
    with open(stream_path, encoding="utf-8") as fh:
        for line in fh:
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("type") == "assistant" and (ev.get("message") or {}).get("model") != "<synthetic>":
                return True
    r = res.get("result") or {}
    usage = r.get("usage") or {}
    return bool(r.get("duration_api_ms") or usage.get("input_tokens") or usage.get("output_tokens"))


def _stream_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def smoke(project, claude_bin=None):
    cfg = config.load(project)
    spent = _smoke_spent()
    if spent + len(SMOKE_CALLS) > SMOKE_BUDGET:
        print("smoke refused: %d of %d D7 smoke calls already spent; %d more needed" % (
            spent, SMOKE_BUDGET, len(SMOKE_CALLS)), file=sys.stderr)
        return 3
    os.makedirs(SMOKE_DIR, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="mp4smoke_")
    report = {"project": project, "config_hash": cfg["config_hash"], "max_turns": SMOKE_MAX_TURNS, "calls": {}}
    try:
        for label, prompt in SMOKE_CALLS:
            stream = os.path.join(SMOKE_DIR, "call_%s.stream.jsonl" % label)
            argv = agent_runner.build_argv(cfg, max_turns=SMOKE_MAX_TURNS, claude_bin=claude_bin)
            res = agent_runner.run(cfg, argv, scratch, prompt, stream, wall_clock_s=600)
            # init arrives before any model turn; a call killed there (isolation mismatch) spent nothing,
            # and its abort result reports zero API time and zero tokens
            spent_flag = "spent" if _model_used(res, stream) else "not-spent"
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            with open(os.path.join(SMOKE_DIR, "calls.log"), "a", encoding="utf-8") as fh:
                fh.write("%s\t%s\tcall_%s\t%s\n" % (stamp, spent_flag, label, res["outcome"]))
            text = _assistant_text(stream)
            res["assistant_text"] = text
            res["leak_markers_found"] = [m for m in LEAK_MARKERS if m.lower() in text.lower()]
            res["prompt"] = prompt
            res["argv"] = argv
            report["calls"][label] = res
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    a, b = report["calls"]["a"], report["calls"]["b"]
    denials = (b.get("result") or {}).get("permission_denials") or []
    report["verdict"] = {
        "isolation_ok_a": not a["isolation_violations"] and a["init"] is not None,
        "isolation_ok_b": not b["isolation_violations"] and b["init"] is not None,
        "no_leak_markers": not a["leak_markers_found"] and not b["leak_markers_found"],
        "git_denied": any("git" in json.dumps(d) for d in denials),
        "cargo_version_seen": "1.89.0-nightly" in _stream_text(os.path.join(SMOKE_DIR, "call_b.stream.jsonl")),
    }
    out = os.path.join(SMOKE_DIR, "smoke_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(scrub_secrets.scrub_text(json.dumps(report, indent=2)) + "\n")
    print(json.dumps(report["verdict"], indent=2))
    print("wrote %s" % mc.rel(out, mc.REPO_DIR))
    return 0 if all(report["verdict"].values()) else 1


PROBE_DIR = os.path.join(SMOKE_DIR, "probe")


def _probe_prompt(outside, canary_file, c_dir):
    return (
        "This is a permissions test of your environment, not a translation task. In ONE message, issue ALL of "
        "the following tool calls at once (in parallel). Do not retry anything that is denied. Then give the "
        "structured status, listing each numbered call as allowed or denied in remaining_issues.\n"
        "1. Read `%(canary)s`.\n"
        "2. Bash: `cat %(canary)s`\n"
        "3. Bash: `ls %(outside)s | head -5`\n"
        "4. Glob with pattern `*` and path `%(outside)s`.\n"
        "5. Grep for `CANARY` with path `%(outside)s`.\n"
        "6. Read `%(c_dir)s/satc.h` (only the first 5 lines).\n"
        "7. Bash: `cargo +nightly-2025-05-13 --version`\n"
        "8. Write the file `probe_inside.txt` in your working directory with the content `ok`.\n"
        "9. Write the file `%(c_dir)s/PROBE_SHOULD_FAIL.txt` with the content `x`.\n"
        "10. Bash: `ls`\n" % {"canary": canary_file, "outside": outside, "c_dir": c_dir})


def probe_evaluate(cfg, stream, prompt, res, inside_written, stray_written, token, note=None):
    """Build and write probe_report.json from a saved probe stream. `token` is the canary text (or, when
    re-evaluating an old stream whose random token was not kept, its fixed prefix)."""
    body = _stream_text(stream)
    tool_calls, results = [], {}
    for line in body.splitlines():
        try:
            ev = json.loads(line)
        except ValueError:
            continue
        msg = ev.get("message")
        if not isinstance(msg, dict):  # e.g. system/permission_denied carries a plain-text message
            continue
        for c in msg.get("content") or []:
            if not isinstance(c, dict):
                continue
            if c.get("type") == "tool_use":
                tool_calls.append({"id": c.get("id"), "name": c.get("name"), "input": c.get("input")})
            elif c.get("type") == "tool_result":
                results[c.get("tool_use_id")] = {"is_error": bool(c.get("is_error")),
                                                 "content": json.dumps(c.get("content"))[:400]}
    for tc in tool_calls:
        tc["result"] = results.get(tc["id"])
    denials = (res.get("result") or {}).get("permission_denials") or []
    report = {
        "project": cfg["project"], "config_hash": cfg["config_hash"], "max_turns": SMOKE_MAX_TURNS,
        "outcome": res["outcome"], "init": res["init"], "isolation_violations": res["isolation_violations"],
        "result": res["result"], "tool_calls": tool_calls, "permission_denials": denials,
        "inside_write_created": inside_written, "subjects_write_created": stray_written,
        "canary_token": token, "canary_in_stream": token in body, "prompt": prompt, "note": note,
        "verdict": {
            "isolation_ok": not res["isolation_violations"] and res["init"] is not None,
            "canary_never_read": token not in body,
            "subjects_write_blocked": not stray_written,
            "inside_write_allowed": bool(inside_written),
            "cargo_allowed": "1.89.0-nightly" in body,
        },
    }
    out = os.path.join(os.path.dirname(stream), "probe_report.json")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write(scrub_secrets.scrub_text(json.dumps(report, indent=2)) + "\n")
    print(json.dumps(report["verdict"], indent=2))
    print("wrote %s" % mc.rel(out, mc.REPO_DIR))
    return report


def smoke_probe(project, claude_bin=None):
    """One call that tries reads outside the working dirs (a planted canary), read-only shell commands, a
    write into subjects/, and the allowed operations. Passes when every outside access is denied, the canary
    text never appears in the stream, and the allowed operations work."""
    import secrets
    cfg = config.load(project)
    spent = _smoke_spent()
    if spent + 1 > SMOKE_BUDGET:
        print("probe refused: %d of %d D7 smoke calls already spent" % (spent, SMOKE_BUDGET), file=sys.stderr)
        return 3
    os.makedirs(PROBE_DIR, exist_ok=True)
    scratch = tempfile.mkdtemp(prefix="mp4probe_")
    cwd = os.path.join(scratch, "crate")
    outside = os.path.join(scratch, "outside")
    os.makedirs(cwd)
    os.makedirs(outside)
    token = "MP4-CANARY-" + secrets.token_hex(8)
    canary_file = os.path.join(outside, "canary.txt")
    with open(canary_file, "w", encoding="utf-8") as fh:
        fh.write(token + "\n")
    stray = os.path.join(cfg["c_dir"], "PROBE_SHOULD_FAIL.txt")
    stream = os.path.join(PROBE_DIR, "call_probe.stream.jsonl")
    try:
        argv = agent_runner.build_argv(cfg, max_turns=SMOKE_MAX_TURNS, claude_bin=claude_bin)
        prompt = _probe_prompt(outside, canary_file, cfg["c_dir"])
        res = agent_runner.run(cfg, argv, cwd, prompt, stream, wall_clock_s=600)
        spent_flag = "spent" if _model_used(res, stream) else "not-spent"
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        with open(os.path.join(SMOKE_DIR, "calls.log"), "a", encoding="utf-8") as fh:
            fh.write("%s\t%s\tcall_probe\t%s\n" % (stamp, spent_flag, res["outcome"]))
        inside_written = os.path.exists(os.path.join(cwd, "probe_inside.txt"))
        stray_written = os.path.exists(stray)
        if stray_written:
            os.remove(stray)  # never leave a file in subjects/
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
    report = probe_evaluate(cfg, stream, prompt, res, inside_written, stray_written, token)
    print("tool calls: %d, permission denials: %d" % (len(report["tool_calls"]), len(report["permission_denials"])))
    return 0 if all(report["verdict"].values()) else 1


# ------------------------------------------------------------------------------------------------
# The iteration loop (what.md design reference, steps 0-9)
# ------------------------------------------------------------------------------------------------
STEPS = ("init", "prompt", "agent", "checks", "closed")   # run_state.json step cursor
EXIT_USAGE_LIMIT = 75
EXIT_INTERRUPTED = 143
MAX_LIMIT_ATTEMPTS = 3    # consecutive usage-limit attempts of one iteration before the run exits for a person
RUN_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")
STOP_SUCCESS = "SUCCESS"
STOP_MAX_ITERATIONS = "MAX_ITERATIONS"
STOP_NO_PROGRESS = "NO_PROGRESS"
STOP_ABORT = "ABORT"
STOP_ABORT_ISOLATION = "ABORT_ISOLATION"
STOP_AUTH_ERROR = "AUTH_ERROR"
NO_CLIPPY = 10 ** 6   # clippy count used in the score when the build failed and clippy could not run
MEASURE_LOGS = ("build.log", "test.log", "clippy_rubric.log", "safety_proxy.json")   # + clippy_<group>.json


class Interrupted(Exception):
    pass


def _on_signal(signum, _frame):
    raise Interrupted(signum)


def measure_crate(work, source, log_dir):
    """Build, test, clippy, safety, interface, integrity (report-only) and hard-coding for one crate.
    Tests are counted against the benchmark's own test names (source/src/bin), not whatever ran."""
    res = dict(checks.run_all(work, log_dir, checks.benchmark_tests(source)))
    res["safety"] = safety_check.proxy(work, raw_path=os.path.join(log_dir, "safety_proxy.json"), source=source)
    res["interface"] = check_interface.compare(os.path.join(source, "src", "interfaces"), work)
    res["integrity"] = {"violations": integrity.verify(work, source, restore=False)}
    res["hardcode_hits"] = integrity.hardcode_scan(work)
    res["summary"] = summarize(res)
    return res


def _build_error_count(check):
    """All build errors; check["build"]["errors"] keeps only the first 50 (a score on it stops moving)."""
    b = check["build"]
    return b.get("error_count", len(b["errors"]))


def evaluate(check, proj):
    """Success predicate (what.md stop rule SUCCESS, D8) and the progress score tuple for one iteration."""
    s = summarize(check)
    t = check["test"]
    failed = set(t["failed_names"])
    known = {k["name"]: k for k in proj["known_failing_tests"]}
    known_failing = {}
    for name, k in known.items():
        panic = ((t["tests"].get(name) or {}).get("panic")) or ""
        known_failing[name] = {"failed": name in failed,
                               "assertion_matches": k["expected_assertion"] in panic,
                               "location_matches": k["expected_location"] in panic}
    blockers = []
    if not s["compiles"]:
        blockers.append("build fails")
    unexpected = sorted(failed - set(known))
    if unexpected:
        blockers.append("failing tests: %s" % ", ".join(unexpected))
    missing = t.get("missing_names") or []
    if s["compiles"] and missing:
        blockers.append("tests with no result (hung, crashed or timed out): %s" % ", ".join(missing))
    added_failing = sorted(n for n, st in (t.get("extra_tests") or {}).items() if st == "FAILED")
    if added_failing:
        blockers.append("failing tests outside the benchmark: %s" % ", ".join(added_failing))
    if s["compiles"] and t.get("exit_code") not in (0, None) and not (failed or missing or added_failing):
        # cargo test failed, but no parsed result explains it (e.g. a doc test that does not compile)
        blockers.append("cargo test exited %d with no failing test parsed (see test.log)" % t["exit_code"])
    for name, v in known_failing.items():
        if not all(v.values()):
            blockers.append("known-failing test %s does not fail as documented" % name)
    if s["compiles"] and t["total"] == 0:
        blockers.append("no tests ran")
    clippy_total = s["clippy_agent_total"]
    if clippy_total is None or clippy_total > 0:
        blockers.append("agent clippy warnings: %s" % clippy_total)
    clippy_errors = (check.get("clippy") or {}).get("errors") or 0
    if s["compiles"] and clippy_errors:
        # a lint raised to an error in the source (e.g. #![deny(warnings)]) is not counted as a warning: the
        # warning count of a clippy run that failed is not a measurement
        blockers.append("clippy errors: %d" % clippy_errors)
    safety_total = sum(v for v in s["safety"].values())
    if safety_total:
        blockers.append("unsafe metrics: %d" % safety_total)
    for f in check["safety"]["findings"]:
        if f["kind"] in ("forbid_missing", "deny_unsafe_build_failed", "extern_c", "link_attr", "libc",
                         "cc_crate", "build_rs", "c_source", "new_dependency"):
            blockers.append("safety finding: %s" % f["kind"])
    if s["interface_missing"] or s["interface_changed"]:
        blockers.append("interface missing %d, changed %d" % (s["interface_missing"], s["interface_changed"]))
    if s["integrity_violations"]:
        blockers.append("integrity violations: %d" % s["integrity_violations"])
    if s["hardcode_hits"]:
        blockers.append("hard-coding hits: %d" % s["hardcode_hits"])
    score = [s["tests_passed"], -_build_error_count(check),
             -(clippy_total if clippy_total is not None else NO_CLIPPY), -safety_total,
             -(s["interface_missing"] + s["interface_changed"])]
    return {"success": not blockers, "blockers": blockers, "known_failing": known_failing,
            "safety_total": safety_total, "score": score}


class Run:
    """One pipeline run: paths, state persistence, logging."""

    def __init__(self, cfg, run_id):
        self.cfg = cfg
        self.p = cfg["pipeline"]
        self.proj = cfg["project_cfg"]
        self.traj = cfg["trajectory_root"]
        self.workspace = cfg["workspace"]
        self.skeleton = cfg["skeleton"]
        self.run_id = run_id
        self.dir = os.path.join(self.traj, "run_%s" % run_id)
        self.state_path = os.path.join(self.dir, "run_state.json")
        self.lock_path = os.path.join(self.dir, "run.lock")
        self.state = None

    def log(self, msg):
        line = "%s %s" % (_now(), msg)
        if not self.cfg.get("quiet"):
            print(line)
        with open(os.path.join(self.dir, "run.log"), "a", encoding="utf-8") as fh:
            fh.write(scrub_secrets.scrub_text(line) + "\n")

    def save(self):
        self.state["updated"] = _now()
        _write_json(self.state_path, self.state)

    def iter_dir(self, k, n):
        name = "iter_%02d" % k if n == 1 else "iter_%02d_attempt%d" % (k, n)
        return os.path.join(self.dir, name)

    def acquire_lock(self):
        if os.path.exists(self.lock_path):
            with open(self.lock_path, encoding="utf-8") as fh:
                try:
                    pid = int(fh.read().strip() or 0)
                except ValueError:
                    pid = 0
            if pid and pid != os.getpid() and _pid_alive(pid):
                raise SystemExit("run %s is locked by live process %d" % (self.run_id, pid))
        with open(self.lock_path, "w", encoding="utf-8") as fh:
            fh.write(str(os.getpid()))

    def release_lock(self):
        try:
            os.remove(self.lock_path)
        except FileNotFoundError:
            pass


def _now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_json(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(scrub_secrets.scrub_text(json.dumps(data, indent=2, sort_keys=True)) + "\n")
    os.replace(tmp, path)


def _read_json(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _cmd_version(argv):
    try:
        out = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=mc.cargo_env(),
                             timeout=60, check=False).stdout.decode("utf-8", "replace").strip()
        return out.splitlines()[0] if out else None
    except (OSError, subprocess.TimeoutExpired):
        return None


def real_run_count():
    """{project: number of real (kind claude) runs recorded under trajectories/}."""
    counts = {}
    for project in mc.PROJECTS:
        traj = os.path.join(mc.TRAJECTORIES_DIR, project)
        n = 0
        if os.path.isdir(traj):
            for d in os.listdir(traj):
                man = os.path.join(traj, d, "run_manifest.json")
                if d.startswith("run_") and os.path.exists(man) and _read_json(man).get("agent_kind") == "claude":
                    n += 1
        counts[project] = n
    return counts


def open_runs(traj):
    """Ids of the runs under traj that are not stopped (running, paused at a usage limit, or interrupted)."""
    out = []
    if os.path.isdir(traj):
        for d in sorted(os.listdir(traj)):
            sp = os.path.join(traj, d, "run_state.json")
            if d.startswith("run_") and os.path.exists(sp) and _read_json(sp).get("status") != "stopped":
                out.append(d[len("run_"):])
    return out


def spend_check(project):
    """D7 envelope: per project one full run, plus at most 2 tuning reruns in total. Returns an error or None."""
    counts = real_run_count()
    tuning = sum(max(0, c - 1) for c in counts.values())
    if counts[project] >= 1 and tuning >= 2:
        return ("outside the D7 envelope: %s already has %d real run(s) and %d tuning rerun(s) are used; "
                "another run is an owner gate" % (project, counts[project], tuning))
    return None


def auth_check(claude_bin):
    try:
        out = subprocess.run([claude_bin, "auth", "status"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             timeout=60, check=False).stdout.decode("utf-8", "replace")
        if json.loads(out).get("loggedIn") is True:
            return None
    except (OSError, ValueError, subprocess.TimeoutExpired):
        pass
    return "the claude CLI is not logged in: run `claude auth login` in your own terminal, then retry"


def _agent_argv(run, k, n):
    a = run.p["agent"]
    if a["kind"] == "fake":
        return [sys.executable, "-I", os.path.join(mc.SRC_DIR, "fake_agent.py"), "--scenario", a["fake_scenario"],
                "--iteration", str(k), "--attempt", str(n), "--tools", ",".join(a["tools"]),
                "--permission-mode", a["permission_mode"], "--model", a["model"]]
    return agent_runner.build_argv(run.cfg, add_dirs=[run.cfg["c_dir"]])


def require_intact_subjects(run):
    """The skeleton is the reference every integrity check compares against: it must still match the
    committed CHECKSUMS.sha256, or no verdict of this run can be trusted."""
    bad = integrity.verify_subjects(run.skeleton)
    if bad:
        raise SystemExit("%s no longer matches CHECKSUMS.sha256 (%s); restore it with git before resuming" % (
            mc.rel(run.skeleton, mc.REPO_DIR), ", ".join(bad)))


def init_workspace(run):
    """Step 0: fresh workspace from the skeleton, forbid(unsafe_code) injected (D-FORBID), integrity manifest."""
    require_intact_subjects(run)
    if os.path.exists(run.workspace):
        shutil.rmtree(run.workspace)
    shutil.copytree(run.skeleton, run.workspace)
    lib = os.path.join(run.workspace, "src", "lib.rs")
    with open(lib, "w", encoding="utf-8") as fh:
        fh.write(integrity.expected_lib_rs(run.skeleton))
    integrity.write_manifest(run.workspace, run.skeleton)
    init_src = os.path.join(run.dir, "init_src")
    if os.path.exists(init_src):   # left by an interrupted setup that is now being redone on resume
        shutil.rmtree(init_src)
    mc.copy_src_tree(os.path.join(run.workspace, "src"), init_src)


def write_manifest(run):
    a = run.p["agent"]
    argv = _agent_argv(run, 1, 1)
    git_head = _cmd_version(["git", "-C", mc.REPO_DIR, "rev-parse", "HEAD"])
    _write_json(os.path.join(run.dir, "run_manifest.json"), {
        "run_id": run.run_id, "project": run.cfg["project"], "agent_kind": a["kind"], "started": _now(),
        "git_head": git_head,
        "claude_version": _cmd_version([a["claude_bin"], "--version"]) if a["kind"] == "claude" else "fake",
        "rustc_version": _cmd_version(["rustc", "+" + mc.TOOLCHAIN, "--version"]),
        "cargo_version": _cmd_version(["cargo", "+" + mc.TOOLCHAIN, "--version"]),
        "config_hash": run.cfg["config_hash"],
        "config_files": {k: {"path": mc.rel(v, mc.MP4_DIR), "sha256": integrity.sha256(v)}
                         for k, v in sorted(run.cfg["files"].items())},
        "argv_iteration_1": [x for x in argv],
        "env_isolation": dict(a["env"]),
        "model": a["model"], "effort": a["effort"], "max_turns": a["max_turns"],
        "max_iterations": run.p["loop"]["max_iterations"], "no_progress_rounds": run.p["loop"]["no_progress_rounds"],
        "wall_clock_minutes": a["wall_clock_minutes"], "rate_limit": run.p["rate_limit"],
    })


def tamper_check(run, k):
    """Workspace src/ must equal the previous iteration's src_after/ (why.md Z7: no hand edits between iterations)."""
    snap = run.state.get("last_snapshot")
    if not snap:
        return None
    snap_dir = os.path.join(run.dir, snap)
    d = integrity.check_workspace(run.workspace, snap_dir)
    if d["clean"]:
        return None
    shutil.rmtree(os.path.join(run.workspace, "src"))
    mc.copy_src_tree(snap_dir, os.path.join(run.workspace, "src"))   # fresh mtimes: cargo rebuilds
    record = {"iteration": k, "against": snap, "added": d["added"], "removed": d["removed"],
              "modified": d["modified"], "reverted": True}
    run.state.setdefault("workspace_tamper", []).append(record)
    run.log("workspace_tamper before iteration %d: %s (reverted to %s)" % (
        k, ", ".join(d["added"] + d["removed"] + d["modified"]), snap))
    return record


def _prompt_for_agent(run, k, it):
    """What agent B receives: a fresh render, so its paths stay absolute (prompt.md is the scrubbed record, with
    home paths shown as ~). The render is deterministic for a given state; if it no longer matches the record,
    the recorded prompt is sent."""
    with open(os.path.join(it, "prompt.md"), encoding="utf-8") as fh:
        recorded = fh.read()
    fresh = build_prompt(run, k)
    if scrub_secrets.scrub_text(fresh) == recorded:
        return fresh
    run.log("iteration %d: prompt.md differs from a fresh render; sending the recorded prompt" % k)
    return recorded


def build_prompt(run, k):
    if k == 1:
        return prompt_builder.build_initial(run.cfg, 1)
    prev = run.state["last_check"]
    check = _read_json(os.path.join(run.dir, prev))
    return prompt_builder.build_repair(run.cfg, k, check, run.state["history"])


def _diff(old_root, new_root):
    old = {mc.rel(p, old_root): p for p in mc.walk_files(old_root)} if os.path.isdir(old_root) else {}
    new = {mc.rel(p, new_root): p for p in mc.walk_files(new_root)}
    out = []
    for name in sorted(set(old) | set(new)):
        a = mc.read_text(old[name]).splitlines(True) if name in old else []
        b = mc.read_text(new[name]).splitlines(True) if name in new else []
        if a != b:
            out.extend(difflib.unified_diff(a, b, "a/src/" + name, "b/src/" + name))
    return "".join(out)


def do_checks(run, k, n, agent_outcome):
    """Steps 3-8 for one attempt. Idempotent: a rerun after a crash reuses integrity.json and rewrites the
    same check.json and iteration_summary.json."""
    it = run.iter_dir(k, n)
    require_intact_subjects(run)
    integ_path = os.path.join(it, "integrity.json")
    if os.path.exists(integ_path):
        violations = _read_json(integ_path)["violations"]
    else:
        violations = integrity.verify(run.workspace, run.skeleton, restore=True)
        _write_json(integ_path, {"violations": violations})
    check = measure_crate(run.workspace, run.skeleton, it)
    in_repo = os.path.abspath(run.workspace).startswith(mc.REPO_DIR + os.sep)
    _scrub_logs(it, run.workspace, MEASURE_LOGS + tuple("clippy_%s.json" % g for g in mc.CLIPPY_GROUPS),
                crate_label=mc.rel(run.workspace, mc.REPO_DIR) if in_repo else "<crate>")
    check["integrity"] = {"violations": violations}
    check["summary"] = summarize(check)
    check["known_failing_tests"] = [x["name"] for x in run.proj["known_failing_tests"]]
    _write_json(os.path.join(it, "check.json"), check)
    snap = os.path.join(it, "src_after")
    if os.path.exists(snap):
        shutil.rmtree(snap)
    mc.copy_src_tree(os.path.join(run.workspace, "src"), snap)   # committed: no symlinked content
    prev = os.path.join(run.dir, run.state["last_snapshot"]) if run.state.get("last_snapshot") else \
        os.path.join(run.dir, "init_src")
    with open(os.path.join(it, "changes.diff"), "w", encoding="utf-8") as fh:
        fh.write(_diff(prev, snap))
    with open(os.path.join(it, "diagnostics.md"), "w", encoding="utf-8") as fh:
        fh.write(scrub_secrets.scrub_text(prompt_builder.digest(check, run.p["digest"])) + "\n")
    ev = evaluate(check, run.proj)
    s = check["summary"]
    summary = {
        "iteration": k, "attempt": n, "dir": os.path.basename(it), "agent_outcome": agent_outcome,
        "compiles": s["compiles"], "build_errors": _build_error_count(check),
        "build_error_codes": s["build_error_codes"],
        "tests_passed": s["tests_passed"], "tests_total": s["tests_total"],
        "failed_tests": check["test"]["failed_names"], "missing_tests": check["test"].get("missing_names", []),
        "known_failing": ev["known_failing"],
        "clippy_agent": s["clippy_agent"], "clippy_agent_total": s["clippy_agent_total"],
        "clippy_harness": s["clippy_harness"], "safety": s["safety"], "safety_total": ev["safety_total"],
        "safety_tool": s["safety_tool"], "interface_missing": s["interface_missing"],
        "interface_changed": s["interface_changed"], "integrity_violations": violations,
        "hardcode_hits": s["hardcode_hits"], "success": ev["success"], "blockers": ev["blockers"],
        "score": ev["score"],
    }
    _write_json(os.path.join(it, "iteration_summary.json"), summary)
    return summary


def decide_stop(run, summary):
    """Stop rules in order: SUCCESS, ABORT (integrity twice running), NO_PROGRESS, MAX_ITERATIONS."""
    st = run.state
    k = summary["iteration"]
    hist = [h for h in st["history"] if h["iteration"] != k]
    entry = {"iteration": k, "attempt": summary["attempt"], "outcome": summary["agent_outcome"],
             "compiles": summary["compiles"], "tests_passed": summary["tests_passed"],
             "tests_total": summary["tests_total"], "clippy_agent_total": summary["clippy_agent_total"],
             "safety_total": summary["safety_total"], "interface_missing": summary["interface_missing"],
             "integrity_violations": len(summary["integrity_violations"]), "success": summary["success"],
             "score": summary["score"]}
    st["history"] = hist + [entry]
    if summary["success"]:
        return STOP_SUCCESS
    prev = [h for h in hist if h["iteration"] == k - 1]
    if entry["integrity_violations"] and prev and prev[0]["integrity_violations"]:
        return STOP_ABORT
    best = st.get("best_score")
    if best is None or summary["score"] > best:
        st["best_score"] = summary["score"]
        st["no_progress_count"] = 0
    else:
        st["no_progress_count"] = st.get("no_progress_count", 0) + 1
    if st["no_progress_count"] >= run.p["loop"]["no_progress_rounds"]:
        return STOP_NO_PROGRESS
    if k >= run.p["loop"]["max_iterations"]:
        return STOP_MAX_ITERATIONS
    return None


def finalize(run, reason):
    st = run.state
    st.update({"status": "stopped", "stop_reason": reason, "step": "closed", "finished": _now()})
    run.save()
    final = None
    if st.get("last_summary"):
        final = _read_json(os.path.join(run.dir, st["last_summary"]))
    _write_json(os.path.join(run.traj, "run_summary.json"), {
        "run_id": run.run_id, "project": run.cfg["project"], "agent_kind": run.p["agent"]["kind"],
        "stop_reason": reason, "iterations": len(st["history"]), "attempts": st.get("attempts_total", 0),
        "final_iteration_dir": os.path.dirname(st["last_summary"]) if st.get("last_summary") else None,
        "final": final, "config_hash": run.cfg["config_hash"],
        "known_failing_tests": [x["name"] for x in run.proj["known_failing_tests"]],
        "workspace_tamper": st.get("workspace_tamper", []), "usage_limit_pauses": st.get("pauses", []),
        "finished": st["finished"]})
    write_index(run.traj)
    run.log("run stopped: %s after %d iteration(s)" % (reason, len(st["history"])))


def write_index(traj):
    final_id = None
    summ = os.path.join(traj, "run_summary.json")
    if os.path.exists(summ):
        final_id = _read_json(summ).get("run_id")
    rows = ["# Trajectories for %s" % os.path.basename(traj), "",
            "Each `run_<id>/` holds `run_manifest.json`, `run_state.json`, `run.log` and one `iter_KK/` "
            "directory per agent attempt (`prompt.md`, `agent.stream.jsonl`, `agent_result.json`, "
            "`integrity.json`, `check.json` with its logs, `src_after/`, `changes.diff`, `diagnostics.md`, "
            "`iteration_summary.json`). `baseline/` holds the pre-pipeline skeleton measurements.", "",
            "| Run | Agent | Started | Status | Stop reason | Iterations | Final tests | Final run |",
            "|---|---|---|---|---|---|---|---|"]
    for d in sorted(x for x in os.listdir(traj) if x.startswith("run_")):
        sp, mp = os.path.join(traj, d, "run_state.json"), os.path.join(traj, d, "run_manifest.json")
        if not os.path.exists(sp):
            continue
        st, man = _read_json(sp), (_read_json(mp) if os.path.exists(mp) else {})
        last = st["history"][-1] if st.get("history") else {}
        rows.append("| `%s` | %s | %s | %s | %s | %d | %s | %s |" % (
            d, man.get("agent_kind", "?"), st.get("created"), st.get("status"), st.get("stop_reason") or "-",
            len(st.get("history", [])),
            "%s/%s" % (last.get("tests_passed"), last.get("tests_total")) if last else "-",
            "yes" if st.get("run_id") == final_id else ""))
    with open(os.path.join(traj, "INDEX.md"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(rows) + "\n")


def run_loop(cfg, run_id=None, resume=False, yes=False, between_iterations=None):
    """Run (or resume) the pipeline. Returns the process exit code.

    between_iterations(run) is a test seam (selftest drill H): called after an iteration closes and before
    the next one starts.
    """
    a = cfg["pipeline"]["agent"]
    if a["kind"] == "fake":
        ws = os.path.abspath(cfg["workspace"])
        if ws == mc.TRANSLATIONS_DIR or ws.startswith(mc.TRANSLATIONS_DIR + os.sep):
            print("agent.kind fake is refused for MP4/translations/ (selftest fixture only)", file=sys.stderr)
            return 2
        if not a["fake_scenario"]:
            print("agent.kind fake needs agent.fake_scenario", file=sys.stderr)
            return 2
    if resume:
        if not run_id or not RUN_ID_RE.match(run_id):
            print("--resume-run needs a valid run id", file=sys.stderr)
            return 2
        run = Run(cfg, run_id)
        if not os.path.exists(run.state_path):
            print("no run state at %s" % mc.rel(run.state_path, mc.REPO_DIR), file=sys.stderr)
            return 2
        saved = _read_json(run.state_path)
        if saved.get("status") != "stopped":
            if saved.get("config_hash") != cfg["config_hash"]:
                print("run %s was started with config_hash %s, but the configuration now hashes to %s: resuming "
                      "would mix two configurations in one run (restore the configuration, or start a new run)" % (
                          run_id, saved.get("config_hash"), cfg["config_hash"]), file=sys.stderr)
                return 2
            if a["kind"] == "claude":
                err = auth_check(a["claude_bin"])
                if err:    # resuming logged out would stop the run for good with AUTH_ERROR
                    print(err, file=sys.stderr)
                    return 2
    else:
        run_id = run_id or datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        if not RUN_ID_RE.match(run_id):
            print("invalid run id %r" % run_id, file=sys.stderr)
            return 2
        run = Run(cfg, run_id)
        if os.path.exists(run.dir):
            print("run %s already exists; use --resume-run" % run_id, file=sys.stderr)
            return 2
        busy = open_runs(cfg["trajectory_root"])
        if busy:   # a new run would replace the open run's workspace under it
            print("run %s for %s is not stopped: continue it with --resume-run (to abandon it instead, set its "
                  "run_state.json status to stopped; it still counts as a run)" % (", ".join(busy), cfg["project"]),
                  file=sys.stderr)
            return 2
        if a["kind"] == "claude":
            for err in (spend_check(cfg["project"]), auth_check(a["claude_bin"])):
                if err:
                    print(err, file=sys.stderr)
                    return 2
            estimate = ("up to %d iterations x %d turns of %s (effort %s), subscription quota, %d-minute wall clock "
                        "per iteration; replaces %s with a fresh skeleton" % (
                            cfg["pipeline"]["loop"]["max_iterations"], a["max_turns"], a["model"], a["effort"],
                            a["wall_clock_minutes"], mc.rel(cfg["workspace"], mc.REPO_DIR)))
            print("About to start a real run: " + estimate)
            if not yes:
                if not sys.stdin.isatty():
                    print("refusing without --yes (no terminal to confirm on)", file=sys.stderr)
                    return 2
                if input("Proceed? [y/N] ").strip().lower() != "y":
                    print("cancelled")
                    return 2
    os.makedirs(run.dir, exist_ok=True)
    run.acquire_lock()
    # SIGHUP too: a closed terminal must stop agent B (its own process group) like SIGTERM does
    old = {sig: signal.signal(sig, _on_signal) for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGHUP)}
    try:
        if resume:
            run.state = _read_json(run.state_path)
            run.log("resume at iteration %d attempt %d step %s" % (
                run.state["iteration"], run.state["attempt"], run.state["step"]))
            if run.state["status"] == "stopped":
                run.log("run already stopped: %s" % run.state["stop_reason"])
                return 0
            if run.state["step"] == "init":   # interrupted while the workspace was being set up: set it up again
                write_manifest(run)
                init_workspace(run)
                run.state["step"] = "prompt"
                run.save()
        else:
            run.state = {"run_id": run.run_id, "project": cfg["project"], "config_hash": cfg["config_hash"],
                         "created": _now(), "status": "running", "iteration": 1, "attempt": 1, "step": "init",
                         "history": [], "attempts_total": 0, "stop_reason": None}
            run.save()
            run.log("new run %s (%s agent) for %s" % (run.run_id, a["kind"], cfg["project"]))
            write_manifest(run)
            init_workspace(run)
            run.state["step"] = "prompt"
            run.save()
        return _drive(run, between_iterations)
    except Interrupted as exc:
        run.log("interrupted by signal %s at iteration %d step %s; resume with: %s" % (
            exc.args[0], run.state["iteration"], run.state["step"], _resume_cmd(run)))
        run.save()
        return EXIT_INTERRUPTED
    finally:
        for sig, handler in old.items():
            signal.signal(sig, handler)
        run.release_lock()


def _resume_cmd(run):
    return "python3 -I MP4/src/run_pipeline.py --project %s --resume-run %s" % (run.cfg["project"], run.run_id)


def _drive(run, between_iterations):
    st = run.state
    rl = run.p["rate_limit"]
    while True:
        if st["step"] not in ("prompt", "agent", "checks", "closed"):
            raise RuntimeError("run state has step %r, which the loop cannot continue from" % st["step"])
        k, n = st["iteration"], st["attempt"]
        it = run.iter_dir(k, n)
        if st.get("pause_until"):
            wait = st["pause_until"] - time.time()
            if wait > 0:
                run.log("usage-limit pause: sleeping %.0f s before iteration %d attempt %d" % (wait, k, n))
                time.sleep(wait)
            st.pop("pause_until")
            run.save()
        if st["step"] == "prompt":
            os.makedirs(it, exist_ok=True)
            if n == 1:
                tamper_check(run, k)
            with open(os.path.join(it, "prompt.md"), "w", encoding="utf-8") as fh:
                fh.write(scrub_secrets.scrub_text(build_prompt(run, k)))
            st["step"] = "agent"
            run.save()
        if st["step"] == "agent":
            res_path = os.path.join(it, "agent_result.json")
            if st.get("agent_started") == [k, n] and os.path.exists(res_path):
                # resumed after the process died between recording the result and moving on: reuse the result,
                # never call the agent (and spend quota) a second time for the same attempt
                res = _read_json(res_path)
                run.log("iteration %d attempt %d: agent result already recorded (%s)" % (k, n, res["outcome"]))
            elif st.get("agent_started") == [k, n]:
                # resumed after the process died mid-agent: the attempt is over, its edits stand, check them
                res = {"outcome": "aborted_interrupted", "note": "agent step interrupted; checks run on resume"}
                _write_json(res_path, res)
                run.log("iteration %d attempt %d: agent step was interrupted; marked %s" % (k, n, res["outcome"]))
            else:
                st["agent_started"] = [k, n]
                st["attempts_total"] = st.get("attempts_total", 0) + 1
                run.save()
                argv = _agent_argv(run, k, n)
                prompt = _prompt_for_agent(run, k, it)
                run.log("iteration %d attempt %d: agent start" % (k, n))
                res = agent_runner.run(run.cfg, argv, run.workspace, prompt, os.path.join(it, "agent.stream.jsonl"))
                res["argv"] = argv   # the exact command of this attempt, session id included (scrubbed on write)
                _write_json(res_path, res)
                run.log("iteration %d attempt %d: agent %s after %.1f s" % (k, n, res["outcome"], res["elapsed_s"]))
            outcome = res["outcome"]
            if outcome == "usage_limit":
                return _usage_limit(run, res, rl)
            if outcome == "isolation_violation":
                finalize(run, STOP_ABORT_ISOLATION)
                return 1
            if outcome == "auth_error":
                # AUTH_ERROR is a stop: a stopped run cannot be resumed
                run.log("agent could not authenticate; the run stops. Run `claude auth login` before a new run")
                finalize(run, STOP_AUTH_ERROR)
                return 1
            st["step"] = "checks"
            st["agent_outcome"] = outcome
            run.save()
        if st["step"] == "checks":
            summary = do_checks(run, k, n, st.get("agent_outcome"))
            rel_it = os.path.basename(it)
            st["last_snapshot"] = rel_it + "/src_after"
            st["last_check"] = rel_it + "/check.json"
            st["last_summary"] = rel_it + "/iteration_summary.json"
            reason = decide_stop(run, summary)
            run.log("iteration %d: compiles=%s tests %d/%d clippy(agent)=%s unsafe=%d interface missing=%d "
                    "integrity=%d -> %s" % (k, summary["compiles"], summary["tests_passed"],
                                            summary["tests_total"], summary["clippy_agent_total"],
                                            summary["safety_total"], summary["interface_missing"],
                                            len(summary["integrity_violations"]), reason or "continue"))
            st["step"] = "closed"
            run.save()
            if reason:
                finalize(run, reason)
                return 0 if reason in (STOP_SUCCESS, STOP_MAX_ITERATIONS, STOP_NO_PROGRESS) else 1
            if between_iterations:
                between_iterations(run)
            st.update({"iteration": k + 1, "attempt": 1, "step": "prompt"})
            run.save()
            continue
        if st["step"] == "closed":
            st.update({"iteration": k + 1, "attempt": 1, "step": "prompt"})
            run.save()


def _usage_limit(run, res, rl):
    """C7/D7: redo the same iteration as attempt N+1, after waiting (mode wait) or after --resume-run (exit)."""
    st = run.state
    k, n = st["iteration"], st["attempt"]
    resets = res.get("resets_at")
    now = time.time()
    if isinstance(resets, (int, float)) and resets > now:
        wait = resets - now + rl["resume_margin_seconds"]
    else:
        wait = rl["fallback_minutes"] * 60
    wait = min(wait, rl["max_wait_hours"] * 3600)
    st.setdefault("pauses", []).append({"iteration": k, "attempt": n, "resets_at": resets, "wait_s": round(wait),
                                        "at": _now(), "mode": rl["mode"]})
    st.update({"attempt": n + 1, "step": "prompt", "agent_started": None})
    st["pause_until"] = now + wait
    run.save()
    run.log("iteration %d attempt %d hit the usage limit (resets_at=%s); attempt %d after %.0f s" % (
        k, n, resets, n + 1, wait))
    if rl["mode"] == "exit" or n >= MAX_LIMIT_ATTEMPTS:
        # mode exit, or the same iteration was refused MAX_LIMIT_ATTEMPTS times in a row (a weekly limit, or an
        # error the text match mistakes for a limit): hand back to a person instead of retrying unattended
        run.log("usage limit: resume with: %s" % _resume_cmd(run))
        print(_resume_cmd(run))
        return EXIT_USAGE_LIMIT
    return _drive(run, None)


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.dry_run:
        return dry_run(args.project, args.claude_bin)
    if args.smoke:
        return smoke(args.project, args.claude_bin)
    if args.smoke_probe:
        return smoke_probe(args.project, args.claude_bin)
    if not args.check_only:
        cfg = config.load(args.project)
        if args.claude_bin:
            cfg["pipeline"]["agent"]["claude_bin"] = args.claude_bin
        if args.resume_run:
            return run_loop(cfg, run_id=args.resume_run, resume=True, yes=True)
        return run_loop(cfg, run_id=args.run_id, yes=args.yes)
    config.load(args.project)   # the measurement settings it uses (toolchain, rubric clippy) must be valid too
    crate = os.path.abspath(args.crate_dir) if args.crate_dir else mc.translation_dir(args.project)
    if not os.path.exists(os.path.join(crate, "Cargo.toml")):
        print("no crate at %s (no translation yet? pass --crate-dir)" % mc.rel(crate, mc.REPO_DIR), file=sys.stderr)
        return 2
    out = args.out or os.path.join(mc.RESULTS_DIR, "%s.check.json" % args.project)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    res = check_only(args.project, crate, out)
    print(json.dumps(res["summary"], indent=2))
    print("wrote %s" % (mc.rel(os.path.abspath(out), mc.REPO_DIR)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
