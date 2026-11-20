"""단계 하나를 실행한다: 에이전트 파일을 지시문으로 넣고 Claude Agent SDK로 한 번 호출한다.

에이전트 파일 맨 위 --- 구간(name, description, tools)은 Claude Code용 설정이다.
여기서는 본문을 지시문으로 쓰고, tools 값은 읽어서 SDK 옵션에 넘긴다.
"""

import re
from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query

저장소 = Path(__file__).resolve().parent.parent  # haruharu/ (에이전트가 지침/ 과 research/ 를 읽는 기준)
모델 = "claude-sonnet-5-5"


def 에이전트_읽기(상대경로: str) -> tuple[str, list[str]]:
    """에이전트 파일에서 (본문, 도구 목록)을 꺼낸다."""
    글 = (저장소 / 상대경로).read_text(encoding="utf-8")
    맞음 = re.match(r"^---\n(.*?)\n---\n(.*)$", 글, re.S)
    if not 맞음:
        return 글, ["Read", "Grep", "Glob"]
    머리, 본문 = 맞음.groups()
    도구줄 = re.search(r"^tools:\s*(.+)$", 머리, re.M)
    도구 = [t.strip() for t in 도구줄.group(1).split(",")] if 도구줄 else ["Read", "Grep", "Glob"]
    return 본문.strip(), 도구


async def 단계_실행(에이전트_경로: str, 입력: str) -> str:
    """에이전트를 한 번 호출해 결과 텍스트를 돌려준다."""
    본문, 도구 = 에이전트_읽기(에이전트_경로)
    옵션 = ClaudeAgentOptions(
        model=모델,
        system_prompt=본문,
        tools=도구,
        allowed_tools=도구,
        cwd=str(저장소),
        max_turns=40,
        setting_sources=[],  # CLAUDE.md 등 프로젝트 설정은 읽지 않는다. 규칙은 지침/ 에서만 읽는다
    )
    조각: list[str] = []
    async for 메시지 in query(prompt=입력, options=옵션):
        if isinstance(메시지, AssistantMessage):
            for 블록 in 메시지.content:
                if isinstance(블록, TextBlock):
                    조각.append(블록.text)
    return "\n".join(조각).strip()
