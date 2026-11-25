"""지침이 캐릭터 이름을 포롱이(너구리)·여울이(족제비)로 바꿔도 그림이 맞게 나온다. AI 호출 없음."""
import unittest

import 산출물


class 캐릭터이름시험(unittest.TestCase):
    def test_새이름과_옛이름을_같은_캐릭터로_본다(self):
        for 이름, 기대 in [('포롱이', '너구리'), ('너구리', '너구리'), ('raccoon', '너구리'),
                         ('여울이', '족제비'), ('족제비', '족제비'), ('weasel', '족제비'), ('동등', None), ('', None)]:
            with self.subTest(이름=이름):
                self.assertEqual(산출물.캐릭터(이름), 기대)

    def test_주연이_여울이면_족제비_그림이_앞에_선다(self):
        html = 산출물._장면html({'문구': {'제목': '골목', '본문': '걸어요', '말풍선': {'포롱이': '와!', '여울이': '1907년'}},
                                 '시안': {'주연': '여울이'}, '시간칸': '낮', '번역': [], '장면ID': '낮-1',
                                 '장소': '근대골목'}, 'A')
        self.assertIn('lead weasel', html)
        self.assertIn('side raccoon', html)
        self.assertIn('포롱이', html)   # 말풍선에는 AI가 쓴 이름을 그대로 보여 준다


if __name__ == '__main__':
    unittest.main()
