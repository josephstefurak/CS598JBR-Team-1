"""MP4 C-to-Rust agentic translation pipeline — entry point.

Usage:
  python3 -I MP4/src/run_pipeline.py --project project_N --check-only [--crate-dir DIR] [--out FILE]

--check-only reruns every measurement without a model, on a temp copy of the
crate (default MP4/translations/project_N), and writes
MP4/results/project_N.check.json plus its logs next to it. It never modifies
the crate it measures.

The agent loop (--yes, --dry-run, --smoke, --resume-run, --run-id) is wired
in M3/M4; until then those flags exit with status 2.
"""
import argparse
import datetime
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import check_interface  # noqa: E402
import checks  # noqa: E402
import integrity  # noqa: E402
import mp4common as mc  # noqa: E402
import safety_check  # noqa: E402

NOT_YET = {"yes": "M4", "dry_run": "M3", "smoke": "M3", "resume_run": "M4", "run_id": "M4"}


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
    ap.add_argument("--yes", action="store_true", help="skip the confirmation before spending quota (M4)")
    ap.add_argument("--dry-run", action="store_true", help="print the claude argv and iteration-1 prompt (M3)")
    ap.add_argument("--smoke", action="store_true", help="isolation smoke call, <= 2 turns (M3)")
    ap.add_argument("--resume-run", metavar="RUN_ID", help="re-enter a run at its recorded step (M4)")
    ap.add_argument("--run-id", metavar="ID", help="explicit run id (M4)")
    return ap


def _toolchain_version():
    code, out = mc.cargo(["--version"], mc.MP4_DIR, timeout=60)
    return out.strip() if code == 0 else None


def _scrub_paths(text, work):
    text = text.replace(work, "<crate>")
    return text.replace(os.path.expanduser("~"), "~")


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
        res.update(checks.run_all(work, log_dir))
        res["safety"] = safety_check.proxy(work, raw_path=os.path.join(log_dir, "safety_proxy.json"), source=source)
        res["interface"] = check_interface.compare(os.path.join(source, "src", "interfaces"), work)
        res["integrity"] = {"violations": integrity.verify(work, source, restore=False)}
        res["hardcode_hits"] = integrity.hardcode_scan(work)
        res["summary"] = summarize(res)
        text = _scrub_paths(json.dumps(res, indent=2), work)
        for name in os.listdir(log_dir):
            p = os.path.join(log_dir, name)
            with open(p, encoding="utf-8", errors="replace") as fh:
                body = fh.read()
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(_scrub_paths(body, work).replace(log_dir, mc.rel(log_dir, mc.REPO_DIR)))
        text = text.replace(log_dir, mc.rel(log_dir, mc.REPO_DIR))
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


def main(argv=None):
    args = build_parser().parse_args(argv)
    for flag, phase in NOT_YET.items():
        if getattr(args, flag):
            print("--%s is not implemented yet (arrives in %s)" % (flag.replace("_", "-"), phase), file=sys.stderr)
            return 2
    if not args.check_only:
        print("the agent loop arrives in M3/M4; only --check-only is available", file=sys.stderr)
        return 2
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
