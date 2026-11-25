import unittest
from 시간표검사 import 시간표_검사
from 관리자실행 import 조건_검사
import test_관리자실행 as fixtures


def row(day,time,slot='낮',stay=90,plan='공통'):
    return {'안':plan,'칸ID':f'{day}-{time}-{slot}','일차':day,'시간칸':slot,'장소명':'시험 장소',
            '시각':{'값':time,'종류':'가정'},'머무는시간':stay}


class 시간검사시험(unittest.TestCase):
    def test_종료일차미정이라도_머무는시간_초과는_조건부참고(self):
        r=시간표_검사({'칸목록':[row(1,'21:34','밤',90)]},{'종료시각':'21:34'},'1박2일')
        self.assertTrue(any('머무는 시간' in x for x in r['일차미정참고']))

    def test_다음날종료면_첫날20시는_종료후아님(self):
        c={'시작일차':1,'시작시각':'11:34','종료일차':2,'종료시각':'18:34'}
        r=시간표_검사({'칸목록':[row(1,'10:00'),row(1,'20:00','밤')]},c,'1박2일')
        self.assertTrue(any('시작 전' in x and '10:00' in x for x in r['충돌']))
        self.assertFalse(any('종료 후' in x for x in r['충돌']))

    def test_같은날종료면_20시는_충돌(self):
        r=시간표_검사({'칸목록':[row(1,'20:00','밤')]},{'시작일차':1,'시작시각':'11:34','종료일차':1,'종료시각':'18:34'},'1박2일')
        self.assertTrue(any('종료 후' in x for x in r['충돌']))

    def test_시작은안이지만_머무는시간이_종료넘음(self):
        r=시간표_검사({'칸목록':[row(2,'18:00',stay=60)]},{'시작일차':1,'시작시각':'10:00','종료일차':2,'종료시각':'18:34'},'1박2일')
        self.assertTrue(any('종료 시각을 넘' in x for x in r['충돌']))

    def test_이전자료_일차는_추측하지않고_조건부검사(self):
        r=시간표_검사({'칸목록':[row(1,'10:00'),row(1,'20:00','밤')]},{'시작시각':'11:34','종료시각':'18:34'},'1박2일')
        self.assertFalse(r['충돌'])
        self.assertTrue(any('시작 일차' in x for x in r['확인대기']))
        self.assertTrue(any('1일차' in x and '20:00' in x for x in r['일차미정참고']))

    def test_서로다른안은_겹침으로_판정안함(self):
        r=시간표_검사({'칸목록':[row(1,'10:00',plan='A'),row(1,'10:00',plan='B')]},{},'1박2일')
        self.assertFalse(r['충돌'])

    def test_같은안의_겹치는일정(self):
        r=시간표_검사({'칸목록':[row(1,'10:00',stay=90),row(1,'11:00',stay=60)]},{},'1박2일')
        self.assertTrue(any('일정 겹침' in x for x in r['충돌']))

    def test_미정시각은_통과로_추정안함(self):
        r=시간표_검사({'칸목록':[row(2,'',stay='미확인')]},{},'1박2일')
        self.assertTrue(any('시각 미정' in x for x in r['확인대기']))

    def test_일차입력과_역전조건_검사(self):
        c=fixtures.코스조건();c.update({'시작일차':2,'시작시각':'18:00','종료일차':1,'종료시각':'19:00'})
        with self.assertRaises(ValueError):조건_검사(c,'1박2일')
        c.update({'시작일차':1,'종료일차':2})
        self.assertEqual(조건_검사(c,'1박2일')['종료일차'],2)
        with self.assertRaises(ValueError):조건_검사(c,'당일')


if __name__=='__main__':unittest.main()
