"""Claude Code 훅 이벤트를 JSON Lines로 기록한다.

- 입력: Claude Code가 stdin으로 넘기는 JSON
- 출력: <프로젝트 루트>/.claude/hooks/logs/events.jsonl 에 한 줄씩 추가
- 각 줄에는 발생 시각(초 단위 epoch 숫자)과 원본 항목이 들어간다.
- tool_response는 내용이 길 수 있으므로 앞 600자만 남긴다.
- 훅이 Claude Code 동작을 막지 않도록 어떤 오류가 나도 종료 코드는 0이다.
"""

import json
import os
import sys
import time
from pathlib import Path

ROOT_ENV = "LOG_EVENT_PROJECT_ROOT"  # 프로젝트 루트를 지정하는 환경변수 (.claude/settings.json의 env에 설정)
MAX_TOOL_RESPONSE = 600


def project_root(payload: dict) -> Path:
    env_root = os.environ.get(ROOT_ENV)
    if env_root:
        return Path(env_root)
    return Path(payload.get("cwd") or os.getcwd())


def build_record(payload: dict) -> dict:
    record = {"timestamp": int(time.time())}
    record.update({k: v for k, v in payload.items() if k != "tool_response"})
    if "tool_response" in payload:
        response = payload["tool_response"]
        text = response if isinstance(response, str) else json.dumps(response, ensure_ascii=False)
        record["tool_response"] = text[:MAX_TOOL_RESPONSE]
    return record


def append_line(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"
    # 깨진 문자가 섞여도 저장이 멈추지 않도록 errors="replace"를 쓴다
    with path.open("a", encoding="utf-8", errors="replace") as f:
        f.write(line)


def main() -> int:
    # Windows 기본 인코딩(cp949) 대신 UTF-8 바이트로 입력을 읽는다
    raw = sys.stdin.buffer.read().decode("utf-8", errors="replace")
    try:
        payload = json.loads(raw) if raw.strip() else {}
        if not isinstance(payload, dict):
            payload = {"raw_input": str(payload)}
    except json.JSONDecodeError:
        payload = {"raw_input": raw[:MAX_TOOL_RESPONSE]}

    log_dir = project_root(payload) / ".claude" / "hooks" / "logs"
    try:
        append_line(log_dir / "events.jsonl", build_record(payload))
    except Exception as exc:  # 훅 실패가 Claude Code를 멈추지 않도록 오류만 남긴다
        try:
            append_line(log_dir / "errors.log", {"timestamp": int(time.time()), "error": repr(exc)})
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
