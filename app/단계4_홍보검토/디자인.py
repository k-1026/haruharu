"""통합 시안의 배경·구도·캐릭터를 재사용하는 코스별 홍보물과 QR 랜딩.

문구를 만들지 않는다. 4단계 에이전트 출력과 확정 코스만 배치한다.
정리본 원본은 보존하며, 생성 SVG에는 예시 코스·기존 QR을 남기지 않는다.
"""
import base64
import copy
import html
import io
import json
import re
import unicodedata
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

ROOT = Path(__file__).resolve().parents[2]
SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)
시안 = {
    'SNS 카드뉴스': ('SNS카드뉴스_예시안_v3_캐릭터배치_캐릭터.svg', 'sns', '1080×1350'),
    '리플릿': ('리플렛_A4_3단접지_알찬평면배치_v2_QR.svg', 'leaflet', 'A4 가로 · 3단 · 긴 코스는 펼침면 추가'),
    '포스터': ('포스터_A3_세로_시안_v1_QR.svg', 'poster', 'A3 세로'),
    '스탬프 투어 북': ('스탬프투어북_A5_디자인예시_v1_QR.svg', 'stampbook', 'A5 세로 · 코스 길이에 따라 쪽수 조정'),
}


def _tag(name):
    return '{' + SVG + '}' + name


@lru_cache(maxsize=32)
def _원본(name):
    return (ROOT / '정리본' / '홍보물' / name).read_text(encoding='utf-8')


def _추가(parent, tag, **attrs):
    return ET.SubElement(parent, _tag(tag), {k.replace('_', '-'): str(v) for k, v in attrs.items()})


def _줄(text, width, size):
    """동아시아 전각 문자를 고려해 줄바꿈한다. 원문을 자르지 않는다."""
    lines, line, used = [], '', 0
    for ch in str(text or ''):
        unit = size if unicodedata.east_asian_width(ch) in 'WF' else size * .57
        if ch == '\n' or (line and used + unit > width):
            lines.append(line)
            line, used = '', 0
            if ch == '\n':
                continue
        line += ch
        used += unit
    return lines + ([line] if line else [])


def _글(value):
    if isinstance(value, dict):
        if value.get('안내'):
            return str(value['안내'])
        return ' · '.join(f'{k}: {_글(v)}' for k, v in value.items())
    if isinstance(value, list):
        return ' / '.join(_글(v) for v in value)
    return str(value or '')


def _코스명(b):
    for name in [b['코스카드'].get('코스이름'), b['확인'].get('코스이름')]:
        if name and name not in ['미정', '[코스 이름 미정]']:
            return str(name)
    return '코스 이름 미정'


def _문자(root, text, x, y, width, size=18, color='#202a49', weight='400'):
    lines = _줄(_글(text), width, size)
    t = _추가(root, 'text', x=x, y=y, fill=color, font_size=size, font_weight=weight,
              font_family='Malgun Gothic,Noto Sans JP,Noto Sans KR,sans-serif')
    for i, line in enumerate(lines):
        _추가(t, 'tspan', x=x, dy=0 if i == 0 else size * 1.45).text = line
    return y + len(lines) * size * 1.45


@lru_cache(maxsize=32)
def _그림(name):
    return 'data:image/webp;base64,' + base64.b64encode((ROOT / '정리본/랜딩_이미지' / name).read_bytes()).decode()


def _사진(root, name, x, y, w, h):
    _추가(root, 'image', href=_그림(name), x=x, y=y, width=w, height=h, preserveAspectRatio='xMidYMid meet')


@lru_cache(maxsize=4)
def _단독그림(symbol):
    source = ET.fromstring(_원본(시안['SNS 카드뉴스'][0]))
    return source.find(f'.//{_tag("symbol")}[@id="{symbol}"]/{_tag("image")}').get('{'+XLINK+'}href')


def _둘(root, night, x, y, w, h, 주연='동등'):
    if 주연 == '동등':
        _사진(root, '캐릭터_밤_크로스백_별랜턴.webp' if night else '캐릭터_낮_크로스백.webp', x, y, w, h)
        return
    raccoon_lead = 주연 in ['포롱이', '너구리', 'raccoon']
    for raccoon, symbol in [(True, 'chD' if night else 'chC'), (False, 'chF' if night else 'chE')]:
        lead = raccoon == raccoon_lead
        size = .59 if lead else .37
        _추가(root, 'image', href=_단독그림(symbol), x=x if raccoon else x+w*.55,
              y=y if lead else y+h*.25, width=w*size, height=h if lead else h*.75, preserveAspectRatio='xMidYMax meet')


@lru_cache(maxsize=1)
def _사진목록():
    source = (ROOT / '정리본/QR랜딩페이지_v1.html').read_text(encoding='utf-8')
    result = {}
    for block in re.findall(r"\{id:'p\d+'.*?(?=\n  \{id:|\n\];)", source, re.S):
        name = re.search(r"ko:\{.*?name:'([^']+)'", block, re.S)
        photo = re.search(r"photo:'([^']+)'", block)
        credit = re.search(r"credit:\{label:'([^']+)', author:'([^']+)', license:'([^']+)', url:'([^']+)'", block)
        if name and photo and credit:
            result[name[1]] = (photo[1], dict(zip(['label','author','license','url'], credit.groups())))
    return result


def _장소사진(name):
    clean = re.sub(r'\s*\([^)]*\)', '', name).strip()
    clean = re.sub(r'^대구(?:광역시)?\s*(?:중구|동구)?\s*', '', clean)
    clean = {'김광석길':'김광석 다시그리기길'}.get(clean, clean)
    return _사진목록().get(clean)


def _장소명(name):
    clean = re.sub(r'^대구(?:광역시)?\s*(?:중구|동구)?\s*', '', str(name)).strip()
    clean = re.sub(r'\s*\(대구(?:광역시)?\s*(?:중구|동구)\)', '', clean)
    return {'김광석길':'김광석 다시그리기길'}.get(clean, clean)


@lru_cache(maxsize=1)
def _일본어표기():
    text = (ROOT / '지침/4_홍보검토/12_번역_용어집.md').read_text(encoding='utf-8')
    official = text.split('## 2. 장소 이름 — 공식 표기', 1)[1].split('### 2-1.', 1)[0]
    result = {}
    for line in official.splitlines():
        cells = [x.strip() for x in line.strip('|').split('|')]
        if line.startswith('| ') and len(cells) >= 7 and cells[2] not in ['미확인', '일본어']:
            result[re.sub(r'\s*\(.*\)', '', cells[0]).strip()] = cells[2]
    return result


def _짧은이름(name):
    return {'서문시장 권역':'서문시장','김광석 다시그리기길':'김광석길','평화시장 닭똥집골목':'평화시장',
            '신천 산책':'신천','西門市場エリア':'西門市場','大邱平和市場タクトンチプ屋通り':'平和市場','新川さんぽ':'新川'}.get(name, name)


def _랜딩시각(row, scene):
    value = str(row.get('시각') or '')
    if '(가정)' not in value and not any(x in value for x in ['미확인','미정']):
        return value
    slot = str(scene.get('시간칸') or '')
    if slot == '낮':
        hour = re.match(r'(\d{1,2}):',value)
        return '오후' if hour and int(hour[1])>=12 else '오전'
    return slot or '방문 시간 확인 중'


def _주소(url, source):
    u = urlsplit(url)
    qs = dict(parse_qsl(u.query))
    qs['from'] = source
    return urlunsplit((u.scheme, u.netloc, u.path, urlencode(qs), u.fragment))


@lru_cache(maxsize=128)
def QR(url):
    import qrcode
    # 흰 여백 4모듈을 포함한 실제 QR. 외부 서비스 호출 없음.
    code = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=4)
    code.add_data(url)
    code.make(fit=True)
    return code.get_matrix()


def _큐알(root, url, x, y, size):
    matrix = QR(url)
    n = len(matrix)
    g = _추가(root, 'svg', x=x, y=y, width=size, height=size, viewBox=f'0 0 {n} {n}', shape_rendering='crispEdges')
    _추가(g, 'title').text = url
    _추가(g, 'rect', width=n, height=n, fill='white')
    path = ' '.join(f'M{x1},{y1}h1v1h-1z' for y1, row in enumerate(matrix) for x1, bit in enumerate(row) if bit)
    _추가(g, 'path', d=path, fill='black')


def _판(kind, template=0):
    """제공된 SVG에서 배경 판형을 가져온다. 예시 문구·QR·도식은 가져오지 않는다."""
    source = ET.fromstring(_원본(시안[kind][0]))
    if kind == '포스터':
        w, h = 1000, 1414
        bg = next(x for x in source if x.tag == _tag('rect'))
    else:
        panels = [x for x in source if x.tag == _tag('g') and x.get('transform', '').startswith('translate')]
        if kind == '리플릿':
            w, h, bg = 570, 705, None
        else:
            w, h = (420, 525) if kind == 'SNS 카드뉴스' else (330, 450)
            bg = next(x for x in panels[template % len(panels)] if x.tag == _tag('rect'))
    out = ET.Element(_tag('svg'), {'width': str(w), 'height': str(h), 'viewBox': f'0 0 {w} {h}'})
    for el in source:
        if el.tag == _tag('style'):
            out.append(copy.deepcopy(el))
        if el.tag == _tag('defs'):
            defs = ET.Element(_tag('defs'))
            for d in el:
                if d.tag != _tag('symbol'):
                    defs.append(copy.deepcopy(d))
            out.append(defs)
    if bg is not None:
        out.append(copy.deepcopy(bg))
    else:
        _추가(out, 'rect', width=w, height=h, rx=18, fill='#fff8ea')
    return out, w, h


def _원문(scene, language):
    c = scene.get('문구') or {}
    if language == '한국어':
        return c.get('제목') or scene['장소'], c.get('본문', '')
    tr = next((t for t in scene.get('번역', []) if t.get('언어') == language), {})
    raw = tr.get('번역', '')
    parts = re.match(r'^\s*[【\[][^】\]]+[】\]]\s*(.*?)\s*[【\[][^】\]]+[】\]]\s*(.*)$', str(raw), re.S)
    return (parts.group(1), parts.group(2)) if parts else (scene['장소'], raw or '')


def _장면쪽(kind, scene, row, number, tone, language, url):
    from app.단계5_산출물.산출물 import _근거글
    night = scene['시간칸'] in ['저녁', '밤']
    dark = tone == 'B' or (tone == 'A+B' and night)
    ink = '#fff' if dark else '#202a49'
    photo = _장소사진(scene['장소'])
    head, body = _원문(scene, language)
    c = scene.get('문구') or {}
    blocks = [(head, 22, '700'), (body, 14, '400')]
    if language == '한국어':
        blocks += [(f'{name}: {line}', 12, '400') for name, line in (c.get('말풍선') or {}).items()]
    if photo:
        blocks += [('사진: '+photo[1]['author']+' · '+photo[1]['license'], 9, '400')]
        blocks += [('원본: '+photo[1]['url'], 8, '400')]
    roots = []

    def new_page(first):
        root, w, h = _판(kind, 3)
        _추가(root, 'rect', width=w, height=h, rx=18, fill='#273251' if dark else '#fff' if tone == 'C' else '#fff8ea')
        y = _문자(root, f"{number:02d} · {row.get('일차') or 1}일차 · {scene['시간칸']} · {row['시각']}" + ('' if first else ' · 이어보기'), 28, 32, w-56, 12, ink)
        if first and photo:
            _사진(root, Path(photo[0]).name, 28, y+4, w-56, 105)
            y += 120
        _문자(root, '전체 일정과 지도는 QR에서 확인', 28, h-133, w-56, 9, ink)
        _둘(root, night, 25, h-118, w-165, 108, (scene.get('시안') or {}).get('주연', '동등'))
        _큐알(root, url, w-120, h-115, 100)
        roots.append(root)
        return root, w, h, y+8

    root, w, h, y = new_page(True)
    for text, size, weight in blocks:
        y += 5
        for line in _줄(_글(text), w-56, size):
            if y+size*1.5 > h-150:
                root, w, h, y = new_page(False)
            y = _문자(root, line, 28, y, w-56, size, ink, weight)
    return roots


def 만들기(b, landing_url, language='한국어'):
    from app.단계5_산출물.산출물 import _근거글
    from app.단계5_산출물.공개자료 import 공개묶음
    b = 공개묶음(b)
    results = []
    title = _코스명(b)
    scenes = b['장면']
    rows = b['시간표']
    for kind in b['확인'].get('홍보물', ['SNS 카드뉴스']):
        if kind not in 시안:
            continue
        url = _주소(landing_url, 시안[kind][1])
        pages = []
        # 긴 코스도 예시의 고정 장소 수에 맞춰 자르지 않는다.
        root, w, h = _판(kind)
        tone = b['확인'].get('톤앤매너', 'A+B')
        dark = tone == 'B' or (tone == 'A+B' and kind in ['SNS 카드뉴스', '스탬프 투어 북'])
        bg = '#273251' if dark else '#fff' if tone == 'C' else '#fff8ea'
        next(x for x in root if x.tag == _tag('rect')).set('style', 'fill:'+bg)
        ink = '#ffffff' if dark else '#202a49'
        if kind == '포스터':
            _문자(root, '대구 여행 코스', 55, 75, 880, 21, ink)
            _문자(root, title, 55, 160, 880, 44, ink, weight='700')
            _문자(root, b['코스카드'].get('대상문장', ''), 55, 320, 880, 24, ink)
            _추가(root, 'rect', x=55, y=410, width=890, height=390, rx=35, fill='#273251')
            _둘(root, False, 70, 430, 525, 355)
            _문자(root, '포롱이 · 여울이', 610, 490, 310, 28, '#fff')
            _문자(root, b['조건'].get('체류기간', ''), 610, 550, 310, 26, '#fff')
            _문자(root, '코스 한눈에 보기', 55, 865, 880, 34, ink, weight='700')
            _문자(root, ' → '.join(r['장소'] for r in rows), 55, 925, 880, max(15, 24 - len(rows)), ink, weight='700')
            if scenes:
                head, body = _원문(scenes[0], language)
                _문자(root, head, 55, 1100, 620, 22, ink, '700')
                _문자(root, body, 55, 1150, 620, 17, ink)
            _큐알(root, url, 735, 1080, 200)
            _문자(root, '전체 일정 · 문구 · 지도', 700, 1310, 285, 17, ink)
            _문자(root, '식사는 개별 선택·개별 결제입니다.', 55, 1370, 650, 18, ink)
        else:
            _문자(root, '포롱이 · 여울이의 대구 탐험', 28, 40, w-56, 15, ink)
            title_size = 25
            while len(_줄(title, w-56, title_size))*title_size*1.45 > h*.23 and title_size>10:
                title_size -= 1
            _문자(root, title, 28, 95, w-56, title_size, ink, '700')
            _둘(root, False, 25, h*.37, w-50, h*.29)
            _문자(root, b['조건'].get('체류기간', '') + ' 여행', 28, h*.73, w-150, 15, ink)
            _큐알(root, url, w-120, h-125, 100)
            _문자(root, '코스 전체 보기', 28, h-40, w-165, 16, ink)
        pages.append(root)
        for i, s in enumerate(scenes if kind != '포스터' else []):
            # A3 포스터와 리플릿에도 원문을 빠짐없이 담는 상세 면을 둔다.
            pages.extend(_장면쪽(kind, s, rows[i], i+1, tone, language, url))
        if kind == '리플릿':
            # 바깥쪽: 뒤표지·코스 요약·표지 / 안쪽: 장소별 상세 3면씩.
            info, _, _ = _판(kind)
            _문자(info, '여행 전 확인해요', 30, 60, 510, 28, weight='700')
            _문자(info, b['코스카드'].get('식사안내', ''), 30, 120, 510, 19)
            _문자(info, '운영시간·휴무·이동 조건은 방문 전 확인하세요. 식당은 후보이며 다른 식당도 선택할 수 있습니다.', 30, 290, 510, 19)
            _큐알(info, url, 190, 440, 190)
            route, _, _ = _판(kind)
            _문자(route, '코스 한눈에 보기', 30, 60, 510, 28, weight='700')
            _문자(route, '\n'.join(f"{r.get('일차') or 1}일차 · {r['시각']} · {r['장소']}" for r in rows), 30, 120, 510, max(12, 22-len(rows)//2))
            panels = [info, route, pages[0], *pages[1:]]
            while len(panels) % 3:
                extra, _, _ = _판(kind)
                _둘(extra, False, 60, 160, 450, 300)
                _문자(extra, '전체 일정과 안내', 30, 70, 510, 28)
                _큐알(extra, url, 210, 490, 150)
                panels.append(extra)
            pages = []
            for offset in range(0, len(panels), 3):
                sheet = ET.Element(_tag('svg'), {'width':'1710', 'height':'705', 'viewBox':'0 0 1710 705'})
                for col, panel in enumerate(panels[offset:offset+3]):
                    panel.set('x', str(col*570)); panel.set('y', '0')
                    panel.set('width', '570'); panel.set('height', '705')
                    sheet.append(panel)
                pages.append(sheet)
        for i, root in enumerate(pages, 1):
            if kind == 'SNS 카드뉴스':
                root.set('width', '1080'); root.set('height', '1350')
            elif kind == '스탬프 투어 북':
                root.set('width', '148mm'); root.set('height', '210mm')
            elif kind == '포스터':
                root.set('width', '297mm'); root.set('height', '420mm')
            elif kind == '리플릿':
                root.set('width', '297mm'); root.set('height', '210mm')
            svg = ET.tostring(root, encoding='unicode')
            results.append({'종류': kind, '페이지': i, '언어': language, '규격': 시안[kind][2],
                            '이름': f'{시안[kind][1]}_{i:02d}.svg', 'svg': svg, '랜딩주소': url,
                            '원본': '정리본/홍보물/' + 시안[kind][0]})
    return results


def 미리보기(pages, landing_url, b=None):
    chunks = []
    for kind in dict.fromkeys(x['종류'] for x in pages):
        selected = [p for p in pages if p['종류'] == kind]
        chunks.append('<section><h2>' + html.escape(kind) + '</h2><p>' + html.escape(selected[0]['규격']) + '</p><div class="pages">')
        for p in selected:
            data = base64.b64encode(p['svg'].encode()).decode()
            chunks.append(f'<figure><img alt="{html.escape(kind)} {p["페이지"]}면" src="data:image/svg+xml;base64,{data}"><figcaption>{p["페이지"]}면</figcaption></figure>')
        chunks.append('</div></section>')
    download = ''
    if b and b.get('홍보id'):
        u = urlsplit(landing_url)
        link = urlunsplit((u.scheme, u.netloc, '/plan/design.zip', urlencode({'id':b['홍보id']}), ''))
        download = f' · <a href="{html.escape(link, quote=True)}" download>홍보물 내려받기 (ZIP)</a>'
    return ('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>코스별 홍보물 디자인</title><style>body{margin:20px;background:#eee9df;font-family:Malgun Gothic,sans-serif;color:#202a49}a{color:#70411d}'
            '.pages{display:flex;flex-wrap:wrap;gap:18px}figure{margin:0;width:min(100%,330px)}img{display:block;width:100%;height:auto}figcaption{margin:8px 0}'
            '@media print{body{margin:0;background:white}header,h2,section>p,figcaption{display:none}.pages{display:block}figure{width:100%;break-after:page;page-break-after:always}img{max-height:275mm;width:100%;object-fit:contain}}</style>'
            '<header><h1>코스별 홍보물</h1><p>'+html.escape((b or {}).get('버전안내',''))+'</p><p>브라우저 인쇄에서 PDF로 저장할 수 있습니다. 전체 일정과 지도는 코스 페이지에서 확인하세요.</p>'
            + ('<p>로컬 검토용 QR · 휴대전화에서 열려면 공개 주소로 배포해야 합니다.</p>' if urlsplit(landing_url).hostname in ['127.0.0.1','localhost'] else '') +
            f'<a href="{html.escape(landing_url, quote=True)}" target="_blank" rel="noopener">이 홍보물의 코스 페이지 열기</a>{download}</header>' + ''.join(chunks) + '</html>')


def 랜딩(b, key, notice=''):
    """기존 QR 페이지의 UI·이미지·출처를 유지하며 예시 데이터만 치환한다."""
    from app.단계5_산출물.공개자료 import 공개묶음
    b = 공개묶음(b)
    source = (ROOT / '정리본/QR랜딩페이지_v1.html').read_text(encoding='utf-8')
    # 사진과 출처 메타데이터는 원본 페이지의 한 묶음 그대로 재사용한다.
    places = []
    for i, (s, row) in enumerate(zip(b['장면'], b['시간표']), 1):
        title, desc = _원문(s, '한국어')
        ja_title, ja_desc = _원문(s, '일본어')
        c = s.get('문구') or {}
        name = _장소명(row['장소'])
        ja_name = _일본어표기().get(name, {'자유식':'自由食','중구 자유식':'中区・自由食','동구 자유식':'東区・自由食'}.get(name, name))
        duration = row.get('머무는시간')
        duration_text = f'약 {duration}분' if isinstance(duration, (int, float)) and duration>0 else str(duration or '')
        common = {'time': _랜딩시각(row,s), 'slot': f"{row.get('일차') or 1}일차", 'stay': duration_text,
                  'hl': [str(row['식사'])] if row.get('식사') else []}
        p = {'id': f'p{i}', 'day': row.get('일차') or 1, 'n': i, 'night': s['시간칸'] in ['저녁','밤'], 'lead':'both',
             '원본장소':row['장소'], '원본시각':row['시각'], 'short':{'ko':_짧은이름(name),'ja':_짧은이름(ja_name)}, 'photo':None,
             'mapQ': None if '자유식' in name else '대구 ' + name, 'ko': {**common, 'name': name, 'desc': title+' · '+desc,
             'bub': list((c.get('말풍선') or {}).items())}, 'ja': {**common, 'name': ja_name, 'desc': ja_title+' · '+ja_desc}}
        if isinstance(duration,(int,float)) and duration>0:
            p['ja']['stay'] = f'約{duration}分'
        p['ja']['slot'] = f"DAY {row.get('일차') or 1}"
        p['ja']['hl'] = ['食事は各自で選び、お支払いください。'] if row.get('식사') else []
        if not s.get('번역'):
            p['ja']['desc'] = ''
        p['ja']['time'] = {'오전':'午前','오후':'午後','점심':'お昼','저녁':'夕方','밤':'夜','숙박':'宿泊','2일차오전':'午前'}.get(common['time'],common['time'])
        photo = _장소사진(row['장소'])
        if photo:
            p['photo'], p['credit'] = photo
        places.append(p)
    title = _코스명(b)
    payload = {'key': key, 'title': title, 'places': places, 'period': b['조건'].get('체류기간', ''),
               'end': b['시작종료'],
               'meal': _글(b['코스카드'].get('식사안내', '')), 'mealJa':'食事は各自で選び、お支払いください。',
               'tagline':_글(b['코스카드'].get('한눈에',''))}
    safe = json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')
    source = re.sub(r'const PLACES = \[.*?\n\];', lambda _: 'const COURSE = '+safe+';\nconst PLACES = COURSE.places;', source, count=1, flags=re.S)
    source = source.replace("'dgx_'+k", "'dgx_'+COURSE.key+'_'+k")
    source = re.sub(r'  if\(day===1\) rows.push.*?\n  else rows.push.*?;\n',
        "  if(day===Math.max(...PLACES.map(p=>p.day))) rows.push(`<li><span class=\"t\">${esc(t('endTime'))}</span><span>${esc(t('end'))}</span><span></span></li>`);\n", source)
    source = source.replace('const pts = {p1:[60,60],p2:[160,50],p3:[270,70],p4:[280,150],p5:[170,160],p6:[70,220],p7:[230,240]};',
        'const pts=Object.fromEntries(PLACES.map((p,i)=>[p.id,[82+(i%2)*166,40+Math.floor(i/2)*95]]));')
    # 코스별 장소 수가 달라도 동작하는 순서 도식. 실제 경로처럼 그리지 않는다.
    source = re.sub(r'  const lp = .*?;\n  let s = `.*?`;\n  PLACES.forEach',
        '  const lp=Object.fromEntries(PLACES.map(p=>[p.id,[0,27]]));\n  let s=`<svg viewBox="0 0 330 ${Math.max(150,Math.ceil(PLACES.length/2)*95+25)}" role="img" aria-label="코스 순서">`;\n  PLACES.forEach', source, count=1, flags=re.S)
    source = source.replace("s += `<text x=\"96\" y=\"205\" font-size=\"10\" fill=\"#6e7280\">${lang==='ja'?'宿泊':'숙박'}</text></svg>`;", "s += '</svg>';")
    source = re.sub(r'  const lab = id=>.*?;\n', '  const lab=id=>PLACES.find(p=>p.id===id).short[lang];\n', source)
    source = re.sub(r'    const short = lang===.*?;\n', '    const short=p.short[lang];\n', source, flags=re.S)
    source = source.replace('${esc(lab(p.id))}</text></g>', '${(Array.from(lab(p.id)).join(\'\').match(/.{1,9}/gu)||[]).map((line,i)=>`<tspan x="${x}" dy="${i?14:0}">${esc(line)}</tspan>`).join(\'\')}</text></g>')
    source = source.replace('${L.hl?', '${L.hl&&L.hl.length?')
    source = source.replace('mapLinks(p.mapQ).map', '(p.mapQ?mapLinks(p.mapQ):[]).map')
    source = source.replace('const gq = PLACES.map(', 'const gq = PLACES.filter(p=>p.mapQ).map(')
    source = source.replace("  $('#mapAll').href =", "  $('#mapAll').hidden=gq.length<2;\n  $('#mapAll').href =")
    # 공통 UI 번역은 원본을 보존하되 일정·종료·소개 예시 문구는 실제 값으로 바꾼다.
    override = """
for(const [locale, labels] of Object.entries(T)){
 labels.brand=COURSE.title;labels.h1a=COURSE.title;labels.h1b='';
 labels.kick=COURSE.period;labels.chip1=COURSE.period;labels.chip2=String(PLACES.length)+'곳';labels.chip3='대구';
 labels.foot=locale==='ja'?COURSE.mealJa:COURSE.meal;labels.aiNote='';
 labels.tagline=COURSE.tagline;labels.day1='DAY 1';labels.day2='DAY 2';
 labels.end=String(COURSE.end.종료지점||'');labels.endTime=String(COURSE.end.종료시각||'');
 labels.mapNote='코스 순서 도식 · 실제 위치·축척과 다릅니다. 길찾기는 장소별 지도 앱에서 확인하세요.';
}
"""
    source = source.replace('/* ---------- 상태 ---------- */', override+'\n/* ---------- 상태 ---------- */')
    source = source.replace('</style>', '.stars{grid-template-columns:repeat(7,minmax(0,1fr));width:100%}.stars button{min-width:0}.stars .l{white-space:normal;overflow-wrap:anywhere;max-width:100%}.tl li{grid-template-columns:80px minmax(0,1fr) auto}.tl a,.hl span,.card p{overflow-wrap:anywhere}.hd b{min-width:0}.wrap{width:100%}.map svg{width:100%;height:auto}</style>', 1)
    source = source.replace('applyLang();\nconst JUMP', """applyLang();
for(const tab of document.querySelectorAll('.tabs button')){tab.hidden=!PLACES.some(p=>p.day===Number(tab.dataset.day));}
const JUMP"""
    )
    source = source.replace("const n=$('#jaNote'); n.hidden = lang!=='ja'; n.textContent = T.ja.aiNote;", "const n=$('#jaNote'); n.hidden = true; n.textContent = '';")
    source = re.sub(r'<!--.*?-->', '', source, flags=re.S)
    return source
