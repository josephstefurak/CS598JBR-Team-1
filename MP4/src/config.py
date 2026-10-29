"""Load and validate MP4/configs/pipeline.yaml and configs/projects/*.yaml.

Every mapping has an allowlist of keys (unknown key = error), values are
type-checked, and the D7 spend envelope is enforced here: model opus,
max_turns <= 60, max_iterations <= 8. The rubric clippy command must equal
the handout's exactly. Paths resolve relative to MP4/configs/ (config files)
or MP4/ (project data). config_hash covers every file that shapes an agent
call, so a trajectory can name the exact configuration it ran with.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402

HANDOUT_CLIPPY_ARGS = ["clippy", "--all-targets", "--all-features", "--",
                       "-W", "clippy::correctness", "-W", "clippy::style",
                       "-W", "clippy::complexity", "-W", "clippy::perf"]
D7_MAX_TURNS = 60
D7_MAX_ITERATIONS = 8
D7_MODEL = "opus"

SCHEMA = {
    "agent": {
        "kind": str, "fake_scenario": (str, type(None)), "resume_session": bool, "claude_bin": str,
        "model": str, "effort": str, "max_turns": int, "max_budget_usd": (int, float),
        "wall_clock_minutes": (int, float), "permission_mode": str, "tools": list, "allowed_tools": list,
        "disallowed_tools": list, "setting_sources": str, "settings_file": str, "system_prompt_file": str,
        "status_schema_file": str, "strict_mcp": bool, "disable_slash_commands": bool, "env": dict,
    },
    "loop": {"max_iterations": int, "no_progress_rounds": int},
    "toolchain": {"name": str, "cargo_locked": bool, "cargo_timeout_seconds": int},
    "checks": {"clippy_rubric_args": list, "clippy_groups": list, "forbid_unsafe_in_lib": bool,
               "forbid_line": str, "hardcode_min_literal": int},
    "safety": {"tool": str, "course_cmd": (str, list, type(None)), "course_version": (str, type(None))},
    "rate_limit": {"mode": str, "fallback_minutes": (int, float), "max_wait_hours": (int, float),
                   "resume_margin_seconds": (int, float)},
    "digest": {"max_build_errors": int, "max_failing_tests": int, "max_panic_chars": int,
               "max_clippy_sites": int, "max_chars": int},
    "prompts": {"initial": str, "repair": str, "cheatsheet": str},
    "projects": {"project_1": str, "project_2": str},
}
PROJECT_SCHEMA = {
    "name": str, "label": str, "crate": str, "modules": list, "c_dir": str, "c_files": list, "test_file": str,
    "interface_dir": str, "expected_pub_items": int, "allow_attributes": list, "known_failing_tests": list,
    "notes": list, "rulings": dict, "c_behaviour": list,
}
KNOWN_FAILING_KEYS = {"name", "reason", "expected_assertion", "expected_location"}
ALLOW_ATTR_KEYS = {"lint", "item", "reason"}
EFFORTS = {"low", "medium", "high", "xhigh", "max"}


class ConfigError(ValueError):
    pass


def _check_map(data, schema, where):
    if not isinstance(data, dict):
        raise ConfigError("%s must be a mapping" % where)
    unknown = sorted(set(data) - set(schema))
    if unknown:
        raise ConfigError("%s: unknown key(s) %s" % (where, ", ".join(unknown)))
    missing = sorted(set(schema) - set(data))
    if missing:
        raise ConfigError("%s: missing key(s) %s" % (where, ", ".join(missing)))
    for key, typ in schema.items():
        if isinstance(typ, dict):
            _check_map(data[key], typ, "%s.%s" % (where, key))
        elif not isinstance(data[key], typ) or (typ is int and isinstance(data[key], bool)):
            raise ConfigError("%s.%s: expected %s, got %r" % (where, key, typ, data[key]))


def _load_yaml(path):
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def validate_pipeline(cfg):
    _check_map(cfg, SCHEMA, "pipeline.yaml")
    a = cfg["agent"]
    if a["model"] != D7_MODEL:
        raise ConfigError("agent.model %r is outside the D7 envelope (model %s)" % (a["model"], D7_MODEL))
    if not 1 <= a["max_turns"] <= D7_MAX_TURNS:
        raise ConfigError("agent.max_turns %d is outside the D7 envelope (1..%d)" % (a["max_turns"], D7_MAX_TURNS))
    if not 1 <= cfg["loop"]["max_iterations"] <= D7_MAX_ITERATIONS:
        raise ConfigError("loop.max_iterations is outside the D7 envelope (1..%d)" % D7_MAX_ITERATIONS)
    if a["kind"] not in ("claude", "fake"):
        raise ConfigError("agent.kind must be claude or fake")
    if a["resume_session"]:
        raise ConfigError("agent.resume_session is not implemented; it must stay false")
    if a["effort"] not in EFFORTS:
        raise ConfigError("agent.effort must be one of %s" % sorted(EFFORTS))
    if a["permission_mode"] != "dontAsk":
        raise ConfigError("agent.permission_mode must be dontAsk (C2: a headless run must never prompt)")
    if a["setting_sources"] != "project":
        raise ConfigError("agent.setting_sources must be project (C4: no user settings, hooks or permissions)")
    for key in ("tools", "allowed_tools", "disallowed_tools"):
        if not all(isinstance(x, str) and x for x in a[key]):
            raise ConfigError("agent.%s must be a list of non-empty strings" % key)
    if not all(isinstance(k, str) and isinstance(v, str) for k, v in a["env"].items()):
        raise ConfigError("agent.env must map strings to strings")
    if cfg["checks"]["clippy_rubric_args"] != HANDOUT_CLIPPY_ARGS:
        raise ConfigError("checks.clippy_rubric_args must equal the handout's rubric clippy command exactly")
    if cfg["toolchain"]["name"] != "nightly-2025-05-13":
        raise ConfigError("toolchain.name must be nightly-2025-05-13 (why.md Z15)")
    if cfg["safety"]["tool"] not in ("proxy", "course"):
        raise ConfigError("safety.tool must be proxy or course")
    if cfg["rate_limit"]["mode"] not in ("wait", "exit"):
        raise ConfigError("rate_limit.mode must be wait or exit")
    return cfg


def validate_project(p, name):
    _check_map(p, PROJECT_SCHEMA, "projects/%s.yaml" % name)
    if p["name"] != name:
        raise ConfigError("projects/%s.yaml: name is %r" % (name, p["name"]))
    for k in p["known_failing_tests"]:
        if not isinstance(k, dict) or set(k) != KNOWN_FAILING_KEYS:
            raise ConfigError("known_failing_tests entries need exactly %s" % sorted(KNOWN_FAILING_KEYS))
        # name, assertion and location are matched as substrings (D8): an empty one would match anything
        if not all(isinstance(v, str) and v.strip() for v in k.values()):
            raise ConfigError("known_failing_tests values must be non-empty strings")
    for k in p["allow_attributes"]:
        if not isinstance(k, dict) or set(k) != ALLOW_ATTR_KEYS:
            raise ConfigError("allow_attributes entries need exactly %s" % sorted(ALLOW_ATTR_KEYS))
        if not all(isinstance(v, str) and v.strip() for v in k.values()):
            raise ConfigError("allow_attributes values must be non-empty strings")
    for key in ("modules", "c_files", "notes", "c_behaviour"):
        if not all(isinstance(x, str) for x in p[key]):
            raise ConfigError("%s must be a list of strings" % key)
    return p


def _cfg_path(rel_path):
    full = os.path.normpath(os.path.join(mc.CONFIGS_DIR, rel_path))
    if not full.startswith(mc.CONFIGS_DIR + os.sep):
        raise ConfigError("config path escapes MP4/configs: %r" % rel_path)
    if not os.path.isfile(full):
        raise ConfigError("config file not found: %s" % mc.rel(full, mc.REPO_DIR))
    return full


def load(project):
    """Validated configuration for one project, with resolved paths and config_hash."""
    mc.check_project(project)
    pipeline = validate_pipeline(_load_yaml(mc.PIPELINE_YAML))
    proj_path = _cfg_path(pipeline["projects"][project])
    proj = validate_project(_load_yaml(proj_path), project)
    a = pipeline["agent"]
    files = {
        "pipeline": mc.PIPELINE_YAML,
        "project": proj_path,
        "settings": _cfg_path(a["settings_file"]),
        "system_prompt": _cfg_path(a["system_prompt_file"]),
        "status_schema": _cfg_path(a["status_schema_file"]),
        "initial": _cfg_path(pipeline["prompts"]["initial"]),
        "repair": _cfg_path(pipeline["prompts"]["repair"]),
        "cheatsheet": _cfg_path(pipeline["prompts"]["cheatsheet"]),
    }
    with open(files["status_schema"], encoding="utf-8") as fh:
        json.load(fh)  # must be valid JSON
    with open(files["settings"], encoding="utf-8") as fh:
        settings = json.load(fh)
    if settings.get("autoMemoryEnabled") is not False or settings.get("disableAllHooks") is not True:
        raise ConfigError("claude_settings.json must set autoMemoryEnabled false and disableAllHooks true (C4)")
    c_dir = os.path.normpath(os.path.join(mc.MP4_DIR, proj["c_dir"]))
    if not c_dir.startswith(os.path.join(mc.SUBJECTS_DIR, project) + os.sep):
        # c_dir becomes agent B's --add-dir: everything under it is readable without a permission rule
        raise ConfigError("c_dir must be inside MP4/subjects/%s/: %r" % (project, proj["c_dir"]))
    if not os.path.isdir(c_dir):
        raise ConfigError("c_dir not found: %s" % proj["c_dir"])
    return {
        "project": project,
        "pipeline": pipeline,
        "project_cfg": proj,
        "files": files,
        "c_dir": c_dir,
        "workspace": mc.translation_dir(project),
        "trajectory_root": os.path.join(mc.TRAJECTORIES_DIR, project),
        "skeleton": mc.skeleton_dir(project),
        "config_hash": config_hash(files),
    }


def config_hash(files):
    h = hashlib.sha256()
    for key in sorted(files):
        with open(files[key], "rb") as fh:
            data = fh.read()
        h.update(("%s\0%s\0" % (key, mc.rel(files[key], mc.MP4_DIR))).encode("utf-8"))
        h.update(hashlib.sha256(data).digest())
    return h.hexdigest()


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Validate the MP4 configuration for a project.")
    ap.add_argument("--project", required=True, choices=mc.PROJECTS)
    cfg = load(ap.parse_args().project)
    print("config OK: %s  config_hash %s" % (cfg["project"], cfg["config_hash"]))
