"""Integrity guards: immutable files, workspace drift, provenance, hard-coding and FFI scans.

why.md Z1, Z2, Z3, Z5, Z6, Z7, D5. Immutable = every file of the CRUST-bench
skeleton (tests, interfaces, Cargo.toml, Cargo.lock, ...) except src/lib.rs,
which must equal FORBID_LINE + the skeleton's lib.rs (D-FORBID). Expected
hashes always come from the skeleton under subjects/, never from a file inside
the workspace the agent can edit.

CLI (exit 0 = clean, 1 = violations/mismatch, 2 = usage or missing input):
  integrity.py --write-manifest --project project_N [--crate-dir DIR]
  integrity.py --verify --project project_N [--crate-dir DIR] [--no-restore]
  integrity.py --check-workspace SNAPSHOT_DIR --project project_N [--crate-dir DIR]
  integrity.py --provenance project_N
  integrity.py --scan --project project_N [--crate-dir DIR]     (hard-coding + FFI)
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402
import rustlex  # noqa: E402

MANIFEST_REL = ".integrity/manifest.sha256"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_subjects(source):
    """Check a subjects skeleton against its parent CHECKSUMS.sha256 (if present). Returns mismatches."""
    sums = os.path.join(os.path.dirname(source), "CHECKSUMS.sha256")
    if not os.path.exists(sums):
        return []
    base = os.path.dirname(source)
    prefix = os.path.basename(source) + "/"
    bad = []
    for line in mc.read_text(sums).splitlines():
        if not line.strip():
            continue
        digest, path = line.split(None, 1)
        path = path.strip()
        if not path.startswith(prefix):
            continue
        full = os.path.join(base, path)
        if not os.path.exists(full) or sha256(full) != digest:
            bad.append(path)
    return bad


def immutable_files(source):
    """Relative paths of every immutable file in the skeleton (all but src/lib.rs)."""
    return [mc.rel(p, source) for p in mc.walk_files(source) if mc.rel(p, source) != "src/lib.rs"]


def expected_lib_rs(source):
    return mc.FORBID_LINE + "\n" + mc.read_text(os.path.join(source, "src", "lib.rs"))


def write_manifest(workspace, source):
    """Record the expected hashes (from source) in workspace/.integrity/manifest.sha256."""
    lines = ["%s  %s" % (sha256(os.path.join(source, r)), r) for r in immutable_files(source)]
    lib = expected_lib_rs(source).encode("utf-8")
    lines.append("%s  %s" % (hashlib.sha256(lib).hexdigest(), "src/lib.rs"))
    path = os.path.join(workspace, MANIFEST_REL)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return path


def verify(workspace, source, restore=True):
    """Compare immutable files and src/lib.rs with the skeleton.

    Returns a list of violations {path, kind, restored}. kind is modified,
    missing, added (new file in src/bin or src/interfaces) or lib_rs.
    With restore=True every violation is undone in the workspace.
    """
    violations = []
    for r in immutable_files(source):
        want = os.path.join(source, r)
        have = os.path.join(workspace, r)
        kind = None
        if not os.path.exists(have):
            kind = "missing"
        elif sha256(have) != sha256(want):
            kind = "modified"
        if kind:
            if restore:
                os.makedirs(os.path.dirname(have), exist_ok=True)
                shutil.copy2(want, have)
            violations.append({"path": r, "kind": kind, "restored": restore})
    for d in mc.INFRA_DIRS:
        wd = os.path.join(workspace, d)
        if not os.path.isdir(wd):
            continue
        for p in mc.walk_files(wd):
            r = mc.rel(p, workspace)
            if not os.path.exists(os.path.join(source, r)):
                if restore:
                    os.remove(p)
                violations.append({"path": r, "kind": "added", "restored": restore})
    lib = os.path.join(workspace, "src", "lib.rs")
    want_lib = expected_lib_rs(source)
    if not os.path.exists(lib) or mc.read_text(lib) != want_lib:
        if restore:
            with open(lib, "w", encoding="utf-8") as fh:
                fh.write(want_lib)
        violations.append({"path": "src/lib.rs", "kind": "lib_rs", "restored": restore})
    return violations


def _tree(root):
    if not os.path.isdir(root):
        return {}
    return {mc.rel(p, root): sha256(p) for p in mc.walk_files(root)}


def diff_trees(a_root, b_root):
    a, b = _tree(a_root), _tree(b_root)
    return {
        "added": sorted(set(a) - set(b)),
        "removed": sorted(set(b) - set(a)),
        "modified": sorted(k for k in set(a) & set(b) if a[k] != b[k]),
    }


def check_workspace(workspace, snapshot_dir):
    """Workspace src/ vs a src_after/ snapshot: has anything changed since the snapshot?"""
    d = diff_trees(os.path.join(workspace, "src"), snapshot_dir)
    d["clean"] = not (d["added"] or d["removed"] or d["modified"])
    return d


def final_snapshot(project):
    """src_after/ of the last iteration of the final run, per trajectories/project_N/run_summary.json."""
    traj = os.path.join(mc.TRAJECTORIES_DIR, project)
    summary = os.path.join(traj, "run_summary.json")
    if not os.path.exists(summary):
        return None, "no final run recorded (%s missing)" % mc.rel(summary, mc.REPO_DIR)
    with open(summary, encoding="utf-8") as fh:
        data = json.load(fh)
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not re.match(r"^[A-Za-z0-9_.-]+$", run_id):
        return None, "run_summary.json has no valid run_id"
    run_dir = os.path.join(traj, "run_%s" % run_id)
    iters = sorted(d for d in os.listdir(run_dir) if re.match(r"^iter_\d+$", d)) if os.path.isdir(run_dir) else []
    for it in reversed(iters):
        snap = os.path.join(run_dir, it, "src_after")
        if os.path.isdir(snap):
            return snap, None
    return None, "run %s has no iter_*/src_after/" % run_id


def provenance(project):
    """translations/project_N/src must equal the final run's last src_after/ byte for byte (why.md Z7)."""
    snap, err = final_snapshot(project)
    if err:
        return {"ok": False, "error": err}
    d = diff_trees(os.path.join(mc.translation_dir(project), "src"), snap)
    d["ok"] = not (d["added"] or d["removed"] or d["modified"])
    d["snapshot"] = mc.rel(snap, mc.REPO_DIR)
    return d


def hardcode_scan(crate, min_len=mc.HARDCODE_MIN_LITERAL):
    """Every string literal >= min_len chars in a test file that also appears in library code (why.md Z2)."""
    test_files = [p for p in mc.walk_files(os.path.join(crate, "src", "bin")) if p.endswith(".rs")] \
        if os.path.isdir(os.path.join(crate, "src", "bin")) else []
    libs = {p: mc.read_text(p) for p in mc.library_sources(crate)}
    hits = []
    seen = set()
    for tf in test_files:
        for value, line in rustlex.string_literals(mc.read_text(tf)):
            if len(value) < min_len or value in seen:
                continue
            seen.add(value)
            for lp, text in libs.items():
                for lit, lline in rustlex.string_literals(text):
                    if value in lit:
                        hits.append({"literal_prefix": value[:40], "length": len(value),
                                     "test_file": mc.rel(tf, crate), "test_line": line,
                                     "lib_file": mc.rel(lp, crate), "lib_line": lline})
    return hits


_FFI_PATTERNS = [
    ("extern_c", re.compile(r'\bextern\s+"[^"]*"')),
    ("link_attr", re.compile(r"#\s*\[\s*link\b")),
    ("libc", re.compile(r"\blibc\s*::")),
    ("cc_crate", re.compile(r"\bcc\s*::")),
]


def ffi_scan(crate, source=None):
    """FFI / dependency / build.rs / C-source scan, shared with safety_check (why.md Z3)."""
    findings = []
    for p in mc.library_sources(crate):
        # strip() blanks comments and literal contents but keeps the quotes, so `extern "C"` still matches
        code = rustlex.strip(mc.read_text(p))
        for kind, rx in _FFI_PATTERNS:
            for m in rx.finditer(code):
                findings.append({"kind": kind, "file": mc.rel(p, crate), "line": rustlex.line_of(code, m.start())})
    if os.path.exists(os.path.join(crate, "build.rs")):
        findings.append({"kind": "build_rs", "file": "build.rs", "line": 0})
    for p in mc.walk_files(crate):
        if p.endswith((".c", ".h", ".cc", ".cpp")):
            findings.append({"kind": "c_source", "file": mc.rel(p, crate), "line": 0})
    deps = cargo_dependencies(os.path.join(crate, "Cargo.toml"))
    extra_deps = []
    if source:
        extra_deps = sorted(set(deps) - set(cargo_dependencies(os.path.join(source, "Cargo.toml"))))
        for d in extra_deps:
            findings.append({"kind": "new_dependency", "file": "Cargo.toml", "line": 0, "name": d})
    return {"findings": findings, "dependencies": deps, "extra_dependencies": extra_deps}


def cargo_dependencies(cargo_toml):
    """Dependency names from [dependencies]/[build-dependencies]/[dev-dependencies] (line-level parse)."""
    if not os.path.exists(cargo_toml):
        return []
    names, section = [], None
    for line in mc.read_text(cargo_toml).splitlines():
        s = line.strip()
        if s.startswith("["):
            section = s.strip("[]").strip()
            continue
        if section and section.endswith("dependencies") and "=" in s and not s.startswith("#"):
            names.append(s.split("=", 1)[0].strip())
    return sorted(set(names))


def _crate_and_source(args):
    source = mc.skeleton_dir(args.project)
    crate = os.path.abspath(args.crate_dir) if args.crate_dir else mc.translation_dir(args.project)
    return crate, source


def main(argv=None):
    ap = argparse.ArgumentParser(description="MP4 integrity guards (why.md Z1-Z7).")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write-manifest", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--check-workspace", metavar="SNAPSHOT_DIR")
    mode.add_argument("--provenance", metavar="PROJECT")
    mode.add_argument("--scan", action="store_true", help="hard-coding + FFI scan")
    ap.add_argument("--project")
    ap.add_argument("--crate-dir")
    ap.add_argument("--no-restore", action="store_true")
    args = ap.parse_args(argv)

    if args.provenance:
        mc.check_project(args.provenance)
        res = provenance(args.provenance)
        print(json.dumps(res, indent=2))
        return 0 if res["ok"] else 1
    if not args.project:
        ap.error("--project is required for this mode")
    mc.check_project(args.project)
    crate, source = _crate_and_source(args)
    bad_subjects = verify_subjects(source)
    if bad_subjects:
        print(json.dumps({"ok": False, "error": "subjects skeleton fails CHECKSUMS.sha256", "files": bad_subjects}))
        return 1
    if not os.path.isdir(crate):
        print("crate directory not found: %s" % crate, file=sys.stderr)
        return 2
    if args.write_manifest:
        print(write_manifest(crate, source))
        return 0
    if args.verify:
        v = verify(crate, source, restore=not args.no_restore)
        print(json.dumps({"ok": not v, "violations": v}, indent=2))
        return 0 if not v else 1
    if args.check_workspace:
        res = check_workspace(crate, os.path.abspath(args.check_workspace))
        print(json.dumps(res, indent=2))
        return 0 if res["clean"] else 1
    res = {"hardcode_hits": hardcode_scan(crate), "ffi": ffi_scan(crate, source)}
    res["ok"] = not res["hardcode_hits"] and not res["ffi"]["findings"]
    print(json.dumps(res, indent=2))
    return 0 if res["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
