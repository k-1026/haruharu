"""하네스 4단계(홍보) 채점: 홍보 폴더에 남은 파일만 읽어 통과/실패를 매긴다. AI를 부르지 않는다(토큰 0).

제품 검사(단계연결.홍보_검사: 형식·장면ID·번역 상태·상호·용어집·출처ID) 결과는 그대로 읽고,
제품에 없는 규칙(공개 문구의 내부 ID·금지 표현·번역 언어·식비 안내)만 여기서 센다.
판단이 필요한 항목(스토리 사실 여부, 출처 등급)은 코드로 보지 않는다 → 다음에 검증 에이전트로.
"""
import json
import re
from pathlib import Path

제한초 = 420  # 제품 설정 run_stage.역할_제한초['홍보검토.md'] (AI 응답 한 번의 상한)

# 지침/4_홍보검토/5_표현_필터.md 1장 '걸러 낼 표현' 중 낱말로 찾을 수 있는 것
금지표현 = ['대구 1등', '가장 맛있는', '최고의', '원조', '최초', '유일한', '언제든', '365일',
        '꼭 먹어야', '반드시 들러야', '필수 코스', '음식 중복 없는', '식사 포함',
        '공항 픽업', '픽업 포함', '모셔다', '교통편 제공',
        '치킨 도시', '치킨의 도시', '치킨의 수도', 'K-치킨벨트 대표', '치킨명소 선정']
# 공개 문구에 들어가면 안 되는 내부 표시 (홍보실행._요청: 근거 ID·경고·미확인·검토 상태를 넣지 않는다)
내부표시 = re.compile(r'(?<![A-Za-z0-9])[RSCOPW]\d{1,4}(?![A-Za-z0-9])|미확인|검토 전|AI 초안|\[자료 필요')


def _읽기(폴더, 이름):
    p = Path(폴더) / 이름
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding='utf-8'))
    except ValueError:
        return None


def _항목(이름, 통과, 메모):
    return {'항목': 이름, '결과': '통과' if 통과 else '실패', '메모': 메모}


def 공개글(홍보):
    """관광객이 보는 글: (어디, 글) 목록. 사실근거·경고·표현필터 칸은 넣지 않는다."""
    글 = []
    카드 = 홍보.get('코스카드') or {}
    for k in ['대상문장', '코스이름', '한눈에']:
        if isinstance(카드.get(k), str):
            글.append((f'코스카드.{k}', 카드[k]))
    for m in 카드.get('식사안내') or []:
        if isinstance(m, dict) and isinstance(m.get('안내'), str):
            글.append((f"코스카드.식사안내 {m.get('칸ID')}", m['안내']))
    for r in 홍보.get('문구목록') or []:
        for k in ['제목', '본문']:
            if isinstance(r.get(k), str):
                글.append((f"문구 {r.get('장면ID')} {k}", r[k]))
        for 누구, 말 in (r.get('말풍선') or {}).items():
            if isinstance(말, str):
                글.append((f"문구 {r.get('장면ID')} 말풍선 {누구}", 말))
    for r in 홍보.get('번역목록') or []:
        for k in ['번역', '역번역']:  # 역번역(한국어)으로 번역문의 금지 표현도 본다
            if isinstance(r.get(k), str):
                글.append((f"번역 {r.get('장면ID')} {r.get('언어')} {k}", r[k]))
    return 글


def 채점(폴더, 입력):
    """폴더 = 홍보_* 폴더. 입력 = {'조건':..., '확정':...}."""
    진행 = _읽기(폴더, '홍보_진행.json') or {}
    크기 = _읽기(폴더, '하네스_크기.json') or {'호출': []}
    검사 = (_읽기(폴더, '4단계_검사.json') or {}).get('검사결과')
    홍보 = _읽기(폴더, '4단계_구조화.json')
    오류 = _읽기(폴더, 'AI_오류.json')
    호출 = 크기.get('호출') or []
    항목 = []

    초들 = [c['경과초'] for c in 호출]
    항목.append(_항목(f'시간(호출마다 {제한초}초 이하)', bool(초들) and all(s <= 제한초 for s in 초들) and not any(c.get('오류') for c in 호출),
                     ' · '.join(f"{i + 1}회 {c['경과초']}초" + (f" ({c['오류']})" if c.get('오류') else '') for i, c in enumerate(호출)) or f"기록 없음 (상태: {진행.get('상태')})"))
    항목.append(_항목('형식·참조 검사(제품 홍보_검사)', 홍보 is not None and 검사 == ['통과'],
                     '통과' if 검사 == ['통과'] else '; '.join((검사 or ['결과 없음'])[:3])))
    항목.append(_항목('첫 시도에 검사 통과(다시 쓰기 없음)', 검사 == ['통과'] and len(호출) == 1,
                     f'AI 호출 {len(호출)}회'))

    if 홍보 is None:
        for n in ['공개 문구에 내부 표시 없음', '금지 표현 없음', '번역 언어·장면 맞음', '식비 미정 안내 없음']:
            항목.append(_항목(n, False, '홍보 결과가 없어 볼 수 없음'))
    else:
        글 = 공개글(홍보)
        내부 = [f'{어디}: {m.group(0)}' for 어디, t in 글 for m in [내부표시.search(t)] if m]
        항목.append(_항목('공개 문구에 내부 표시 없음', not 내부, '; '.join(내부[:4]) or f'공개 글 {len(글)}곳 확인'))
        금지 = [f'{어디}: {w}' for 어디, t in 글 for w in 금지표현 if w in t]
        항목.append(_항목('금지 표현 없음', not 금지, '; '.join(금지[:4]) or '없음'))

        언어권 = set((입력.get('조건') or {}).get('언어권') or [])
        번역 = 홍보.get('번역목록') or []
        장면 = {r.get('장면ID') for r in 홍보.get('문구목록') or []}
        다른언어 = sorted({r.get('언어') for r in 번역} - 언어권)
        빠짐 = sorted(f'{s}/{l}' for s in 장면 for l in 언어권
                    if not any(r.get('장면ID') == s and r.get('언어') == l for r in 번역))
        항목.append(_항목('번역 언어·장면 맞음', not 다른언어 and not 빠짐,
                         (f'다른 언어 {다른언어} ' if 다른언어 else '') + (f'빠진 번역 {빠짐[:4]}' if 빠짐 else '') or
                         f"{'·'.join(sorted(언어권))} {len(번역)}행"))
        식비 = [어디 for 어디, t in 글 if '식비' in t and ('미정' in t or '포함 여부' in t)]
        항목.append(_항목('식비 미정 안내 없음', not 식비, ', '.join(식비[:4]) or '없음'))

    return {
        '단계': 4, '상태': 진행.get('상태'), '안내': 진행.get('안내'),
        '경과초': round(sum(초들), 1) if 초들 else None,
        '받은글자': sum(c['받은글자'] for c in 호출) if 호출 else None,
        '쓴글자': sum(c['쓴글자'] for c in 호출) if 호출 else None,
        '목표글자': {'받은글자': '기록만', '쓴글자': '기록만'},
        '항목': 항목, '전체통과': all(h['결과'] == '통과' for h in 항목),
        '오류': (오류 or {}).get('오류') if 오류 else None,
    }
