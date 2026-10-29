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
