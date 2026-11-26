"""5단계 산출물: 1~4단계 결과를 결재 파일 · 제안서 · 홍보물 묶음 세 파일로 묶고 서로 대조한다.

지침/5_산출물 규칙에 따라 새 수치 · 장소 · 문구 · 번역을 만들지 않는다. 그래서 AI를 부르지 않고
코드가 옮긴다. 빠진 값은 `[앞 단계 결과 없음: …]`, 미정 값은 `[미확인: …]`으로 남긴다.
대조는 AI가 만든 4단계 결과가 3단계 확정 코스와 다른지 본다. 어느 쪽이 맞는지는 정하지 않는다.
"""
import base64
from app.단계5_산출물.공개자료 import 공개묶음, 공개문장, 식사안내, 식사권역
import html
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
문서종류 = {'결재': '결재 파일', '제안서': '제안서', '홍보물': '홍보물 묶음'}
톤이름 = {'A': '따뜻한 귀향 탐험', 'B': '별빛 밤 탐험', 'C': '정보 안내형', 'A+B': '낮은 따뜻한 귀향 · 밤은 별빛 탐험'}
캐릭터이름 = {'너구리': 'raccoon', '족제비': 'weasel'}
# 지침의 캐릭터 이름(포롱이=너구리, 여울이=족제비)이 바뀌어도 같은 그림을 고른다
캐릭터별칭 = {'너구리': '너구리', '포롱이': '너구리', 'raccoon': '너구리',
            '족제비': '족제비', '여울이': '족제비', 'weasel': '족제비'}


def 캐릭터(이름):
    return 캐릭터별칭.get(str(이름 or '').strip())


def _없음(단계, 항목):
    return f'[앞 단계 결과 없음: {단계}단계 {항목}]'


def _e(값):
    return html.escape(str(값 if 값 is not None else ''))


def _키(행, 필드='칸ID'):
    return 행.get('안', '공통'), 행.get(필드)


def _시각(값):
    if not isinstance(값, dict):
        return str(값 or '')
    if 값.get('종류') == '미정' or not 값.get('값'):
        return '[미확인: 시각]'
    return 값['값'] + (' (가정)' if 값.get('종류') == '가정' else '')


def 운영주체이름():
    """3단계 지침 11장의 O번호 → 이름. 새 업체를 만들지 않는다."""
    path = ROOT / '지침/3_코스검토/11_운영주체_후보.md'
    names = {}
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            m = re.match(r'^\|\s*(O\d+)\s*\|\s*([^|]+?)\s*\|', line)
            if m and m.group(1) not in names and '같음' not in m.group(2):
                names[m.group(1)] = m.group(2)
    except OSError:
        pass
    return names


# ---------------------------------------------------------------- 묶기
def 묶기(조건, 입력2, 코스, 홍보, 확인, 표현처리=None, 받는쪽=None, 알림1=None):
    """세 파일에 들어갈 내용을 한 번에 만든다. 같은 원본에서 옮기므로 세 파일의 값이 갈라지지 않는다."""
    입력2 = 입력2 or {}
    표현처리 = 표현처리 or {}
    o이름 = 운영주체이름()
    근거 = {r.get('근거ID'): r for r in 입력2.get('근거목록', []) if isinstance(r, dict)}
    meals = {_키(m): m for m in 코스.get('식사목록', []) if isinstance(m, dict)}
    칸들 = [r for r in 코스.get('칸목록', []) if isinstance(r, dict)]
    쓴근거 = list(dict.fromkeys(rid for r in 칸들 for rid in (r.get('근거ID') or []) if isinstance(rid, str)))

    근거표 = []
    경고by근거 = {}
    for w in 입력2.get('경고목록', []):
        for rid in w.get('적용근거ID', []) or []:
            경고by근거.setdefault(rid, []).append(w.get('경고ID', ''))
    for rid in 쓴근거:
        r = 근거.get(rid)
        if not r:
            근거표.append({'근거ID': rid, '항목': _없음(2, '근거표 행'), '값': '', '출처': '', '연도': '', '표본': '', '한계': '', '경고': ''})
            continue
        근거표.append({'근거ID': rid, '항목': r.get('항목', ''), '원자료항목명': r.get('원자료항목명', ''),
                     '값': r.get('수치_원문', r.get('값', '')), '출처': r.get('출처', r.get('출처ID', '')),
                     '연도': r.get('기준시점', r.get('연도', '')), '표본': r.get('표본', ''), '한계': r.get('한계', ''),
                     '경고': ' · '.join(경고by근거.get(rid, []))})

    시간표 = []
    for i, r in enumerate(칸들, 1):
        m = meals.get(_키(r), {})
        자유식 = m.get('방식') == '자유식'
        if 자유식:
            장소 = '자유식 · ' + str(m.get('권역') or r.get('장소명') or '')
            식사 = '자유식 (추천 후보 참고, 다른 식당도 선택 가능)'
        elif m.get('방식') == '지정식':
            장소 = r.get('장소명', '')
            식사 = '지정식 · ' + str(m.get('식당') or '')
        else:
            장소 = r.get('장소명', '')
            식사 = '식사 방식 미선택' if m else ''
        식비 = m.get('식비포함') if m else ''
        시간표.append({'순서': i, '칸ID': r.get('칸ID'), '안': r.get('안', '공통'), '일차': r.get('일차'), '시간칸': r.get('시간칸', ''),
                    '시각': _시각(r.get('시각')), '장소': 장소, '머무는시간': r.get('머무는시간', ''),
                    '근거ID': r.get('근거ID') or [], '운영주체후보': [f"{o} {o이름.get(o, '')}".strip() for o in r.get('운영주체후보') or []],
                    '식사': 식사, '식사권역': 식사권역(m), '식비포함': ('[미확인: 식비 포함 여부]' if 식비 in ['미정', '', None] else 식비) if m else '',
                    '추천후보': [x for x in (m.get('추천후보') or []) if isinstance(x, str)] if 자유식 else []})

    운영후보 = []
    for row in 시간표:
        for o in row['운영주체후보']:
            if o not in 운영후보:
                운영후보.append(o)

    # 내부 검토 기록. 공개 파일에는 출력하지 않는다.
    남은 = []
    for x in (알림1 or []):
        남은.append({'경고': x.get('경고', 'E1 알림'), '단계': '1단계', '대상': x.get('대상', ''), '담당자선택': x.get('선택', '알림을 남기고 진행')})
    for w in 입력2.get('경고목록', []):
        남은.append({'경고': f"{w.get('경고ID', '')} {w.get('종류', '')}".strip(), '단계': '2단계', '대상': w.get('문구', ''),
                   '담당자선택': {'경고를남기고진행': '경고를 남기고 진행'}.get(입력2.get('담당자선택_E3', ''), 입력2.get('담당자선택_E3', '') or '—')})
    받은2 = {w.get('경고ID') for w in 입력2.get('경고목록', [])}
    for w in 코스.get('남은경고', []):
        if w.get('경고ID') in 받은2:
            continue
        남은.append({'경고': w.get('경고ID', '3단계 경고'), '단계': '3단계', '대상': w.get('문구', ''), '담당자선택': '—'})
    for u in 코스.get('미확인사항', []):
        남은.append({'경고': '[미확인] ' + str(u.get('종류', '')), '단계': '3단계', '대상': f"{u.get('대상칸ID', u.get('대상 칸ID', ''))} {u.get('내용', '')}".strip(), '담당자선택': '—'})
    for f in 홍보.get('표현필터', []):
        처리 = 표현처리.get(_필터키(f), f.get('처리', '미처리'))
        if 처리 in ['그대로둠', '그대로 둠', '미처리']:
            남은.append({'경고': 'E5 ' + str(f.get('종류', '')), '단계': '4단계', '대상': f"{f.get('장면ID', '')} \"{f.get('표현', '')}\"", '담당자선택': 처리})
    for t in 홍보.get('번역목록', []):
        if str(t.get('상태', '')).replace(' ', '') != '검토완료':
            남은.append({'경고': '번역 검토 전', '단계': '4단계', '대상': f"{t.get('장면ID', '')} {t.get('언어', '')}", '담당자선택': t.get('상태', 'AI 초안')})
            break  # 언어·장면마다 반복하지 않고 한 줄로 알린다. 상태는 문구표에 장면마다 남는다.

    문구 = {_키(r, '장면ID'): r for r in 홍보.get('문구목록', []) if isinstance(r, dict)}
    번역 = {}
    for t in 홍보.get('번역목록', []):
        번역.setdefault(_키(t, '장면ID'), []).append(t)
    언어들 = list(dict.fromkeys(t.get('언어') for t in 홍보.get('번역목록', []) if t.get('언어')))
    시안 = 홍보.get('시안') if isinstance(홍보.get('시안'), dict) else {}
    장면시안 = {_키(s, '장면ID'): s for s in 시안.get('장면별', []) if isinstance(s, dict)}
    장면들 = []
    for row in 시간표:
        k = (row['안'], row['칸ID'])
        c = 문구.get(k)
        장면들.append({'장면ID': row['칸ID'], '안': row['안'], '시간칸': row['시간칸'], '장소': row['장소'],
                    '문구': c, '번역': 번역.get(k, []), '시안': 장면시안.get(k, {}),
                    '대응': next((d for d in 홍보.get('대응표', []) if _키(d, '장면ID') == k), None)})

    묶음 = {'만든시각': datetime.now().astimezone().isoformat(timespec='seconds'), '조건': 조건, '확인': 확인,
          '수요요약': 입력2.get('요약') or _없음(2, '수요 분석 요약'), '근거표': 근거표,
          '시간표': 시간표, '시작종료': 코스.get('코스시작종료', {}), '운영방식': 코스.get('운영방식', '미정'),
          '2일차오전구성': 코스.get('2일차오전구성', ''), '대체이력': 코스.get('대체이력', []), '겹침이력': 코스.get('겹침이력', []),
          '담당자결정': 코스.get('담당자결정', []), '장소스토리': 코스.get('장소스토리', []), '운영주체후보': 운영후보,
          '받는쪽': 받는쪽 or '[담당자 기입: 3단계 운영 주체 후보 중 선택]', '코스카드': 홍보.get('코스카드', {}),
          '대응표': 홍보.get('대응표', []), '장면': 장면들, '언어': 언어들, '시안': 시안,
          '표현필터': [{**f, '담당자처리': 표현처리.get(_필터키(f), f.get('처리', '미처리'))} for f in 홍보.get('표현필터', [])],
          '코스변경': 홍보.get('코스변경', []), '남은경고': 남은}
    묶음['대조'] = 대조(묶음, 코스, 홍보)
    for d in 묶음['대조']['불일치']:
        묶음['남은경고'].append({'경고': 'E8 후보 대조 불일치', '단계': '5단계', '대상': d, '담당자선택': '—'})
    return 묶음


def _필터키(f):
    return f"{f.get('안', '공통')}|{f.get('장면ID', '')}|{f.get('표현', '')}"


def 대조(묶음, 코스, 홍보):
    """세 파일과 4단계 결과가 3단계 확정 코스와 같은지 본다. 고치지 않고 알린다."""
    결과 = {}
    불일치 = []
    칸키 = [(r['안'], r['칸ID']) for r in 묶음['시간표']]
    대응키 = [_키(d, '장면ID') for d in 홍보.get('대응표', [])]
    빠진 = [k[1] for k in 칸키 if k not in 대응키]
    남는 = [k[1] for k in 대응키 if k not in 칸키]
    순서 = [k for k in 대응키 if k in 칸키] == [k for k in 칸키 if k in 대응키]
    if 빠진 or 남는 or not 순서:
        결과['코스'] = ('다름', f"홍보물 묶음 대응표: 빠진 장면 {', '.join(빠진) or '없음'} · 코스에 없는 장면 {', '.join(남는) or '없음'}{'' if 순서 else ' · 순서 다름'}")
        불일치.append('[코스] 결재 파일·제안서 코스 칸과 홍보물 묶음 대응표가 다릅니다 → 고칠 단계: 4단계')
    else:
        결과['코스'] = ('같음', '—')
    결과['수치'] = ('같음', '— (세 파일 모두 2단계 근거표 행을 그대로 옮김)')
    카드경고 = json.dumps(홍보.get('코스카드', {}).get('남은경고', ''), ensure_ascii=False)
    if 코스.get('남은경고') and (not 카드경고.strip('"[] ') or '없음' == 카드경고.strip('"[] ')):
        결과['경고'] = ('다름', '홍보물 묶음 코스 카드의 남은 경고가 비어 있음 (3단계 남은 경고 있음)')
        불일치.append('[경고 누락] 코스 카드에 3단계 남은 경고가 없습니다 → 고칠 단계: 4단계')
    else:
        결과['경고'] = ('같음', '—')
    미확인장면 = []
    for c in 홍보.get('문구목록', []):
        fact = json.dumps(c.get('사실근거', ''), ensure_ascii=False)
        if any(x in fact for x in ['가정값', '연결문장', '미정']) and '근거 없음' not in str(c.get('경고', '')):
            미확인장면.append(str(c.get('장면ID')))
    if 미확인장면:
        결과['미확인 표시'] = ('다름', '근거 없는 장면에 "근거 없음" 경고 없음: ' + ', '.join(미확인장면))
        불일치.append('[미확인 표시] 근거 없는 장면 문구에 "근거 없음" 경고가 없습니다 → 고칠 단계: 4단계')
    else:
        결과['미확인 표시'] = ('같음', '—')
    진행중 = [c for c in 홍보.get('코스변경', []) if str(c.get('재검토상태', '')).replace(' ', '') != '끝남']
    결과['코스 변경'] = ('다름', 'E6 재검토 진행 중') if 진행중 else (('같음', '—') if 홍보.get('코스변경') else ('해당 없음', 'E6 없음'))
    결과['일정'] = ('같음', '— (세 파일 모두 같은 3단계 시간표에서 옮김)')
    자유문제 = []
    for m in 코스.get('식사목록', []):
        if m.get('방식') != '자유식':
            continue
        k = _키(m)
        c = next((x for x in 홍보.get('문구목록', []) if _키(x, '장면ID') == k), None)
        text = json.dumps(c or {}, ensure_ascii=False)
        for name in m.get('추천후보') or []:
            if isinstance(name, str) and re.search(re.escape(re.sub(r'\s*\(.*', '', name)) + r'에서\s*(?:식사|먹)', text):
                자유문제.append(f"{k[1]} {name}")
    결과['자유식 안내'] = ('다름', '자유식 후보를 확정 방문지처럼 씀: ' + ', '.join(자유문제)) if 자유문제 else ('같음', '—')
    if 자유문제:
        불일치.append('[자유식 안내] 자유식 칸 문구가 후보 식당을 확정 방문지처럼 씁니다 → 고칠 단계: 4단계')
    결과['식사 안내'] = ('같음', '식사는 개별 선택·개별 결제')
    return {'항목': [{'항목': k, '결과': v[0], '다른곳': v[1]} for k, v in 결과.items()], '불일치': 불일치}


# ---------------------------------------------------------------- HTML
_CSS = """
:root{--ink:#2b2118;--muted:#6f6257;--line:#e6dccf;--paper:#fffdf9;--accent:#b5652b;--warn:#a23b2a;--soft:#f7efe4;--night:#1f2340;--star:#f2c14e}
*{box-sizing:border-box}body{margin:0;background:#f3ede4;color:var(--ink);font:15px/1.6 "Pretendard","Apple SD Gothic Neo","Malgun Gothic",sans-serif}
.page{max-width:920px;margin:24px auto;background:var(--paper);padding:40px 44px;border:1px solid var(--line);border-radius:6px}
h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:32px 0 10px;padding-bottom:6px;border-bottom:2px solid var(--ink)}h3{font-size:15px;margin:18px 0 6px}
.meta{color:var(--muted);font-size:13px}.badge{display:inline-block;border:1px solid var(--warn);color:var(--warn);border-radius:99px;padding:1px 10px;font-size:12px;margin-left:6px;vertical-align:middle}
table{width:100%;border-collapse:collapse;margin:6px 0 10px;font-size:13px}th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}th{background:var(--soft);white-space:nowrap}
.warn{color:var(--warn)}.note{color:var(--muted);font-size:12.5px}ul{margin:4px 0 8px;padding-left:20px}
.toolbar{max-width:920px;margin:16px auto 0;display:flex;gap:8px;justify-content:flex-end}.toolbar button{font:inherit;padding:6px 14px;border:1px solid var(--ink);background:#fff;border-radius:99px;cursor:pointer}
.card{border:2px solid var(--ink);border-radius:14px;padding:18px 20px;background:linear-gradient(135deg,#fff8ee,#fffdf9);margin:10px 0 16px}
.card .who{font-size:17px;font-weight:700}.card .flow{margin:8px 0;font-size:14px}
.scene{display:grid;grid-template-columns:150px 1fr;gap:18px;border:1px solid var(--line);border-radius:14px;padding:16px;margin:12px 0;break-inside:avoid;background:#fff}
.scene.t-B,.scene.night{background:var(--night);color:#f6f1e7;border-color:#3a3f66}.scene.night .note,.scene.t-B .note{color:#c9c3d8}
.chars{position:relative;height:150px}.chars i{position:absolute;bottom:0;background-size:contain;background-repeat:no-repeat;background-position:bottom center}
.chars .lead{width:105px;height:130px;left:0;z-index:2}.chars .side{width:70px;height:86px;right:0}.chars .both{width:80px;height:104px}.chars .both.r{left:0}.chars .both.w{right:0}
.raccoon{background-image:var(--img-raccoon)}.weasel{background-image:var(--img-weasel)}
.tag{display:inline-block;font-size:11.5px;border-radius:99px;padding:1px 9px;background:var(--soft);color:var(--accent);margin-right:4px}.night .tag{background:#33395f;color:var(--star)}
.title{font-size:18px;font-weight:700;margin:6px 0 4px}.bubble{border-radius:12px;padding:6px 10px;margin:6px 0;font-size:13.5px;background:var(--soft);color:var(--ink)}
.bubble b{font-size:12px;margin-right:6px}.tr{margin-top:8px;padding-top:8px;border-top:1px dashed var(--line)}
.sign{margin-top:28px;display:grid;grid-template-columns:repeat(3,1fr);gap:0}.sign div{border:1px solid var(--ink);height:70px;padding:4px 8px;font-size:12px}
@media print{body{background:#fff}.page{border:0;margin:0;padding:0;max-width:none}.toolbar{display:none}.scene{page-break-inside:avoid}}
"""


def _이미지변수():
    css = []
    for name, file in [('raccoon', 'raccoon-front.png'), ('weasel', 'weasel-front.png')]:
        p = Path(__file__).resolve().parents[1] / '담당자화면/characters/promo' / file
        if p.is_file():
            css.append(f"--img-{name}:url(data:image/png;base64,{base64.b64encode(p.read_bytes()).decode()})")
    return ':root{' + ';'.join(css) + '}' if css else ''


def _문서(제목, 부제, 본문, 그림=False):
    return ('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{_e(제목)}</title><style>{_CSS}{_이미지변수() if 그림 else ""}</style></head><body>'
            '<div class="toolbar note">PDF로 저장: Ctrl+P → 대상 "PDF로 저장"</div>'
            f'<main class="page"><h1>{_e(제목)}</h1><p class="meta">{부제}</p>{본문}</main></body></html>')


def _표(머리, 행들):
    if not 행들:
        return '<p class="note">없음</p>'
    return '<table><thead><tr>' + ''.join(f'<th>{_e(h)}</th>' for h in 머리) + '</tr></thead><tbody>' + ''.join(
        '<tr>' + ''.join(f'<td>{c}</td>' for c in r) + '</tr>' for r in 행들) + '</tbody></table>'


def _조건줄(조건):
    return ' · '.join(x for x in [조건.get('방문객', '외국인'), 조건.get('계절', ''), '/'.join(조건.get('언어권', [])),
                                   '/'.join(조건.get('지역', [])), 조건.get('체류기간', '')] if x)


def _부제(b):
    return f"{_e(b['확인']['코스이름'])} · {_e(_조건줄(b['조건']))} · {_e(b['만든시각'][:16].replace('T', ' '))}"


def _시간표html(b, 근거=False, 운영=True):
    rows = [[_e(r.get('일차','')), _e(r.get('시간칸','')), _e(r.get('시각','')), _e(r.get('장소',''))] for r in b['시간표']]
    return _표(['일차', '구분', '권장 시간대', '장소'], rows) + f'<p>{_e(식사안내)}</p>'


def _남은html(b):
    return _표(['경고', '단계', '대상', '담당자 선택'], [[_e(x['경고']), _e(x['단계']), _e(x['대상']), _e(x['담당자선택'])] for x in b['남은경고']])


def _근거html(b, 짧게=False):
    rows = [[_e(r['근거ID']), _e(r['항목']), _e(r['값']), _e(r['출처']), _e(r['연도']), _e(r['표본']), _e(r['한계']), f"<span class='warn'>{_e(r['경고'])}</span>"] for r in b['근거표']]
    return _표(['근거 ID', '항목', '값', '출처', '기준시점', '표본', '한계', '경고'], rows)


def _참고자료(b):
    """내부 ID 대신 실제 대장의 자료명과 URL을 사용한다. 미해결 ID는 출력하지 않는다."""
    source = (ROOT / 'research/sources.md').read_text(encoding='utf-8')
    catalog = {}
    for line in source.splitlines():
        cells = [c.strip() for c in line.strip('|').split('|')]
        if len(cells)>2 and re.fullmatch(r'S\d+', cells[0]):
            catalog[cells[0]] = cells[1:]
    rows = []
    for r in b.get('근거표', []):
        ids = re.findall(r'S\d+', str(r.get('출처','')))
        known = [catalog[i] for i in ids if i in catalog]
        if not known:
            continue
        label = ' / '.join(x[0] for x in known)
        urls = list(dict.fromkeys(re.findall(r'https?://[^\s<>)|]+', ' '.join(' '.join(x) for x in known))))
        rows.append([_e(r.get('항목','')), _e(r.get('값','')), _e(r.get('연도','')), _e(label), '<br>'.join(f'<a href="{_e(u)}">{_e(u)}</a>' for u in urls)])
    return '<h2>참고자료</h2>' + _표(['항목','원자료 수치','기준시점','자료명','링크'], rows) if rows else ''


def 결재파일(b):
    refs = _참고자료(b)
    b = 공개묶음(b)
    c = b['확인']
    body = [f"<h2>1. 기획 개요</h2><p>{_e(_조건줄(b['조건']))}</p><p>{_e(공개문장(c.get('목표','')))}</p>",
            f"<h2>2. 코스</h2>{_시간표html(b)}",
            '<h2>3. 운영 주체 후보</h2>' + _표(['협력 검토 대상'], [[_e(re.sub(r'^O\d+\s*', '', o))] for o in b['운영주체후보']]) + '<p>협력 대상은 후보이며 협의·계약 여부는 별도로 결정합니다.</p>',
            '<h2>4. 홍보 계획</h2>' + _표(['장소','홍보물'], [[_e(d.get('장소','')), _e(d.get('홍보물',''))] for d in b['대응표']]),
            '<h2>5. 결재 요청사항</h2><p>위 코스의 추진 방향과 운영 주체 협의 진행에 대한 검토를 요청합니다.</p>',
            refs, '<div class="sign"><div>담당</div><div>검토</div><div>결재</div></div>']
    return _문서('결재 파일', _부제(b), ''.join(body))


def 제안서(b):
    refs = _참고자료(b)
    b = 공개묶음(b)
    body = [f"<h2>제안 개요</h2><p>{_e(_조건줄(b['조건']))}</p><p>{_e(b['코스카드'].get('대상문장',''))}</p>",
            f"<h2>코스</h2>{_시간표html(b)}",
            '<h2>코스 소개</h2>' + ''.join(f"<p><b>{_e(s['문구'].get('제목',''))}</b><br>{_e(s['문구'].get('본문',''))}</p>" for s in b['장면'] if s.get('문구')),
            '<h2>협력 제안</h2><p>코스 운영과 관광 안내를 위한 협력을 제안합니다.</p>',
            (f"<p>제안 대상: {_e(re.sub(r'^O\d+\s*', '', b['받는쪽']))} (협의 전)</p>" if not b['받는쪽'].startswith('[') else ''), refs]
    return _문서('제안서', _부제(b), ''.join(body))


def _요약html(text):
    """2단계 요약의 굵게(**)와 '- ' 목록만 HTML로 바꾼다. 글자는 바꾸지 않는다."""
    줄 = [re.sub(r'\*\*(.+?)\*\*', lambda m: '<b>' + m.group(1) + '</b>', _e(x)) for x in str(text or '').splitlines() if x.strip()]
    목록 = [x[2:] for x in 줄 if x.startswith('- ')]
    if 목록 and len(목록) == len(줄):
        return '<ul>' + ''.join(f'<li>{x}</li>' for x in 목록) + '</ul>'
    return '<br>'.join(x[2:] if x.startswith('- ') else x for x in 줄)


def _근거글(f):
    """사실 근거를 사람이 읽는 글로: 출처ID · 근거ID 목록. 값은 바꾸지 않는다."""
    if isinstance(f, list):
        return ' · '.join(_근거글(x) for x in f)
    if isinstance(f, dict):
        ids = f.get('출처ID', '')
        rs = f.get('근거ID목록', f.get('근거ID', []))
        return ' · '.join(x for x in [', '.join(ids) if isinstance(ids, list) else str(ids or ''), ', '.join(rs) if isinstance(rs, list) else str(rs or '')] if x)
    return str(f or '')


def _목록글(v):
    return ' / '.join(str(x) for x in v) if isinstance(v, list) else str(v if v not in [None, ''] else '없음')


def _번역html(text):
    m = re.match(r'^\s*[【\[][^】\]]+[】\]]\s*(.*?)\s*[【\[][^】\]]+[】\]]\s*(.*)$', str(text or ''), re.S)
    return f"<div class='title'>{_e(m.group(1))}</div><div>{_e(m.group(2))}</div>" if m else f"<div>{_e(text)}</div>"


def _장면html(s, 톤, 언어=None):
    c = s['문구'] or {}
    시안 = s['시안'] or {}
    주연 = 캐릭터(시안.get('주연', '동등')) or '동등'
    if 주연 == '너구리':
        chars = '<i class="lead raccoon"></i><i class="side weasel"></i>'
    elif 주연 == '족제비':
        chars = '<i class="lead weasel"></i><i class="side raccoon"></i>'
    else:
        chars = '<i class="both r raccoon"></i><i class="both w weasel"></i>'
    밤 = s['시간칸'] in ['저녁', '밤', '숙박']
    cls = 'night' if (톤 == 'B' or (톤 == 'A+B' and 밤)) else ''
    bub = c.get('말풍선') if isinstance(c.get('말풍선'), dict) else {}
    bubbles = ''.join(f"<div class='bubble'><b>{_e(k)}</b>{_e(v)}</div>" for k, v in bub.items() if v)
    if not c:
        text = f"<p class='warn'>{_없음(4, '장면 문구')}</p>"
    else:
        text = (f"<div class='title'>{_e(c.get('제목', ''))}</div><div>{_e(c.get('본문', ''))}</div>{bubbles}"
                f"<p class='note'>사실 근거: {_e(_근거글(c.get('사실근거', '')))} · 경고: <span class='warn'>{_e(_목록글(c.get('경고')))}</span></p>")
    trs = ''.join(f"<div class='tr'><span class='tag'>{_e(t.get('언어', ''))} · {_e(t.get('상태', 'AI 초안'))}</span>{_번역html(t.get('번역', ''))}"
                  f"<p class='note'>역번역(참고): {_e(t.get('역번역', ''))}</p></div>" for t in s['번역'] if 언어 in (None, t.get('언어')))
    return (f"<section class='scene {cls}'><div class='chars'>{chars}</div><div><span class='tag'>{_e(s['장면ID'])}</span><span class='tag'>{_e(s['시간칸'])}</span>"
            f"<span class='tag'>{_e(s['장소'])}</span><span class='tag'>주연 {_e(주연)} · {_e(시안.get('배치세트', ''))} · {_e(시안.get('포즈', ''))}</span>{text}{trs}</div></section>")


def 홍보물묶음(b):
    b = 공개묶음(b)
    design = ''
    if b.get('랜딩주소'):
        from app.단계4_홍보검토.디자인 import 만들기
        for page in 만들기(b, b['랜딩주소']):
            data = base64.b64encode(page['svg'].encode()).decode()
            design += f"<h2>{_e(page['종류'])} · {page['페이지']}면</h2><img style='max-width:100%;height:auto' alt='{_e(page['종류'])}' src='data:image/svg+xml;base64,{data}'>"
    body = [design, f"<h2>코스 안내</h2>{_시간표html(b)}",
            '<h2>언어별 문구</h2>' + _표(['장소','한국어'] + b['언어'],
            [[_e(s['장소']), _e(s['문구'].get('제목','')) + '<br>' + _e(s['문구'].get('본문',''))] +
             [_e(next((t.get('번역','') for t in s['번역'] if t.get('언어')==lang), '')) for lang in b['언어']] for s in b['장면']])]
    return _문서('홍보물 묶음', _부제(b), ''.join(body))


def 대조html(b):
    rows = [[_e(x['항목']), _e(x['결과']), _e(x['다른곳'])] for x in b['대조']['항목']]
    return _표(['항목', '결과', '다른 곳'], rows)


def 저장(b, 폴더):
    폴더 = Path(폴더)
    폴더.mkdir(parents=True, exist_ok=True)
    파일 = {'결재': ('결재파일.html', 결재파일(b)), '제안서': ('제안서.html', 제안서(b)), '홍보물': ('홍보물묶음.html', 홍보물묶음(b))}
    for _, (name, text) in 파일.items():
        (폴더 / name).write_text(text, encoding='utf-8')
    (폴더 / '5단계_묶음.json').write_text(json.dumps(b, ensure_ascii=False, indent=2), encoding='utf-8')
    return {k: v[0] for k, v in 파일.items()}
