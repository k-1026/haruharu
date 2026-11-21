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
from 흐름 import 빠진_조건, 확정체류기간_정하기, 전달_준비, 전달_검사, 근거_경고_추출  # noqa: E402

결과2_정상 = """## 근거표
| ID | 항목 | 수치 |
|---|---|---|
| R01 | 숙박 | 59.5% |
| R02 | 음식 | 1.7% |

## 경고 (E3)
- [W1 간접 근거] 영어권은 미주로만 봅니다 (적용 근거: R01 · R02)
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

    def test_추출(self):
        r, w = 근거_경고_추출(결과2_정상)
        self.assertEqual(r, {"R01", "R02"})
        self.assertEqual(w, {"W1": {"R01", "R02"}})

    def test_정상_통과(self):
        전달 = 전달_준비(조건_정상, "1박2일", "경고를남기고진행", 결과2_정상, "기관 데이터: 없음")
        self.assertEqual(전달_검사(전달), [])
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
        전달 = json.loads((실행 / "3단계_전달_준비.json").read_text(encoding="utf-8"))
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
        self.assertTrue((실행 / "1단계_선택_1.json").exists())

    def test_2단계_조건_바꾸기(self):
        # 2단계 E3에서 조건 바꾸기 → 새 조건 → 1단계부터 다시
        실행, 호출 = self.돌리기(["1", "2", "1", "2", "1", "1", "2",
                                 "3", "2", "1", "2", "1", "1", "1"])
        self.assertEqual(len(호출), 4)
        self.assertIn("계절: 가을", 호출[2])

    def test_추천받기_미선택이면_전달_안함(self):
        실행, _ = self.돌리기(["1", "2", "1", "3", "1", "1", "1", "3"])
        전달 = json.loads((실행 / "3단계_전달_준비.json").read_text(encoding="utf-8"))
        self.assertTrue(any("미선택" in m for m in 전달["검사결과"]))


if __name__ == "__main__":
    unittest.main()
