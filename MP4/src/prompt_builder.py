"""Render the iteration prompts from configs/prompts/*.md.

Templates use {{name}} placeholders. Project context comes from
configs/projects/<project>.yaml, feedback from the previous iteration's check
results (a capped digest), and history from earlier iteration summaries. An
unknown or unfilled placeholder is an error, so a template typo cannot reach
the agent silently.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")


def render(template, values):
    names = set(_PLACEHOLDER_RE.findall(template))
    missing = sorted(names - set(values))
    if missing:
        raise KeyError("template placeholders without values: %s" % ", ".join(missing))
    return _PLACEHOLDER_RE.sub(lambda m: str(values[m.group(1)]), template)


def project_notes(proj):
    out = ["### Context"] + ["- %s" % n for n in proj["notes"]]
    if proj["c_behaviour"]:
        out += ["", "### C behaviour rulings (owner ruling D-FAITHFUL)"] + ["- %s" % n for n in proj["c_behaviour"]]
    out += ["", "### Allow-attributes"]
    if proj["allow_attributes"]:
        out += ["- Only `#[allow(%s)]` on `%s` (%s). No other allow-attribute anywhere." % (
            a["lint"], a["item"], a["reason"]) for a in proj["allow_attributes"]]
    else:
        out += ["- None permitted."]
    if proj["known_failing_tests"]:
        out += ["", "### Known-defective tests"]
        for k in proj["known_failing_tests"]:
            out += ["- `%s`: %s Implement the C behaviour; this test is expected to fail and is reported "
                    "separately. Do not modify the test." % (k["name"], " ".join(k["reason"].split()))]
    return "\n".join(out)


def _clip(text, n):
    text = text or ""
    return text if len(text) <= n else text[:n] + "\n[... truncated]"


def digest(check, caps):
    """Markdown feedback from one check result (run_pipeline --check-only shape), within the configured caps."""
    out = []
    b = check.get("build") or {}
    out.append("### Build: %s" % ("ok" if b.get("ok") else "FAILED"))
    if not b.get("ok"):
        errs = b.get("errors") or []
        for e in errs[:caps["max_build_errors"]]:
            out.append("- %s%s" % ("[%s] " % e["code"] if e.get("code") else "", e["message"]))
        if len(errs) > caps["max_build_errors"]:
            out.append("- ... %d more" % (len(errs) - caps["max_build_errors"]))
        if b.get("first_error"):
            out += ["", "```", _clip(b["first_error"], caps["max_panic_chars"]), "```"]
    t = check.get("test") or {}
    known = set(check.get("known_failing_tests") or [])
    out.append("")
    out.append("### Tests: %d of %d passed" % (t.get("passed", 0), t.get("total", 0)))
    failing = [n for n in t.get("failed_names", [])]
    for name in failing[:caps["max_failing_tests"]]:
        panic = (t.get("tests", {}).get(name) or {}).get("panic") or ""
        label = " (known-defective test, expected to fail)" if name in known else ""
        out += ["- `%s` FAILED%s" % (name, label), "", "```", _clip(panic, caps["max_panic_chars"]), "```"]
    c = check.get("clippy")
    out.append("")
    if c:
        groups = c.get("groups", {})
        out.append("### Clippy (your code only; warnings from the test files are excluded): %s" % ", ".join(
            "%s %d" % (g, groups[g]["agent"]) for g in groups))
        sites = [s for g in groups for s in groups[g]["sites"] if s["origin"] == "agent"]
        for s in sites[:caps["max_clippy_sites"]]:
            out.append("- `%s:%d` %s: %s" % (s["file"], s["line"], s["lint"], s["message"]))
        rustc = [s for s in (c.get("rustc") or {}).get("sites", []) if s["origin"] == "agent"]
        for s in rustc[:caps["max_clippy_sites"]]:
            out.append("- `%s:%d` %s (rustc): %s" % (s["file"], s["line"], s["lint"], s["message"]))
    else:
        out.append("### Clippy: not run (the build failed)")
    s = check.get("safety") or {}
    out.append("")
    out.append("### Safety (%s): unsafe lines %s, unsafe calls %s, unsafe casts %s, pointer arithmetic %s" % (
        s.get("tool"), s.get("unsafe_lines"), s.get("unsafe_calls"), s.get("unsafe_casts"),
        s.get("pointer_arithmetic")))
    for f in (s.get("findings") or [])[:20]:
        if f.get("kind") == "deny_unsafe_build_failed":
            out.append("- building with `-D unsafe_code` failed")
        else:
            out.append("- %s %s" % (f.get("kind"), f.get("file", "")))
    i = check.get("interface") or {}
    out.append("")
    out.append("### Interface: %s missing, %s changed" % (i.get("missing"), i.get("changed")))
    for mod, m in (i.get("modules") or {}).items():
        for item in m.get("missing", []):
            out.append("- missing `%s::%s`" % (mod, item))
        for ch in m.get("changed", []):
            out.append("- changed `%s::%s`: expected `%s`, found `%s`"
                       % (mod, ch["item"], ch["expected"], ch["actual"]))
    v = (check.get("integrity") or {}).get("violations") or []
    if v:
        out += ["", "### Integrity violations (restored by the wrapper; this iteration cannot succeed)"]
        out += ["- %s %s" % (x["kind"], x["path"]) for x in v]
    h = check.get("hardcode_hits") or []
    if h:
        out += ["", "### Hard-coding: test literals found in library code"]
        out += ["- `%s:%d` contains a %d-character literal from `%s:%d`" % (
            x["lib_file"], x["lib_line"], x["length"], x["test_file"], x["test_line"]) for x in h]
    return _clip("\n".join(out), caps["max_chars"])


def history_table(history):
    if not history:
        return "No earlier iterations."
    rows = ["| Iteration | Agent outcome | Builds | Tests passed | Clippy (yours) | Unsafe | Interface missing |",
            "|---|---|---|---|---|---|---|"]
    for h in history:
        rows.append("| %s | %s | %s | %s/%s | %s | %s | %s |" % (
            h.get("iteration"), h.get("outcome"), "yes" if h.get("compiles") else "no", h.get("tests_passed"),
            h.get("tests_total"), h.get("clippy_agent_total"), h.get("safety_total"), h.get("interface_missing")))
    return "\n".join(rows)


def _values(cfg, iteration):
    p, proj = cfg["pipeline"], cfg["project_cfg"]
    with open(cfg["files"]["cheatsheet"], encoding="utf-8") as fh:
        cheatsheet = fh.read().strip()
    return {
        "project_label": proj["label"],
        "iteration": iteration,
        "max_iterations": p["loop"]["max_iterations"],
        "crate": proj["crate"],
        "c_dir": cfg["c_dir"],
        "modules": ", ".join("`%s`" % m for m in proj["modules"]),
        "expected_pub_items": proj["expected_pub_items"],
        "c_files": ", ".join("`%s`" % f for f in proj["c_files"]),
        "test_file": proj["test_file"],
        "toolchain": p["toolchain"]["name"],
        "project_notes": project_notes(proj),
        "cheatsheet": cheatsheet,
    }


def build_initial(cfg, iteration=1):
    with open(cfg["files"]["initial"], encoding="utf-8") as fh:
        return render(fh.read(), _values(cfg, iteration))


def build_repair(cfg, iteration, check, history):
    vals = _values(cfg, iteration)
    check = dict(check)
    check["known_failing_tests"] = [k["name"] for k in cfg["project_cfg"]["known_failing_tests"]]
    vals["diagnostics"] = digest(check, cfg["pipeline"]["digest"])
    vals["history"] = history_table(history)
    with open(cfg["files"]["repair"], encoding="utf-8") as fh:
        return render(fh.read(), vals)


GUARDRAIL_PATTERNS = [
    re.compile(r"do not (modify|alter|change).*test", re.I),
    re.compile(r"FFI"),
    re.compile(r"unsafe", re.I),
    re.compile(r"hard.?cod", re.I),
]
FN_BODY_RE = re.compile(r"\bfn\s+\w+\s*(<[^>]*>)?\s*\([^)]*\)[^{;]*\{[^}]*[;\w][^}]*\}", re.S)
PROJECT_IDENT_RE = re.compile(r"\b(satc|psbt)_\w+")


def template_texts(cfg):
    """The fixed prompt texts (no project context): templates, system prompt, cheatsheet."""
    out = {}
    for key in ("initial", "repair", "system_prompt", "cheatsheet"):
        with open(cfg["files"][key], encoding="utf-8") as fh:
            out[key] = fh.read()
    return out


if __name__ == "__main__":
    import argparse
    import config
    ap = argparse.ArgumentParser(description="Print the iteration-1 prompt for a project.")
    ap.add_argument("--project", required=True, choices=mc.PROJECTS)
    print(build_initial(config.load(ap.parse_args().project)))
