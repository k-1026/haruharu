"""내부 검토 묶음을 보존하고 공개 가능한 필드만 새 사본으로 구성한다."""
import copy
import re

식사안내 = '식사는 개별 선택·개별 결제입니다.'
_내부표현 = re.compile(r'미확인|미정|미고정|미선택|미입력|정해지지\s*않|아직\s*정하지|자료 필요|검토\s*전|검토\s*초안|AI\s*초안|근거\s*없음|수요\s*근거|경고|가정\s*값|가정값|확인\s*필요|확인\s*중|식[사비]\s*포함|식비|식사\s*제공|식사\s*방식\s*미선택|\b[RWSE]\d+\b')


def 공개문장(value):
    """미확인 문장을 사실로 고쳐 쓰지 않고 해당 문장 전체를 제외한다."""
    if not isinstance(value, str):
        return ''
    parts = re.split(r'(?<=[.!?。！？])\s+|\n|\s*/\s*', value)
    return ' '.join(p.strip() for p in parts if p.strip() and not _내부표현.search(p))


def 기본제목(조건):
    def join(value):
        return '·'.join(map(str, value)) if isinstance(value, list) else str(value or '')
    return ' '.join(x for x in [join(조건.get('지역')), join(조건.get('계절')), join(조건.get('체류기간')), '여행'] if x)[:40]


def 식사권역(meal):
    area = re.sub(r'^식사 방식 미선택\s*·\s*권역 후보:\s*', '', str(meal.get('권역') or ''))
    if meal.get('방식') != '지정식' and area in (meal.get('추천후보') or []):
        district = re.search(r'(?:대구(?:광역시)?\s*)?(중구|동구)', area)
        return district[1] + ' 자유식' if district else '자유식'
    return area


def 공개묶음(bundle):
    """내부 경고는 해결 처리하지 않는다. 공개 사본에서는 안내·시각·문구를 선별한다."""
    b = copy.deepcopy(bundle)
    excluded = []
    name = 공개문장(b.get('확인', {}).get('코스이름', '')) or 공개문장(b.get('코스카드', {}).get('코스이름', '')) or 기본제목(b.get('조건', {}))
    b.setdefault('확인', {})['코스이름'] = name
    card = b.setdefault('코스카드', {})
    card.update({'코스이름':name, '식사안내':식사안내, '남은경고':[]})
    for key in ['대상문장', '한눈에']:
        card[key] = 공개문장(card.get(key, ''))
    for row in b.get('시간표', []):
        for key in ['시각', '장소']:
            old = str(row.get(key) or '')
            if _내부표현.search(old) or '(가정)' in old:
                hour = re.match(r'(\d{1,2}):', old)
                row[key] = (('오후' if int(hour[1]) >= 12 else '오전') if hour and row.get('시간칸') == '낮' else row.get('시간칸', '')) if key == '시각' else ''
                excluded.append(f"{row.get('칸ID', '')} {key}: {old}")
        if '미선택' in str(row.get('식사', '')):
            area = 공개문장(row.get('식사권역', ''))
            row['장소'] = area or '자유식'
        row['식비포함'] = ''
        row['식사'] = 식사안내 if row.get('식사') else ''
        if isinstance(row.get('머무는시간'), str):
            row['머무는시간'] = 공개문장(row['머무는시간'])
        if isinstance(row.get('머무는시간'), str):
            row['머무는시간'] = 공개문장(row['머무는시간'])
    for scene in b.get('장면', []):
        c = scene.get('문구') or {}
        # 위치·운영·이동의 미확인은 문구 전반에 영향을 줄 수 있으므로
        # 해당 장면의 설명과 번역을 함께 제외한다. 제목/일정 자체는 보존한다.
        issues = [w for w in bundle.get('남은경고', [])
                  if scene.get('장면ID') and str(scene['장면ID']) in str(w.get('대상', ''))
                  and re.search(r'운영|영업|휴무|이동|예약|종료.*시각|시각.*미정', str(w.get('경고', '')) + ' ' + str(w.get('대상', '')))]
        text_changed = False
        for key in ['제목', '본문']:
            old = c.get(key, '')
            c[key] = '' if issues and key == '본문' else 공개문장(old)
            if old != c[key]:
                text_changed = True
                excluded.append(f"{scene.get('장면ID', '')} {key}: {old}")
        c['말풍선'] = {} if issues else {k:공개문장(v) for k,v in (c.get('말풍선') or {}).items() if 공개문장(v)}
        c.pop('사실근거', None); c.pop('경고', None)
        if (issues or text_changed) and scene.get('번역'):
            excluded.append(f"{scene.get('장면ID', '')} 번역: 원문에서 제외한 안내와 함께 제외")
        scene['번역'] = [] if issues or text_changed else [dict(언어=t.get('언어',''), 번역=공개문장(t.get('번역',''))) for t in scene.get('번역', [])]
        scene['문구'] = c
    rows = {(r.get('안', '공통'), r.get('칸ID')):r for r in b.get('시간표', [])}
    scenes = []
    for scene in b.get('장면', []):
        row = rows.get((scene.get('안', '공통'), scene.get('장면ID')), {})
        scene['장소'] = row.get('장소', '')
        if scene['장소']:
            scenes.append(scene)
    b['장면'] = scenes
    b['시간표'] = [r for r in b.get('시간표', []) if r.get('장소')]
    public_rows = {(r.get('안', '공통'), r.get('칸ID')):r for r in b['시간표']}
    b['대응표'] = [{**d, '장소':public_rows[(d.get('안', '공통'),d.get('장면ID'))]['장소']}
                 for d in b.get('대응표', []) if (d.get('안', '공통'),d.get('장면ID')) in public_rows]
    card['한눈에'] = ' → '.join(r['장소'] for r in b['시간표'])
    b['시작종료'] = {k:공개문장(str(v or '')) for k,v in b.get('시작종료', {}).items()}
    b['운영방식'] = 공개문장(b.get('운영방식', ''))
    def 협력후보(value):
        return 공개문장(re.sub(r'\([^)]*\[U\][^)]*\)', '', str(value))).strip()
    b['운영주체후보'] = [협력후보(o) for o in b.get('운영주체후보', []) if 협력후보(o)]
    b['받는쪽'] = 협력후보(b.get('받는쪽', ''))
    b['남은경고'] = []; b['표현필터'] = []
    b['_공개제외'] = excluded
    return b


def 공개내보내기(bundle):
    b = 공개묶음(bundle)
    return {'코스이름':b['확인']['코스이름'], '조건':b['조건'], '식사안내':식사안내,
            '시간표':[{k:r.get(k) for k in ['일차','시간칸','시각','장소','머무는시간']} for r in b['시간표']],
            '장면':[{'장소':s['장소'], '제목':s['문구'].get('제목',''), '본문':s['문구'].get('본문',''),
                     '번역':s['번역']} for s in b['장면']]}
