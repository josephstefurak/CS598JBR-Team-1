"""Stand-in for `claude -p --output-format stream-json` used by selftest.py.

Emits canned events in the real vocabulary (system/init, assistant, user,
rate_limit_event, result). FAKE_CLAUDE_MODE selects the scenario:
  normal       init with the --tools set, one tool round trip, result success
  usage_limit  rate_limit_event rejected, then an error result mentioning the limit
  max_turns    result error_max_turns
  slow         init, then sleeps (for the wall-clock kill)
  wrong_tools  init advertising an extra tool (isolation mismatch)
  secret       normal, with a planted key, e-mail and home path in assistant text
"""
import json
import os
import sys
import time


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def emit(ev):
    sys.stdout.write(json.dumps(ev) + "\n")
    sys.stdout.flush()


def main():
    mode = os.environ.get("FAKE_CLAUDE_MODE", "normal")
    sys.stdin.read()
    tools = (arg("--tools", "") or "").split(",")
    if "--json-schema" in sys.argv:
        tools.append("StructuredOutput")  # as the real CLI does
    if mode == "wrong_tools":
        tools = tools + ["WebFetch"]
    sid = arg("--session-id", "00000000-0000-4000-8000-000000000000")
    emit({"type": "system", "subtype": "init", "session_id": sid, "tools": tools, "mcp_servers": [],
          "slash_commands": [], "model": "claude-opus-fake", "permissionMode": arg("--permission-mode"),
          "claude_code_version": "0.0.0-fake", "cwd": os.getcwd()})
    if mode == "slow":
        time.sleep(60)
        return 0
    if mode == "usage_limit":
        emit({"type": "rate_limit_event",
              "rate_limit_info": {"status": "rejected", "resetsAt": 1900000000, "rateLimitType": "five_hour"}})
        emit({"type": "result", "subtype": "success", "is_error": True, "num_turns": 0,
              "result": "Claude usage limit reached. Your limit resets at 5pm.", "session_id": sid})
        return 1
    if mode == "max_turns":
        emit({"type": "result", "subtype": "error_max_turns", "is_error": True, "num_turns": 2, "session_id": sid})
        return 1
    text = "Building the crate now."
    if mode == "secret":
        text += " key " + "sk" + "-ant-" + "api03-" + "B" * 30
        text += " mail someone" + "@" + "corp.test path /" + "Users/someone/x"
    emit({"type": "assistant", "message": {"content": [
        {"type": "text", "text": text},
        {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "cargo +nightly-2025-05-13 build"}}]}})
    emit({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": "t1", "content": "Finished `dev` profile"}]}})
    emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": 2, "result": "done",
          "permission_denials": [], "session_id": sid,
          "structured_output": {"status": "done", "summary": "fake", "files_changed": [], "remaining_issues": []}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
