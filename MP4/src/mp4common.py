"""Shared paths, defaults and subprocess helpers for the MP4 pipeline.

Python 3.9, stdlib + PyYAML only. Every entry point inserts its own directory
on sys.path so `python3 -I` works.
"""
import os
import shutil
import subprocess
import tempfile

SRC_DIR = os.path.dirname(os.path.abspath(__file__))
MP4_DIR = os.path.dirname(SRC_DIR)
REPO_DIR = os.path.dirname(MP4_DIR)
SUBJECTS_DIR = os.path.join(MP4_DIR, "subjects")
TRANSLATIONS_DIR = os.path.join(MP4_DIR, "translations")
TRAJECTORIES_DIR = os.path.join(MP4_DIR, "trajectories")
RESULTS_DIR = os.path.join(MP4_DIR, "results")
CONFIGS_DIR = os.path.join(MP4_DIR, "configs")
PIPELINE_YAML = os.path.join(CONFIGS_DIR, "pipeline.yaml")

PROJECTS = ("project_1", "project_2")

# TODO-move-to-pipeline.yaml: defaults below move to configs/pipeline.yaml in M3.
TOOLCHAIN = "nightly-2025-05-13"
CLIPPY_GROUPS = ("correctness", "style", "complexity", "perf")
RUBRIC_CLIPPY_ARGS = [
    "clippy", "--all-targets", "--all-features", "--",
    "-W", "clippy::correctness",
    "-W", "clippy::style",
    "-W", "clippy::complexity",
    "-W", "clippy::perf",
]
FORBID_LINE = "#![forbid(unsafe_code)]"
HARDCODE_MIN_LITERAL = 20
CARGO_TIMEOUT_S = 900
HARNESS_PREFIXES = ("src/bin/",)
INFRA_DIRS = ("src/bin", "src/interfaces")
SKIP_DIRS = frozenset({"target", ".git", "__pycache__", ".integrity"})


def load_pipeline_config():
    """Return configs/pipeline.yaml as a dict, or {} when it does not exist yet."""
    if not os.path.exists(PIPELINE_YAML):
        return {}
    import yaml
    with open(PIPELINE_YAML, encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        raise ValueError("configs/pipeline.yaml must be a mapping")
    return data


def check_project(name):
    """Validate a --project value at the boundary."""
    if name not in PROJECTS:
        raise SystemExit("unknown project %r (expected one of %s)" % (name, ", ".join(PROJECTS)))
    return name


def skeleton_dir(project):
    return os.path.join(SUBJECTS_DIR, check_project(project), "rust_skeleton")


def translation_dir(project):
    return os.path.join(TRANSLATIONS_DIR, check_project(project))


def cargo_env(extra=None):
    """Environment for cargo children: ~/.cargo/bin first on PATH, no colour."""
    env = dict(os.environ)
    cargo_bin = os.path.join(os.path.expanduser("~"), ".cargo", "bin")
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p and p != cargo_bin]
    env["PATH"] = os.pathsep.join([cargo_bin] + parts)
    env["CARGO_TERM_COLOR"] = "never"
    if extra:
        env.update(extra)
    return env


def cargo(args, cwd, log_path=None, env_extra=None, timeout=CARGO_TIMEOUT_S):
    """Run `cargo +TOOLCHAIN <args>` in cwd. Returns (exit_code, combined_output).

    The full combined stdout+stderr is written to log_path when given. A
    timeout is reported as exit code 124 with the partial output.
    """
    cmd = ["cargo", "+" + TOOLCHAIN] + list(args)
    try:
        proc = subprocess.run(cmd, cwd=cwd, env=cargo_env(env_extra), stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=timeout)
        code, out = proc.returncode, proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired as exc:
        code = 124
        out = (exc.output or b"").decode("utf-8", "replace") + "\n[mp4] cargo timed out after %ss\n" % timeout
    except FileNotFoundError:
        code, out = 127, "[mp4] cargo not found on PATH (expected ~/.cargo/bin/cargo)\n"
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(cmd) + "\n" + out + "\n[exit %d]\n" % code)
    return code, out


def copy_crate(src, dst_parent=None):
    """Copy a crate directory (without target/ and .git/) to a fresh temp dir. Returns the copy path."""
    parent = dst_parent or tempfile.mkdtemp(prefix="mp4crate_")
    dst = os.path.join(parent, os.path.basename(os.path.normpath(src)) or "crate")
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns("target", ".git", "__pycache__"))
    return dst


def touch(path):
    os.utime(path, None)


def rel(path, base):
    return os.path.relpath(path, base).replace(os.sep, "/")


def walk_files(root, skip_dirs=SKIP_DIRS):
    """Yield every file under root (sorted), skipping build and VCS dirs."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in skip_dirs)
        for name in sorted(filenames):
            yield os.path.join(dirpath, name)


def library_sources(crate):
    """Rust files that are 'generated code' for metrics: src/**/*.rs minus src/bin and src/interfaces."""
    out = []
    src = os.path.join(crate, "src")
    if not os.path.isdir(src):
        return out
    for path in walk_files(src):
        r = rel(path, crate)
        if not r.endswith(".rs"):
            continue
        if any(r == d or r.startswith(d + "/") for d in INFRA_DIRS):
            continue
        out.append(path)
    return out


def read_text(path):
    with open(path, encoding="utf-8", errors="replace") as fh:
        return fh.read()
