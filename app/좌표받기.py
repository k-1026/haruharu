"""장소 CSV의 주소로 위도·경도를 받아 검토용 표를 만든다. 사람이 검토한 뒤 --반영으로 장소 CSV에 옮긴다.

- 주소 검색은 OpenStreetMap Nominatim(무료)을 쓴다. 이용 규칙대로 1초에 한 번만 묻는다.
- 주소가 비어 있는 장소는 묻지 않는다. 장소 이름으로 추정해 찾지 않는다.
- 결과마다 정밀도(건물 / 도로 단위 / 못 찾음)를 남긴다. 못 찾으면 빈칸이다.

사용:
  python app/좌표받기.py            # research/data/장소좌표_검토용.csv 생성
  python app/좌표받기.py --반영     # 검토용 표에서 '사용' 열이 O인 행만 장소 CSV 위도·경도에 옮김
"""
import argparse
import csv
import io
import json
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

from 설정 import 설정_읽기, 자료_파일

검색주소 = 'https://nominatim.openstreetmap.org/search'
머리말 = {'User-Agent': 'haruharu-course-planner/0.1 (local demo)'}
검토열 = ['순번', '장소명', '주소', '위도', '경도', '정밀도', '찾은이름', '출처', '확인일', '사용']


def 장소파일():
    return 자료_파일(설정_읽기(), 'HARUHARU_PLACES_FILE', '장소운영정보_중구동구_데모코스_2026.csv')


def 검토파일():
    return 장소파일().with_name('장소좌표_검토용.csv')


def 정밀도(결과):
    """번지까지 맞으면 건물, 길까지만 맞으면 도로 단위."""
    주소 = 결과.get('address') or {}
    if 주소.get('house_number') or 결과.get('addresstype') in ('building', 'house'):
        return '건물'
    # jsonv2는 category, 예전 형식은 class. 길 전체 중 한 점이라 실제 위치와 수백 m 이상 다를 수 있다
    if 결과.get('category') == 'highway' or 결과.get('class') == 'highway':
        return '도로 단위'
    return '근처 (' + str(결과.get('addresstype') or 결과.get('type') or '종류 미상') + ')'


def 주소검색(주소, 묻기=None):
    """주소 하나 → (위도, 경도, 정밀도, 찾은이름). 못 찾으면 빈칸과 '못 찾음'."""
    질의 = urllib.parse.urlencode({'q': 주소, 'format': 'jsonv2', 'addressdetails': 1, 'limit': 1, 'countrycodes': 'kr'})
    if 묻기 is None:
        def 묻기(url):
            with urllib.request.urlopen(urllib.request.Request(url, headers=머리말), timeout=20) as 응답:
                return json.loads(응답.read().decode('utf-8'))
    결과 = 묻기(검색주소 + '?' + 질의)
    if not 결과:
        return '', '', '못 찾음', ''
    첫째 = 결과[0]
    return 첫째['lat'], 첫째['lon'], 정밀도(첫째), 첫째.get('display_name', '')


def 이름으로_보완(이름, 주소, 묻기=None):
    """주소 검색이 길 단위로만 맞을 때, 장소 이름으로 시설을 찾는다.
    찾은 시설 이름이 장소 이름과 같고 같은 구에 있을 때만 받는다. 지도 자료의 길 이름은 공식 주소와 다를 수 있어
    (예: 향촌문화관 공식 주소 중앙대로, 지도 자료 서성로14길) 길 이름까지는 맞추지 않는다. 사람이 검토표에서 확인한다."""
    구 = next((낱 for 낱 in 주소.split() if 낱.endswith('구') and len(낱) <= 4), '')
    if not 구:
        return None
    짧은이름 = 이름.split('(')[0].strip()
    위도, 경도, 정밀, 찾은 = 주소검색(f'대구 {구} {짧은이름}', 묻기)
    시설이름 = 찾은.split(',')[0].replace(' ', '')
    if 위도 and 시설이름 == 짧은이름.replace(' ', '') and f' {구},' in 찾은:
        return 위도, 경도, '시설 (이름 검색 · 사람 확인 필요)', 찾은
    return None


def 검토표_만들기(묻기=None, 쉬기=1.0):
    행들 = list(csv.DictReader(open(장소파일(), encoding='utf-8-sig')))
    표 = []
    for i, 행 in enumerate(행들):
        주소 = (행.get('주소') or '').strip()
        if not 주소:
            표.append({'순번': 행['순번'], '장소명': 행['장소명'], '주소': '', '정밀도': '주소 없음', '사용': ''})
            continue
        if i and 쉬기:
            time.sleep(쉬기)
        위도, 경도, 정밀, 이름 = 주소검색(주소, 묻기)
        if 정밀 != '건물':
            if 쉬기:
                time.sleep(쉬기)
            보완 = 이름으로_보완(행['장소명'], 주소, 묻기)
            if 보완:
                위도, 경도, 정밀, 이름 = 보완
        표.append({'순번': 행['순번'], '장소명': 행['장소명'], '주소': 주소, '위도': 위도, '경도': 경도, '정밀도': 정밀,
                  '찾은이름': 이름, '출처': 'OpenStreetMap Nominatim', '확인일': date.today().isoformat(), '사용': ''})
    with open(검토파일(), 'w', encoding='utf-8-sig', newline='') as f:
        쓰기 = csv.DictWriter(f, fieldnames=검토열)
        쓰기.writeheader()
        쓰기.writerows(표)
    return 표


def 반영():
    """검토용 표에서 사람이 '사용'에 O를 적은 행만 장소 CSV의 위도·경도로 옮긴다. 나머지는 건드리지 않는다."""
    검토 = {r['순번']: r for r in csv.DictReader(open(검토파일(), encoding='utf-8-sig')) if r.get('사용', '').strip().upper() == 'O'}
    원문 = open(장소파일(), encoding='utf-8-sig', newline='').read()
    줄끝 = '\r\n' if '\r\n' in 원문 else '\n'
    행들 = list(csv.reader(io.StringIO(원문)))
    열 = {k: i for i, k in enumerate(행들[0])}
    바뀜 = []
    for 행 in 행들[1:]:
        r = 검토.get(행[열['순번']])
        if r and r['위도'] and r['경도']:
            행[열['위도']], 행[열['경도']] = r['위도'], r['경도']
            바뀜.append(행[열['장소명']])
    글 = io.StringIO()
    csv.writer(글, lineterminator=줄끝).writerows(행들)
    open(장소파일(), 'w', encoding='utf-8-sig', newline='').write(글.getvalue())
    return 바뀜


def main():
    p = argparse.ArgumentParser(description='장소 주소 → 좌표 검토표 만들기 / 반영')
    p.add_argument('--반영', action='store_true', help='검토표에서 사용=O인 좌표를 장소 CSV에 옮김')
    a = p.parse_args()
    if a.반영:
        바뀜 = 반영()
        print(f'{len(바뀜)}곳 반영: ' + ', '.join(바뀜))
        return
    for r in 검토표_만들기():
        print(f"{r['순번']:>2} {r['장소명']:<20} {r['정밀도']:<10} {r.get('위도', '')},{r.get('경도', '')}")
    print(f'\n검토표: {검토파일()}\n확인 후 쓸 행의 "사용" 칸에 O를 적고 --반영으로 옮기세요.')


if __name__ == '__main__':
    main()
