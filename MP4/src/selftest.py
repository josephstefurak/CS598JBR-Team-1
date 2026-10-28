"""Self-test: run every MP4 check against selftest_fixture/ and assert the planted counts.

The fixture plants exactly: one unsafe block holding one transmute and one
ptr.add, one agent lint per clippy group (eq_op, needless_return,
needless_bool, boxed_local), one harness lint (needless_return in the test
file), one failing test of two, one 20+ char test literal copied into library
code, and one interface item missing. Everything runs on temp copies; nothing
in the repository is modified.

Prints PASS/FAIL per assertion and a final count; exit 1 if anything failed.
"""
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_interface  # noqa: E402
import checks  # noqa: E402
import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402
import safety_check  # noqa: E402
import scrub_secrets  # noqa: E402

FIXTURE = os.path.join(mc.SRC_DIR, "selftest_fixture")
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


if __name__ == "__main__":
    sys.exit(main())
