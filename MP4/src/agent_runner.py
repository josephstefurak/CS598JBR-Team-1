"""Launch agent B (Claude Code headless) for one iteration and capture its trajectory.

why.md C1-C9, D1. The argv comes entirely from configs/pipeline.yaml. The
prompt goes on stdin. stdout (stream-json) is teed line by line, scrubbed,
to agent.stream.jsonl. The system/init line is checked on every call: tools
must equal the configured set plus StructuredOutput (added by --json-schema), no MCP servers, no slash commands,
permissionMode as configured, model as configured. A mismatch kills the
process and the iteration is aborted. The wall clock is enforced on the whole
process group (SIGTERM, then SIGKILL).

Outcomes: ok | max_turns | budget | usage_limit | overloaded | auth_error | error
| timeout | isolation_violation.
"""
import json
import os
import queue
import re
import signal
import subprocess
import sys
import threading
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402
import scrub_secrets  # noqa: E402

EMPTY_MCP = '{"mcpServers":{}}'
# --json-schema (always passed, C6) adds this tool for the structured final status. It has no file, shell or
# network access. Owner ruling at the M3 gate, 2026-10-29: expected in init alongside the configured tools.
STRUCTURED_OUTPUT_TOOL = "StructuredOutput"
_LIMIT_RE = re.compile(r"limit|resets|rate_limit|429", re.I)
_OVERLOAD_RE = re.compile(r"overloaded|529", re.I)
_AUTH_RE = re.compile(r"Failed to authenticate|OAuth|not logged in|/login", re.I)


def _subst(items, values):
    out = []
    for s in items:
        for k, v in values.items():
            s = s.replace("{%s}" % k, v)
        out.append(s)
    return out


def build_argv(cfg, max_turns=None, session_id=None, claude_bin=None, add_dirs=None):
    """argv for one headless call. Every flag from C1-C6 comes from pipeline.yaml."""
    p = cfg["pipeline"]
    a = p["agent"]
    values = {"toolchain": p["toolchain"]["name"], "subjects": mc.SUBJECTS_DIR}
    with open(cfg["files"]["status_schema"], encoding="utf-8") as fh:
        schema = json.dumps(json.load(fh), separators=(",", ":"))
    argv = [claude_bin or a["claude_bin"], "-p",
            "--output-format", "stream-json", "--verbose",
            "--model", a["model"], "--effort", a["effort"],
            "--max-turns", str(max_turns or a["max_turns"]),
            "--max-budget-usd", str(a["max_budget_usd"]),
            "--permission-mode", a["permission_mode"],
            "--tools", ",".join(a["tools"])]
    argv += ["--allowedTools"] + _subst(a["allowed_tools"], values)
    argv += ["--disallowedTools"] + _subst(a["disallowed_tools"], values)
    argv += ["--setting-sources", a["setting_sources"],
             "--settings", cfg["files"]["settings"],
             "--append-system-prompt-file", cfg["files"]["system_prompt"],
             "--json-schema", schema]
    if a["strict_mcp"]:
        argv += ["--strict-mcp-config", "--mcp-config", EMPTY_MCP]
    if a["disable_slash_commands"]:
        argv += ["--disable-slash-commands"]
    argv += ["--session-id", session_id or str(uuid.uuid4())]
    for d in (add_dirs if add_dirs is not None else [cfg["c_dir"]]):
        argv += ["--add-dir", d]
    return argv


def agent_env(cfg):
    """cargo-ready PATH plus the isolation variables (C4)."""
    return mc.cargo_env(dict(cfg["pipeline"]["agent"]["env"]))


def check_init(init, cfg):
    """List of isolation violations found in a system/init event."""
    a = cfg["pipeline"]["agent"]
    v = []
    tools = init.get("tools")
    expected = sorted(a["tools"] + [STRUCTURED_OUTPUT_TOOL])
    if not isinstance(tools, list) or sorted(tools) != expected:
        v.append("tools %r != expected %r" % (tools, expected))
    if "mcp_servers" not in init:
        v.append("mcp_servers missing from init")
    elif init["mcp_servers"]:
        v.append("mcp_servers not empty: %r" % (init["mcp_servers"],))
    slash = init.get("slash_commands")
    if slash is None:
        v.append("slash_commands missing from init")
    elif slash:
        v.append("slash_commands not empty: %r" % (slash,))
    if init.get("permissionMode") != a["permission_mode"]:
        v.append("permissionMode %r != %r" % (init.get("permissionMode"), a["permission_mode"]))
    if a["model"] not in str(init.get("model", "")).lower():
        v.append("model %r does not match %r" % (init.get("model"), a["model"]))
    return v


def _rate_limit_info(ev):
    info = ev.get("rate_limit_info") if isinstance(ev.get("rate_limit_info"), dict) else ev
    return info.get("status"), info.get("resetsAt") or info.get("resets_at"), info.get("rateLimitType")


def classify(result, rate_rejected, resets_at, killed_for_timeout, violation):
    if violation:
        return "isolation_violation"
    if killed_for_timeout:
        return "timeout"
    if result is None:
        return "usage_limit" if rate_rejected else "error"
    sub = result.get("subtype", "")
    text = json.dumps(result.get("result", "")) + json.dumps(result.get("errors", ""))
    if sub == "error_max_turns":
        return "max_turns"
    if sub == "error_max_budget_usd":
        return "budget"
    if result.get("is_error") and _AUTH_RE.search(text):
        return "auth_error"
    if rate_rejected or (result.get("is_error") and _LIMIT_RE.search(text)):
        return "usage_limit"
    if result.get("is_error") and _OVERLOAD_RE.search(text):
        return "overloaded"
    if sub == "success" and not result.get("is_error"):
        return "ok"
    return "error"


def _kill(proc, grace=10):
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        return
    try:
        proc.wait(timeout=grace)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
        proc.wait()


def run(cfg, argv, cwd, prompt, stream_path, wall_clock_s=None, env=None):
    """Spawn agent B, tee its stream, enforce isolation and the wall clock. Returns a summary dict."""
    wall = wall_clock_s if wall_clock_s is not None else cfg["pipeline"]["agent"]["wall_clock_minutes"] * 60
    os.makedirs(os.path.dirname(stream_path), exist_ok=True)
    started = time.time()
    proc = subprocess.Popen(argv, cwd=cwd, env=env or agent_env(cfg), stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True)
    lines = queue.Queue()

    def pump(stream, tag):
        for raw in iter(stream.readline, b""):
            lines.put((tag, raw.decode("utf-8", "replace")))
        lines.put((tag, None))

    for stream, tag in ((proc.stdout, "out"), (proc.stderr, "err")):
        threading.Thread(target=pump, args=(stream, tag), daemon=True).start()
    try:
        proc.stdin.write(prompt.encode("utf-8"))
        proc.stdin.close()
    except BrokenPipeError:
        pass

    init, result, violation = None, None, []
    rate_rejected, resets_at, rate_events = False, None, []
    killed_for_timeout = False
    open_streams = 2
    stderr_text = []
    n_lines = 0
    try:
        with open(stream_path, "w", encoding="utf-8") as out:
            while open_streams:
                remaining = wall - (time.time() - started)
                if remaining <= 0 and not killed_for_timeout:
                    killed_for_timeout = True
                    _kill(proc)
                try:
                    tag, line = lines.get(timeout=max(0.1, min(remaining, 1.0)) if remaining > 0 else 1.0)
                except queue.Empty:
                    continue
                if line is None:
                    open_streams -= 1
                    continue
                if tag == "err":
                    stderr_text.append(line)
                    continue
                out.write(scrub_secrets.scrub_text(line))
                out.flush()
                n_lines += 1
                try:
                    ev = json.loads(line)
                except ValueError:
                    continue
                etype = ev.get("type")
                if etype == "system" and ev.get("subtype") == "init" and init is None:
                    init = ev
                    violation = check_init(ev, cfg)
                    if violation:
                        _kill(proc)
                elif etype == "rate_limit_event":
                    status, resets, kind = _rate_limit_info(ev)
                    rate_events.append({"status": status, "resets_at": resets, "type": kind})
                    if status == "rejected":
                        rate_rejected, resets_at = True, resets
                elif etype == "result":
                    result = ev
    except BaseException:
        # interrupted (SIGTERM/SIGINT in the caller, or any error): never leave agent B running
        _kill(proc)
        raise
    try:
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        _kill(proc)
    if stderr_text:
        with open(stream_path + ".stderr", "w", encoding="utf-8") as fh:
            fh.write(scrub_secrets.scrub_text("".join(stderr_text)))
    outcome = classify(result, rate_rejected, resets_at, killed_for_timeout, violation)
    return {
        "outcome": outcome,
        "exit_code": proc.returncode,
        "elapsed_s": round(time.time() - started, 1),
        "stream_lines": n_lines,
        "stream_path": stream_path,
        "isolation_violations": violation,
        "init": None if init is None else {
            k: init.get(k) for k in ("model", "permissionMode", "tools", "mcp_servers", "slash_commands",
                                     "claude_code_version", "session_id", "cwd")},
        "rate_limit_events": rate_events,
        "resets_at": resets_at,
        "result": None if result is None else {
            k: result.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "duration_api_ms",
                                       "total_cost_usd",
                                       "usage", "permission_denials", "structured_output", "result")},
    }
