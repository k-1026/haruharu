"""
서브에이전트가 시작하고 끝날 때 run_log.jsonl에 자동으로 한 줄씩 기록한다.
에이전트가 직접 기록하지 않아도 로그가 남도록 하는 장치다 (SubagentStart / SubagentStop 훅).

입력: Claude Code가 stdin으로 넘기는 JSON
  - hook_event_name: "SubagentStart" 또는 "SubagentStop"
  - agent_type: 에이전트 이름 (researcher, model-simulator, competitor-analyzer, reviewer 등)
  - cwd: 프로젝트 폴더 (run_log.jsonl 위치)
  - last_assistant_message: 끝날 때 에이전트의 마지막 답변 (SubagentStop에서만 있음)
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))


def main():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # 입력이 없거나 깨졌으면 아무것도 하지 않는다 (작업을 막지 않음)

    event = data.get("hook_event_name", "")
    agent = data.get("agent_type") or "unknown"
    cwd = data.get("cwd") or os.getcwd()

    if event == "SubagentStart":
        status = "진행중"
        reason = None
    elif event == "SubagentStop":
        # 종료는 완료로 기록한다. 실패·보류 같은 세부 판정은 에이전트가 직접 쓰는 줄에서 한다.
        status = "완료"
        reason = None
    else:
        return 0

    entry = {
        "time": datetime.now(KST).isoformat(timespec="seconds"),
        "step": "(자동 기록)",
        "agent": agent,
        "goal": "서브에이전트 " + ("시작" if event == "SubagentStart" else "종료"),
        "status": status,
    }
    if reason:
        entry["reason"] = reason

    path = os.path.join(cwd, "run_log.jsonl")
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
