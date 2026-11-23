import copy
import unittest
from 운영검토 import 검토입력_검사, 검토_반영, 준비_검사, 화면정보


def example():
    source={'확정체류기간':'1박2일','코스작성조건':{'시작일차':1,'종료일차':2,'시작지점':'장소A','종료지점':'장소B',
           '시작시각':'10:00','종료시각':'11:00','2일차오전구성':'자유시간'}}
    course={'코스시작종료':copy.deepcopy(source['코스작성조건']),'2일차오전구성':'자유시간',
            '칸목록':[{'안':'공통','칸ID':'관광','일차':1,'시간칸':'낮','장소명':'장소A','시각':{'값':'10:00','종류':'가정'},'머무는시간':60},
                    {'안':'공통','칸ID':'숙박','일차':1,'시간칸':'숙박','장소명':'숙박 권역','시각':{'값':'22:00','종류':'가정'},'머무는시간':600},
                    {'안':'공통','칸ID':'자유','일차':2,'시간칸':'2일차오전','장소명':'자유시간','시각':{'값':'08:00','종류':'가정'},'머무는시간':120}],
            '식사목록':[], '미확인사항':[], '확정조건':{'겹침처리':True},'남은경고':[]}
    data={'방문시작일':'2026-11-25','일정확인':[], '운영확인':[], '겹침처리':'노선겹침없음','겹침메모':'기존 상품 목록과 동선을 대조함', '담당자최종확인':True}
    for r in course['칸목록']:
        key=r['칸ID'];end={'관광':(1,'11:00'),'숙박':(2,'08:00'),'자유':(2,'10:00')}[key]
        data['일정확인'].append({'안':'공통','칸ID':key,'시작일차':r['일차'],'시작시각':r['시각']['값'],
                               '종료일차':end[0],'종료시각':end[1],'장소권역':r['장소명'],'이후연결':'다음 일정 또는 종료 장소로 연결',
                               '연결확인':True,'확인메모':'이동 여유와 연결을 담당자가 확인'})
    data['운영확인']=[{'안':'공통','칸ID':'관광','대상명':'장소A','처리':'유지','운영상태':'운영','영업시작':'09:00','영업종료':'18:00',
                     '익일종료':False,'마감시각':'17:00','출처명':'운영 주체 안내','출처URL':'https://example.invalid/hours','출처등급':'운영주체',
                     '확인일':'2026-11-23','방문일운영확인':True,'메모':'방문 요일과 휴무 확인'}]
    return course,source,data


class 운영검토시험(unittest.TestCase):
    def test_자유식_휴무후보만_명시적으로_제외가능(self):
        c,s,d=example();c['칸목록'][0]['시간칸']='저녁'
        c['식사목록']=[{'안':'공통','칸ID':'관광','방식':'자유식','추천후보':['후보A','후보B'],'식당':''}]
        op=d['운영확인'][0];op['대상명']='후보A';op['처리']='제외';op['운영상태']='휴무'
        other=copy.deepcopy(op);other.update({'대상명':'후보B','처리':'유지','운영상태':'운영'})
        d['운영확인'].append(other)
        result,ready=self.run_check(c,s,d)
        self.assertEqual(result['식사목록'][0]['추천후보'],['후보B'])
        self.assertTrue(ready['진행가능'])

    def run_check(self,course,source,data):
        checked=검토입력_검사(data,course,source)
        revised=검토_반영(course,checked)
        return revised,준비_검사(revised,source,checked)

    def test_정상기간과_출처확인_최종확인후에만_준비(self):
        c,s,d=example();before=copy.deepcopy(c)
        r,check=self.run_check(c,s,d)
        self.assertTrue(check['진행가능'])
        self.assertEqual(c,before)
        self.assertEqual(r['칸목록'][1]['머무는시간'],600)
        d['담당자최종확인']=False
        self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_운영마감초과_휴무_출처미확인은_통과안함(self):
        for field,value in [('영업종료','10:30'),('운영상태','휴무'),('출처명',''),('방문일운영확인',False)]:
            c,s,d=example();d['운영확인'][0][field]=value
            with self.subTest(field=field):self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_숙박역전_일정중복ID_잘못된날짜는_거부(self):
        c,s,d=example();d['일정확인'][1]['종료일차']=1;d['일정확인'][1]['종료시각']='08:00'
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)
        c,s,d=example();d['일정확인'].append(copy.deepcopy(d['일정확인'][0]))
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)
        c,s,d=example();d['방문시작일']='2026-02-30'
        with self.assertRaises(ValueError):검토입력_검사(d,c,s)

    def test_미정기간과_미확인연결은_준비안됨(self):
        c,s,d=example();d['일정확인'][2]['종료시각']='';d['일정확인'][2]['연결확인']=False
        self.assertFalse(self.run_check(c,s,d)[1]['진행가능'])

    def test_수정없는화면정보에_숙박자유시간도_있음(self):
        c,s,d=example();info=화면정보(c,s)
        self.assertEqual(len(info['일정목록']),3)
        self.assertEqual(len(info['운영대상']),1)

    def test_첫_관광지_변경은_이전_근거를_새_장소에_붙이지_않음(self):
        c,s,d=example();c['칸목록'][0]['근거ID']=['R19'];c['칸목록'][0]['운영주체후보']=['옛 운영 주체']
        d['일정확인'][0]['장소권역']='향촌문화관'
        revised,ready=self.run_check(c,s,d)
        first=revised['칸목록'][0]
        self.assertEqual(first['장소명'],'향촌문화관')
        self.assertEqual(first['근거ID'],[])
        self.assertEqual(first['운영주체후보'],[])
        self.assertTrue(any('근거 없음' in w['문구'] and w['칸ID']=='관광' for w in revised['남은경고']))
        self.assertTrue(any('재확인 필요' in w for w in ready['유지경고']))
        self.assertEqual(c['칸목록'][0]['근거ID'],['R19'])


if __name__=='__main__':unittest.main()
