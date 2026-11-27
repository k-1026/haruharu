"""하네스 채점: 3단계 시험 폴더에 남은 파일만 읽어 항목별 통과/실패를 매긴다. AI를 부르지 않는다(토큰 0).

제품 코드가 이미 만든 검사 결과(코스_검사·시간표_검사·체크리스트)를 그대로 읽고,
제품에 없는 규칙(후보표 밖 장소, 낮 치킨 등)만 여기서 센다.
"""
import json
from pathlib import Path

from app.단계3_코스검토.코스조립 import 치킨장소인가
from app.단계3_코스검토.장소정보 import _이름

제한초 = 60
목표 = {'받은글자': 15000, '쓴글자': 3000}
고정칸 = {'숙박', '2일차오전'}  # 후보표가 아니라 코드가 정해진 문장으로 넣는 칸


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


def _모든칸(코스):
    """A안(공통) 칸 + B안(대안제안) 칸을 (안이름, 칸) 목록으로."""
    칸 = [('A', r) for r in 코스.get('칸목록') or []]
    b = 코스.get('대안제안') or {}
    칸 += [('B', r) for r in ((b.get('코스') or {}).get('칸목록') or [])]
    return 칸


def 채점(폴더, 입력):
    """폴더 = 통합시험_* 폴더. 입력 = 3단계_입력.json 내용. 항목 목록과 숫자 기록을 돌려준다."""
    상태 = _읽기(폴더, '통합시험_상태.json') or {}
    크기 = _읽기(폴더, '3단계_크기.json') or {}
    검사 = _읽기(폴더, '3단계_전달_검사.json') or {}
    표 = _읽기(폴더, '3단계_후보표.json') or {}
    오류 = _읽기(폴더, 'AI_오류.json')
    코스 = _읽기(폴더, '3단계_구조화.json')
    if not isinstance(코스, dict) or '칸목록' not in 코스:
        코스 = None
    조건 = 입력.get('코스작성조건') or {}
    항목 = []

    # 시간: 응답이 없으면(시간 초과·실패) 실패로 본다
    초 = 크기.get('경과초')
    항목.append(_항목('시간(60초 이하)', 초 is not None and 초 <= 제한초,
                     f'{초}초' if 초 is not None else f"기록 없음 (상태: {상태.get('상태')}, 오류: {상태.get('오류종류', '-')})"))

    # 형식: 조립됐고 제품의 형식 검사를 통과했는가
    형식 = 검사.get('형식검사')
    항목.append(_항목('형식(조립·형식 검사)', 코스 is not None and 형식 == ['통과'],
                     '통과' if 형식 == ['통과'] else '; '.join((형식 or 상태.get('문제') or ['조립 안 됨'])[:3])))

    if 코스 is None:
        for 이름 in ['치킨(담당자 선택 시 저녁 1번까지)', '낮 치킨 식사 없음', '휴무·운영시간·시간 충돌 없음',
                   '후보표 밖 장소 없음', '1박2일 숙박 칸', 'A/B 둘 다(또는 B 불가 이유)']:
            항목.append(_항목(이름, False, '코스가 조립되지 않아 볼 수 없음'))
    else:
        칸들 = _모든칸(코스)
        치킨선택 = 조건.get('치킨선택') == '선택'
        # 조립된 코스는 장소명에서 '(치킨 옵션)' 표시가 빠지므로 후보표의 치킨 장소 이름과도 맞춘다
        후보치킨 = {_이름(r.get('장소명') or '') for r in (표.get('장소') or {}).values() if 치킨장소인가(r.get('장소명'))}
        치킨 = [(안, r) for 안, r in 칸들 if 치킨장소인가(r.get('장소명')) or _이름(r.get('장소명') or '') in 후보치킨]
        안별 = {}
        for 안, r in 치킨:
            안별[안] = 안별.get(안, 0) + 1
        ok = (not 치킨) or (치킨선택 and all(n <= 1 for n in 안별.values()) and all(r.get('시간칸') == '저녁' for _, r in 치킨))
        항목.append(_항목('치킨(담당자 선택 시 저녁 1번까지)', ok,
                         f"치킨 {len(치킨)}곳, 담당자 선택: {'예' if 치킨선택 else '아니오'}"))
        if 치킨선택:
            # 지침 2_입력.md 5-1: 치킨은 고정하지 않고 저녁 후보로 나란히 보여 준다.
            # 그래서 '코스에 들어갔나'가 아니라 '저녁을 바꿀 때 치킨이 후보로 뜨나'를 본다(화면과 같은 함수).
            a치킨 = [r.get('장소명') for 안, r in 치킨 if 안 == 'A']
            항목.append(_항목('치킨 선택 시 후보표에 치킨 있음', bool(후보치킨), f'후보 {len(후보치킨)}곳'))
            저녁 = [r for r in 코스.get('칸목록') or [] if r.get('시간칸') == '저녁']
            try:
                from app.단계3_코스검토.식사선택 import 후보목록
                화면조건 = {**(입력.get('조건') or {}), **조건}
                뜸 = [r for r in 저녁 if any(x.get('치킨') for x in 후보목록(코스, r, 화면조건))
                     or 치킨장소인가(r.get('장소명')) or _이름(r.get('장소명') or '') in 후보치킨]
                메모 = f"저녁 {len(저녁)}칸 중 {len(뜸)}칸에서 치킨 선택 가능 · A안 코스에 들어간 치킨: {', '.join(a치킨) or '없음'}"
                항목.append(_항목('치킨 선택 시 저녁 후보에 치킨 보임', bool(저녁) and len(뜸) == len(저녁), 메모))
            except Exception as e:  # 화면 후보 함수가 못 읽으면 실패로 남긴다
                항목.append(_항목('치킨 선택 시 저녁 후보에 치킨 보임', False, f'후보 확인 실패: {type(e).__name__}'))
        낮 = [f"{안}:{r.get('칸ID')}" for 안, r in 치킨 if r.get('시간칸') != '저녁']
        항목.append(_항목('낮 치킨 식사 없음', not 낮, ', '.join(낮) or '없음'))

        충돌 = list((검사.get('시간표검사') or {}).get('충돌') or [])
        충돌 += [f"{c.get('안')} {c.get('C번호')}: {c.get('메모')}" for c in 코스.get('체크리스트') or []
               if c.get('C번호') in ['C4', 'C5'] and c.get('결과') == '통과 못 함']
        항목.append(_항목('휴무·운영시간·시간 충돌 없음', not 충돌, '; '.join(충돌[:3]) or '없음'))

        후보 = {_이름(r.get('장소명') or '') for r in (표.get('장소') or {}).values()}
        밖 = sorted({r.get('장소명') for _, r in 칸들
                    if r.get('시간칸') not in 고정칸 and _이름(r.get('장소명') or '') not in 후보})
        항목.append(_항목('후보표 밖 장소 없음', bool(후보) and not 밖, ', '.join(밖) or ('없음' if 후보 else '후보표 없음')))

        if 입력.get('확정체류기간') == '1박2일':
            숙박 = [r for 안, r in 칸들 if 안 == 'A' and r.get('시간칸') == '숙박']
            항목.append(_항목('1박2일 숙박 칸', bool(숙박), f'{len(숙박)}칸'))

        b = 코스.get('대안제안') or {}
        b칸 = (b.get('코스') or {}).get('칸목록') or []
        이유 = str(코스.get('대안불가이유') or '').strip()
        항목.append(_항목('A/B 둘 다(또는 B 불가 이유)', bool(b칸) or bool(이유),
                         f'B안 {len(b칸)}칸' if b칸 else (f'B 불가: {이유[:80]}' if 이유 else 'B안도 이유도 없음')))

    return {
        '상태': 상태.get('상태'), '안내': 상태.get('안내'),
        '경과초': 초, '받은글자': 크기.get('받은글자'), '쓴글자': 크기.get('쓴글자'), '목표글자': 목표,
        '항목': 항목, '전체통과': all(h['결과'] == '통과' for h in 항목),
        '오류': (오류 or {}).get('오류') if 오류 else None,
    }
