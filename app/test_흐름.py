"""1 → 2단계 흐름 시험. 에이전트는 호출하지 않는다 (가짜 결과로 대신).

사용: app 폴더에서  python -m unittest test_흐름 -v
"""

import asyncio
import json
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

# claude_agent_sdk가 없어도 orchestrator를 불러올 수 있게 빈 모듈을 끼운다
sys.modules.setdefault("claude_agent_sdk", types.SimpleNamespace(
    AssistantMessage=object, ClaudeAgentOptions=object, TextBlock=object, query=None))

import orchestrator  # noqa: E402
from 흐름 import 빠진_조건, 확정체류기간_정하기, 전달_준비, 전달_검사, 근거표_읽기, 경고_읽기  # noqa: E402

결과2_정상 = """## 수요 분석 요약
- 숙박: 1박 59.5% (KOSIS 2024, n=1,010)

## 근거표
| ID | 항목 | 원자료 항목명 | 수치 | 파일 · 행 위치 | 출처 | 연도 | 표본 · 대상 | 한계 | 경고 |
|---|---|---|---|---|---|---|---|---|---|
| R01 | 숙박 | 전체 / 1박 | 59.5% | 외국인/대구_외국인숙박기간_2024.csv, category=전체 | KOSIS | 2024 | n=1,010 | 대구 전체 | W1 |
| R02 | 음식 | 닭튀김/치킨 | 1.7% | 외국인/대구_외국인추천음식상위20_2024.csv, item=닭튀김/치킨 | KOSIS | 2024 | n=1,010 | [자료 필요: 구 구분] | W1 |

## 경고 (E3)
- [W1 간접 근거] 구 구분이 없습니다 (적용 근거: R01 · R02)
"""

조건_정상 = {"계절": "봄", "언어권": ["일본어"], "지역": ["중구"], "체류기간": "1박2일"}


class 순수함수(unittest.TestCase):
    def test_지역이_비면_누락(self):
        self.assertEqual(빠진_조건({**조건_정상, "지역": []}), ["지역"])

    def test_모두_있으면_누락없음(self):
        self.assertEqual(빠진_조건(조건_정상), [])

    def test_추천받기_미선택(self):
        self.assertEqual(확정체류기간_정하기({**조건_정상, "체류기간": "추천받기"}, None), "미선택")

    def test_추천받기_선택(self):
        self.assertEqual(확정체류기간_정하기({**조건_정상, "체류기간": "추천받기"}, "당일"), "당일")

    def test_근거표_구조화(self):
        행 = 근거표_읽기(결과2_정상)
        self.assertEqual([r["근거ID"] for r in 행], ["R01", "R02"])
        self.assertEqual(행[0]["수치"], 59.5)
        self.assertEqual(행[1]["원자료항목명"], "닭튀김/치킨")
        self.assertIn("파일_행위치", 행[0])

    def test_경고_읽기(self):
        self.assertEqual(경고_읽기(결과2_정상)[0]["적용근거ID"], ["R01", "R02"])

    def 검사(self, 글):
        return 전달_검사(전달_준비(조건_정상, "1박2일", "경고를남기고진행", 글, ""))

    def test_적용근거_없는_경고도_잡음(self):
        글 = 결과2_정상.replace(" (적용 근거: R01 · R02)", "")
        self.assertTrue(any("W1" in m and "연결 누락" in m for m in self.검사(글)))

    def test_근거ID_중복(self):
        글 = 결과2_정상.replace("| R02 |", "| R01 |")
        self.assertTrue(any("근거 ID 중복: R01" in m for m in self.검사(글)))

    def test_경고ID_중복(self):
        글 = 결과2_정상 + "- [W1 기간 다름] 다른 경고 (적용 근거: R01)\n"
        self.assertTrue(any("경고 ID 중복: W1" in m for m in self.검사(글)))

    def test_미확인사항_구조화(self):
        전달 = 전달_준비(조건_정상, "1박2일", "경고를남기고진행", 결과2_정상, "기관 데이터: 없음")
        self.assertIn("기관 데이터 없음", 전달["미확인사항"])
        self.assertTrue(any("자료 필요" in m for m in 전달["미확인사항"]))
        self.assertIn("59.5%", 전달["요약"])

    def test_정상_통과(self):
        전달 = 전달_준비(조건_정상, "1박2일", "경고를남기고진행", 결과2_정상, "기관 데이터: 없음")
        self.assertEqual(전달_검사(전달), [])
        self.assertEqual(len(전달["근거목록"]), 2)
        self.assertEqual(전달["조건"]["지역"], ["중구"])

    def test_체류기간_미선택_막음(self):
        전달 = 전달_준비({**조건_정상, "체류기간": "추천받기"}, "미선택", "경고를남기고진행", 결과2_정상, "")
        self.assertTrue(any("미선택" in m for m in 전달_검사(전달)))

    def test_없는_근거를_가리키는_경고(self):
        글 = 결과2_정상.replace("R01 · R02", "R01 · R09")
        전달 = 전달_준비(조건_정상, "1박2일", "경고를남기고진행", 글, "")
        self.assertTrue(any("R09" in m for m in 전달_검사(전달)))


class 흐름시험(unittest.TestCase):
    """input과 에이전트 호출을 가짜로 바꿔 orchestrator.메인을 끝까지 돌린다."""

    def 돌리기(self, 답들: list[str]) -> tuple[Path, list[str]]:
        호출 = []

        async def 가짜_실행(에이전트, 입력):
            호출.append(입력)
            return "1단계 결과" if "기획조건" in 에이전트 else 결과2_정상

        폴더 = Path(tempfile.mkdtemp())
        with mock.patch.object(orchestrator, "단계_실행", 가짜_실행), \
             mock.patch.object(orchestrator, "실행_폴더_기준", 폴더), \
             mock.patch("builtins.input", side_effect=답들), \
             mock.patch("builtins.print"):
            asyncio.run(orchestrator.메인())
        return next(폴더.iterdir()), 호출

    def test_정상_진행(self):
        # 계절 봄, 언어권 일본어, 지역 중구, 1박2일 → 1단계 진행 → 기관 없음 → E3 진행
        실행, 호출 = self.돌리기(["1", "2", "1", "2", "1", "1", "1"])
        전달 = json.loads(next(실행.rglob("3단계_전달_준비.json")).read_text(encoding="utf-8"))
        self.assertEqual(전달["검사결과"], ["통과"])
        self.assertEqual(전달["확정체류기간"], "1박2일")
        self.assertEqual(len(호출), 2)

    def test_지역_누락이면_다시_받음(self):
        # 지역을 비움 → 다시 지역만 물음 → 동구
        실행, 호출 = self.돌리기(["1", "2", "", "2", "2", "1", "1", "1"])
        self.assertIn("지역: 동구", 호출[0])

    def test_1단계_조건_바꾸기(self):
        # 1단계에서 조건 바꾸기 → 새 조건(여름) → 다시 1단계 → 진행
        실행, 호출 = self.돌리기(["1", "2", "1", "2", "2", "2", "2", "1", "2", "1", "1", "1"])
        self.assertIn("계절: 여름", 호출[1])
        self.assertTrue((실행 / "01회차" / "1단계_선택.json").exists())
        self.assertTrue((실행 / "02회차" / "1단계_결과.md").exists())

    def test_2단계_조건_바꾸기(self):
        # 2단계 E3에서 조건 바꾸기 → 새 조건 → 1단계부터 다시
        실행, 호출 = self.돌리기(["1", "2", "1", "2", "1", "1", "2",
                                 "3", "2", "1", "2", "1", "1", "1"])
        self.assertEqual(len(호출), 4)
        self.assertIn("계절: 가을", 호출[2])
        self.assertTrue((실행 / "01회차" / "2단계_결과.md").exists())
        self.assertTrue((실행 / "02회차" / "2단계_결과.md").exists())

    def test_추천받기_미선택이면_전달_안함(self):
        실행, _ = self.돌리기(["1", "2", "1", "3", "1", "1", "1", "3"])
        전달 = json.loads(next(실행.rglob("3단계_전달_준비.json")).read_text(encoding="utf-8"))
        self.assertTrue(any("미선택" in m for m in 전달["검사결과"]))


if __name__ == "__main__":
    unittest.main()
