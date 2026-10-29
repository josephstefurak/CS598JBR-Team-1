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
    missing, added (new file in src/bin or src/interfaces), lib_rs or symlink.
    With restore=True every violation is undone in the workspace.
    """
    violations = []
    # A linked src/, src/bin or src/interfaces would turn every restore below into writes and deletions in the
    # directory it points to (code the agent runs through cargo could create one): remove the link first.
    for d in ("src",) + tuple(mc.INFRA_DIRS):
        p = os.path.join(workspace, d)
        if os.path.islink(p):
            if restore:
                os.remove(p)
            violations.append({"path": d, "kind": "symlink", "restored": restore})
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
                if os.path.islink(have):   # never write through a link to a file outside the crate
                    os.remove(have)
                # copyfile, not copy2: the restored file must be newer than the build made from the agent's
                # edit, or cargo keeps reusing that build (a tampered test binary) as up to date
                shutil.copyfile(want, have)
            violations.append({"path": r, "kind": kind, "restored": restore})
    for d in mc.INFRA_DIRS:
        wd = os.path.join(workspace, d)
        if not os.path.isdir(wd) or os.path.islink(wd):
            continue
        for p in mc.walk_files(wd):
            r = mc.rel(p, workspace)
            if not os.path.exists(os.path.join(source, r)):
                if restore:
                    os.remove(p)
                violations.append({"path": r, "kind": "added", "restored": restore})
    violations += sweep_strays(workspace, source, restore)
    lib = os.path.join(workspace, "src", "lib.rs")
    want_lib = expected_lib_rs(source)
    if not os.path.exists(lib) or os.path.islink(lib) or mc.read_text(lib) != want_lib:
        if restore:
            if os.path.islink(lib):
                os.remove(lib)
            with open(lib, "w", encoding="utf-8") as fh:
                fh.write(want_lib)
        violations.append({"path": "src/lib.rs", "kind": "lib_rs", "restored": restore})
    return violations


# Top-level workspace entries that are the wrapper's or cargo's, never the agent's
_WRAPPER_DIRS = frozenset({"target", ".integrity"})


def sweep_strays(workspace, source, restore=True):
    """Owner gate G1 (a): every file outside src/ that is not in the skeleton, and every symlink anywhere in the
    workspace, is removed (restore=True) and recorded. Files outside src/ reach the build and the graders' own
    clippy run without being library code (.cargo/config.toml lint caps or a test runner, clippy.toml,
    build.rs, tests/, .claude/settings.json), and a symlink can carry content from outside the crate.
    Immutable files and src/lib.rs are left to verify(), which restores them; src/bin and src/interfaces are
    already covered there too. Returns violations {path, kind (outside_src | symlink), restored}."""
    covered = set(immutable_files(source)) | {"src/lib.rs"}
    violations = []
    for dirpath, dirnames, filenames in os.walk(workspace):
        rel_dir = mc.rel(dirpath, workspace) if dirpath != workspace else ""
        in_src = rel_dir == "src" or rel_dir.startswith("src/")
        for name in sorted(dirnames):
            p = os.path.join(dirpath, name)
            r = mc.rel(p, workspace)
            if os.path.islink(p):            # never descended into (os.walk does not follow links)
                if r not in ("src",) + tuple(mc.INFRA_DIRS):   # those verify() already removed or recorded
                    if restore:
                        os.remove(p)
                    violations.append({"path": r, "kind": "symlink", "restored": restore})
                dirnames.remove(name)
            elif not rel_dir and name in _WRAPPER_DIRS:
                dirnames.remove(name)
        for name in sorted(filenames):
            p = os.path.join(dirpath, name)
            r = mc.rel(p, workspace)
            if r in covered or any(r.startswith(d + "/") for d in mc.INFRA_DIRS):
                continue                     # verify() restores these, and records files added there
            if os.path.islink(p):
                kind = "symlink"
            elif in_src:
                continue
            else:
                kind = "outside_src"
            if restore:
                os.remove(p)
            violations.append({"path": r, "kind": kind, "restored": restore})
    if restore:   # directories the agent created outside src/ (now empty of files): remove, bottom-up
        for dirpath, dirnames, filenames in os.walk(workspace, topdown=False):
            r = mc.rel(dirpath, workspace) if dirpath != workspace else ""
            top = r.split("/", 1)[0]
            if not r or top in _WRAPPER_DIRS or top == "src" or os.path.isdir(os.path.join(source, r)):
                continue
            if not os.listdir(dirpath):
                os.rmdir(dirpath)
    return violations


# Lint-level attributes (owner gate G1 (b)). In library code they block SUCCESS, except the D-ALLOW pairs the
# project config lists: they silence the graders' own clippy run, or turn its warnings into errors.
_LINT_ATTR_RE = re.compile(r"#\s*(!)?\s*\[\s*(allow|expect|warn|deny|forbid|cfg_attr)\s*\(")
_LINT_WORD_RE = re.compile(r"\b(allow|expect|warn|deny|forbid)\s*\(")
_ITEM_RE = re.compile(r"\b(?:fn|struct|enum|union|trait|type|const|static|mod|impl)\s+([A-Za-z_][A-Za-z0-9_]*)")


def _paren_body(code, open_idx):
    """Text between the parenthesis at open_idx and its match, or None if it is never closed."""
    depth = 0
    for i in range(open_idx, len(code)):
        if code[i] == "(":
            depth += 1
        elif code[i] == ")":
            depth -= 1
            if depth == 0:
                return code[open_idx + 1:i], i
    return None, len(code)


def lint_attribute_scan(crate, allowed=()):
    """Every allow/expect/warn/deny/forbid attribute (and cfg_attr carrying one) in library code, except an
    outer #[allow(...)] whose lints are all permitted for the item it is attached to. allowed is the project's
    allow_attributes list ({lint, item}). src/lib.rs is skipped: integrity restores it to the wrapper's own
    text (the injected #![forbid(unsafe_code)] plus the skeleton). Returns [{file, line, attribute, item}]."""
    pairs = {(a["lint"].replace(" ", ""), a["item"]) for a in allowed}
    hits = []
    for p in mc.library_sources(crate):
        if mc.rel(p, crate) == "src/lib.rs":
            continue
        code = rustlex.strip(mc.read_text(p))
        for m in _LINT_ATTR_RE.finditer(code):
            inner, kind = bool(m.group(1)), m.group(2)
            body, close = _paren_body(code, m.end() - 1)
            if body is None:
                body = code[m.end():m.end() + 80]
            if kind == "cfg_attr" and not _LINT_WORD_RE.search(body):
                continue                     # e.g. cfg_attr(test, derive(Debug)): not a lint level
            item = None
            if not inner:
                im = _ITEM_RE.search(code, close)
                item = im.group(1) if im else None
            lints = [x.replace(" ", "") for x in body.split(",") if x.strip()]
            if kind == "allow" and not inner and lints and all((lt, item) in pairs for lt in lints):
                continue
            hits.append({"file": mc.rel(p, crate), "line": rustlex.line_of(code, m.start()),
                         "attribute": " ".join(code[m.start():close + 2].split())[:120], "item": item})
    return hits


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
    final_dir = data.get("final_iteration_dir")
    if final_dir is not None:
        # the attempt the run's last check measured, e.g. iter_03_attempt2 after a usage-limit retry
        if not isinstance(final_dir, str) or not _ITER_DIR_RE.match(final_dir):
            return None, "run_summary.json has an invalid final_iteration_dir"
        snap = os.path.join(run_dir, final_dir, "src_after")
        if os.path.isdir(snap):
            return snap, None
        return None, "run %s has no %s/src_after/" % (run_id, final_dir)
    iters = [d for d in os.listdir(run_dir) if _ITER_DIR_RE.match(d)] if os.path.isdir(run_dir) else []
    for it in sorted(iters, key=_iter_key, reverse=True):
        snap = os.path.join(run_dir, it, "src_after")
        if os.path.isdir(snap):
            return snap, None
    return None, "run %s has no iter_*/src_after/" % run_id


_ITER_DIR_RE = re.compile(r"^iter_(\d+)(?:_attempt(\d+))?$")


def _iter_key(name):
    m = _ITER_DIR_RE.match(name)
    return int(m.group(1)), int(m.group(2) or 1)


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
