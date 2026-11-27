"""하네스 2단계(수요 근거) 채점: 폴더에 남은 파일만 읽는다. AI를 부르지 않는다(토큰 0)."""
import json
import re
from pathlib import Path

제한초 = 30  # 제품 설정 run_stage.역할_제한초['수요요약.md']


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


def 지어낸숫자(요약, 근거글):
    """요약에 나온 숫자 중 AI에 준 근거·조건 글 어디에도 없는 것."""
    숫자 = re.findall(r'\d+(?:[.,]\d+)?', 요약)
    return sorted({n for n in 숫자 if n.replace(',', '') not in 근거글.replace(',', '')})


def 채점(폴더, 조건):
    from app.단계2_수요근거.근거추출 import 요약입력
    진행 = _읽기(폴더, '기획_진행.json') or {}
    호출 = (_읽기(폴더, '하네스_크기.json') or {}).get('호출') or []
    전달 = _읽기(폴더, '3단계_전달_준비.json')
    추출 = _읽기(폴더, '근거_추출.json')
    오류 = _읽기(폴더, 'AI_오류.json')
    단계2 = (진행.get('단계') or [{}, {}])[1]
    항목 = []

    초들 = [c['경과초'] for c in 호출]
    항목.append(_항목(f'시간(요약 {제한초}초 이하)', bool(호출) and all(s <= 제한초 for s in 초들) and not any(c.get('오류') for c in 호출),
                     ' · '.join(f"{c['경과초']}초" + (f" ({c['오류']})" if c.get('오류') else '') for c in 호출)
                     or f"AI 호출 없음 (상태: {진행.get('상태')}, {진행.get('안내', '')[:80]})"))
    통과 = 전달 is not None and 전달.get('검사결과') == ['통과'] and 단계2.get('상태') == '완료'
    항목.append(_항목('형식(요약 읽힘 · 3단계 전달 검사 통과)', 통과,
                     '통과' if 통과 else ('; '.join((전달 or {}).get('검사결과') or []) or 진행.get('안내') or '전달 파일 없음')[:200]))

    기관 = (추출 or {}).get('기관업로드') or {}
    항목.append(_항목('기관 자료 반영(가상설문 행 적용)', 기관.get('적용행수', 0) > 0,
                     f"적용 {기관.get('적용행수', 0)}행 · 제외 {기관.get('제외행수', 0)}행" if 기관 else '기관 자료 없음'))

    원문 = (Path(폴더) / '2단계_AI요약_원문.md')
    요약 = ''
    if 원문.is_file():
        from app.공통.에이전트실행 import JSON_꺼내기
        값 = JSON_꺼내기(원문.read_text(encoding='utf-8')) or {}
        요약 = 값.get('요약') if isinstance(값.get('요약'), str) else ''
    if 요약 and 추출:
        근거글 = json.dumps(요약입력(추출), ensure_ascii=False) + json.dumps(조건, ensure_ascii=False)
        없음 = 지어낸숫자(요약, 근거글)
        항목.append(_항목('요약에 근거 밖 숫자 없음', not 없음, ', '.join(없음[:8]) or f'요약 {len(요약)}자 확인'))
    else:
        항목.append(_항목('요약에 근거 밖 숫자 없음', False, '요약을 읽지 못함'))

    return {
        '단계': 2, '상태': '2단계완료(3단계는 부르지 않음)' if 단계2.get('상태') == '완료' else 진행.get('상태'), '안내': 진행.get('안내'),
        '경과초': round(sum(초들), 1) if 초들 else None,
        '받은글자': sum(c['받은글자'] for c in 호출) if 호출 else None,
        '쓴글자': sum(c['쓴글자'] for c in 호출) if 호출 else None,
        '목표글자': {'받은글자': '기록만', '쓴글자': '기록만'},
        '항목': 항목, '전체통과': all(h['결과'] == '통과' for h in 항목),
        '오류': (오류 or {}).get('오류') if 오류 else None,
    }
