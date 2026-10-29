"""Shared paths, defaults and subprocess helpers for the MP4 pipeline.

Python 3.9, stdlib + PyYAML only. Every entry point inserts its own directory
on sys.path so `python3 -I` works.
"""
import os
import shutil
import signal
import subprocess
import tempfile
import threading

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

# Fallback defaults. configs/pipeline.yaml (toolchain.*, checks.*) overrides them at import
# time; see _apply_pipeline_config() at the end of this module.
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
TIMEOUT_EXIT = 124        # exit code cargo() reports for a timeout
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


# Variables from the caller's shell that would change what cargo builds or lints (flags, wrappers, target dir).
# The measurements, and agent B's own cargo commands, must not depend on who launched the controller.
CARGO_ENV_DROP = ("RUSTFLAGS", "CARGO_ENCODED_RUSTFLAGS", "CARGO_BUILD_RUSTFLAGS", "RUSTDOCFLAGS",
                  "CARGO_ENCODED_RUSTDOCFLAGS", "CARGO_TARGET_DIR", "CARGO_BUILD_TARGET_DIR", "CARGO_BUILD_TARGET",
                  "RUSTC_WRAPPER", "RUSTC_WORKSPACE_WRAPPER", "CARGO_BUILD_RUSTC_WRAPPER")


def cargo_env(extra=None):
    """Environment for cargo children: ~/.cargo/bin first on PATH, no colour, no inherited build flags."""
    env = {k: v for k, v in os.environ.items() if k not in CARGO_ENV_DROP}
    cargo_bin = os.path.join(os.path.expanduser("~"), ".cargo", "bin")
    parts = [p for p in env.get("PATH", "").split(os.pathsep) if p and p != cargo_bin]
    env["PATH"] = os.pathsep.join([cargo_bin] + parts)
    env["CARGO_TERM_COLOR"] = "never"
    if extra:
        env.update(extra)
    return env


def _kill_group(proc):
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


# cargo runs in its own process group, so a terminal hangup (SIGHUP), Ctrl-\ (SIGQUIT) or a plain kill (SIGTERM)
# reaches only this process. While cargo runs, such a signal whose action is still the default is caught, cargo's
# group is killed, and the signal is sent again with its default action. SIGINT raises KeyboardInterrupt anyway.
_HANDOVER_SIGNALS = tuple(getattr(signal, n) for n in ("SIGHUP", "SIGQUIT", "SIGTERM") if hasattr(signal, n))


class _Signalled(BaseException):
    pass


def _raise_signalled(signum, _frame):
    raise _Signalled(signum)


def cargo(args, cwd, log_path=None, env_extra=None, timeout=None):
    """Run `cargo +TOOLCHAIN <args>` in cwd. Returns (exit_code, combined_output).

    The full combined stdout+stderr is written to log_path when given. A
    timeout (default CARGO_TIMEOUT_S, read at call time so pipeline.yaml
    applies) is reported as exit code 124 with the partial output. cargo runs
    in its own process group, and a timeout or an interruption kills the whole
    group: a hung test binary must not outlive the run.
    """
    timeout = timeout or CARGO_TIMEOUT_S
    cmd = ["cargo", "+" + TOOLCHAIN] + list(args)
    try:
        proc = subprocess.Popen(cmd, cwd=cwd, env=cargo_env(env_extra), stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, start_new_session=True)
    except FileNotFoundError:
        proc = None
        code, out = 127, "[mp4] cargo not found on PATH (expected ~/.cargo/bin/cargo)\n"
    if proc is not None:
        caught = {}
        if threading.current_thread() is threading.main_thread():
            for sig in _HANDOVER_SIGNALS:
                if signal.getsignal(sig) == signal.SIG_DFL:
                    caught[sig] = signal.signal(sig, _raise_signalled)
        try:
            raw, _ = proc.communicate(timeout=timeout)
            code = proc.returncode
        except subprocess.TimeoutExpired:
            _kill_group(proc)
            raw, _ = proc.communicate()   # the output read before the timeout is kept
            code = TIMEOUT_EXIT
            raw += b"\n[mp4] cargo timed out after %ds; its process group was killed\n" % timeout
        except _Signalled as exc:
            _kill_group(proc)
            proc.wait()
            for sig, old in caught.items():
                signal.signal(sig, old)
            caught = {}
            os.kill(os.getpid(), exc.args[0])   # now with its default action
            raise
        except BaseException:
            _kill_group(proc)
            proc.wait()
            raise
        finally:
            for sig, old in caught.items():
                signal.signal(sig, old)
        out = raw.decode("utf-8", "replace")
    if log_path:
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write("$ " + " ".join(cmd) + "\n" + out + "\n[exit %d]\n" % code)
    return code, out


def _symlinks(directory, names):
    return [n for n in names if os.path.islink(os.path.join(directory, n))]


def copy_src_tree(src, dst):
    """Copy a crate's src/ for a committed snapshot. Symlinks are left out: code the agent runs through cargo
    could link a file from elsewhere on the machine into src/, and copytree would copy what it points to.
    Fresh mtimes (copyfile), so a build made from an edited file is never reused as up to date."""
    shutil.copytree(src, dst, ignore=_symlinks, copy_function=shutil.copyfile)


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


def _apply_pipeline_config():
    """Take toolchain and check settings from configs/pipeline.yaml, so they live in one place."""
    global TOOLCHAIN, CLIPPY_GROUPS, RUBRIC_CLIPPY_ARGS, FORBID_LINE, HARDCODE_MIN_LITERAL, CARGO_TIMEOUT_S
    cfg = load_pipeline_config()
    tc = cfg.get("toolchain") or {}
    ck = cfg.get("checks") or {}
    TOOLCHAIN = tc.get("name", TOOLCHAIN)
    CARGO_TIMEOUT_S = tc.get("cargo_timeout_seconds", CARGO_TIMEOUT_S)
    CLIPPY_GROUPS = tuple(ck.get("clippy_groups", CLIPPY_GROUPS))
    RUBRIC_CLIPPY_ARGS = list(ck.get("clippy_rubric_args", RUBRIC_CLIPPY_ARGS))
    FORBID_LINE = ck.get("forbid_line", FORBID_LINE)
    HARDCODE_MIN_LITERAL = ck.get("hardcode_min_literal", HARDCODE_MIN_LITERAL)


_apply_pipeline_config()
