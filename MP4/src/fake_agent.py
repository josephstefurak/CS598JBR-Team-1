"""Scripted stand-in for agent B, used only by selftest drills against a copy of selftest_fixture.

The loop runs it through agent_runner exactly like `claude -p`: prompt on stdin, stream-json on stdout,
cwd = the workspace. It speaks the real event vocabulary, so isolation checks, the wall-clock kill and
outcome classification are exercised for real. A scenario JSON maps iteration -> attempt -> actions:

  {"variants_dir": "<dir>", "1": {"1": ["copy:broken", "sleep:30"]}, "2": {"1": ["copy:clean"]}}

Actions:
  copy:<variant>  copy <variants_dir>/<variant>/* into the workspace's src/
  noop            change nothing
  edit_test       append a line to the first test file under src/bin/ (an integrity violation)
  rate_limit      emit a rejected rate_limit_event (resets in 5 s) and a usage-limit error result
  auth_error      emit the CLI's lost-login error result (owner gate G2)
  overloaded      emit an API overloaded error result (owner gate G7)
  connection_error  emit a connection error result (owner gate G7)
  write:<path>    write a small file at <path>, relative to the workspace (owner gate G1)
  say:<text>      emit an assistant text event (leak-marker scan, owner gate G4)
  sleep:<s>       sleep (for wall-clock and SIGTERM drills)
Missing iterations or attempts mean noop. It refuses to run inside MP4/translations/.
"""
import argparse
import json
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mp4common as mc  # noqa: E402


def emit(ev):
    sys.stdout.write(json.dumps(ev) + "\n")
    sys.stdout.flush()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--iteration", type=int, required=True)
    ap.add_argument("--attempt", type=int, required=True)
    ap.add_argument("--tools", required=True)
    ap.add_argument("--permission-mode", required=True)
    ap.add_argument("--model", required=True)
    a = ap.parse_args()
    sys.stdin.read()
    cwd = os.path.abspath(os.getcwd())
    if cwd == mc.TRANSLATIONS_DIR or cwd.startswith(mc.TRANSLATIONS_DIR + os.sep):
        print("fake_agent refuses to run inside MP4/translations/", file=sys.stderr)
        return 2
    with open(a.scenario, encoding="utf-8") as fh:
        scenario = json.load(fh)
    actions = (scenario.get(str(a.iteration)) or {}).get(str(a.attempt)) or ["noop"]
    emit({"type": "system", "subtype": "init", "session_id": "fake-%d-%d" % (a.iteration, a.attempt),
          "tools": a.tools.split(",") + ["StructuredOutput"], "mcp_servers": [], "slash_commands": [],
          "model": "claude-%s-fake" % a.model, "permissionMode": a.permission_mode,
          "claude_code_version": "fake", "cwd": cwd})
    done = []
    for act in actions:
        kind, _, arg = act.partition(":")
        if kind == "copy":
            src = os.path.join(scenario["variants_dir"], arg)
            for name in os.listdir(src):
                shutil.copy2(os.path.join(src, name), os.path.join(cwd, "src", name))
        elif kind == "edit_test":
            bin_dir = os.path.join(cwd, "src", "bin")
            target = sorted(f for f in os.listdir(bin_dir) if f.endswith(".rs"))[0]
            with open(os.path.join(bin_dir, target), "a", encoding="utf-8") as fh:
                fh.write("\n// edited by the agent\n")
        elif kind == "rate_limit":
            emit({"type": "rate_limit_event", "rate_limit_info": {
                "status": "rejected", "resetsAt": int(time.time()) + 5, "rateLimitType": "five_hour"}})
            emit({"type": "result", "subtype": "success", "is_error": True, "num_turns": 0,
                  "result": "Claude usage limit reached; your limit resets soon.", "permission_denials": []})
            return 1
        elif kind in ("auth_error", "overloaded", "connection_error"):
            text = {"auth_error": "Failed to authenticate. API Error: 401 OAuth token has expired. Please run /login",
                    "overloaded": "API Error: 529 Overloaded",
                    "connection_error": "API Error: Connection error."}[kind]
            emit({"type": "result", "subtype": "success", "is_error": True, "num_turns": 0, "result": text,
                  "permission_denials": []})
            return 1
        elif kind == "write":
            path = os.path.normpath(os.path.join(cwd, arg))
            if os.path.isabs(arg) or not path.startswith(cwd + os.sep):
                print("write: path must stay inside the workspace: %r" % arg, file=sys.stderr)
                return 2
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write("written by the fake agent\n")
        elif kind == "say":
            emit({"type": "assistant", "message": {"model": "claude-%s-fake" % a.model, "content": [
                {"type": "text", "text": arg}]}})
        elif kind == "sleep":
            time.sleep(float(arg))
        elif kind != "noop":
            print("unknown action %r" % act, file=sys.stderr)
            return 2
        done.append(act)
    emit({"type": "assistant", "message": {"model": "claude-%s-fake" % a.model, "content": [
        {"type": "text", "text": "fake agent actions: %s" % ", ".join(done)}]}})
    emit({"type": "result", "subtype": "success", "is_error": False, "num_turns": 1, "result": "done",
          "permission_denials": [], "structured_output": {
              "status": "done", "summary": "fake: %s" % ", ".join(done), "files_changed": [],
              "remaining_issues": []}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
