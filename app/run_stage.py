"""단계 하나를 실행한다: 에이전트 지침을 설정한 AI 제공자에 전달한다.

에이전트 파일의 본문은 지시문이다. Read/Grep/Glob은 Gemini에서 제한된 조회 도구로 대응한다.
"""

import re
import asyncio
from pathlib import Path

from 설정 import 설정_읽기
from 제미나이자료 import 저장소도구

저장소 = Path(__file__).resolve().parent.parent  # haruharu/ (에이전트가 지침/ 과 research/ 를 읽는 기준)


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


기본_제한초 = 900  # 관리자 화면 3단계 제한(900초)과 맞춤. AI 한 번 호출을 기다리는 최대 시간. .env의 AI_TIMEOUT_SECONDS로 바꾼다


class AI응답시간초과(TimeoutError):
    """AI가 제한 시간 안에 답하지 않았다. 혼잡 재시도 대상이 아니다(같은 시간을 또 기다리지 않게)."""


def 제한초_읽기(config) -> int:
    값=(config.get('AI_TIMEOUT_SECONDS') or '').strip()
    if not 값:return 기본_제한초
    try:
        초=int(값)
    except ValueError:
        raise ValueError('AI_TIMEOUT_SECONDS는 초 단위 정수로 쓰세요 (예: 900).') from None
    if 초<=0:raise ValueError('AI_TIMEOUT_SECONDS는 1 이상이어야 합니다.')
    return 초


async def 단계_실행(에이전트_경로: str, 입력: str) -> str:
    """설정한 AI 제공자로 에이전트를 한 번 호출한다. 제한 시간을 넘기면 끊고 이유를 올린다."""
    본문, 도구 = 에이전트_읽기(에이전트_경로)
    config=설정_읽기(저장소)
    제한초=제한초_읽기(config)
    provider=(config.get('AI_PROVIDER') or 'claude').strip().lower()
    if provider=='gemini':
        key=(config.get('GEMINI_API_KEY') or '').strip()
        model=(config.get('GEMINI_MODEL') or '').strip()
        if not key:raise ValueError('GEMINI_API_KEY가 없습니다. 프로젝트 .env에 각자의 키를 넣으세요.')
        if not model:raise ValueError('GEMINI_MODEL을 .env에서 지정하세요.')
        일=_제미나이_실행(본문,입력,model,key,도구,제한초)
    elif provider=='claude':
        일=_클로드_실행(본문,입력,(config.get('CLAUDE_MODEL') or 'claude-sonnet-5-5').strip(),도구)
    else:
        raise ValueError('AI_PROVIDER는 gemini 또는 claude만 선택할 수 있습니다.')
    try:
        return await asyncio.wait_for(일,timeout=제한초)
    except asyncio.TimeoutError:
        raise AI응답시간초과(
            f'AI({provider})가 {제한초}초 동안 응답하지 않아 중단했습니다. '
            '인터넷 연결과 AI 로그인·키를 확인한 뒤 다시 실행하세요. '
            '더 오래 기다려야 하는 단계라면 .env의 AI_TIMEOUT_SECONDS를 늘리세요.'
        ) from None


async def _클로드_실행(본문,입력,model,도구):
    from claude_agent_sdk import AssistantMessage, ClaudeAgentOptions, TextBlock, query
    옵션 = ClaudeAgentOptions(
        model=model,
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


async def _제미나이_실행(본문,입력,model,key,도구,제한초=기본_제한초):
    try:
        from google import genai
        from google.genai import types
    except ImportError as error:
        raise RuntimeError('Gemini SDK가 없습니다. app/requirements.txt의 패키지를 설치하세요.') from error
    available={'Read':0,'Grep':1,'Glob':2}
    file_tools=저장소도구(저장소)
    tools=[file_tools[available[name]] for name in 도구 if name in available]
    options=types.GenerateContentConfig(
        system_instruction=본문,
        tools=tools or None,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(maximum_remote_calls=21) if tools else None,
    )
    # 스레드 안의 요청은 바깥에서 끊을 수 없다. 통신 자체에도 제한을 걸어야 asyncio.run이 스레드를 끝없이 기다리지 않는다
    client=genai.Client(api_key=key,http_options=types.HttpOptions(timeout=제한초*1000))
    try:
        response=await asyncio.to_thread(client.models.generate_content,model=model,contents=입력,config=options)
    finally:
        client.close()
    if not response.text:raise ValueError('Gemini가 텍스트 결과를 반환하지 않았습니다. 원본·사용량은 별도 확인이 필요합니다.')
    return response.text.strip()
