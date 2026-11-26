"""선택 지역 검사와 저녁 음식 설문 근거. 자료를 읽기만 하며 조건을 바꾸지 않는다."""
import csv
import re
from pathlib import Path

from app.단계3_코스검토.장소정보 import 장소목록, _이름


def 저녁음식근거(조건):
    """전체 외국인과 해당 거주국가의 추천 음식 1+2순위 행을 구분해 전달한다."""
    상대 = 'research/data/외국인/대구_외국인추천음식상위20_2024.csv'
    국가 = {'일본어': '일본', '중국어 간체': '중국', '중국어 번체': '대만'}
    대상 = {국가[x] for x in 조건.get('언어권', []) if x in 국가}
    try:
        with (Path(__file__).resolve().parents[2] / 상대).open(encoding='utf-8-sig', newline='') as f:
            return [{'음식': r['item'], '비율': r['value_pct'], '단위': '%', '표본수': r['sample_n'],
                     '대상': r['subgroup'], '집계': r['band'], '연도': 2024, '출처파일': 상대,
                     '행': line, '한계': '대구 전체 조사. 가을·커플의 교차값이나 특정 식당 선호가 아님.'}
                    for line, r in enumerate(csv.DictReader(f), 2)
                    if r['band'] == '1 + 2순위' and (
                        (r['category'] == '전체' and r['subgroup'] == '소계') or
                        (r['category'] == '거주국가' and r['subgroup'] in 대상))]
    except (OSError, KeyError, UnicodeError):
        return []  # 없는 근거를 만들지 않고 호출 쪽에서 미확인으로 표시


저녁원칙 = ('저녁은 추천 음식 설문 근거를 참고하되 운영시간·이동·담당자 선택을 함께 검토한다. '
          '치킨은 필수 음식이 아니라 선택 옵션이며, 다른 음식도 가능하다. 찜갈비도 고정하지 않는다. '
          '전체 외국인과 거주국가별 응답을 구분하고 표본·연도·한계를 유지한다. '
          '추천 응답 비율은 특정 식당 선호나 반드시 먹고 싶다는 뜻이 아니다. '
          '근거가 없으면 미확인으로 남기고 지어내지 않는다.')


def 지역반영(코스, 조건):
    """명시 구와 보유 장소 대장을 함께 대조한다. 모르는 장소는 통과로 꾸미지 않는다."""
    허용 = 조건.get('지역') or []
    if not 허용:
        return None
    보유 = {}
    for p in 장소목록():
        if p.get('구'):
            보유.setdefault(_이름(p['장소명']), set()).add(p['구'])
    장소들 = []
    for row in 코스.get('칸목록') or []:
        if isinstance(row, dict):
            장소들.append((str(row.get('장소명') or ''), str(row.get('구') or '')))
    for meal in 코스.get('식사목록') or []:
        if not isinstance(meal, dict):
            continue
        if meal.get('식당'):
            장소들.append((str(meal['식당']), ''))
        for candidate in meal.get('추천후보') or []:
            name = (candidate.get('장소명') or candidate.get('이름') or candidate.get('식당') or '') if isinstance(candidate, dict) else candidate
            장소들.append((str(name), ''))
    벗어남, 미확인 = [], []
    for name, district in 장소들:
        if name in ['', '미선택', '미정', '미확인']:
            continue
        구 = set(re.findall(r'(중구|동구|서구|남구|북구|수성구|달서구|달성군|군위군)', name + ' ' + district))
        구 |= 보유.get(_이름(name), set())
        if 구 - set(허용):
            벗어남.append(f"{name}({', '.join(sorted(구 - set(허용)))})")
        elif not 구:
            미확인.append(name)
    if 벗어남:
        return {'조건': '지역', '반영': '못지킴', '이유': f"필수 지역은 {', '.join(허용)}인데 범위 밖 후보가 있습니다: {'; '.join(dict.fromkeys(벗어남))}. 선택 지역 안에서 다시 검토해야 합니다.", '확인방법': '코드:장소 대장·명시 지역 대조'}
    if 미확인 or not 장소들:
        return {'조건': '지역', '반영': '미확인', '이유': '소속 지역을 확인할 자료가 부족합니다: ' + ('; '.join(dict.fromkeys(미확인)) or '일정 없음'), '확인방법': '코드:장소 대장·명시 지역 대조'}
    return {'조건': '지역', '반영': '지킴', '이유': '명시 지역과 보유 장소 대장에서 선택 지역 밖 후보가 발견되지 않았습니다.', '확인방법': '코드:장소 대장·명시 지역 대조'}


def 필수조건반영(코스, 조건):
    보고 = [dict(x) for x in 코스.get('필수조건반영') or [] if isinstance(x, dict) and x.get('조건') != '지역']
    for row in 보고:
        if row.get('반영') != '지킴' and not str(row.get('이유') or '').strip():
            row['이유'] = 'AI가 이유를 적지 않았습니다. 충족 여부와 근거를 다시 확인해야 합니다.'
    지역 = 지역반영(코스, 조건)
    if 지역:
        보고.append(지역)
    return 보고
