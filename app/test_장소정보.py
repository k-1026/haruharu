import copy
import unittest
from 장소정보 import 장소목록, 장소찾기, 운영정보_제안
from 운영검토 import 화면정보, 검토입력_검사, 검토_반영, 준비_검사
from test_운영검토 import example


class 장소정보시험(unittest.TestCase):
    def test_입구미확정이어도_검토된_대표위치를_찾는다(self):
        from 장소정보 import 대표위치
        for name in ['근대골목 (대구광역시 중구)','대구광역시 중구 서문시장','서문시장 야시장',
                     '식사 방식 미선택 · 권역 후보: 대구광역시 중구 서문시장',
                     '평화시장 닭똥집골목 (대구광역시 동구) — 운영시간 자료 없음']:
            with self.subTest(name=name):
                row=대표위치(name)
                self.assertIsNotNone(row)
                self.assertEqual(len(row['중심']),2)
                self.assertTrue(row['근거URL'].startswith('https://'))
                self.assertIn('대표',row['설명'])
                self.assertFalse(row['입구확인'])

    def test_숙소는_명시된_권역만_표시한다(self):
        from 장소정보 import 대표위치
        row=대표위치('숙소 (중구 동성로 일대 호텔 후보 권역, 업체 미고정)',시간칸='숙박')
        self.assertEqual(row['이름'],'동성로')
        for name in ['숙소 (중구·동구 권역 미정)','숙소 (동구, 업체 미고정)','없는 서문시장 가게','서문시장과 평화시장 중 미선택']:
            self.assertIsNone(대표위치(name,시간칸='숙박'))
    def test_실제자료와_이동기준점_검색(self):
        rows=장소목록()
        self.assertTrue(any(r['장소명']=='동대구역' for r in rows))
        self.assertTrue(any(r['장소명']=='서문시장 야시장' for r in rows))
        self.assertEqual(장소찾기('대구광역시 중구 서문시장 권역')['장소명'],'서문시장')
        self.assertEqual(장소찾기('자유식 · 대구광역시 중구 서문시장 권역')['장소명'],'서문시장')
        self.assertIsNone(장소찾기('존재하지 않는 서문시장 가게'))
        self.assertNotEqual(장소찾기('서문시장')['장소명'],장소찾기('서문시장 야시장')['장소명'])

    def test_운영자료는_시각만_제안하고_사람확인은_만들지않음(self):
        row=운영정보_제안('봉산찜갈비')
        self.assertEqual(row['영업종료'],'21:00')
        self.assertEqual(row['마감시각'],'20:30')
        self.assertFalse(row['방문일운영확인'])
        self.assertEqual(row['확인일'],'2026-11-18')
        self.assertEqual(운영정보_제안('향촌문화관')['영업시작'],'')

    def test_화면에_기존확인_우선하고_충돌누락_안내(self):
        c,s,d=example();c['칸목록'][0].update({'장소명':'봉산찜갈비','시각':{'값':'20:45','종류':'가정'}})
        before=copy.deepcopy(c);info=화면정보(c,s)
        op=info['운영대상'][0]
        self.assertEqual(op['입력값']['영업종료'],'21:00')
        self.assertTrue(any('영업시간' in x or '마감' in x for x in op['확인필요']))
        c['운영검토기록']={'운영확인':[dict(d['운영확인'][0],대상명='봉산찜갈비',영업종료='23:00')]}
        self.assertEqual(화면정보(c,s)['운영대상'][0]['입력값']['영업종료'],'23:00')
        self.assertNotIn('운영검토기록',before)

    def test_상시기획은_날짜없이저장하고_날짜검증완료로바꾸지않음(self):
        c,s,d=example();d.update({'운영기준':'상시기획','운영조건':'금·토 출발 / 동계 별도 확인','방문시작일':''})
        checked=검토입력_검사(d,c,s)
        self.assertEqual(checked['운영조건'],d['운영조건'])
        self.assertEqual(checked['운영기준'],'상시기획')
        # 상시 상품은 출발일 대신 정기휴무로 요일을 계산한다. 휴무 자료가 없으면 자동 통과하지 않는다.
        self.assertTrue(any('출발 가능 요일' in x for x in 준비_검사(검토_반영(c,checked),s,checked)['확인필요']))

    def test_좌표는_빈칸이면_None_값있으면_실수쌍(self):
        from unittest import mock
        import 장소정보
        rows=[{'장소명':'김광석길','위도':'35.86','경도':'128.6'},{'장소명':'근대골목','위도':'','경도':''}]
        with mock.patch.object(장소정보,'장소목록',return_value=rows):
            self.assertEqual(장소정보.좌표('대구광역시 중구 김광석길'),(35.86,128.6))
            self.assertIsNone(장소정보.좌표('근대골목'))
            self.assertIsNone(장소정보.좌표('없는 장소'))


if __name__=='__main__':unittest.main()
