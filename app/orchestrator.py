"""오케스트레이터: 순서를 지키고, 담당자 선택을 받고, 앞 단계 결과를 다음 단계에 넘긴다.

지금은 1단계 -> 2단계까지 연결했다. 3 · 4단계는 stages.py에 추가되면 이어 붙인다.
사용: python orchestrator.py
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from run_stage import 단계_실행
from stages import STAGES
from upload import 파일_받기

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


def 저장(실행: Path, 단계: int, 내용: str) -> None:
    실행.mkdir(parents=True, exist_ok=True)
    (실행 / f"{단계}단계_결과.md").write_text(내용, encoding="utf-8")


async def 메인() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    실행 = 실행_폴더_기준 / datetime.now().strftime("%Y%m%d_%H%M%S")

    print("== 담당자용 체류 기획 에이전트 ==")
    while True:
        # 1단계: 조건 입력 -> 자료 확인
        조건 = input("\n조건을 입력하세요 (예: 봄 · 일본어 · 중구 · 1박2일): ").strip()
        print(f"\n[1단계 {STAGES[1]['이름']}] 실행 중...")
        결과1 = await 단계_실행(STAGES[1]["에이전트"], f"조건: {조건}")
        저장(실행, 1, 결과1)
        print("\n" + 결과1)

        선택 = 묻기("1단계 알림을 어떻게 할까요?", ["알림을 남기고 진행", "조건 바꾸기 (처음으로)"])
        if 선택 == 1:
            break

    # 2단계: 수요 근거
    기관 = 묻기("기관 데이터가 있나요?", ["없음 (우리 자료만 사용)", "있음 (CSV · XLSX 파일 올리기)"])
    기관_안내 = "기관 데이터: 없음"
    if 기관 == 2:
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
        기관_안내 = (
            "기관 데이터: 있음\n"
            + "파일(CSV): " + ", ".join(str(p) for p in csv목록)
            + f"\n담당자가 적은 것: 출처 {출처} · 기간 {기간} · 대상 {대상} · 지역 {지역} · 단위 {단위}"
            + "\n지침/2_수요근거/입력_형식.md 5장대로 읽은 내용을 먼저 보이고, 담당자 확인 전에는 근거표에 넣지 않는다."
        )
    입력2 = (
        "1단계 결과:\n" + 결과1
        + "\n\n담당자 선택: 알림을 남기고 진행\n" + 기관_안내
    )
    print(f"\n[2단계 {STAGES[2]['이름']}] 실행 중...")
    결과2 = await 단계_실행(STAGES[2]["에이전트"], 입력2)
    저장(실행, 2, 결과2)
    print("\n" + 결과2)

    묻기("2단계 경고를 어떻게 할까요?", ["경고를 남기고 진행 (3단계는 아직 연결 전)", "종료"])
    print(f"\n결과 저장 위치: {실행}")


if __name__ == "__main__":
    asyncio.run(메인())
