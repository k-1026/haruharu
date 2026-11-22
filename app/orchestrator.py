"""오케스트레이터: 순서를 지키고, 담당자 선택을 받고, 앞 단계 결과를 다음 단계에 넘긴다.

지금은 1단계 -> 2단계 -> 3단계 전달 준비(검사)까지. 실제 3단계 호출은 3단계 담당과
전달 형식을 맞춘 뒤 연결한다 (지침/공통/단계_넘김.md 4장).
사용: python orchestrator.py
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from run_stage import 단계_실행
from stages import STAGES
from upload import 파일_받기
from 흐름 import (
    계절_선택지,
    언어권_선택지,
    지역_선택지,
    체류기간_선택지,
    확정체류기간_선택지,
    빠진_조건,
    조건_문장,
    확정체류기간_정하기,
    전달_준비,
    전달_검사,
)

실행_폴더_기준 = Path(__file__).resolve().parent / "runs"


def 묻기(질문: str, 선택지: list[str]) -> int:
    """번호로 고르게 한다. 고른 번호(1부터)를 돌려준다."""
    print(f"\n{질문}")
    for i, 문구 in enumerate(선택지, 1):
        print(f"  {i}. {문구}")
    while True:
        답 = input("번호: ").strip()
        if 답.isdigit() and 1 <= int(답) <= len(선택지):
            return int(답)
        print("목록에 있는 번호를 입력하세요.")


def 여러개_묻기(질문: str, 선택지: list[str]) -> list[str]:
    """쉼표로 여러 번호를 고르게 한다. 비우면 빈 목록 (기본값 없음)."""
    print(f"\n{질문} (여러 개는 쉼표로, 예: 1,2)")
    for i, 문구 in enumerate(선택지, 1):
        print(f"  {i}. {문구}")
    while True:
        답 = input("번호: ").strip()
        if not 답:
            return []
        번호 = [s.strip() for s in 답.split(",")]
        if all(n.isdigit() and 1 <= int(n) <= len(선택지) for n in 번호):
            return list(dict.fromkeys(선택지[int(n) - 1] for n in 번호))
        print("목록에 있는 번호를 입력하세요.")


def 하나_묻기_빈값허용(질문: str, 선택지: list[str]) -> str:
    print(f"\n{질문}")
    for i, 문구 in enumerate(선택지, 1):
        print(f"  {i}. {문구}")
    while True:
        답 = input("번호 (모르면 엔터): ").strip()
        if not 답:
            return ""
        if 답.isdigit() and 1 <= int(답) <= len(선택지):
            return 선택지[int(답) - 1]
        print("목록에 있는 번호를 입력하세요.")


def 조건_입력(이전: dict | None = None) -> dict:
    """조건을 받는다. 빠진 조건은 그 조건만 다시 묻는다. 지역 기본값은 넣지 않는다."""
    조건 = dict(이전 or {})
    묻는법 = {
        "계절": lambda: 하나_묻기_빈값허용("계절을 고르세요", 계절_선택지),
        "언어권": lambda: 여러개_묻기("대상 언어권을 고르세요", 언어권_선택지),
        "지역": lambda: 여러개_묻기("지역을 고르세요 (기본값 없음)", 지역_선택지),
        "체류기간": lambda: 하나_묻기_빈값허용("체류 기간을 고르세요", 체류기간_선택지),
    }
    for 이름 in 묻는법:
        if 이름 not in 조건:
            조건[이름] = 묻는법[이름]()
    while 빠짐 := 빠진_조건(조건):
        print("\n빠진 조건이 있습니다: " + ", ".join(빠짐) + ". 다른 일은 하지 않고 이 조건만 다시 받습니다.")
        for 이름 in 빠짐:
            조건[이름] = 묻는법[이름]()
    return 조건


def 저장(실행: Path, 이름: str, 내용: str) -> None:
    실행.mkdir(parents=True, exist_ok=True)
    (실행 / 이름).write_text(내용, encoding="utf-8")


def 저장_json(실행: Path, 이름: str, 값: dict) -> None:
    저장(실행, 이름, json.dumps(값, ensure_ascii=False, indent=2))


async def 일단계(폴더: Path, 조건: dict) -> tuple[bool, str]:
    """1단계를 한 번 실행한다. (진행 여부, 결과)를 돌려준다."""
    print(f"\n[1단계 {STAGES[1]['이름']}] 실행 중...")
    결과1 = await 단계_실행(STAGES[1]["에이전트"], "조건: " + 조건_문장(조건))
    저장(폴더, "1단계_결과.md", 결과1)
    print("\n" + 결과1)
    선택 = 묻기("1단계 알림을 어떻게 할까요?", ["알림을 남기고 진행", "조건 바꾸기 (조건 입력으로)"])
    저장_json(폴더, "1단계_선택.json", {"조건": 조건, "담당자선택": ["알림을남기고진행", "조건바꾸기"][선택 - 1]})
    return 선택 == 1, 결과1


def 기관데이터_받기(실행: Path) -> str:
    기관 = 묻기("기관 데이터가 있나요?", ["없음 (우리 자료만 사용)", "있음 (CSV · XLSX 파일 올리기)"])
    if 기관 == 1:
        return "기관 데이터: 없음"
    while True:
        경로 = input("파일 경로 (CSV 또는 XLSX): ")
        try:
            csv목록 = 파일_받기(경로, 실행)
            break
        except ValueError as 오류:
            print(오류)
    출처 = input("출처 (기관 · 조사 이름, 모르면 엔터): ").strip() or "미확인"
    기간 = input("기간 (모르면 엔터): ").strip() or "미확인"
    대상 = input("대상 (모르면 엔터): ").strip() or "미확인"
    지역 = input("지역 (모르면 엔터): ").strip() or "미확인"
    단위 = input("단위 (모르면 엔터): ").strip() or "미확인"
    return (
        "기관 데이터: 있음\n"
        + "파일(CSV): " + ", ".join(str(p) for p in csv목록)
        + f"\n담당자가 적은 것: 출처 {출처} · 기간 {기간} · 대상 {대상} · 지역 {지역} · 단위 {단위}"
        + "\n지침/2_수요근거/입력_형식.md 5장대로 읽은 내용을 먼저 보이고, 담당자 확인 전에는 근거표에 넣지 않는다."
    )


async def 메인() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    실행 = 실행_폴더_기준 / datetime.now().strftime("%Y%m%d_%H%M%S")
    print("== 담당자용 체류 기획 에이전트 ==")

    # 조건을 바꿀 때마다 새 회차 폴더(01회차, 02회차 …)에 저장한다. 이전 회차 파일은 덮어쓰지 않는다.
    조건 = 조건_입력()
    회차 = 0
    while True:
        회차 += 1
        폴더 = 실행 / f"{회차:02d}회차"
        진행, 결과1 = await 일단계(폴더, 조건)
        if not 진행:
            조건 = 조건_입력()
            continue

        기관_안내 = 기관데이터_받기(폴더)
        입력2 = "1단계 결과:\n" + 결과1 + "\n\n담당자 선택: 알림을 남기고 진행\n" + 기관_안내
        print(f"\n[2단계 {STAGES[2]['이름']}] 실행 중...")
        결과2 = await 단계_실행(STAGES[2]["에이전트"], 입력2)
        저장(폴더, "2단계_결과.md", 결과2)
        print("\n" + 결과2)

        선택 = 묻기("2단계 경고를 어떻게 할까요? (E3)", ["경고를 남기고 진행", "조건 바꾸기 (1단계로)"])
        if 선택 == 2:
            저장_json(폴더, "2단계_선택.json", {"담당자선택_E3": "조건바꾸기"})
            조건 = 조건_입력()
            continue
        break

    고른값 = None
    if 조건["체류기간"] == "추천받기":
        n = 묻기("최종 체류 기간을 고르세요 (2단계 추천 참고)", 확정체류기간_선택지 + ["아직 정하지 않음"])
        고른값 = 확정체류기간_선택지[n - 1] if n <= len(확정체류기간_선택지) else None
    확정 = 확정체류기간_정하기(조건, 고른값)
    저장_json(폴더, "2단계_선택.json", {"담당자선택_E3": "경고를남기고진행", "확정체류기간": 확정})

    전달 = 전달_준비(조건, 확정, "경고를남기고진행", 결과2, 기관_안내)
    문제 = 전달_검사(전달)
    전달["검사결과"] = 문제 or ["통과"]
    저장_json(폴더, "3단계_전달_준비.json", 전달)
    if 문제:
        print("\n3단계로 넘길 수 없습니다:\n- " + "\n- ".join(문제))
    else:
        print("\n3단계 전달 준비 완료 (실제 3단계 호출은 형식 합의 후 연결).")
    print(f"\n결과 저장 위치: {실행}")


if __name__ == "__main__":
    asyncio.run(메인())
