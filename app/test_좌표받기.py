import csv
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest import mock

import 좌표받기


def 장소CSV(폴더):
    p = Path(폴더) / 'places.csv'
    p.write_bytes(('﻿순번,장소명,주소,비고,위도,경도\r\n'
                   '1,가게,대구 중구 어느로 1,,,\r\n'
                   '2,골목,,"메모, 쉼표",,\r\n'
                   '3,기념관,대구 중구 다른로 2,,,\r\n').encode('utf-8'))
    return p


class 좌표받기시험(unittest.TestCase):
    def test_기존검토표를_자동검색으로_덮어쓰지않는다(self):
        with TemporaryDirectory() as d,mock.patch.dict(os.environ,{'HARUHARU_DATA_DIR':d,'HARUHARU_PLACES_FILE':'places.csv'}):
            장소CSV(d)
            path=좌표받기.검토파일();path.write_text('기존 검토 내용',encoding='utf-8')
            with self.assertRaises(ValueError):좌표받기.검토표_만들기(묻기=lambda _:self.fail('조회하면 안 됨'))
            self.assertEqual(path.read_text(encoding='utf-8'),'기존 검토 내용')

    def test_메타정보가_있는_미검토_좌표는_지도에서_쓰지않는다(self):
        import 장소정보
        row={'장소명':'가게','위도':'35.8','경도':'128.6','좌표검토상태':'재검토필요'}
        with mock.patch.object(장소정보,'장소목록',return_value=[row]):
            self.assertIsNone(장소정보.좌표('가게'))
            row.update({'좌표검토상태':'자료대조완료','좌표검토자':'자료대조:Codex',
                        '좌표근거URL':'https://example.org/place','좌표확인일':'2026-11-24',
                        '좌표검토근거':'공식 페이지 지도 좌표','좌표위치기준':'시설대표점'})
            self.assertEqual(장소정보.좌표('가게'),(35.8,128.6))

    def test_정밀도를_구분한다(self):
        self.assertEqual(좌표받기.정밀도({'address': {'house_number': '1'}}), '건물')
        self.assertEqual(좌표받기.정밀도({'category': 'highway', 'type': 'secondary'}), '도로 단위')
        self.assertTrue(좌표받기.정밀도({'addresstype': 'suburb'}).startswith('근처'))

    def test_주소없는_장소는_묻지_않고_못찾으면_빈칸(self):
        물음 = []

        def 묻기(url):
            물음.append(url)
            return [] if len(물음) == 2 else [{'lat': '35.1', 'lon': '128.6', 'address': {'house_number': '1'}, 'display_name': '가게'}]
        with TemporaryDirectory() as d:
            장소CSV(d)
            with mock.patch.dict(os.environ, {'HARUHARU_DATA_DIR': d, 'HARUHARU_PLACES_FILE': 'places.csv'}):
                표 = 좌표받기.검토표_만들기(묻기, 쉬기=0)
        self.assertEqual(len(물음), 3)  # 주소 2번 + 못 찾은 곳 이름 보완 1번 (주소 없는 곳은 묻지 않음)
        self.assertEqual([r['정밀도'] for r in 표], ['건물', '주소 없음', '못 찾음'])
        self.assertEqual(표[2]['위도'], '')

    def test_반영은_사용O_행만_옮기고_나머지는_보존(self):
        with TemporaryDirectory() as d:
            p = 장소CSV(d)
            with mock.patch.dict(os.environ, {'HARUHARU_DATA_DIR': d, 'HARUHARU_PLACES_FILE': 'places.csv'}):
                with open(좌표받기.검토파일(), 'w', encoding='utf-8-sig', newline='') as f:
                    w = csv.DictWriter(f, fieldnames=좌표받기.검토열)
                    w.writeheader()
                    w.writerow({'순번': '1', '장소명':'가게','주소':'대구 중구 어느로 1','위도': '35.1', '경도': '128.6', '사용': 'O',
                                '검토자':'시험 담당자','검토일':'2026-11-24','근거URL':'https://example.org/place',
                                '검토근거':'장소명과 주소 및 시설 좌표 대조','검토상태':'자료대조완료','위치기준':'시설대표점'})
                    w.writerow({'순번': '3', '위도': '35.2', '경도': '128.7', '사용': ''})
                self.assertEqual(좌표받기.반영(), ['가게'])
            글 = p.read_bytes().decode('utf-8-sig')
        self.assertIn('1,가게,대구 중구 어느로 1,,35.1,128.6,', 글)
        self.assertIn('2,골목,,"메모, 쉼표",,', 글)
        self.assertIn('3,기념관,대구 중구 다른로 2,,,', 글)

    def test_사용O라도_검토정보없으면_전체반영을_거부하고_원본보존(self):
        with TemporaryDirectory() as d:
            p=장소CSV(d);before=p.read_bytes()
            with mock.patch.dict(os.environ,{'HARUHARU_DATA_DIR':d,'HARUHARU_PLACES_FILE':'places.csv'}):
                with open(좌표받기.검토파일(),'w',encoding='utf-8-sig',newline='') as f:
                    w=csv.DictWriter(f,fieldnames=좌표받기.검토열);w.writeheader()
                    w.writerow({'순번':'1','위도':'35.1','경도':'128.6','사용':'O'})
                with self.assertRaises(ValueError):좌표받기.반영()
            self.assertEqual(p.read_bytes(),before)

    def test_좌표역전_미래날짜_장소불일치_입구대기는_거부(self):
        row={'순번':'1','장소명':'가게','주소':'대구 중구 어느로 1','위도':'35.1','경도':'128.6','사용':'O',
             '검토자':'자료대조:Codex','검토일':'2026-11-24','근거URL':'https://example.org/place',
             '검토근거':'공식 지도 좌표','검토상태':'자료대조완료','위치기준':'시설대표점'}
        for change in [{'위도':'128.6','경도':'35.1'},{'위도':'nan'},{'검토일':'2999-01-01'},
                       {'장소명':'다른 가게'},{'검토상태':'입구선택대기'},{'근거URL':'javascript:alert(1)'},
                       {'검토자':''},{'검토근거':''}]:
            with self.subTest(change=change),TemporaryDirectory() as d:
                p=장소CSV(d);before=p.read_bytes()
                with mock.patch.dict(os.environ,{'HARUHARU_DATA_DIR':d,'HARUHARU_PLACES_FILE':'places.csv'}):
                    with open(좌표받기.검토파일(),'w',encoding='utf-8-sig',newline='') as f:
                        w=csv.DictWriter(f,fieldnames=좌표받기.검토열,extrasaction='ignore');w.writeheader();w.writerow({**row,**change})
                    with self.assertRaises(ValueError):좌표받기.반영()
                self.assertEqual(p.read_bytes(),before)

    def test_이름보완은_이름과_구가_맞을때만_받는다(self):
        맞음=lambda url:[{'lat':'35.87','lon':'128.59','display_name':'향촌문화관, 서성로14길, 중구, 대구광역시'}]
        self.assertEqual(좌표받기.이름으로_보완('향촌문화관','대구광역시 중구 중앙대로 449',맞음)[2],'시설 (이름 검색 · 사람 확인 필요)')
        다른이름=lambda url:[{'lat':'35.87','lon':'128.59','display_name':'대구역, 중앙대로, 중구, 대구광역시'}]
        self.assertIsNone(좌표받기.이름으로_보완('향촌문화관','대구광역시 중구 중앙대로 449',다른이름))
        다른구=lambda url:[{'lat':'35.87','lon':'128.59','display_name':'향촌문화관, 어느로, 동구, 대구광역시'}]
        self.assertIsNone(좌표받기.이름으로_보완('향촌문화관','대구광역시 중구 중앙대로 449',다른구))


if __name__ == '__main__':
    unittest.main()
