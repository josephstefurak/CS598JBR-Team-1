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

The agent loop (--yes, --resume-run, --run-id) is wired in M4; until then
those flags exit with status 2.
"""
import argparse
import datetime
import json
import os
import shlex
import shutil
import sys
import tempfile

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

NOT_YET = {"yes": "M4", "resume_run": "M4", "run_id": "M4"}
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
    ap.add_argument("--yes", action="store_true", help="skip the confirmation before spending quota (M4)")
    ap.add_argument("--dry-run", action="store_true", help="print the claude argv and iteration-1 prompt (M3)")
    ap.add_argument("--smoke", action="store_true", help="isolation smoke call, <= 2 turns (M3)")
    ap.add_argument("--resume-run", metavar="RUN_ID", help="re-enter a run at its recorded step (M4)")
    ap.add_argument("--run-id", metavar="ID", help="explicit run id (M4)")
    ap.add_argument("--claude-bin", help="override agent.claude_bin (tests)")
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


def main(argv=None):
    args = build_parser().parse_args(argv)
    for flag, phase in NOT_YET.items():
        if getattr(args, flag):
            print("--%s is not implemented yet (arrives in %s)" % (flag.replace("_", "-"), phase), file=sys.stderr)
            return 2
    if args.dry_run:
        return dry_run(args.project, args.claude_bin)
    if args.smoke:
        return smoke(args.project, args.claude_bin)
    if not args.check_only:
        print("the agent loop arrives in M4; available now: --check-only, --dry-run, --smoke", file=sys.stderr)
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
