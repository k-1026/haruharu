"""등록된 공식 페이지의 지도 표시점을 읽는다. AI·브라우저·자동 반영 없음."""
from datetime import date,datetime
import html
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request,urlopen

공식호스트={'access.visitkorea.or.kr','www.daegufood.go.kr','daegufood.go.kr'}


def _공식URL(url):
    u=urlsplit(url)
    if u.scheme!='https' or u.hostname not in 공식호스트 or u.username or u.password or u.port not in (None,443):
        raise ValueError('등록된 공식 HTTPS 페이지가 아닙니다.')


def 페이지읽기(url):
    _공식URL(url)
    with urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0 (haruharu coordinate review)'}),timeout=15) as response:
        _공식URL(response.geturl())
        raw=response.read(2_000_001)
        if len(raw)>2_000_000:raise ValueError('공식 페이지 크기 상한 초과')
    try:return raw.decode('utf-8')
    except UnicodeDecodeError:return raw.decode('cp949')


def 추출(text,name):
    text=html.unescape(text)
    number=r'([+-]?\d+(?:\.\d+)?)'
    patterns=[r"findingAway\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]"+number+r"['\"]\s*,\s*['\"]"+number+r"['\"]",
              r"apiKakaoMap\(\s*['\"]map['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*,\s*"+number+r'\s*,\s*'+number]
    points=set()
    for pattern in patterns:
        for title,lat,lon in re.findall(pattern,text):
            if title.strip()!=name.strip():continue
            if not(-90<=float(lat)<=90 and -180<=float(lon)<=180):raise ValueError('위도·경도 범위 오류')
            points.add((lat,lon))
    if len(points)!=1:raise ValueError('장소명이 일치하는 단일 지도 좌표가 없습니다. 추정하지 않습니다.')
    return points.pop()


def 후보수집(sources,읽기=페이지읽기):
    rows=[]
    for source in sources:
        row={'장소명':source['장소명'],'근거URL':source['URL'],'수집일':date.today().isoformat(),
             '사용':'','검토자':'','검토상태':'검토대기','위치기준':'시설대표점'}
        try:
            _공식URL(source['URL'])
            row['위도'],row['경도']=추출(읽기(source['URL']),source.get('페이지장소명',source['장소명']))
        except Exception as error:
            row.update({'검토상태':'수집실패','이유':f'{type(error).__name__}: {error}'[:300]})
        rows.append(row)
    return rows


def 실행():
    root=Path(__file__).resolve().parents[2]
    path=root/'research/data/시연장소_좌표근거_1124.json'
    sources=json.loads(path.read_text(encoding='utf-8'))
    aliases={'김광석길':'김광석다시그리기길','산호찜갈비':'산호찜갈비식당','원주통닭 (치킨 옵션)':'원주통닭'}
    for source in sources:source.setdefault('페이지장소명',aliases.get(source['장소명'],source['장소명']))
    rows=후보수집(sources)
    folder=root/'app/runs';folder.mkdir(exist_ok=True)
    output=folder/('공식좌표_후보_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    output.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'공식 좌표 후보 {len(rows)}곳: {output}')
    print('후보 수집만 했습니다. 기존 검토표·장소 CSV·입구 선택은 변경하지 않았습니다.')

if __name__=='__main__':실행()
