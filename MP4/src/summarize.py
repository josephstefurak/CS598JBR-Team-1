"""Generate MP4/results/results.md, LaTeX table fragments, and the generated README sections.

Every number comes from committed artifacts: trajectories/<project>/run_summary.json (the final run) and
results/<project>.check.json (run_pipeline.py --check-only on the committed translation). The two must
agree on every reported field, or nothing is written (why.md standing priority 2). README sections between
`<!-- BEGIN GENERATED: name -->` and `<!-- END GENERATED: name -->` are rendered from configs/pipeline.yaml.

  summarize.py                 results for both projects
  summarize.py --readme        rewrite the generated README sections
  summarize.py --check-readme  exit 1 if the README sections are out of date
  summarize.py --report        fill the generated tables in docs/report_mp4_draft.md and .tex
  summarize.py --check-report  exit 1 if those tables are out of date

The default mode also writes the per-iteration trend tables, the usage-limit digest (`rate_limit_event` records)
and results/repair_mining.md, a timeline of every agent session's cargo feedback with stream line numbers.
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config  # noqa: E402
import mp4common as mc  # noqa: E402

README = os.path.join(mc.MP4_DIR, "README.md")
GROUPS = ("correctness", "style", "complexity", "perf")
SAFETY = ("unsafe_lines", "unsafe_calls", "unsafe_casts", "pointer_arithmetic")


class MismatchError(ValueError):
    pass


def _load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def compare(run_summary, check):
    """Fields where the final run's shipped iteration and the --check-only result disagree. The guard counts
    (integrity, lint attributes, hard-coding) are compared too: a crate that only check-only finds guard hits in
    must not be tabulated (review 2, C23)."""
    final = run_summary.get("final") or {}
    s = check["summary"]
    iv = final.get("integrity_violations")
    pairs = [("compiles", final.get("compiles"), s["compiles"]),
             ("integrity_violations", len(iv) if isinstance(iv, list) else iv, s.get("integrity_violations")),
             ("lint_attribute_hits", final.get("lint_attribute_hits"), s.get("lint_attribute_hits")),
             ("hardcode_hits", final.get("hardcode_hits"), s.get("hardcode_hits")),
             ("tests_passed", final.get("tests_passed"), s["tests_passed"]),
             ("tests_total", final.get("tests_total"), s["tests_total"])]
    for g in GROUPS:
        pairs.append(("clippy_agent.%s" % g, (final.get("clippy_agent") or {}).get(g), s["clippy_agent"].get(g)))
        pairs.append(("clippy_harness.%s" % g, (final.get("clippy_harness") or {}).get(g),
                      s["clippy_harness"].get(g)))
    for m in SAFETY:
        pairs.append(("safety.%s" % m, (final.get("safety") or {}).get(m), s["safety"][m]))
    return [{"field": f, "run_summary": a, "check_only": b} for f, a, b in pairs if a != b]


def build_rows(entries):
    """entries: [{label, run_summary, check}] -> table rows, after the equality check."""
    rows = []
    for e in entries:
        diffs = compare(e["run_summary"], e["check"])
        if diffs:
            raise MismatchError("%s: run_summary.json and check.json disagree: %s" % (e["label"], diffs))
        s = e["check"]["summary"]
        rows.append({
            "label": e["label"], "compiles": s["compiles"], "passed": s["tests_passed"], "total": s["tests_total"],
            "iterations": e["run_summary"]["iterations"], "stop_reason": e["run_summary"]["stop_reason"],
            "clippy": s["clippy_agent"], "harness": s["clippy_harness"], "safety": s["safety"],
            "safety_tool": s["safety_tool"], "known_failing": e["run_summary"].get("known_failing_tests") or [],
        })
    return rows


def _rate(p, t):
    return "%.1f%%" % (100.0 * p / t) if t else "n/a"


def md_overall(rows):
    out = ["| Project | Compiles | Tests Passed | Total Tests | Pass Rate | Agent Iterations | Stop reason |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %d | %d | %s | %d | %s |" % (
            r["label"], "Yes" if r["compiles"] else "No", r["passed"], r["total"], _rate(r["passed"], r["total"]),
            r["iterations"], r["stop_reason"]))
    kf = [(r["label"], n) for r in rows for n in r["known_failing"]]
    if kf:
        out += [""] + ["Known-defective benchmark test: `%s` (%s), see README." % (n, lbl) for lbl, n in kf]
    return "\n".join(out)


def _safety_label(tool):
    if tool == "course":
        return "course tool"
    return "interim proxy (`safety_check.py --tool proxy`); official tool PENDING"


def md_safety(rows):
    out = ["| Project | Unsafe Lines | Unsafe Calls | Unsafe Casts | Pointer Arithmetic | Measured by |",
           "|---|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s | %s |" % ((r["label"],) + tuple(r["safety"][m] for m in SAFETY) + (
            _safety_label(r["safety_tool"]),)))
    if any(r["safety_tool"] != "course" for r in rows):
        out += ["", "Additional metrics produced by the course unsafe-metrics tool: PENDING (tool not yet released)."]
    return "\n".join(out)


def md_idiom(rows):
    out = ["| Project | Correctness | Style | Complexity | Performance |", "|---|---|---|---|---|"]
    for r in rows:
        out.append("| %s | %s | %s | %s | %s |" % ((r["label"],) + tuple(r["clippy"][g] for g in GROUPS)))
    out += [""] + ["Warnings from the immutable benchmark test file are excluded above: %s has %s." % (
        r["label"], ", ".join("%s %d" % (g, r["harness"][g]) for g in GROUPS)) for r in rows]
    return "\n".join(out)


def render_markdown(rows, trends=None, usage=None):
    out = ["# MP4 results", "",
           "Generated by `MP4/src/summarize.py` from `trajectories/<project>/run_summary.json` and "
           "`results/<project>.check.json`. Do not edit by hand.", "",
           "## Overall results", "", md_overall(rows),
           "", "## Safety analysis", "", md_safety(rows),
           "", "## Idiomaticity analysis (clippy, agent-written code)", "", md_idiom(rows)]
    for t in trends or []:
        out += ["", "## Per-iteration trend: %s" % t["label"], "", md_trend(t)]
    if usage is not None:
        out += ["", "## API and usage limits", "", md_usage(usage)]
    return "\n".join(out) + "\n"


def _tex(s):
    return s.replace("_", "\\_").replace("%", "\\%")


def render_tex(rows):
    overall = ["%s & %s & %d & %d & %s & %d \\\\" % (
        _tex(r["label"]), "Yes" if r["compiles"] else "No", r["passed"], r["total"],
        _tex(_rate(r["passed"], r["total"])), r["iterations"]) for r in rows]
    safety = ["%s & %s \\\\" % (_tex(r["label"]), " & ".join(str(r["safety"][m]) for m in SAFETY)) for r in rows]
    idiom = ["%s & %s \\\\" % (_tex(r["label"]), " & ".join(str(r["clippy"][g]) for g in GROUPS)) for r in rows]
    return {"overall.tex": "\n".join(overall) + "\n", "safety.tex": "\n".join(safety) + "\n",
            "idiom.tex": "\n".join(idiom) + "\n"}


def write_results(entries, out_dir, trends=None, usage=None, mining=None):
    """trends/usage/mining (M10) are optional so a run without trajectories (the selftest fixture) still works."""
    rows = build_rows(entries)
    os.makedirs(out_dir, exist_ok=True)
    paths = [os.path.join(out_dir, "results.md")]
    with open(paths[0], "w", encoding="utf-8") as fh:
        fh.write(render_markdown(rows, trends, usage))
    files = render_tex(rows)
    for t in trends or []:
        files["trend_%s.tex" % t["project"]] = render_trend_tex(t)
    if mining is not None:
        files["repair_mining.md"] = mining
    for name, text in files.items():
        paths.append(os.path.join(out_dir, name))
        with open(paths[-1], "w", encoding="utf-8") as fh:
            fh.write(text)
    return paths


# ------------------------------------------------------------------------------------- trajectories (M10)
# Per-iteration trend, usage-limit digest and the repair-example miner all read the final run named in
# run_summary.json, so a superseded run never feeds the report.
def final_run_dir(project, run_summary):
    return os.path.join(mc.TRAJECTORIES_DIR, project, "run_%s" % run_summary["run_id"])


def iter_dirs(run_dir):
    return sorted(d for d in os.listdir(run_dir) if d.startswith("iter_") and os.path.isdir(os.path.join(run_dir, d)))


def stream_events(path):
    """[(1-based line number, event)] of a stream-json file; lines that are not JSON objects are skipped."""
    out = []
    if not os.path.exists(path):
        return out
    with open(path, encoding="utf-8", errors="replace") as fh:
        for n, line in enumerate(fh, 1):
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict):
                out.append((n, ev))
    return out


def diff_stats(path):
    """{file: [added, removed]} from a unified diff."""
    stats, cur = {}, None
    if not os.path.exists(path):
        return stats
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("+++ "):
                name = line[4:].strip()
                cur = name[2:] if name.startswith("b/") else name
                stats.setdefault(cur, [0, 0])
            elif line.startswith("--- "):
                continue
            elif cur is not None and line.startswith("+"):
                stats[cur][0] += 1
            elif cur is not None and line.startswith("-"):
                stats[cur][1] += 1
    return stats


def iteration_trend(project, label, run_summary):
    """One row per agent attempt of the final run: controller measurements plus the agent session's own numbers."""
    run_dir = final_run_dir(project, run_summary)
    rows = []
    for d in iter_dirs(run_dir):
        base = os.path.join(run_dir, d)
        summ_path = os.path.join(base, "iteration_summary.json")
        if not os.path.exists(summ_path):
            continue
        s = _load(summ_path)
        events = stream_events(os.path.join(base, "agent.stream.jsonl"))
        result = next((ev for _, ev in reversed(events) if ev.get("type") == "result"), {})
        iv = s.get("integrity_violations")
        added = removed = 0
        for a, r in diff_stats(os.path.join(base, "changes.diff")).values():
            added, removed = added + a, removed + r
        rows.append({
            "dir": d, "iteration": s.get("iteration"), "attempt": s.get("attempt"), "compiles": s.get("compiles"),
            "build_errors": s.get("build_errors"), "passed": s.get("tests_passed"), "total": s.get("tests_total"),
            "clippy": s.get("clippy_agent") or {}, "harness_total": sum((s.get("clippy_harness") or {}).values()),
            "safety_total": s.get("safety_total"), "interface_missing": s.get("interface_missing"),
            "interface_changed": s.get("interface_changed"),
            "integrity": len(iv) if isinstance(iv, list) else iv, "success": s.get("success"),
            "turns": result.get("num_turns"), "output_tokens": (result.get("usage") or {}).get("output_tokens"),
            "minutes": round(result["duration_ms"] / 60000.0, 1) if result.get("duration_ms") else None,
            "added": added, "removed": removed,
        })
    return {"project": project, "label": label, "run_id": run_summary["run_id"], "rows": rows}


def _cell(v):
    return "n/a" if v is None else str(v)


def md_trend(trend):
    out = ["Run `run_%s`. Clippy, safety and interface are the controller's measurements after the iteration "
           "(safety: interim proxy, official tool PENDING). Turns, output tokens and minutes are from the agent "
           "session's own `result` event; lines changed are from `changes.diff`." % trend["run_id"], "",
           "| Iteration | Compiles | Tests | Clippy (agent) C/S/X/P | Clippy (harness) | Safety (proxy) | "
           "Interface missing/changed | Integrity | Turns | Output tokens | Minutes | Lines +/- | Success |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in trend["rows"]:
        out.append("| %s | %s | %s/%s | %s | %s | %s | %s/%s | %s | %s | %s | %s | +%d/-%d | %s |" % (
            r["dir"], "Yes" if r["compiles"] else "No", _cell(r["passed"]), _cell(r["total"]),
            "/".join(_cell(r["clippy"].get(g)) for g in GROUPS), r["harness_total"], _cell(r["safety_total"]),
            _cell(r["interface_missing"]), _cell(r["interface_changed"]), _cell(r["integrity"]), _cell(r["turns"]),
            _cell(r["output_tokens"]), _cell(r["minutes"]), r["added"], r["removed"],
            "Yes" if r["success"] else "No"))
    return "\n".join(out)


def render_trend_tex(trend):
    return "\n".join("%s & %s & %s/%s & %s & %s & %s & %s & %s \\\\" % (
        _tex(r["dir"]), "Yes" if r["compiles"] else "No", _cell(r["passed"]), _cell(r["total"]),
        "/".join(_cell(r["clippy"].get(g)) for g in GROUPS), _cell(r["safety_total"]), _cell(r["turns"]),
        _cell(r["minutes"]), "+%d/-%d" % (r["added"], r["removed"])) for r in trend["rows"]) + "\n"


def usage_digest(entries):
    """rate_limit_event records from every agent stream of the final runs, plus the controller's pause records."""
    out = []
    for e in entries:
        run_dir = final_run_dir(e["project"], e["run_summary"])
        events = []
        for d in iter_dirs(run_dir):
            for _, ev in stream_events(os.path.join(run_dir, d, "agent.stream.jsonl")):
                if ev.get("type") == "rate_limit_event":
                    info = ev.get("rate_limit_info") or {}
                    events.append({"dir": d, "status": info.get("status"), "type": info.get("rateLimitType")})
        out.append({"label": e["label"], "project": e["project"], "run_id": e["run_summary"]["run_id"],
                    "events": events, "pauses": len(e["run_summary"].get("usage_limit_pauses") or [])})
    return out


def md_usage(usage):
    out = ["| Project | `rate_limit_event` records | Statuses | Limit windows | Rejected | Usage-limit pauses |",
           "|---|---|---|---|---|---|"]
    for u in usage:
        statuses = sorted({_cell(e["status"]) for e in u["events"]})
        kinds = sorted({_cell(e["type"]) for e in u["events"]})
        out.append("| %s | %d | %s | %s | %d | %d |" % (
            u["label"], len(u["events"]), ", ".join(statuses) or "-", ", ".join(kinds) or "-",
            sum(1 for e in u["events"] if e["status"] not in ("allowed", "allowed_warning")), u["pauses"]))
    out += ["", "Source: `grep -c '\"type\":\"rate_limit_event\"' trajectories/project_*/run_*/iter_*/"
            "agent.stream.jsonl` and `run_summary.json` `usage_limit_pauses`."]
    return "\n".join(out)


# ------------------------------------------------------------------------------------- repair-example miner (M10)
DIAG_HEAD = re.compile(r"^(warning|error)(?:\[(E\d{4})\])?: (.*)$")
DIAG_SPAN = re.compile(r"^\s*--> (\S+?):(\d+):\d+")
DIAG_LINT = re.compile(r"index\.html#([a-z0-9_]+)|#\[warn\(([a-z0-9_:]+)\)\]|`-W clippy::([a-z0-9-]+)`")
TEST_RESULT = re.compile(r"test result: (ok|FAILED)\. (\d+) passed; (\d+) failed")


def parse_cargo_output(text):
    """(diagnostics with a source span, [test result tuples]). Spans under src/bin/ are the benchmark harness."""
    diags, cur = [], None
    for line in text.splitlines():
        m = DIAG_HEAD.match(line)
        if m:
            cur = {"level": m.group(1), "code": m.group(2), "message": m.group(3), "path": None, "line": None,
                   "lint": None}
            diags.append(cur)
            continue
        if cur is None:
            continue
        s = DIAG_SPAN.match(line)
        if s and cur["path"] is None:
            cur["path"], cur["line"] = s.group(1), int(s.group(2))
            continue
        lint = DIAG_LINT.search(line)
        if lint and cur["lint"] is None:
            cur["lint"] = next(g for g in lint.groups() if g).replace("clippy::", "").replace("-", "_")
    seen, unique = {}, []
    for d in diags:   # cargo repeats a diagnostic per target, sometimes without its notes: keep one, with the lint
        key = (d["level"], d["code"], d["message"], d["path"], d["line"])
        if not d["path"]:
            continue
        if key in seen:
            seen[key]["lint"] = seen[key]["lint"] or d["lint"]
        else:
            seen[key] = d
            unique.append(d)
    return unique, TEST_RESULT.findall(text)


def _is_harness(path):
    return any(path.startswith(p) for p in mc.HARNESS_PREFIXES)


def _cargo_kind(command):
    m = re.search(r"\bcargo\b(?:\s+\+\S+)?\s+(build|check|test|clippy)\b", command or "")
    return m.group(1) if m else None


def _content_text(content):
    if isinstance(content, list):
        return "\n".join(c.get("text", "") for c in content if isinstance(c, dict))
    return content if isinstance(content, str) else ""


def _crate_rel(path):
    m = re.search(r"/translations/project_\d+/(.+)$", path or "")
    return m.group(1) if m else os.path.basename(path or "")


def _short(text, n=110):
    text = " ".join((text or "").split()).replace("|", "\\|")
    return text if len(text) <= n else text[:n - 3] + "..."


def mine_stream(path):
    """Chronological feedback timeline of one agent session: file writes, the agent's own words, cargo calls with
    their diagnostics split library vs harness, and permission denials. Line numbers are the stream's lines."""
    uses, timeline = {}, []
    for ln, ev in stream_events(path):
        if ev.get("type") == "system" and ev.get("subtype") == "permission_denied":
            timeline.append({"line": ln, "kind": "denied", "detail": "%s: %s" % (
                ev.get("tool_name") or "?", _short(ev.get("message"), 100))})
            continue
        msg = ev.get("message")
        content = msg.get("content") if isinstance(msg, dict) else None
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict):
                continue
            t = item.get("type")
            if ev.get("type") == "assistant" and t == "tool_use":
                inp = item.get("input") or {}
                uses[item.get("id")] = (ln, item.get("name"), inp)
                if item.get("name") in ("Write", "Edit"):
                    timeline.append({"line": ln, "kind": item["name"], "file": _crate_rel(inp.get("file_path"))})
            elif ev.get("type") == "assistant" and t == "text" and (item.get("text") or "").strip():
                timeline.append({"line": ln, "kind": "text", "detail": _short(item["text"])})
            elif ev.get("type") == "user" and t == "tool_result":
                use = uses.get(item.get("tool_use_id"))
                kind = _cargo_kind(use[2].get("command")) if use and use[1] == "Bash" else None
                if not kind:
                    continue
                diags, tests = parse_cargo_output(_content_text(item.get("content")))
                timeline.append({"line": ln, "kind": "cargo " + kind, "call_line": use[0],
                                 "failed": bool(item.get("is_error")), "diags": diags, "tests": tests})
    return timeline


def _lib_key(d):
    return d["code"] or d["lint"] or d["message"]


def _cargo_detail(ev):
    lib = [d for d in ev["diags"] if not _is_harness(d["path"])]
    parts = []
    for level in ("error", "warning"):
        group = [d for d in lib if d["level"] == level]
        if group:
            names = {}
            for d in group:
                names.setdefault(_lib_key(d), []).append("%s:%d" % (d["path"], d["line"]))
            parts.append("library %ss: %s" % (level, "; ".join(
                "%s x%d (%s)" % (k, len(v), ", ".join(v[:3]) + (", ..." if len(v) > 3 else ""))
                for k, v in sorted(names.items()))))
    first_err = next((d for d in lib if d["level"] == "error"), None)
    if first_err:
        parts.append("first: \"%s\"" % _short(first_err["message"], 90))
    harness = sum(1 for d in ev["diags"] if _is_harness(d["path"]))
    if harness:
        parts.append("harness diagnostics %d" % harness)
    for status, p, f in ev["tests"]:
        parts.append("test result: %s. %s passed; %s failed" % (status, p, f))
    if not parts:
        parts.append("no diagnostics in library code")
    return "; ".join(parts)


def lint_ledger(timeline):
    """{library lint or error code: [count at the first clippy/build call that saw any, count at the last call]}."""
    calls = [ev for ev in timeline if ev["kind"] in ("cargo clippy", "cargo build", "cargo check", "cargo test")]
    keys = sorted({_lib_key(d) for ev in calls for d in ev["diags"] if not _is_harness(d["path"])})
    out = {}
    for k in keys:
        counts = [sum(1 for d in ev["diags"] if not _is_harness(d["path"]) and _lib_key(d) == k) for ev in calls]
        first = next(i for i, c in enumerate(counts) if c)
        out[k] = {"first": counts[first], "first_line": calls[first]["line"], "last": counts[-1],
                  "last_line": calls[-1]["line"]}
    return out


def render_mining(entries):
    out = ["# Repair-example mining", "",
           "Generated by `MP4/src/summarize.py` from the final runs' `agent.stream.jsonl` files. Do not edit by hand. "
           "`Line` is the 1-based line of the named stream file (`sed -n '<Line>p' <file>`); `call` is the line of "
           "the command that produced a tool result. `harness` diagnostics are in the immutable benchmark files "
           "(`src/bin/`). The agent's thinking is redacted in the stream, so its reasons appear only where it wrote "
           "text."]
    for e in entries:
        run_dir = final_run_dir(e["project"], e["run_summary"])
        out += ["", "## %s (%s), run `run_%s`" % (e["label"], e["project"], e["run_summary"]["run_id"])]
        for d in iter_dirs(run_dir):
            rel = "trajectories/%s/run_%s/%s" % (e["project"], e["run_summary"]["run_id"], d)
            timeline = mine_stream(os.path.join(run_dir, d, "agent.stream.jsonl"))
            stats = diff_stats(os.path.join(run_dir, d, "changes.diff"))
            out += ["", "### %s: `%s/agent.stream.jsonl`" % (d, rel), "",
                    "`%s/changes.diff`: %s" % (rel, ", ".join("`%s` +%d/-%d" % (f, a, r) for f, (a, r) in sorted(
                        stats.items())) or "no changes"), ""]
            diag_path = os.path.join(run_dir, d, "diagnostics.md")
            if os.path.exists(diag_path):
                heads = [ln[4:].strip() for ln in mc.read_text(diag_path).splitlines() if ln.startswith("### ")]
                out += ["Controller feedback after this iteration (`%s/diagnostics.md`): %s" % (
                    rel, "; ".join(heads)), ""]
            out += ["| Line | Event | Detail |", "|---|---|---|"]
            for ev in timeline:
                if ev["kind"] in ("Write", "Edit"):
                    detail = "`%s`" % ev["file"]
                elif ev["kind"].startswith("cargo"):
                    detail = "call %d%s; %s" % (ev["call_line"], ", exit non-zero" if ev["failed"] else "",
                                                _cargo_detail(ev))
                else:
                    detail = ev["detail"]
                out.append("| %d | %s | %s |" % (ev["line"], ev["kind"], detail))
            ledger = lint_ledger(timeline)
            out += ["", "Library errors and lints across this session's cargo calls (first call that saw it -> last "
                        "call): " + ("; ".join("%s %d (line %d) -> %d (line %d)" % (
                            k, v["first"], v["first_line"], v["last"], v["last_line"]) for k, v in ledger.items())
                                     or "none")]
    return "\n".join(out) + "\n"


# ------------------------------------------------------------------------------------- report draft blocks (M10)
REPORT_MD = os.path.join(mc.MP4_DIR, "docs", "report_mp4_draft.md")
REPORT_TEX = os.path.join(mc.MP4_DIR, "docs", "report_mp4_draft.tex")


def report_blocks(rows, trends, usage):
    """{name: (markdown body, LaTeX body)}: the same generated text that results.md and the .tex fragments carry."""
    tex = render_tex(rows)
    blocks = {"overall": (md_overall(rows), tex["overall.tex"].rstrip("\n")),
              "safety": (md_safety(rows), tex["safety.tex"].rstrip("\n")),
              "idiom": (md_idiom(rows), tex["idiom.tex"].rstrip("\n")),
              "usage": (md_usage(usage), None)}
    for t in trends:
        blocks["trend_%s" % t["project"]] = (md_trend(t), render_trend_tex(t).rstrip("\n"))
    return blocks


def render_tex_blocks(text, sections):
    for name, body in sections.items():
        pat = re.compile(r"(% BEGIN GENERATED: {0}\n)(?:.*?\n)?(% END GENERATED: {0})".format(re.escape(name)), re.S)
        if not pat.search(text):
            raise ValueError("report .tex has no generated block %r" % name)
        text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text


def update_report(blocks, check):
    """Fill (or, with check, compare) the generated blocks of both report drafts. Returns the out-of-date paths."""
    stale = []
    for path, idx, render in ((REPORT_MD, 0, render_readme), (REPORT_TEX, 1, render_tex_blocks)):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        new = render(text, {k: v[idx] for k, v in blocks.items() if v[idx] is not None})
        if new != text:
            stale.append(mc.rel(path, mc.REPO_DIR))
            if not check:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(new)
    return stale


# ------------------------------------------------------------------------------------- README sections
def generated_sections(pipeline):
    import run_pipeline   # only for MAX_LIMIT_ATTEMPTS; keeps this module's imports light
    a, lp, rl = pipeline["agent"], pipeline["loop"], pipeline["rate_limit"]
    if rl["mode"] == "wait":
        pause = ("waits until the limit resets (+%d s, at most %d h) and redoes the iteration "
                 "(`iter_KK_attemptN`); after %d refused attempts of one iteration it exits with code 75 for a "
                 "`--resume-run`" % (rl["resume_margin_seconds"], rl["max_wait_hours"],
                                     run_pipeline.MAX_LIMIT_ATTEMPTS))
    else:
        pause = ("exits with code 75 and prints the `--resume-run` command, which redoes the iteration "
                 "(`iter_KK_attemptN`)")
    stopping = "\n".join([
        "The loop (`MP4/src/run_pipeline.py`) checks after every iteration, in this order:", "",
        "1. **SUCCESS**: the crate builds with `%s`; every benchmark test passes except the documented "
        "known-defective ones, and each of those fails on its documented assertion (a benchmark test that "
        "hangs, crashes or reports no result counts as failed; tests the agent adds are reported separately and "
        "must pass too); clippy runs without errors and agent-attributable clippy warnings are 0 in all four "
        "rubric groups; the safety metrics are all 0, `#![forbid(unsafe_code)]` is in place and there is no FFI; "
        "every interface item is present and unchanged; no integrity violation; no test literal copied into "
        "library code; no lint-level attribute (`allow`, `expect`, `warn`, `deny`, `forbid`, or one inside "
        "`cfg_attr`) in library code except the project's permitted `#[allow]`. SUCCESS ends the run from "
        "iteration %d on; a clean crate before that gets a review iteration." % (
            pipeline["toolchain"]["name"], lp["min_iterations"]),
        "2. **ABORT**: integrity violations (tests, interfaces, `Cargo.toml`/`Cargo.lock` or `src/lib.rs` "
        "changed, files created outside `src/`, symlinks) in two consecutive iterations.",
        "3. **NO_PROGRESS**: the score (tests passed, then fewer build errors, clippy warnings, unsafe findings, "
        "missing interface items) has not strictly improved for %d consecutive iterations." % lp[
            "no_progress_rounds"],
        "4. **MAX_ITERATIONS**: %d iterations." % lp["max_iterations"], "",
        "At NO_PROGRESS and MAX_ITERATIONS the best-scoring iteration (a successful one first, then the score "
        "above; the later one on a tie) is restored into `translations/` and named in "
        "`run_summary.json` `final_iteration_dir`, not the last.", "",
        "Each iteration is one fresh agent session capped at %d turns and a %d-minute wall clock. The run also "
        "stops if the agent's startup line is missing, shows any capability beyond the configured tools, or "
        "shows an API key instead of the subscription login (ABORT_ISOLATION). A usage-limit rejection is not "
        "a stop: the run %s. An API outage (overloaded, connection error) is handled the same way with a "
        "%g-minute wait. A lost CLI login also pauses: the run exits with code 75 and continues with "
        "`--resume-run` after `claude auth login`." % (
            a["max_turns"], a["wall_clock_minutes"], pause, rl["fallback_minutes"]),
    ])
    inference = "\n".join([
        "| Setting | Value | Where |", "|---|---|---|",
        "| Model | `%s` (alias resolved by Claude Code) | `configs/pipeline.yaml` `agent.model` |" % a["model"],
        "| Effort | `%s` | `agent.effort` |" % a["effort"],
        "| Max turns per iteration | %d | `agent.max_turns` |" % a["max_turns"],
        "| Wall clock per iteration | %d min | `agent.wall_clock_minutes` |" % a["wall_clock_minutes"],
        "| Budget tripwire | %s USD (subscription auth; tripwire only) | `agent.max_budget_usd` |" % a[
            "max_budget_usd"],
        "| Permission mode | `%s` | `agent.permission_mode` |" % a["permission_mode"],
        "| Max iterations | %d | `loop.max_iterations` |" % lp["max_iterations"],
        "| Temperature, top-p, max output tokens | not configurable through Claude Code; provider defaults | - |",
    ])
    return {"stopping-condition": stopping, "inference-settings": inference}


def render_readme(text, sections):
    for name, body in sections.items():
        pat = re.compile(r"(<!-- BEGIN GENERATED: %s -->\n)(?:.*?\n)?(<!-- END GENERATED: %s -->)" % (
            re.escape(name), re.escape(name)), re.S)
        if not pat.search(text):
            raise ValueError("README has no generated block %r" % name)
        text = pat.sub(lambda m: m.group(1) + body + "\n" + m.group(2), text)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="Generate results tables and README sections from artifacts.")
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument("--readme", action="store_true")
    mode.add_argument("--check-readme", action="store_true")
    mode.add_argument("--report", action="store_true", help="fill the generated blocks of docs/report_mp4_draft.*")
    mode.add_argument("--check-report", action="store_true", help="exit 1 if those blocks are out of date")
    a = ap.parse_args(argv)
    if a.readme or a.check_readme:
        pipeline = config.validate_pipeline(config._load_yaml(mc.PIPELINE_YAML))
        with open(README, encoding="utf-8") as fh:
            text = fh.read()
        new = render_readme(text, generated_sections(pipeline))
        if a.check_readme:
            print("README generated sections: %s" % ("up to date" if new == text else "OUT OF DATE"))
            return 0 if new == text else 1
        with open(README, "w", encoding="utf-8") as fh:
            fh.write(new)
        print("README generated sections written")
        return 0
    entries = []
    for project in mc.PROJECTS:
        summ = os.path.join(mc.TRAJECTORIES_DIR, project, "run_summary.json")
        chk = os.path.join(mc.RESULTS_DIR, "%s.check.json" % project)
        missing = [mc.rel(p, mc.REPO_DIR) for p in (summ, chk) if not os.path.exists(p)]
        if missing:
            print("PENDING %s: missing %s" % (project, ", ".join(missing)), file=sys.stderr)
            return 2
        entries.append({"label": config.load(project)["project_cfg"]["label"], "project": project,
                        "run_summary": _load(summ), "check": _load(chk)})
    trends = [iteration_trend(e["project"], e["label"], e["run_summary"]) for e in entries]
    usage = usage_digest(entries)
    try:
        if a.report or a.check_report:
            stale = update_report(report_blocks(build_rows(entries), trends, usage), a.check_report)
            if a.check_report:
                print("report generated blocks: %s" % ("OUT OF DATE: " + ", ".join(stale) if stale else "up to date"))
                return 1 if stale else 0
            print("report generated blocks written%s" % (": " + ", ".join(stale) if stale else " (no change)"))
            return 0
        for p in write_results(entries, mc.RESULTS_DIR, trends, usage, render_mining(entries)):
            print("wrote %s" % mc.rel(p, mc.REPO_DIR))
    except MismatchError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print("results equal --check-only for %d project(s)" % len(entries))
    return 0


if __name__ == "__main__":
    sys.exit(main())
