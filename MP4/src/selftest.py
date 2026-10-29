"""Self-test: run every MP4 check against selftest_fixture/ and assert the planted counts.

The fixture plants exactly: one unsafe block holding one transmute and one
ptr.add, one agent lint per clippy group (eq_op, needless_return,
needless_bool, boxed_local), one harness lint (needless_return in the test
file), one failing test of two, one 20+ char test literal copied into library
code, and one interface item missing. Everything runs on temp copies; nothing
in the repository is modified.

Prints PASS/FAIL per assertion and a final count; exit 1 if anything failed.
"""
import glob
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import agent_runner  # noqa: E402
import check_interface  # noqa: E402
import checks  # noqa: E402
import config  # noqa: E402
import prompt_builder  # noqa: E402
import run_pipeline  # noqa: E402
import summarize  # noqa: E402
import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402
import safety_check  # noqa: E402
import scrub_secrets  # noqa: E402

FIXTURE = os.path.join(mc.SRC_DIR, "selftest_fixture")
FAKE_CLAUDE = os.path.join(mc.SRC_DIR, "tests", "fake_claude.py")
RESULTS = {"pass": 0, "fail": 0}


def expect(name, actual, expected):
    ok = actual == expected
    RESULTS["pass" if ok else "fail"] += 1
    print("%s  %-58s actual=%r expected=%r" % ("PASS" if ok else "FAIL", name, actual, expected))
    return ok


def expect_true(name, cond, detail=""):
    return expect(name + ((" (%s)" % detail) if detail else ""), bool(cond), True)


def fresh_copy(tmp_root, label):
    return mc.copy_crate(FIXTURE, tempfile.mkdtemp(prefix=label + "_", dir=tmp_root))


def main():
    tmp_root = tempfile.mkdtemp(prefix="mp4_selftest_")
    try:
        _run(tmp_root)
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)
    print("selftest: %d PASS, %d FAIL" % (RESULTS["pass"], RESULTS["fail"]))
    return 1 if RESULTS["fail"] else 0


def _run(tmp_root):
    # --- checks.py: build, test, rubric clippy, per-group clippy ---------------------------
    crate = fresh_copy(tmp_root, "checks")
    logs = os.path.join(tmp_root, "logs")
    res = checks.run_all(crate, logs)
    expect("build ok", res["build"]["ok"], True)
    expect("tests passed", res["test"]["passed"], 1)
    expect("tests total", res["test"]["total"], 2)
    expect("failing test name", res["test"]["failed_names"], ["fails"])
    expect_true("failing test panic text captured",
                "planted failure" in (res["test"]["tests"]["fails"]["panic"] or ""))
    groups = res["clippy"]["groups"]
    for g in mc.CLIPPY_GROUPS:
        expect("clippy %s agent" % g, groups[g]["agent"], 1)
    expect("clippy style harness (test-file lint attributed to harness)", groups["style"]["harness"], 1)
    expect("clippy harness total", res["clippy"]["harness_total"], 1)
    expect("clippy agent total", res["clippy"]["agent_total"], 4)
    expect("clippy correctness lint", sorted(groups["correctness"]["lints"]), ["clippy::eq_op"])
    expect("rubric clippy exit", res["clippy_rubric"]["exit_code"], 0)
    expect_true("rubric clippy log written", os.path.exists(os.path.join(logs, "clippy_rubric.log")))
    for g in mc.CLIPPY_GROUPS:
        expect_true("clippy_%s.json written" % g, os.path.exists(os.path.join(logs, "clippy_%s.json" % g)))

    # test-name dedupe across executables (why.md H-L10)
    dup = ("     Running unittests src/bin/test.rs (x)\ntest a ... ok\ntest b ... FAILED\n"
           "     Running src/bin/test.rs (y)\ntest a ... ok\ntest b ... FAILED\n")
    parsed = checks.parse_test_output(dup)
    expect("dedupe: distinct test names", len(parsed), 2)
    expect("dedupe: executions per name", parsed["a"]["executions"], 2)

    # --- safety_check.py (proxy) -------------------------------------------------------------
    crate = fresh_copy(tmp_root, "safety")
    s = safety_check.proxy(crate, raw_path=os.path.join(tmp_root, "safety.json"))
    expect_true("unsafe_lines >= 1", s["unsafe_lines"] >= 1, "got %d" % s["unsafe_lines"])
    expect("unsafe_casts", s["unsafe_casts"], 1)
    expect("pointer_arithmetic", s["pointer_arithmetic"], 1)
    expect("unsafe_blocks", s["extra"]["unsafe_blocks"], 1)
    expect("transmute count", s["extra"]["transmute"], 1)
    expect("forbid missing detected", s["extra"]["forbid_unsafe_code_first_line"], False)
    expect("-D unsafe_code build fails", s["extra"]["deny_unsafe_build"]["ok"], False)
    expect("ffi findings on clean fixture", s["extra"]["ffi"], 0)
    expect("schema keys", sorted(s), sorted(["tool", "tool_version", "unsafe_lines", "unsafe_calls",
                                             "unsafe_casts", "pointer_arithmetic", "extra", "findings",
                                             "raw_path"]))
    commented = "// unsafe { x.add(1) }\nfn f() { let s = \"unsafe { transmute(p) }\"; }\n"
    c = safety_check.count_file(rustlex.strip(commented))
    expect("unsafe text in comments/strings ignored",
           (c["unsafe_lines"], c["unsafe_casts"], c["pointer_arithmetic"]), (0, 0, 0))
    expect("int .wrapping_add outside unsafe not pointer arithmetic",
           safety_check.count_file(rustlex.strip("fn f(a: u32) -> u32 { a.wrapping_add(1) }"))["pointer_arithmetic"], 0)
    try:
        safety_check.course(crate)
        expect("course tool unset -> exit 2", "returned", "SystemExit(2)")
    except SystemExit as exc:
        expect("course tool unset -> exit 2", exc.code, 2)

    # FFI scan: plant extern "C" and build.rs in a copy
    crate = fresh_copy(tmp_root, "ffi")
    with open(os.path.join(crate, "src", "fixture.rs"), "a", encoding="utf-8") as fh:
        fh.write('\nextern "C" { fn abs(x: i32) -> i32; }\n')
    with open(os.path.join(crate, "build.rs"), "w", encoding="utf-8") as fh:
        fh.write("fn main() {}\n")
    kinds = sorted(f["kind"] for f in integrity.ffi_scan(crate)["findings"])
    expect("ffi scan: extern C + build.rs", kinds, ["build_rs", "extern_c"])

    # --- integrity.py --------------------------------------------------------------------------
    crate = fresh_copy(tmp_root, "integrity")
    expect("hard-coding scan hits", len(integrity.hardcode_scan(crate)), 1)
    source = FIXTURE
    integrity.write_manifest(crate, source)
    expect_true("manifest written", os.path.exists(os.path.join(crate, integrity.MANIFEST_REL)))
    v = integrity.verify(crate, source, restore=True)  # lib.rs lacks the forbid header -> 1 lib_rs violation
    expect("lib.rs without forbid header detected", [x["kind"] for x in v], ["lib_rs"])
    expect("clean after restore", integrity.verify(crate, source, restore=True), [])
    test_file = os.path.join(crate, "src", "bin", "fixture_test.rs")
    with open(test_file, "a", encoding="utf-8") as fh:
        fh.write("\n// agent edit\n")
    v = integrity.verify(crate, source, restore=True)
    expect("integrity violations detected", len(v), 1)
    expect("integrity violations restored", sum(1 for x in v if x["restored"]), 1)
    expect("restored test file matches source",
           integrity.sha256(test_file), integrity.sha256(os.path.join(source, "src", "bin", "fixture_test.rs")))
    os.makedirs(os.path.join(crate, "src", "interfaces"), exist_ok=True)
    with open(os.path.join(crate, "src", "interfaces", "new.rs"), "w", encoding="utf-8") as fh:
        fh.write("pub fn x() {}\n")
    v = integrity.verify(crate, source, restore=True)
    expect("added file in src/interfaces detected and removed",
           ([x["kind"] for x in v], os.path.exists(os.path.join(crate, "src", "interfaces", "new.rs"))),
           (["added"], False))

    snap = os.path.join(tmp_root, "snap_src")
    shutil.copytree(os.path.join(crate, "src"), snap)
    expect("check-workspace clean vs own snapshot", integrity.check_workspace(crate, snap)["clean"], True)
    with open(os.path.join(crate, "src", "fixture.rs"), "a", encoding="utf-8") as fh:
        fh.write("\n")
    expect("check-workspace detects drift", integrity.check_workspace(crate, snap)["modified"], ["fixture.rs"])

    # provenance against a synthetic trajectory tree
    fake_mp4 = os.path.join(tmp_root, "fake_mp4")
    traj = os.path.join(fake_mp4, "trajectories", "project_1")
    run_snap = os.path.join(traj, "run_r1", "iter_02", "src_after")
    shutil.copytree(os.path.join(FIXTURE, "src"), run_snap)
    os.makedirs(os.path.join(traj, "run_r1", "iter_01", "src_after"))
    with open(os.path.join(traj, "run_summary.json"), "w", encoding="utf-8") as fh:
        fh.write('{"run_id": "r1"}')
    shutil.copytree(FIXTURE, os.path.join(fake_mp4, "translations", "project_1"),
                    ignore=shutil.ignore_patterns("target"))
    saved = (mc.TRAJECTORIES_DIR, mc.TRANSLATIONS_DIR)
    mc.TRAJECTORIES_DIR = os.path.join(fake_mp4, "trajectories")
    mc.TRANSLATIONS_DIR = os.path.join(fake_mp4, "translations")
    try:
        expect("provenance ok when src == last src_after", integrity.provenance("project_1")["ok"], True)
        with open(os.path.join(fake_mp4, "translations", "project_1", "src", "fixture.rs"), "a",
                  encoding="utf-8") as fh:
            fh.write("// hand edit\n")
        p = integrity.provenance("project_1")
        expect("provenance detects a hand edit", (p["ok"], p["modified"]), (False, ["fixture.rs"]))
    finally:
        mc.TRAJECTORIES_DIR, mc.TRANSLATIONS_DIR = saved

    # --- check_interface.py --------------------------------------------------------------------
    rep = check_interface.compare(os.path.join(FIXTURE, "src", "interfaces"), FIXTURE)
    expect("interface missing", rep["missing"], 1)
    expect("interface missing item", rep["modules"]["fixture"]["missing"], ["fixture_missing"])
    expect("interface changed", rep["changed"], 0)
    changed_dir = fresh_copy(tmp_root, "iface")
    path = os.path.join(changed_dir, "src", "fixture.rs")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("pub fn double(x: i32) -> i32", "pub fn double(x: i64) -> i32"))
    rep = check_interface.compare(os.path.join(FIXTURE, "src", "interfaces"), changed_dir)
    expect("interface changed signature detected", [c["item"] for c in rep["modules"]["fixture"]["changed"]],
           ["double"])

    # --- scrub_secrets.py ----------------------------------------------------------------------
    sdir = tempfile.mkdtemp(prefix="scrub_", dir=tmp_root)
    planted = os.path.join(sdir, "agent.stream.jsonl")
    secret = "sk" + "-ant-" + "oat01-" + "A" * 24
    with open(planted, "w", encoding="utf-8") as fh:
        fh.write('{"type":"system","note":"%s"}\n' % secret)
    expect("scrub hits", len(scrub_secrets.check([sdir])), 1)
    scrub_secrets.fix([sdir])
    expect("scrub clean after --fix", len(scrub_secrets.check([sdir])), 0)
    with open(planted, encoding="utf-8") as fh:
        expect_true("secret removed from file", secret not in fh.read())
    # assembled so this file does not trip its own scan
    expect("home path rewritten", scrub_secrets.scrub_text("/" + "Users" + "/someone/x"), "~/x")

    fixture_check = dict(res)
    fixture_check["safety"] = s
    fixture_check["interface"] = check_interface.compare(os.path.join(FIXTURE, "src", "interfaces"), FIXTURE)
    fixture_check["integrity"] = {"violations": [{"path": "src/bin/fixture_test.rs", "kind": "modified",
                                                  "restored": True}]}
    fixture_check["hardcode_hits"] = integrity.hardcode_scan(FIXTURE)
    _run_m3(tmp_root, fixture_check)
    _run_m4(tmp_root)
    _run_m5(tmp_root)
    _run_m6(tmp_root)
    _run_m8(tmp_root)


def _fake_run(cfg, tmp_root, mode, wall_clock_s=30):
    argv = [sys.executable, FAKE_CLAUDE] + agent_runner.build_argv(cfg)[1:]
    env = agent_runner.agent_env(cfg)
    env["FAKE_CLAUDE_MODE"] = mode
    stream = os.path.join(tmp_root, "fake_%s" % mode, "agent.stream.jsonl")
    return agent_runner.run(cfg, argv, tmp_root, "prompt", stream, wall_clock_s=wall_clock_s, env=env), stream


def _run_m3(tmp_root, fixture_check):
    # --- config.py ---------------------------------------------------------------------------
    cfgs = {p: config.load(p) for p in mc.PROJECTS}
    expect("config loads both projects", sorted(cfgs), list(mc.PROJECTS))
    import copy
    import yaml
    with open(mc.PIPELINE_YAML, encoding="utf-8") as fh:
        raw = yaml.safe_load(fh)
    bad = copy.deepcopy(raw)
    bad["surprise"] = 1
    try:
        config.validate_pipeline(bad)
        expect("unknown top-level key rejected", "accepted", "ConfigError")
    except config.ConfigError:
        expect("unknown top-level key rejected", "ConfigError", "ConfigError")
    for label, key, value in (("model outside D7 rejected", "model", "sonnet"),
                              ("max_turns > 60 rejected", "max_turns", 61)):
        bad = copy.deepcopy(raw)
        bad["agent"][key] = value
        try:
            config.validate_pipeline(bad)
            expect(label, "accepted", "ConfigError")
        except config.ConfigError:
            expect(label, "ConfigError", "ConfigError")
    expect("config_hash is stable", config.load("project_1")["config_hash"], cfgs["project_1"]["config_hash"])

    # --- agent_runner argv (C2-C6) -------------------------------------------------------------
    cfg = cfgs["project_1"]
    argv = agent_runner.build_argv(cfg)
    required = ["-p", "--output-format", "--verbose", "--model", "--effort", "--max-turns", "--max-budget-usd",
                "--permission-mode", "--tools", "--allowedTools", "--disallowedTools", "--setting-sources",
                "--settings", "--append-system-prompt-file", "--json-schema", "--strict-mcp-config",
                "--mcp-config", "--disable-slash-commands", "--session-id", "--add-dir"]
    expect("argv carries every C1-C6 flag", [f for f in required if f not in argv], [])
    expect("argv denies git", "Bash(git *)" in argv, True)
    expect("argv add-dir is the project's C dir", argv[argv.index("--add-dir") + 1], cfg["c_dir"])
    expect("agent env sets isolation vars",
           {k: agent_runner.agent_env(cfg).get(k) for k in ("CLAUDE_CODE_DISABLE_CLAUDE_MDS",
                                                            "CLAUDE_CODE_DISABLE_AUTO_MEMORY")},
           {"CLAUDE_CODE_DISABLE_CLAUDE_MDS": "1", "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1"})

    # --- agent_runner scenarios against fake_claude.py ----------------------------------------
    r, _ = _fake_run(cfg, tmp_root, "normal")
    expect("runner: normal completion -> ok", (r["outcome"], r["isolation_violations"]), ("ok", []))
    expect("runner: structured status captured", (r["result"] or {}).get("structured_output", {}).get("status"),
           "done")
    r, _ = _fake_run(cfg, tmp_root, "usage_limit")
    expect("runner: usage limit detected", (r["outcome"], r["resets_at"]), ("usage_limit", 1900000000))
    r, _ = _fake_run(cfg, tmp_root, "max_turns")
    expect("runner: max turns detected", r["outcome"], "max_turns")
    r, _ = _fake_run(cfg, tmp_root, "slow", wall_clock_s=2)
    expect("runner: wall-clock kill -> timeout", r["outcome"], "timeout")
    expect_true("runner: killed promptly", r["elapsed_s"] < 20, "%.1fs" % r["elapsed_s"])
    r, _ = _fake_run(cfg, tmp_root, "wrong_tools")
    expect("runner: tool-list mismatch aborts", r["outcome"], "isolation_violation")
    r, stream = _fake_run(cfg, tmp_root, "secret")
    with open(stream, encoding="utf-8") as fh:
        body = fh.read()
    expect("runner: stream scrubbed on write (key, e-mail, home path)",
           [scrub_secrets.scan_text(body), "[REDACTED:anthropic_key]" in body, "[REDACTED:email]" in body],
           [[], True, True])

    # --- prompt_builder -------------------------------------------------------------------------
    for p in mc.PROJECTS:
        c = cfgs[p]
        prompts = {"initial": prompt_builder.build_initial(c),
                   "repair": prompt_builder.build_repair(c, 2, fixture_check, [
                       {"iteration": 1, "outcome": "ok", "compiles": True, "tests_passed": 1, "tests_total": 2,
                        "clippy_agent_total": 4, "safety_total": 3, "interface_missing": 1}])}
        for kind, text in prompts.items():
            expect("%s %s: every guardrail phrase present" % (p, kind),
                   [rx.pattern for rx in prompt_builder.GUARDRAIL_PATTERNS if not rx.search(text)], [])
            expect("%s %s: no Rust fn body" % (p, kind), prompt_builder.FN_BODY_RE.findall(text), [])
            expect("%s %s: no unfilled placeholder" % (p, kind), "{{" in text, False)
        expect("%s repair: carries the failing test and its panic" % p,
               "`fails` FAILED" in prompts["repair"] and "planted failure" in prompts["repair"], True)
        expect("%s repair: carries clippy sites" % p, "clippy::eq_op" in prompts["repair"], True)
    texts = prompt_builder.template_texts(cfgs["project_1"])
    expect("templates/system prompt/cheatsheet: no satc_/psbt_ identifiers",
           {k: prompt_builder.PROJECT_IDENT_RE.findall(v) for k, v in texts.items()
            if prompt_builder.PROJECT_IDENT_RE.findall(v)}, {})


# ------------------------------------------------------------------------------------------------
# M4 loop drills A-H (fake agent against copies of selftest_fixture; no model quota)
# ------------------------------------------------------------------------------------------------
VARIANTS = os.path.join(mc.SRC_DIR, "selftest_fixture_variants")
ITER_FILES = ["prompt.md", "agent.stream.jsonl", "agent_result.json", "integrity.json", "check.json",
              "build.log", "test.log", "clippy_rubric.log", "clippy_correctness.json", "clippy_style.json",
              "clippy_complexity.json", "clippy_perf.json", "safety_proxy.json", "src_after", "changes.diff",
              "diagnostics.md", "iteration_summary.json"]


def drill_cfg(tmp_root, name, scenario, max_iterations=8, mode="wait", min_iterations=1):
    import copy
    root = os.path.join(tmp_root, "drill_" + name)
    skeleton = os.path.join(root, "skeleton")
    # a benchmark-shaped skeleton: no src/<module>.rs, so the agent has to provide it
    shutil.copytree(FIXTURE, skeleton, ignore=shutil.ignore_patterns("target", "fixture.rs"))
    shutil.copy2(os.path.join(FIXTURE, "src", "interfaces", "fixture.rs"),
                 os.path.join(skeleton, "src", "interfaces", "fixture.rs"))
    scen = dict(scenario)
    scen["variants_dir"] = VARIANTS
    scen_path = os.path.join(root, "scenario.json")
    with open(scen_path, "w", encoding="utf-8") as fh:
        json.dump(scen, fh)
    cfg = copy.deepcopy(config.load("project_1"))
    cfg["pipeline"]["agent"].update({"kind": "fake", "fake_scenario": scen_path, "wall_clock_minutes": 2})
    cfg["pipeline"]["loop"]["max_iterations"] = max_iterations
    # the M4/M5 drills predate owner gate G3 and expect SUCCESS to stop at the first clean iteration
    cfg["pipeline"]["loop"]["min_iterations"] = min_iterations
    cfg["pipeline"]["rate_limit"].update({"mode": mode, "resume_margin_seconds": 1})
    cfg["project_cfg"] = {
        "name": "project_1", "label": "selftest fixture", "crate": "fixture", "modules": ["fixture"],
        "c_dir": "", "c_files": [], "test_file": "src/bin/fixture_test.rs", "interface_dir": "src/interfaces",
        "expected_pub_items": 8,
        "allow_attributes": [{"lint": "clippy::boxed_local", "item": "total", "reason": "fixture interface"}],
        "known_failing_tests": [{"name": "fails", "reason": "planted failing test",
                                 "expected_assertion": "planted failure",
                                 "expected_location": "src/bin/fixture_test.rs:"}],
        "notes": ["selftest fixture"], "rulings": {}, "c_behaviour": []}
    cfg.update({"skeleton": skeleton, "workspace": os.path.join(root, "workspace"),
                "trajectory_root": os.path.join(root, "traj"), "c_dir": skeleton, "quiet": True})
    os.makedirs(cfg["trajectory_root"])
    return cfg


def _state(cfg, run_id):
    with open(os.path.join(cfg["trajectory_root"], "run_" + run_id, "run_state.json"), encoding="utf-8") as fh:
        return json.load(fh)


def _fork_run(cfg, run_id, wait_step, sig, settle=1.0, timeout=180):
    """Run the loop in a child process, signal it once it reaches wait_step, return its exit status."""
    import time as _time
    pid = os.fork()
    if pid == 0:
        try:
            code = run_pipeline.run_loop(cfg, run_id=run_id, yes=True)
        except BaseException:
            code = 99
        os._exit(code)
    deadline = _time.time() + timeout
    path = os.path.join(cfg["trajectory_root"], "run_" + run_id, "run_state.json")
    while _time.time() < deadline:
        try:
            with open(path, encoding="utf-8") as fh:
                if json.load(fh).get("step") == wait_step:
                    break
        except (OSError, ValueError):
            pass
        _time.sleep(0.1)
    _time.sleep(settle)
    os.kill(pid, sig)
    _, status = os.waitpid(pid, 0)
    return os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)


def _run_m4(tmp_root):
    import signal as _signal

    # A: success at iteration 2
    cfg = drill_cfg(tmp_root, "A", {"1": {"1": ["copy:partial"]}, "2": {"1": ["copy:clean"]}})
    code = run_pipeline.run_loop(cfg, run_id="A", yes=True)
    st = _state(cfg, "A")
    expect("drill A: success at iteration 2", (code, st["stop_reason"], len(st["history"])), (0, "SUCCESS", 2))
    run_dir = os.path.join(cfg["trajectory_root"], "run_A")
    for it in ("iter_01", "iter_02"):
        expect("drill A: %s has every design-reference file" % it,
               [f for f in ITER_FILES if not os.path.exists(os.path.join(run_dir, it, f))], [])
    expect("drill A: run files",
           [f for f in ("run_state.json", "run.log", "run_manifest.json") if not os.path.exists(
               os.path.join(run_dir, f))] + [f for f in ("INDEX.md", "run_summary.json") if not os.path.exists(
                   os.path.join(cfg["trajectory_root"], f))], [])
    with open(os.path.join(run_dir, "iter_01", "iteration_summary.json"), encoding="utf-8") as fh:
        s1 = json.load(fh)
    expect("drill A: iteration 1 blockers (clippy + interface)",
           [b.split(":")[0] for b in s1["blockers"]], ["agent clippy warnings", "interface missing 1, changed 0"])
    expect("drill A: known-failing test verified (D8)", s1["known_failing"]["fails"],
           {"failed": True, "assertion_matches": True, "location_matches": True})
    with open(os.path.join(run_dir, "iter_02", "prompt.md"), encoding="utf-8") as fh:
        p2 = fh.read()
    expect("drill A: repair prompt carries iteration-1 feedback",
           "needless_return" in p2 and "missing `fixture::fixture_missing`" in p2, True)
    with open(os.path.join(run_dir, "run_manifest.json"), encoding="utf-8") as fh:
        man = json.load(fh)
    expect("drill A: manifest records versions and config hash",
           [k for k in ("git_head", "rustc_version", "cargo_version", "config_hash", "argv_iteration_1",
                        "env_isolation") if not man.get(k)], [])
    with open(os.path.join(run_dir, "iter_02", "changes.diff"), encoding="utf-8") as fh:
        expect("drill A: changes.diff shows the repair", "+    x * 2" in fh.read(), True)

    # summarize.py on drill A output, against --check-only of the final workspace
    chk = run_pipeline.measure_crate(mc.copy_crate(cfg["workspace"]), cfg["skeleton"],
                                     os.path.join(tmp_root, "A_check_logs"), cfg["project_cfg"]["allow_attributes"])
    with open(os.path.join(cfg["trajectory_root"], "run_summary.json"), encoding="utf-8") as fh:
        rsum = json.load(fh)
    out = summarize.write_results([{"label": "selftest fixture", "run_summary": rsum, "check": chk}],
                                  os.path.join(tmp_root, "results"))
    with open(out[0], encoding="utf-8") as fh:
        md = fh.read()
    expect("summarize: results.md row from drill A", "| selftest fixture | Yes | 1 | 2 | 50.0% | 2 | SUCCESS |" in md,
           True)
    bad = json.loads(json.dumps(rsum))
    bad["final"]["tests_passed"] = 2
    try:
        summarize.build_rows([{"label": "x", "run_summary": bad, "check": chk}])
        expect("summarize: mismatch with check-only refused", "accepted", "MismatchError")
    except summarize.MismatchError:
        expect("summarize: mismatch with check-only refused", "MismatchError", "MismatchError")

    # B: max_iterations 1
    cfg = drill_cfg(tmp_root, "B", {"1": {"1": ["copy:partial"]}}, max_iterations=1)
    code = run_pipeline.run_loop(cfg, run_id="B", yes=True)
    st = _state(cfg, "B")
    expect("drill B: MAX_ITERATIONS at 1", (code, st["stop_reason"], len(st["history"])), (0, "MAX_ITERATIONS", 1))

    # C: agent does nothing -> NO_PROGRESS at iteration 4
    cfg = drill_cfg(tmp_root, "C", {})
    code = run_pipeline.run_loop(cfg, run_id="C", yes=True)
    st = _state(cfg, "C")
    expect("drill C: NO_PROGRESS at iteration 4", (code, st["stop_reason"], len(st["history"])), (0, "NO_PROGRESS", 4))

    # D: agent edits the test file -> violation recorded, restored, not green; clean next iteration succeeds
    cfg = drill_cfg(tmp_root, "D", {"1": {"1": ["copy:clean", "edit_test"]}, "2": {"1": ["noop"]}})
    code = run_pipeline.run_loop(cfg, run_id="D", yes=True)
    st = _state(cfg, "D")
    with open(os.path.join(cfg["trajectory_root"], "run_D", "iter_01", "iteration_summary.json"),
              encoding="utf-8") as fh:
        d1 = json.load(fh)
    expect("drill D: violation recorded and restored",
           [(v["path"], v["kind"], v["restored"]) for v in d1["integrity_violations"]],
           [("src/bin/fixture_test.rs", "modified", True)])
    expect("drill D: iteration with a violation is not green", d1["success"], False)
    expect("drill D: test file restored in workspace",
           integrity.sha256(os.path.join(cfg["workspace"], "src", "bin", "fixture_test.rs")),
           integrity.sha256(os.path.join(cfg["skeleton"], "src", "bin", "fixture_test.rs")))
    expect("drill D: next clean iteration succeeds", (code, st["stop_reason"], len(st["history"])),
           (0, "SUCCESS", 2))
    cfg = drill_cfg(tmp_root, "D2", {"1": {"1": ["copy:clean", "edit_test"]}, "2": {"1": ["edit_test"]}})
    code = run_pipeline.run_loop(cfg, run_id="D2", yes=True)
    expect("drill D2: violations twice running -> ABORT", (code, _state(cfg, "D2")["stop_reason"]), (1, "ABORT"))

    # E: usage-limit rejection -> paused, redone as iter_01_attempt2 (mode wait)
    cfg = drill_cfg(tmp_root, "E", {"1": {"1": ["rate_limit"], "2": ["copy:partial"]}, "2": {"1": ["copy:clean"]}})
    code = run_pipeline.run_loop(cfg, run_id="E", yes=True)
    st = _state(cfg, "E")
    run_dir = os.path.join(cfg["trajectory_root"], "run_E")
    expect("drill E: paused once and redone as iter_01_attempt2",
           (code, st["stop_reason"], len(st.get("pauses", [])), sorted(
               d for d in os.listdir(run_dir) if d.startswith("iter_"))),
           (0, "SUCCESS", 1, ["iter_01", "iter_01_attempt2", "iter_02"]))
    expect_true("drill E: waited until resets_at (+margin)", 3 <= st["pauses"][0]["wait_s"] <= 8,
                "%ss" % st["pauses"][0]["wait_s"])
    # E2: mode exit -> exit 75, then --resume-run redoes the attempt
    cfg = drill_cfg(tmp_root, "E2", {"1": {"1": ["rate_limit"], "2": ["copy:clean"]}}, mode="exit")
    code = run_pipeline.run_loop(cfg, run_id="E2", yes=True)
    st = _state(cfg, "E2")
    expect("drill E2: mode exit -> code 75, attempt 2 queued", (code, st["attempt"], st["step"]), (75, 2, "prompt"))
    code = run_pipeline.run_loop(cfg, run_id="E2", resume=True)
    expect("drill E2: resume redoes the iteration and succeeds", (code, _state(cfg, "E2")["stop_reason"]),
           (0, "SUCCESS"))

    # F: SIGTERM during the agent step -> resume marks aborted-interrupted, runs checks, continues
    cfg = drill_cfg(tmp_root, "F", {"1": {"1": ["copy:partial", "sleep:60"]}, "2": {"1": ["copy:clean"]}})
    code = _fork_run(cfg, "F", "agent", _signal.SIGTERM)
    expect("drill F: SIGTERM during agent -> exit 143", code, 143)
    st = _state(cfg, "F")
    expect("drill F: state left at the agent step", (st["iteration"], st["step"]), (1, "agent"))
    code = run_pipeline.run_loop(cfg, run_id="F", resume=True)
    st = _state(cfg, "F")
    with open(os.path.join(cfg["trajectory_root"], "run_F", "iter_01", "agent_result.json"), encoding="utf-8") as fh:
        f_out = json.load(fh)["outcome"]
    expect("drill F: resume -> aborted_interrupted, checked, continued to SUCCESS",
           (code, f_out, st["history"][0]["outcome"], st["stop_reason"]),
           (0, "aborted_interrupted", "aborted_interrupted", "SUCCESS"))

    # G: kill during checks -> resume reruns checks idempotently
    cfg = drill_cfg(tmp_root, "G", {"1": {"1": ["copy:clean"]}}, max_iterations=1)
    code = _fork_run(cfg, "G", "checks", _signal.SIGKILL, settle=0.5)
    expect("drill G: killed during checks", (code, _state(cfg, "G")["step"]), (-9, "checks"))
    code = run_pipeline.run_loop(cfg, run_id="G", resume=True)
    summ_path = os.path.join(cfg["trajectory_root"], "run_G", "iter_01", "iteration_summary.json")
    with open(summ_path, encoding="utf-8") as fh:
        g1 = fh.read()
    run = run_pipeline.Run(cfg, "G")
    run.state = _state(cfg, "G")
    run.state["last_snapshot"] = None
    run_pipeline.do_checks(run, 1, 1, run.state["history"][0]["outcome"])
    with open(summ_path, encoding="utf-8") as fh:
        g2 = fh.read()
    expect("drill G: resume completes (stale lock taken over)", (code, _state(cfg, "G")["stop_reason"]),
           (0, "SUCCESS"))
    expect("drill G: rerun of checks gives an identical iteration_summary.json", g1 == g2, True)

    # H: hand edit of workspace src between iterations -> workspace_tamper recorded and reverted
    cfg = drill_cfg(tmp_root, "H", {"1": {"1": ["copy:partial"]}, "2": {"1": ["noop"]}}, max_iterations=2)

    def hand_edit(run):
        with open(os.path.join(run.workspace, "src", "fixture.rs"), "a", encoding="utf-8") as fh:
            fh.write("\n// hand edit\n")

    code = run_pipeline.run_loop(cfg, run_id="H", yes=True, between_iterations=hand_edit)
    st = _state(cfg, "H")
    with open(os.path.join(cfg["workspace"], "src", "fixture.rs"), encoding="utf-8") as fh:
        ws_text = fh.read()
    expect("drill H: workspace_tamper recorded and reverted",
           (code, [(t["iteration"], t["modified"], t["reverted"]) for t in st.get("workspace_tamper", [])],
            "// hand edit" in ws_text), (0, [(2, ["fixture.rs"], True)], False))

    # README: required headings, generated sections equal pipeline.yaml
    with open(summarize.README, encoding="utf-8") as fh:
        readme = fh.read()
    required = ["Agentic framework and version", "Model(s) and provider / runtime", "Inference settings",
                "OS and runtime", "External tools available to the agent", "Dependency installation",
                "How to run the pipeline", "Stopping condition", "API and usage limits that affected the experiment",
                "Models, frameworks and tools used", "Repository layout", "Infrastructure interventions"]
    expect("README: every required heading", [h for h in required if "\n## %s\n" % h not in readme], [])
    pipeline = config.validate_pipeline(config._load_yaml(mc.PIPELINE_YAML))
    expect("README: generated sections equal pipeline.yaml",
           summarize.render_readme(readme, summarize.generated_sections(pipeline)) == readme, True)

    # guards
    cfg = drill_cfg(tmp_root, "guard", {})
    cfg["workspace"] = os.path.join(mc.TRANSLATIONS_DIR, "project_1")
    expect("guard: fake agent refused for MP4/translations", run_pipeline.run_loop(cfg, run_id="guard", yes=True), 2)


# ------------------------------------------------------------------------------------------------
# M5 adversarial guard traps (what.md M5 step 2) and regressions for the review-1 fixes
# ------------------------------------------------------------------------------------------------
CLEAN_VARIANT = os.path.join(VARIANTS, "clean", "fixture.rs")


def _edit(path, old, new):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if old not in text:
        raise AssertionError("selftest edit target not found in %s: %r" % (path, old))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(old, new, 1))


def _append(path, text):
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(text)


def _trap_run(tmp_root, name):
    """A freshly initialised workspace (forbid line, manifest) holding the clean variant, as after an agent turn."""
    cfg = drill_cfg(tmp_root, name, {})
    run = run_pipeline.Run(cfg, name)
    os.makedirs(run.iter_dir(1, 1))
    run.state = {"history": [], "last_snapshot": None, "iteration": 1, "attempt": 1}
    run_pipeline.init_workspace(run)
    shutil.copy2(CLEAN_VARIANT, os.path.join(cfg["workspace"], "src", "fixture.rs"))
    return cfg, run


def _trap(tmp_root, name, mutate):
    """Apply one agent edit, then run the loop's own steps 3-8 (do_checks: restore, measure, evaluate)."""
    cfg, run = _trap_run(tmp_root, name)
    mutate(cfg["workspace"])
    return cfg, run, run_pipeline.do_checks(run, 1, 1, "ok")


def _ps_lines(marker):
    import subprocess
    out = subprocess.run(["ps", "-axo", "pid,command"], stdout=subprocess.PIPE).stdout.decode("utf-8", "replace")
    return [ln for ln in out.splitlines() if marker in ln and "ps -axo" not in ln]


def _run_m5(tmp_root):
    fx = lambda ws: os.path.join(ws, "src", "fixture.rs")  # noqa: E731
    test_rs = lambda ws: os.path.join(ws, "src", "bin", "fixture_test.rs")  # noqa: E731

    cfg, run, s = _trap(tmp_root, "trap_control", lambda ws: None)
    expect("trap control: clean variant succeeds", (s["success"], s["blockers"]), (True, []))
    build_log = mc.read_text(os.path.join(run.iter_dir(1, 1), "build.log"))
    expect("loop logs: crate path scrubbed from build.log",
           ([p for p in {cfg["workspace"], os.path.realpath(cfg["workspace"])} if p in build_log],
            "(<crate>)" in build_log), ([], True))

    # (a) the agent edits the test file to make the planted failure pass, and builds it with cargo test
    def edit_test_and_build(ws):
        _edit(test_rs(ws), "assert_eq!(double(2), 5,", "assert_eq!(double(2), 4,")
        mc.cargo(["test", "--locked", "--no-fail-fast"], ws)

    cfg, _, s = _trap(tmp_root, "trap_a", edit_test_and_build)
    expect("trap a: test file edit -> integrity violation, restored, not green",
           (s["success"], s["blockers"], [(v["path"], v["kind"], v["restored"]) for v in s["integrity_violations"]],
            integrity.sha256(test_rs(cfg["workspace"])) == integrity.sha256(test_rs(cfg["skeleton"]))),
           (False, ["integrity violations: 1"], [("src/bin/fixture_test.rs", "modified", True)], True))
    expect("trap a: the restored test is what gets measured (no stale tampered build)",
           (s["tests_passed"], s["failed_tests"]), (1, ["fails"]))

    # (b) a new dependency: restored in the loop; the FFI/dependency scan names it on an unrestored crate
    add_dep = lambda ws: _edit(os.path.join(ws, "Cargo.toml"), "[dependencies]\n",  # noqa: E731
                               "[dependencies]\nlibc = \"0.2\"\n")
    cfg, _, s = _trap(tmp_root, "trap_b", add_dep)
    expect("trap b: Cargo.toml dependency -> integrity violation, restored",
           (s["success"], s["blockers"], [(v["path"], v["kind"]) for v in s["integrity_violations"]]),
           (False, ["integrity violations: 1"], [("Cargo.toml", "modified")]))
    unrestored = mc.copy_crate(cfg["workspace"], tempfile.mkdtemp(dir=tmp_root))
    add_dep(unrestored)
    expect("trap b: dependency scan on an unrestored crate",
           [(f["kind"], f.get("name")) for f in integrity.ffi_scan(unrestored, cfg["skeleton"])["findings"]],
           [("new_dependency", "libc")])

    # (c) build.rs plus an extern "C" block (FFI to the original C)
    _, _, s = _trap(tmp_root, "trap_c", lambda ws: (
        _append(os.path.join(ws, "build.rs"), "fn main() {}\n"),
        _append(fx(ws), '\nextern "C" {\n    fn abs(x: i32) -> i32;\n}\n')))
    # since owner gate G1 the build.rs outside src/ is deleted and recorded before measuring
    expect("trap c: build.rs + extern C -> safety finding, build.rs removed as an integrity violation",
           (s["success"], s["blockers"], [(v["path"], v["kind"]) for v in s["integrity_violations"]]),
           (False, ["safety finding: extern_c", "integrity violations: 1"], [("build.rs", "outside_src")]))

    # (d) an unsafe block inside a safe-looking pub fn (why.md Z4)
    unsafe_fn = "\npub fn first(v: &[u32]) -> u32 {\n    unsafe { *v.as_ptr() }\n}\n"
    _, _, s = _trap(tmp_root, "trap_d", lambda ws: _append(fx(ws), unsafe_fn))
    expect("trap d: unsafe block -> build fails, counted, -D unsafe_code build fails",
           (s["success"], s["compiles"], s["safety_total"] > 0,
            [b for b in s["blockers"] if b.startswith(("build fails", "unsafe metrics", "safety finding"))]),
           (False, False, True, ["build fails", "unsafe metrics: %d" % s["safety_total"],
                                 "safety finding: deny_unsafe_build_failed"]))

    # (e) a test literal pasted into library code (why.md Z2)
    _, _, s = _trap(tmp_root, "trap_e", lambda ws: _edit(fx(ws), 'concat!("hello from the ", "fixture harness")',
                                                         '"hello from the fixture harness"'))
    expect("trap e: test literal in library code -> hard-coding hit", (s["success"], s["blockers"]),
           (False, ["hard-coding hits: 1"]))

    # (f) a changed pub signature that still compiles against the tests
    _, _, s = _trap(tmp_root, "trap_f", lambda ws: _edit(
        fx(ws), "pub fn is_positive(x: i32) -> bool {\n    x > 0",
        "pub fn is_positive(x: impl Into<i64>) -> bool {\n    x.into() > 0"))
    expect("trap f: changed pub signature -> interface changed", (s["success"], s["compiles"], s["blockers"]),
           (False, True, ["interface missing 0, changed 1"]))

    # (g) a hand edit of src/ between iterations
    cfg, run, s = _trap(tmp_root, "trap_g", lambda ws: None)
    run.state["last_snapshot"] = "iter_01/src_after"
    _append(fx(cfg["workspace"]), "\n// hand edit between iterations\n")
    rec = run_pipeline.tamper_check(run, 2)
    expect("trap g: hand edit between iterations -> workspace_tamper, reverted",
           ((rec or {}).get("modified"), (rec or {}).get("reverted"),
            "hand edit" in mc.read_text(fx(cfg["workspace"]))), (["fixture.rs"], True, False))

    # --- regressions for review-1 fixes ------------------------------------------------------------
    expect("benchmark tests: satc", checks.benchmark_tests(mc.skeleton_dir("project_1")),
           ["satc_collision_test", "satc_point_scale_xy_test", "satc_point_test", "satc_polygon_get_centroid_test"])
    expect("benchmark tests: libpsbt", checks.benchmark_tests(mc.skeleton_dir("project_2")),
           ["empty_input_test", "encode_decode_test", "read_test_vector", "test_vector"])

    # agent-written unit tests are reported apart and do not change the benchmark counts
    _, _, s = _trap(tmp_root, "unit_tests", lambda ws: _append(fx(ws), (
        "\n#[cfg(test)]\nmod tests {\n    #[test]\n    fn t1() {}\n    #[test]\n    fn t2() {}\n}\n")))
    with open(os.path.join(tmp_root, "drill_unit_tests", "traj", "run_unit_tests", "iter_01", "check.json"),
              encoding="utf-8") as fh:
        extra = json.load(fh)["test"]["extra_tests"]
    expect("agent unit tests: benchmark counts unchanged, reported apart",
           (s["tests_passed"], s["tests_total"], s["success"], sorted(extra)),
           (1, 2, True, ["fixture::tests::t1", "fixture::tests::t2"]))

    # a benchmark test that never finishes: killed with its process group, counted as no result, not green
    crate = fresh_copy(tmp_root, "hang")
    shutil.copy2(CLEAN_VARIANT, fx(crate))
    _edit(fx(crate), "pub fn is_positive(x: i32) -> bool {\n    x > 0",
          "pub fn is_positive(x: i32) -> bool {\n    let mut y = x;\n    while y != 0 {\n"
          "        y = y.wrapping_mul(1);\n    }\n    x > 0")
    hang_logs = os.path.join(tmp_root, "hang_logs")
    checks.run_build(crate, hang_logs)
    saved = mc.CARGO_TIMEOUT_S
    mc.CARGO_TIMEOUT_S = 8    # read at call time
    try:
        t = checks.run_test(crate, hang_logs, ["fails", "passes"])
    finally:
        mc.CARGO_TIMEOUT_S = saved
    import time as _time
    _time.sleep(1)
    expect("hung test: timed out, no result, counted as not passed",
           (t["timed_out"], t["missing_names"], t["failed_names"], t["passed"], t["total"]),
           (True, ["passes"], ["fails"], 0, 2))
    expect("hung test: no test process left running", _ps_lines(crate), [])
    hung = {"build": {"ok": True, "errors": [], "error_codes": []}, "test": t,
            "clippy": {"groups": {}, "agent_total": 0}, "interface": {"missing": 0, "changed": 0},
            "safety": {"tool": "proxy", "unsafe_lines": 0, "unsafe_calls": 0, "unsafe_casts": 0,
                       "pointer_arithmetic": 0, "findings": []},
            "integrity": {"violations": []}, "hardcode_hits": []}
    ev = run_pipeline.evaluate(hung, {"known_failing_tests": []})
    expect("hung test: blocks success", (ev["success"], "tests with no result (hung, crashed or timed out): passes"
                                         in ev["blockers"]), (False, True))
    expect("hung test: named in the repair digest", "no result for `passes`" in prompt_builder.digest(
        dict(hung, known_failing_tests=["fails"]), config.load("project_1")["pipeline"]["digest"]), True)

    # a terminal hangup while cargo runs (no handlers installed, as in --check-only) takes cargo's group with it
    import signal as _signal
    import subprocess
    code_hup = ("import sys; sys.path.insert(0, %r); import mp4common as mc; "
                "mc.cargo(['test', '--locked', '--no-fail-fast'], %r, timeout=120)" % (mc.SRC_DIR, crate))
    child = subprocess.Popen([sys.executable, "-I", "-c", code_hup])
    _time.sleep(4)
    child.send_signal(_signal.SIGHUP)
    child.wait(timeout=30)
    _time.sleep(1)
    left = _ps_lines(crate)
    for ln in left:   # never leave a spinning test binary behind, whatever the result
        try:
            os.kill(int(ln.split()[0]), _signal.SIGKILL)
        except (OSError, ValueError):
            pass
    expect("hangup during cargo: the process ends as SIGHUP, no test process left", (child.returncode, left),
           (-_signal.SIGHUP, []))

    # cargo test failing with no parsed failure (e.g. a doc test that does not compile) is not a clean run
    unexplained = dict(hung, test=dict(t, exit_code=101, missing_names=[], failed_names=[], extra_tests={}))
    expect("cargo test exit 101 with nothing parsed blocks success",
           [b for b in run_pipeline.evaluate(unexplained, {"known_failing_tests": []})["blockers"]
            if b.startswith("cargo test exited")], ["cargo test exited 101 with no failing test parsed (see test.log)"])

    # provenance follows run_summary.final_iteration_dir (an iter_KK_attemptN retry is the final snapshot)
    fake_mp4 = os.path.join(tmp_root, "fake_mp4_attempt")
    traj = os.path.join(fake_mp4, "trajectories", "project_1")
    os.makedirs(os.path.join(traj, "run_r2", "iter_02", "src_after"))
    shutil.copytree(os.path.join(FIXTURE, "src"), os.path.join(traj, "run_r2", "iter_02_attempt2", "src_after"))
    shutil.copytree(FIXTURE, os.path.join(fake_mp4, "translations", "project_1"),
                    ignore=shutil.ignore_patterns("target"))
    saved = (mc.TRAJECTORIES_DIR, mc.TRANSLATIONS_DIR)
    mc.TRAJECTORIES_DIR = os.path.join(fake_mp4, "trajectories")
    mc.TRANSLATIONS_DIR = os.path.join(fake_mp4, "translations")
    try:
        for summary, want in ((('{"run_id": "r2", "final_iteration_dir": "iter_02_attempt2"}'), True),
                              (('{"run_id": "r2"}'), True),
                              (('{"run_id": "r2", "final_iteration_dir": "../../x"}'), False)):
            with open(os.path.join(traj, "run_summary.json"), "w", encoding="utf-8") as fh:
                fh.write(summary)
            expect("provenance with a retry attempt: %s" % summary, integrity.provenance("project_1")["ok"], want)
    finally:
        mc.TRAJECTORIES_DIR, mc.TRANSLATIONS_DIR = saved

    # the safety proxy's -D unsafe_code build leaves no temp copy behind
    tmpdir = tempfile.gettempdir()
    before = {d for d in os.listdir(tmpdir) if d.startswith("mp4crate_")}
    safety_check.proxy(fresh_copy(tmp_root, "leak"), raw_path=None)
    after = {d for d in os.listdir(tmpdir) if d.startswith("mp4crate_")}
    expect("safety proxy removes its temp crate copy", sorted(after - before), [])

    # symlinks planted by agent code: never written through, never copied into a committed snapshot
    outside = os.path.join(tmp_root, "outside")
    os.makedirs(outside)
    secret, victim = os.path.join(outside, "secret.rs"), os.path.join(outside, "victim.rs")
    for path, text in ((secret, "// OUTSIDE-SECRET\n"), (victim, "// OUTSIDE-VICTIM\n")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)

    def plant_links(ws):
        os.symlink(secret, os.path.join(ws, "src", "linked.rs"))
        os.remove(test_rs(ws))
        os.symlink(victim, test_rs(ws))

    cfg, run, s = _trap(tmp_root, "symlinks", plant_links)
    it_text = "".join(mc.read_text(p) for p in mc.walk_files(run.iter_dir(1, 1)) if not os.path.islink(p))
    expect("symlinks: restore replaces the link, snapshot leaves the linked file out",
           (mc.read_text(victim), os.path.islink(test_rs(cfg["workspace"])),
            os.path.exists(os.path.join(run.iter_dir(1, 1), "src_after", "linked.rs")), "OUTSIDE-SECRET" in it_text),
           ("// OUTSIDE-VICTIM\n", False, False, False))
    sdir = tempfile.mkdtemp(prefix="scrub_links_", dir=tmp_root)
    target = os.path.join(outside, "mail.txt")
    with open(target, "w", encoding="utf-8") as fh:
        fh.write("someone" + "@" + "corp.test\n")
    os.symlink(target, os.path.join(sdir, "link.txt"))
    scrub_secrets.fix([sdir])
    expect("scrub --fix does not write through a symlink", mc.read_text(target), "someone" + "@" + "corp.test\n")

    # a linked src/bin directory: the restore must not delete or write anything in the directory it points to
    keep = os.path.join(outside, "dir")
    os.makedirs(keep)
    with open(os.path.join(keep, "thesis.tex"), "w", encoding="utf-8") as fh:
        fh.write("keep me\n")

    def link_bin_dir(ws):
        shutil.rmtree(os.path.join(ws, "src", "bin"))
        os.symlink(keep, os.path.join(ws, "src", "bin"))

    cfg, run, s = _trap(tmp_root, "dirlink", link_bin_dir)
    expect("linked src/bin: link removed and restored, the linked directory untouched",
           (sorted(os.listdir(keep)), os.path.islink(os.path.join(cfg["workspace"], "src", "bin")),
            ("src/bin", "symlink") in [(v["path"], v["kind"]) for v in s["integrity_violations"]],
            integrity.sha256(test_rs(cfg["workspace"])) == integrity.sha256(test_rs(cfg["skeleton"]))),
           (["thesis.tex"], False, True, True))

    # test output parsing: libtest's lines only (after cargo's first Running line), doc tests included
    header = "     Running unittests src/bin/test.rs (target/debug/deps/test-x)\n"
    parsed = checks.parse_test_output(
        "   Compiling x\n5 | // test foo ... FAILED\n5 | // test empty_input_test ... ok\n" + header +
        "70736274fftest empty_input_test ... ok\n70736274fftest notours ... FAILED\ntest a ... ok\n"
        "   Doc-tests fixture\ntest src/fixture.rs - fixture::triple (line 39) ... FAILED\n",
        expected=["empty_input_test", "a"])
    expect("test lines: glued benchmark result read, compile snippets and unknown glued names ignored, doc test kept",
           {n: v["status"] for n, v in parsed.items()},
           {"empty_input_test": "ok", "a": "ok", "src/fixture.rs - fixture::triple (line 39)": "FAILED"})
    import time as _time
    t0 = _time.time()
    checks.parse_test_output(header + "test a ... " * 8000 + "\n", expected=["a"])
    expect("test lines: a pathological 88 KB line parses in under a second", _time.time() - t0 < 1.0, True)

    # malformed Rust (an agent cut off mid-edit) must not hang the interface scan
    import subprocess
    probe = ("import json, sys; sys.path.insert(0, %r); import check_interface\n"
             "srcs = ['pub fn f() -> i32 {\\n 1\\n', 'pub fn f() -> &str { \"abc', \"pub fn f() -> char { 'a\",\n"
             "        'pub struct S;\\nimpl S {\\n pub fn a(&self) {}\\n', '#![allow(x)]\\npub fn f() {}\\n#!']\n"
             "print(json.dumps([sorted(check_interface.extract_items(s)) for s in srcs]))" % mc.SRC_DIR)
    try:
        out = subprocess.run([sys.executable, "-I", "-c", probe], stdout=subprocess.PIPE, timeout=60).stdout
        malformed = json.loads(out.decode("utf-8"))
    except subprocess.TimeoutExpired:
        malformed = "hung"
    expect("interface scan terminates on unclosed braces, literals and a stray #!", malformed,
           [["f"], ["f"], ["f"], ["S"], ["f"]])
    # a module file the scan cannot read at all: reported, never raised (a crash would repeat on every resume)
    satc_iface = os.path.join(mc.skeleton_dir("project_1"), "src", "interfaces")
    cut = fresh_copy(tmp_root, "cut")
    with open(os.path.join(cut, "src", "satc.rs"), "w", encoding="utf-8") as fh:
        fh.write(mc.read_text(os.path.join(satc_iface, "satc.rs"))[:1350])
    rep = check_interface.compare(satc_iface, cut)
    expect("interface: unreadable module reported as parse_error, items missing",
           (bool(rep["modules"]["satc"]["parse_error"]), rep["missing"] == rep["interface_items"]), (True, True))

    # lints raised to errors in the source are not a clean clippy run
    _, _, s = _trap(tmp_root, "deny_lints", lambda ws: (
        _edit(fx(ws), "pub fn double(x: i32) -> i32 {\n    x * 2\n}",
              "pub fn double(x: i32) -> i32 {\n    return x * 2;\n}"),
        _edit(fx(ws), "//! Self-test", "#![deny(clippy::all)]\n//! Self-test")))
    errs = [b for b in s["blockers"] if b.startswith("clippy errors: ")]
    expect("deny attribute: clippy errors block success, warnings read 0",
           (s["success"], s["clippy_agent_total"], len(errs) == 1 and int(errs[0].split(": ")[1]) > 0),
           (False, 0, True))

    # resume: interrupted during workspace setup (step "init") continues instead of spinning
    cfg = drill_cfg(tmp_root, "init_resume", {"1": {"1": ["copy:clean"]}}, max_iterations=1)
    run = run_pipeline.Run(cfg, "IR")
    os.makedirs(os.path.join(run.dir, "init_src"))   # the interrupted setup had already started its snapshot
    run_pipeline._write_json(run.state_path, {
        "run_id": "IR", "project": "project_1", "config_hash": cfg["config_hash"], "created": "x",
        "status": "running", "iteration": 1, "attempt": 1, "step": "init", "history": [], "attempts_total": 0,
        "stop_reason": None})
    code = run_pipeline.run_loop(cfg, run_id="IR", resume=True)
    expect("resume from step init sets the workspace up and runs", (code, _state(cfg, "IR")["stop_reason"]),
           (0, "SUCCESS"))

    # resume after the agent result was recorded but before the step moved on: the agent is not called again
    cfg = drill_cfg(tmp_root, "reuse", {"1": {"1": ["copy:partial"]}}, max_iterations=1)
    run = run_pipeline.Run(cfg, "RU")
    os.makedirs(run.iter_dir(1, 1))
    run.state = {"history": []}
    run_pipeline.init_workspace(run)
    shutil.copy2(CLEAN_VARIANT, fx(cfg["workspace"]))   # the recorded attempt's edits
    with open(os.path.join(run.iter_dir(1, 1), "prompt.md"), "w", encoding="utf-8") as fh:
        fh.write("recorded prompt")
    run_pipeline._write_json(os.path.join(run.iter_dir(1, 1), "agent_result.json"), {"outcome": "ok"})
    run_pipeline._write_json(run.state_path, {
        "run_id": "RU", "project": "project_1", "config_hash": cfg["config_hash"], "created": "x",
        "status": "running", "iteration": 1, "attempt": 1, "step": "agent", "agent_started": [1, 1],
        "history": [], "attempts_total": 1, "stop_reason": None})
    code = run_pipeline.run_loop(cfg, run_id="RU", resume=True)
    st = _state(cfg, "RU")
    expect("resume reuses a recorded agent result (no second call)",
           (code, st["stop_reason"], st["attempts_total"],
            os.path.exists(os.path.join(run.iter_dir(1, 1), "agent.stream.jsonl"))), (0, "SUCCESS", 1, False))

    # usage limit on the same iteration MAX_LIMIT_ATTEMPTS times running: hand back to a person (exit 75)
    run.state = {"iteration": 2, "attempt": run_pipeline.MAX_LIMIT_ATTEMPTS, "history": [], "step": "agent",
                 "pauses": [{"iteration": 2, "cause": "usage_limit"}] * (run_pipeline.MAX_LIMIT_ATTEMPTS - 1)}
    rl = dict(cfg["pipeline"]["rate_limit"], mode="wait")
    expect("usage-limit retries capped in wait mode", run_pipeline._usage_limit(run, {"resets_at": None}, rl),
           run_pipeline.EXIT_USAGE_LIMIT)

    # a new run is refused while another run of the project is still open (it would replace its workspace)
    cfg = drill_cfg(tmp_root, "open_run", {"1": {"1": ["copy:clean"]}}, max_iterations=1)
    os.makedirs(os.path.join(cfg["trajectory_root"], "run_OPEN"))
    run_pipeline._write_json(os.path.join(cfg["trajectory_root"], "run_OPEN", "run_state.json"),
                             {"status": "running", "step": "prompt"})
    expect("new run refused while another run is open", run_pipeline.run_loop(cfg, run_id="NEW", yes=True), 2)

    # resume refuses a run whose configuration changed since it started
    cfg = drill_cfg(tmp_root, "hash_resume", {"1": {"1": ["copy:clean"]}}, max_iterations=1)
    run = run_pipeline.Run(cfg, "HR")
    os.makedirs(run.dir)
    run_pipeline._write_json(run.state_path, {
        "run_id": "HR", "project": "project_1", "config_hash": "0" * 64, "created": "x", "status": "running",
        "iteration": 1, "attempt": 1, "step": "prompt", "history": [], "attempts_total": 0, "stop_reason": None})
    expect("resume refused after a configuration change", run_pipeline.run_loop(cfg, run_id="HR", resume=True), 2)

    # isolation fails closed: no system/init event, or an API key instead of the subscription login
    cfg = config.load("project_1")
    for mode in ("no_init", "api_key"):
        r, _ = _fake_run(cfg, tmp_root, mode)
        expect("isolation: %s -> isolation_violation" % mode, r["outcome"], "isolation_violation")
    saved_env = dict(os.environ)
    os.environ.update({"ANTHROPIC_API_KEY": "x", "RUSTFLAGS": "-A warnings"})
    try:
        env = agent_runner.agent_env(cfg)
        cenv = mc.cargo_env({"RUSTFLAGS": "-D unsafe_code"})
    finally:
        os.environ.clear()
        os.environ.update(saved_env)
    expect("agent env: no API key, no inherited RUSTFLAGS",
           ("ANTHROPIC_API_KEY" in env, "RUSTFLAGS" in env, cenv.get("RUSTFLAGS")), (False, False, "-D unsafe_code"))

    # scrubbing: upstream benchmark e-mails (licence headers the agent may keep) are not personal data
    upstream = "j" + "@" + "w1.fi"
    expect("scrub: upstream e-mail kept, other e-mail flagged",
           (scrub_secrets.scan_text("Copyright <%s>" % upstream), [h[1] for h in scrub_secrets.scan_text(
               "mail someone" + "@" + "corp.test")]), ([], ["email"]))

    # the progress score uses the full build error count, not the 50 kept in the list
    many = dict(hung, build={"ok": False, "errors": [{"code": None, "message": "x"}] * 50, "error_count": 70,
                             "error_codes": []}, clippy=None)
    expect("score: build errors beyond the first 50 still count",
           run_pipeline.evaluate(many, {"known_failing_tests": []})["score"][1], -70)

    # config validation at the boundary
    import copy as _copy
    proj = _copy.deepcopy(config.load("project_2")["project_cfg"])
    proj["known_failing_tests"][0]["expected_assertion"] = ""
    bad = []
    try:
        config.validate_project(proj, "project_2")
    except config.ConfigError:
        bad.append("empty assertion")
    raw = config._load_yaml(mc.PIPELINE_YAML)
    raw["agent"]["setting_sources"] = "user,project"
    try:
        config.validate_pipeline(raw)
    except config.ConfigError:
        bad.append("setting_sources")
    expect("config: empty known-failing assertion and user setting sources rejected", bad,
           ["empty assertion", "setting_sources"])

    # agent B gets a fresh render of the recorded prompt; a mismatch falls back to the record
    cfg = drill_cfg(tmp_root, "prompt_send", {})
    home_c_dir = "/" + "Users/someone/repo/MP4/subjects/project_1/c"   # a path the scrubber rewrites (assembled)
    cfg["c_dir"] = home_c_dir
    run = run_pipeline.Run(cfg, "PS")
    os.makedirs(run.iter_dir(1, 1))
    run.state = {"history": []}
    pm = os.path.join(run.iter_dir(1, 1), "prompt.md")
    with open(pm, "w", encoding="utf-8") as fh:
        fh.write(scrub_secrets.scrub_text(run_pipeline.build_prompt(run, 1)))
    sent = run_pipeline._prompt_for_agent(run, 1, run.iter_dir(1, 1))
    with open(pm, "w", encoding="utf-8") as fh:
        fh.write("recorded")
    expect("prompt to agent: absolute paths sent, the record keeps ~, recorded prompt on mismatch",
           (home_c_dir in sent, home_c_dir in mc.read_text(pm) or "~/repo" in scrub_secrets.scrub_text(sent),
            run_pipeline._prompt_for_agent(run, 1, run.iter_dir(1, 1))), (True, True, "recorded"))

    # every attempt records its exact argv (session id included)
    with open(os.path.join(tmp_root, "drill_A", "traj", "run_A", "iter_01", "agent_result.json"),
              encoding="utf-8") as fh:
        expect("agent_result.json records the attempt's argv", bool(json.load(fh).get("argv")), True)

    # a skeleton that no longer matches CHECKSUMS.sha256 stops the run before any verdict
    cfg = drill_cfg(tmp_root, "subjects", {})
    with open(os.path.join(os.path.dirname(cfg["skeleton"]), "CHECKSUMS.sha256"), "w", encoding="utf-8") as fh:
        fh.write("%s  skeleton/Cargo.toml\n" % ("0" * 64))
    try:
        run_pipeline.require_intact_subjects(run_pipeline.Run(cfg, "SJ"))
        refused = False
    except SystemExit:
        refused = True
    expect("changed subjects skeleton refused", refused, True)


def _run_m6(tmp_root):
    """Owner gates G1-G7 (why.md D-M5GATES), applied at M6 step 1."""
    fx = lambda ws: os.path.join(ws, "src", "fixture.rs")  # noqa: E731

    # G1 (a): files outside src/ and symlinks are removed and recorded; covers review-1 probe x3 and F9
    outside = os.path.join(tmp_root, "g1_outside.rs")
    with open(outside, "w", encoding="utf-8") as fh:
        fh.write("// outside\n")

    def plant_strays(ws):
        _edit(fx(ws), "pub fn double(x: i32) -> i32 {\n    x * 2\n}",
              "pub fn double(x: i32) -> i32 {\n    return x * 2;\n}")   # a warning the lint cap would hide
        os.makedirs(os.path.join(ws, ".cargo"))
        _append(os.path.join(ws, ".cargo", "config.toml"), '[build]\nrustflags = ["--cap-lints", "allow"]\n')
        _append(os.path.join(ws, "clippy.toml"), "too-many-arguments-threshold = 99\n")
        os.makedirs(os.path.join(ws, "tests"))
        _append(os.path.join(ws, "tests", "t.rs"), "#[test]\nfn t() {}\n")
        os.makedirs(os.path.join(ws, ".claude"))
        _append(os.path.join(ws, ".claude", "settings.json"), "{}\n")
        os.symlink(outside, os.path.join(ws, "src", "linked.rs"))

    cfg, run, s = _trap(tmp_root, "g1_strays", plant_strays)
    ws = cfg["workspace"]
    expect("G1a: files outside src/ and a symlink -> removed, recorded, not green",
           (s["success"], sorted((v["path"], v["kind"], v["restored"]) for v in s["integrity_violations"]),
            sorted(x for x in os.listdir(ws) if x != "target")),
           (False, [(".cargo/config.toml", "outside_src", True), (".claude/settings.json", "outside_src", True),
                    ("clippy.toml", "outside_src", True), ("src/linked.rs", "symlink", True),
                    ("tests/t.rs", "outside_src", True)],
            [".gitignore", ".integrity", "Cargo.lock", "Cargo.toml", "src"]
            if os.path.exists(os.path.join(cfg["skeleton"], ".gitignore")) else
            [".integrity", "Cargo.lock", "Cargo.toml", "src"]))
    expect("G1a: lint cap removed before measuring, so clippy still sees the warning", s["blockers"],
           ["agent clippy warnings: 1", "integrity violations: 5"])
    expect("G1a: the linked file is outside the snapshot and the target untouched",
           (os.path.exists(os.path.join(run.iter_dir(1, 1), "src_after", "linked.rs")), mc.read_text(outside)),
           (False, "// outside\n"))
    rep_ws = _with(fresh_copy(tmp_root, "g1_report"), lambda w: _append(os.path.join(w, "notes.md"), "x\n"))
    expect("G1a: report-only mode records without deleting",
           ([(v["path"], v["restored"]) for v in integrity.sweep_strays(rep_ws, FIXTURE, restore=False)],
            os.path.exists(os.path.join(rep_ws, "notes.md"))), ([("notes.md", False)], True))

    # G1 (b): lint-level attributes in library code block SUCCESS, except the D-ALLOW pair; covers probe x2
    allow_all = lambda ws: _edit(fx(ws), "//! Self-test", "#![allow(clippy::all)]\n//! Self-test")  # noqa: E731
    _, _, s = _trap(tmp_root, "g1_allow_all", allow_all)
    expect("G1b: #![allow(clippy::all)] -> lint attribute blocks success", (s["success"], s["blockers"],
           s["lint_attribute_hits"]), (False, ["lint attributes: 1"], 1))
    other_item = lambda ws: _edit(fx(ws), "pub fn double(", "#[allow(clippy::boxed_local)]\npub fn double(")  # noqa
    _, _, s = _trap(tmp_root, "g1_wrong_item", other_item)
    expect("G1b: the permitted lint on another item is not permitted", s["blockers"], ["lint attributes: 1"])
    crate = fresh_copy(tmp_root, "g1_scan")
    shutil.copy2(CLEAN_VARIANT, fx(crate))
    _append(fx(crate), "\n#[cfg_attr(test, derive(Debug))]\npub struct A;\n#[cfg_attr(test, expect(dead_code))]\n"
                       "pub struct B;\n#[allow(clippy::boxed_local, dead_code)]\npub fn c(v: Box<i32>) -> i32 { *v }\n"
                       "// #[allow(dead_code)] in a comment\npub const D: &str = \"#[allow(x)]\";\n"
                       "#[warn(missing_docs)]\npub fn e() {}\n")
    hits = integrity.lint_attribute_scan(crate, [{"lint": "clippy::boxed_local", "item": "total"},
                                                 {"lint": "clippy::boxed_local", "item": "c"}])
    expect("G1b: scan flags cfg_attr(expect), a pair plus an extra lint, warn; ignores derive, comments, literals",
           [(h["item"], h["attribute"].split("(")[0]) for h in hits], [("B", "#[cfg_attr"), ("c", "#[allow"),
                                                                       ("e", "#[warn")])
    lib_crate = fresh_copy(tmp_root, "g1_lib")
    _edit(os.path.join(lib_crate, "src", "lib.rs"), "pub mod", mc.FORBID_LINE + "\npub mod")
    expect("G1b: the wrapper's #![forbid(unsafe_code)] in src/lib.rs is not a finding",
           integrity.lint_attribute_scan(lib_crate, []), [])
    chk = json.loads(json.dumps(run_pipeline.summarize(dict(
        build={"ok": True, "error_codes": []}, test={"passed": 1, "total": 1}, clippy=None,
        safety={"unsafe_lines": 0, "unsafe_calls": 0, "unsafe_casts": 0, "pointer_arithmetic": 0, "tool": "proxy"},
        interface={"missing": 0, "changed": 0}, integrity={"violations": []}, hardcode_hits=[],
        lint_attributes=hits))))
    expect("G1b: summary counts lint attribute hits", chk["lint_attribute_hits"], 3)
    digest = prompt_builder.digest({"lint_attributes": hits}, config.load("project_1")["pipeline"]["digest"])
    expect("G1b: repair feedback names each lint attribute", "### Lint attributes" in digest and "on `B`" in digest,
           True)

    # G2: a lost login pauses (exit 75), and the run continues on resume
    cfg = drill_cfg(tmp_root, "g2", {"1": {"1": ["auth_error"], "2": ["copy:clean"]}})
    code = run_pipeline.run_loop(cfg, run_id="G2", yes=True)
    st = _state(cfg, "G2")
    expect("G2: auth error -> exit 75, run open at attempt 2, cause recorded",
           (code, st["status"], st["attempt"], [p.get("cause") for p in st["pauses"]], st["pauses"][0]["wait_s"]),
           (75, "running", 2, ["auth_error"], 0))
    code = run_pipeline.run_loop(cfg, run_id="G2", resume=True)
    st = _state(cfg, "G2")
    expect("G2: resume after login -> SUCCESS on iter_01_attempt2", (code, st["stop_reason"], os.path.isdir(
        os.path.join(cfg["trajectory_root"], "run_G2", "iter_01_attempt2"))), (0, "SUCCESS", True))

    # G3: a clean crate after iteration 1 gets a review iteration before SUCCESS
    cfg = drill_cfg(tmp_root, "g3", {"1": {"1": ["copy:clean"]}, "2": {"1": ["noop"]}}, min_iterations=2)
    code = run_pipeline.run_loop(cfg, run_id="G3", yes=True)
    st = _state(cfg, "G3")
    with open(os.path.join(cfg["trajectory_root"], "run_G3", "iter_02", "prompt.md"), encoding="utf-8") as fh:
        p2 = fh.read()
    expect("G3: min_iterations 2 -> SUCCESS at iteration 2, not 1",
           (code, st["stop_reason"], [h["success"] for h in st["history"]]), (0, "SUCCESS", [True, True]))
    expect("G3: the review iteration's prompt says the crate already meets every check",
           "the crate already meets every check" in p2, True)
    raw = config._load_yaml(mc.PIPELINE_YAML)
    expect("G3: pipeline.yaml sets loop.min_iterations 2", raw["loop"]["min_iterations"], 2)
    raw["loop"]["min_iterations"] = 9
    try:
        config.validate_pipeline(raw)
        expect("G3: min_iterations above max_iterations rejected", "accepted", "ConfigError")
    except config.ConfigError:
        expect("G3: min_iterations above max_iterations rejected", "ConfigError", "ConfigError")

    # G4: --config / --manifest-path denied on cargo; the agent's words are scanned for leak markers
    pcfg = config.load("project_1")
    argv = agent_runner.build_argv(pcfg)
    denied = argv[argv.index("--disallowedTools") + 1:argv.index("--setting-sources")]
    expect("G4: cargo --config and --manifest-path denied",
           [d for d in denied if "--config" in d or "--manifest-path" in d],
           ["Bash(cargo *--config*)", "Bash(cargo *--manifest-path*)"])
    cfg = drill_cfg(tmp_root, "g4", {"1": {"1": ["say:I follow the Working agreement", "copy:clean"]}})
    run_pipeline.run_loop(cfg, run_id="G4", yes=True)
    with open(os.path.join(cfg["trajectory_root"], "run_G4", "iter_01", "agent_result.json"), encoding="utf-8") as fh:
        found = json.load(fh).get("leak_markers_found")
    expect("G4: leak marker in the agent's text recorded and logged",
           (found, "LEAK MARKERS" in mc.read_text(os.path.join(cfg["trajectory_root"], "run_G4", "run.log"))),
           (["Working agreement"], True))

    # G5: the project note reaches the prompt for both projects
    for proj in mc.PROJECTS:
        expect("G5: %s prompt tells the agent to keep public items in src/<module>.rs" % proj,
               "defined directly in src/<module>.rs" in prompt_builder.build_initial(config.load(proj)), True)

    # G6: at MAX_ITERATIONS the best iteration ships, not a last one that does not build
    cfg = drill_cfg(tmp_root, "g6", {"1": {"1": ["copy:partial"]}, "2": {"1": ["copy:broken"]}}, max_iterations=2)
    code = run_pipeline.run_loop(cfg, run_id="G6", yes=True)
    with open(os.path.join(cfg["trajectory_root"], "run_summary.json"), encoding="utf-8") as fh:
        rs = json.load(fh)
    snap = os.path.join(cfg["trajectory_root"], "run_G6", "iter_01", "src_after")
    expect("G6: MAX_ITERATIONS ships iter_01 (builds) over iter_02 (broken)",
           (code, rs["stop_reason"], rs["final_iteration_dir"], rs["last_iteration_dir"], rs["final_selection"],
            rs["final"]["compiles"], integrity.diff_trees(os.path.join(cfg["workspace"], "src"), snap)),
           (0, "MAX_ITERATIONS", "iter_01", "iter_02", "best", True, {"added": [], "removed": [], "modified": []}))
    expect("G6: best_iteration prefers success, then score, the later on a tie", _best_of([
        (1, False, [1, 0, -1, 0, 0]), (2, True, [1, 0, 0, 0, 0]), (3, False, [2, 0, 0, 0, 0]),
        (4, True, [1, 0, 0, 0, 0])], tmp_root), "iter_04")

    # G7: overloaded and connection failures pause (fallback wait) and redo the iteration
    for kind in ("overloaded", "connection_error"):
        cfg = drill_cfg(tmp_root, "g7_" + kind, {"1": {"1": [kind], "2": ["copy:clean"]}})
        cfg["pipeline"]["rate_limit"]["fallback_minutes"] = 0.02
        code = run_pipeline.run_loop(cfg, run_id="G7", yes=True)
        st = _state(cfg, "G7")
        expect("G7: %s -> pause, attempt 2, SUCCESS" % kind,
               (code, st["stop_reason"], [(p["cause"], p["wait_s"]) for p in st["pauses"]], len(st["history"])),
               (0, "SUCCESS", [(kind, 1)], 1))
    expect("G7: connection error with no result line read from stderr",
           agent_runner.classify(None, False, None, False, [], "Error: socket hang up"), "connection_error")
    expect("G7: other failures without a result stay errors",
           agent_runner.classify(None, False, None, False, [], "panic"), "error")


def _with(path, fn):
    fn(path)
    return path


def _best_of(entries, tmp_root):
    """best_iteration over a synthetic history: (iteration, success, score) or (iteration, success, guard_clean,
    score)."""
    cfg = drill_cfg(tmp_root, "g6_best_%d" % len(os.listdir(tmp_root)), {})
    run = run_pipeline.Run(cfg, "B")
    hist = []
    for e in entries:
        k, ok, sc = (e[0], e[1], e[-1])
        h = {"iteration": k, "attempt": 1, "success": ok, "score": sc}
        if len(e) == 4:
            h["guard_clean"] = e[2]
        hist.append(h)
        os.makedirs(os.path.join(run.iter_dir(k, 1), "src_after"))
    run.state = {"history": hist}
    return run_pipeline.best_iteration(run)


def _run_m8(tmp_root):
    """Fixes from review 2 (docs/programs/mp4/reviews/review-2.md, C1-C23)."""
    import stat as _stat
    import subprocess
    fx = lambda ws: os.path.join(ws, "src", "fixture.rs")  # noqa: E731
    sat = config.load("project_1")["project_cfg"]["allow_attributes"]

    # C1: a guard-blocked iteration never ships ahead of a guard-clean one, whatever its score
    expect("C1: best_iteration ranks guard-clean before a higher-scoring blocked iteration", _best_of([
        (1, False, False, [1, 0, 0, 0, 0]), (2, False, True, [1, 0, -1, 0, 0])], tmp_root), "iter_02")
    expect("C1: guard_clean sees lint, hard-coding, integrity and a gamed known-failing test",
           [run_pipeline.guard_clean(x) for x in (
               {}, {"lint_attribute_hits": 1}, {"hardcode_hits": 1}, {"integrity_violations": [{"path": "x"}]},
               {"known_failing": {"t": {"failed": False, "assertion_matches": False, "location_matches": False}}})],
           [True, False, False, False, False])

    # C2: a unit test that plants a lint cap while the wrapper measures is caught and removed
    plant = (
        "\n#[cfg(test)]\nmod plant {\n    #[test]\n    fn plant() {\n"
        "        std::fs::create_dir_all(\".cargo\").unwrap();\n"
        "        std::fs::write(\".cargo/config.toml\", \"[build]\\nrustflags = [\\\"--cap-lints\\\", "
        "\\\"allow\\\"]\\n\").unwrap();\n    }\n}\n")
    cfg, run, s = _trap(tmp_root, "c2_plant", lambda ws: (
        _edit(fx(ws), "pub fn double(x: i32) -> i32 {\n    x * 2\n}",
              "pub fn double(x: i32) -> i32 {\n    return x * 2;\n}"), _append(fx(ws), plant)))
    expect("C2: lint cap planted during measurement -> recorded after measurement, removed, not green",
           (s["success"], [(v["path"], v["kind"], v.get("after_measurement")) for v in s["integrity_violations"]],
            os.path.exists(os.path.join(cfg["workspace"], ".cargo", "config.toml"))),
           (False, [(".cargo/config.toml", "outside_src", True)], False))

    # C3: interrupted while stopping -> the resume finishes that stop (no extra iteration), src/ comes back
    cfg = drill_cfg(tmp_root, "c3", {"1": {"1": ["copy:partial"]}, "2": {"1": ["copy:broken"]}}, max_iterations=2)
    run_pipeline.run_loop(cfg, run_id="C3", yes=True)
    sp = os.path.join(cfg["trajectory_root"], "run_C3", "run_state.json")
    st = _state(cfg, "C3")
    st.update({"status": "running", "step": "closed", "pending_stop": "MAX_ITERATIONS", "stop_reason": None})
    run_pipeline._write_json(sp, st)
    shutil.rmtree(os.path.join(cfg["workspace"], "src"))
    code = run_pipeline.run_loop(cfg, run_id="C3", resume=True)
    st = _state(cfg, "C3")
    expect("C3: resume after an interrupted stop finishes it, ships iter_01, runs no iteration 3",
           (code, st["status"], st["stop_reason"], len(st["history"]), "pending_stop" in st,
            integrity.diff_trees(os.path.join(cfg["workspace"], "src"),
                                 os.path.join(cfg["trajectory_root"], "run_C3", "iter_01", "src_after"))),
           (0, "stopped", "MAX_ITERATIONS", 2, False, {"added": [], "removed": [], "modified": []}))

    # C9: INDEX.md shows the shipped iteration's tests, not the last one's
    with open(os.path.join(cfg["trajectory_root"], "INDEX.md"), encoding="utf-8") as fh:
        row = [ln for ln in fh.read().splitlines() if ln.startswith("| `run_C3`")]
    expect("C9: INDEX.md final tests follow the shipped iteration", "| 2 | 1/2 |" in (row or [""])[0], True)

    # C4: a directory that is not a crate is refused before anything is written or deleted
    notcrate = tempfile.mkdtemp(prefix="notcrate_", dir=tmp_root)
    _append(os.path.join(notcrate, "keep.txt"), "keep\n")
    out = subprocess.run([sys.executable, "-I", os.path.join(mc.SRC_DIR, "integrity.py"), "--verify",
                          "--project", "project_1", "--crate-dir", notcrate], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    expect("C4: integrity.py --verify on a non-crate directory exits 2 and deletes nothing",
           (out.returncode, sorted(os.listdir(notcrate))), (2, ["keep.txt"]))

    # C5: lint attributes and test literals are found in any library file, whatever its name or directory
    crate = fresh_copy(tmp_root, "c5")
    shutil.copy2(CLEAN_VARIANT, fx(crate))
    os.makedirs(os.path.join(crate, "src", "m", "target"))
    _append(os.path.join(crate, "src", "imp.txt"), "#![allow(clippy::all)]\nfn hidden() {}\n")
    _append(os.path.join(crate, "src", "m", "target", "x.rs"), "#![allow(clippy::all)]\n")
    _append(fx(crate), "\n#[r#allow(clippy::needless_return)]\npub fn r() -> i32 {\n    return 1;\n}\n")
    _append(os.path.join(crate, "src", "greeting.txt"), "hello from the fixture harness")
    expect("C5: lint scan reads non-.rs files, nested target/ dirs and r#allow",
           sorted((h["file"], h["attribute"].split("(")[0]) for h in integrity.lint_attribute_scan(crate, [
               {"lint": "clippy::boxed_local", "item": "total"}])),
           [("src/fixture.rs", "#[r#allow"), ("src/imp.txt", "#![allow"), ("src/m/target/x.rs", "#![allow")])
    expect("C5: hard-coding scan matches a test literal kept in a non-.rs file",
           [h["lib_file"] for h in integrity.hardcode_scan(crate)], ["src/greeting.txt"])
    cfg, run, s = _trap(tmp_root, "c5_integrity_dir", lambda ws: _append(
        os.path.join(ws, ".integrity", "helpers.rs"), "#![allow(clippy::all)]\n"))
    expect("C5: files written into .integrity/ besides the manifest are strays",
           ([(v["path"], v["kind"]) for v in s["integrity_violations"]],
            sorted(os.listdir(os.path.join(cfg["workspace"], ".integrity")))),
           ([(".integrity/helpers.rs", "outside_src")], ["manifest.sha256"]))

    # C7: the permitted allow in every valid spelling; an allow on a generic impl is not the permitted item
    crate = fresh_copy(tmp_root, "c7")
    with open(os.path.join(crate, "src", "fixture.rs"), "w", encoding="utf-8") as fh:
        fh.write("#[allow(clippy::too_many_arguments, reason = \"fixed signature, 8 parameters\")]\n"
                 "pub fn satc_is_separating_axis() {}\n"
                 "#[allow(\n    clippy::too_many_arguments\n)]\npub fn satc_is_separating_axis() {}\n"
                 "#[allow(clippy::too_many_arguments)]\npub const fn satc_is_separating_axis() {}\n"
                 "#[allow(clippy::too_many_arguments)]\nimpl<'a> W<'a> {\n    fn satc_is_separating_axis() {}\n}\n")
    expect("C7: reason =, multi-line and const fn forms permitted; generic impl flagged",
           [(h["line"], h["item"]) for h in integrity.lint_attribute_scan(crate, sat)], [(9, "W")])

    # C8: the CLI's own connection-failure wordings pause; terminal_reason is recorded
    texts = ["API Error: Unable to connect to API. Check your internet connection",
             "API Error: Connection dropped (EPIPE)", "API Error: Connection refused (ConnectionRefused)",
             "API Error: Can't reach the API server (FailedToOpenSocket)", "Request timed out",
             "API Error: Connection lost while your computer was asleep"]
    expect("C8: the CLI's connection-failure texts classify as connection_error",
           [agent_runner.classify({"subtype": "success", "is_error": True, "result": t}, False, None, False, [])
            for t in texts], ["connection_error"] * len(texts))

    # C10: a hand edit made while a run waits on a pause is reverted and recorded
    cfg = drill_cfg(tmp_root, "c10", {"1": {"1": ["copy:partial", "auth_error"], "2": ["noop"]}}, max_iterations=1)
    code1 = run_pipeline.run_loop(cfg, run_id="C10", yes=True)
    _append(os.path.join(cfg["workspace"], "src", "hand.rs"), "// hand edit while paused\n")
    code2 = run_pipeline.run_loop(cfg, run_id="C10", resume=True)
    st = _state(cfg, "C10")
    expect("C10: edit during a pause -> workspace_tamper against the pause snapshot, reverted",
           (code1, code2, [(t["against"], t["added"]) for t in st.get("workspace_tamper", [])],
            os.path.exists(os.path.join(cfg["workspace"], "src", "hand.rs"))),
           (75, 0, [("iter_01/src_at_pause", ["hand.rs"])], False))

    # C12: the integrity list in the repair digest is capped
    many = {"integrity": {"violations": [{"kind": "outside_src", "path": "b/%d" % i} for i in range(30)]}}
    dg = prompt_builder.digest(many, config.load("project_1")["pipeline"]["digest"])
    expect("C12: digest lists 20 integrity violations and the remainder count",
           (dg.count("- outside_src b/"), "- ... 10 more" in dg), (20, True))

    # C13: chmod-ed directories cannot hide or pin strays
    cfg, run, s = _trap(tmp_root, "c13", lambda ws: (
        os.makedirs(os.path.join(ws, "locked")), _append(os.path.join(ws, "locked", "a.toml"), "x\n"),
        os.makedirs(os.path.join(ws, "hidden")), _append(os.path.join(ws, "hidden", "b.toml"), "x\n"),
        os.chmod(os.path.join(ws, "locked"), 0o555), os.chmod(os.path.join(ws, "hidden"), 0o311)))
    expect("C13: strays in read-only and unlistable directories are removed and recorded",
           (sorted((v["path"], v["kind"], v["restored"]) for v in s["integrity_violations"]),
            [d for d in ("locked", "hidden") if os.path.exists(os.path.join(cfg["workspace"], d))]),
           ([("hidden/b.toml", "outside_src", True), ("locked/a.toml", "outside_src", True)], []))

    # C14: the owner's Finder metadata is removed without counting against the agent
    cfg, run, s = _trap(tmp_root, "c14", lambda ws: _append(os.path.join(ws, ".DS_Store"), "x"))
    expect("C14: .DS_Store removed, not recorded",
           (s["integrity_violations"], os.path.exists(os.path.join(cfg["workspace"], ".DS_Store"))), ([], False))

    # C15: a symlink at an immutable path is replaced even when its target has the same content
    target = os.path.join(tmp_root, "same_lock")
    shutil.copy2(os.path.join(FIXTURE, "Cargo.lock"), target)

    def link_lock(ws):
        os.remove(os.path.join(ws, "Cargo.lock"))
        os.symlink(target, os.path.join(ws, "Cargo.lock"))

    cfg, run, s = _trap(tmp_root, "c15", link_lock)
    lock = os.path.join(cfg["workspace"], "Cargo.lock")
    expect("C15: Cargo.lock symlink to identical content -> violation, regular file again",
           ([(v["path"], v["kind"]) for v in s["integrity_violations"]], os.path.islink(lock),
            _stat.S_ISREG(os.lstat(lock).st_mode)), ([("Cargo.lock", "symlink")], False, True))

    # C16: the leak scan reads every block the agent wrote, skips non-objects, and never fails open
    sdir = tempfile.mkdtemp(prefix="leak_", dir=tmp_root)
    stream = os.path.join(sdir, "s.jsonl")
    with open(stream, "w", encoding="utf-8") as fh:
        fh.write("null\n[1]\n" + json.dumps({"type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Write", "input": {"content": "// the Working agreement says"}}]}}) + "\n")
    expect("C16: tool_use input scanned, non-object lines skipped, missing stream -> None",
           (run_pipeline.leak_scan(stream), run_pipeline.leak_scan(os.path.join(sdir, "missing.jsonl"))),
           (["Working agreement"], None))
    real = sorted(glob.glob(os.path.join(mc.TRAJECTORIES_DIR, "project_*", "run_*", "iter_*", "agent.stream.jsonl")))
    expect("C16: no leak marker in the committed real streams under the wider scan",
           [p for p in real if run_pipeline.leak_scan(p)], [])

    # S3: lost logins (each already handed to a person) do not use up the unattended-wait cap
    cfg = drill_cfg(tmp_root, "s3", {"1": {"1": ["auth_error"], "2": ["auth_error"], "3": ["auth_error"],
                                           "4": ["overloaded"], "5": ["copy:clean"]}})
    cfg["pipeline"]["rate_limit"]["fallback_minutes"] = 0.02
    codes = [run_pipeline.run_loop(cfg, run_id="S3", yes=True)]
    while codes[-1] == run_pipeline.EXIT_USAGE_LIMIT and len(codes) < 6:
        codes.append(run_pipeline.run_loop(cfg, run_id="S3", resume=True))
    st = _state(cfg, "S3")
    expect("S3: three lost logins, then an outage that waits and the iteration succeeds",
           (codes, st["stop_reason"], [p["cause"] for p in st["pauses"]]),
           ([75, 75, 75, 0], "SUCCESS", ["auth_error"] * 3 + ["overloaded"]))

    # C19, C21, C23
    raw = config._load_yaml(mc.PIPELINE_YAML)
    raw["loop"].update({"min_iterations": 5, "max_iterations": 8, "no_progress_rounds": 3})
    try:
        config.validate_pipeline(raw)
        expect("C19: min_iterations beyond no_progress_rounds + 1 rejected", "accepted", "ConfigError")
    except config.ConfigError:
        expect("C19: min_iterations beyond no_progress_rounds + 1 rejected", "ConfigError", "ConfigError")
    raw = config._load_yaml(mc.PIPELINE_YAML)
    raw["rate_limit"]["fallback_minutes"] = 0.5
    expect("C21: README text keeps a fractional wait", "0.5-minute wait" in summarize.generated_sections(raw)[
        "stopping-condition"], True)
    rs = {"final": {"compiles": True, "tests_passed": 1, "tests_total": 1, "clippy_agent": {}, "clippy_harness": {},
                    "safety": {m: 0 for m in summarize.SAFETY}, "integrity_violations": [],
                    "lint_attribute_hits": 0, "hardcode_hits": 0}}
    ck = {"summary": dict(rs["final"], integrity_violations=0, lint_attribute_hits=1, clippy_agent={},
                          clippy_harness={})}
    expect("C23: compare reports a guard count only check-only sees",
           [d["field"] for d in summarize.compare(rs, ck)], ["lint_attribute_hits"])


if __name__ == "__main__":
    sys.exit(main())
