"""하네스 5단계(결재 파일·제안서·홍보물 묶음) 채점. AI 없음, 토큰 0."""
import html
import json
import re
from pathlib import Path

from app.단계3_코스검토.장소정보 import _이름

파일들 = {'결재파일.html': '결재 파일', '제안서.html': '제안서', '홍보물묶음.html': '홍보물 묶음'}


def _항목(이름, 통과, 메모):
    return {'항목': 이름, '결과': '통과' if 통과 else '실패', '메모': 메모}


def _글(p):
    return html.unescape(re.sub(r'<[^>]+>', ' ', p.read_text(encoding='utf-8'))) if p.is_file() else ''


def 채점(폴더, 확정):
    폴더 = Path(폴더)
    실행 = json.loads((폴더 / '하네스_실행.json').read_text(encoding='utf-8'))
    묶음p = 폴더 / '5단계_묶음.json'
    묶음 = json.loads(묶음p.read_text(encoding='utf-8')) if 묶음p.is_file() else None
    항목 = [_항목('만들기 오류 없음', not 실행.get('오류'), 실행.get('오류') or f"{실행['경과초']}초")]
    글 = {n: _글(폴더 / f) for f, n in 파일들.items()}
    항목.append(_항목('세 파일 모두 만들어짐', all(글.values()), ', '.join(f'{n} {len(t)}자' for n, t in 글.items())))

    if 묶음 is None:
        for n in ['제품 대조(코스·경고·미확인 표시) 불일치 없음', '세 파일에 코스 장소가 모두 나옴', '남은 경고가 묶음 기록에 모두 보존됨', '공개 파일에 내부 표시 없음']:
            항목.append(_항목(n, False, '묶음이 없어 볼 수 없음'))
    else:
        불일치 = (묶음.get('대조') or {}).get('불일치') or []
        항목.append(_항목('제품 대조(코스·경고·미확인 표시) 불일치 없음', not 불일치, '; '.join(불일치[:3]) or '없음'))
        장소 = [_이름(r.get('장소명') or '') for r in 확정.get('칸목록') or []
               if r.get('시간칸') not in ['숙박', '2일차오전', '점심', '저녁'] and r.get('장소명')]
        # 식사 칸은 방식 미선택이면 식당 이름 대신 권역만 쓰는 것이 제품 규칙이라 뺀다
        빠짐 = [f'{n}: {p}' for n, t in 글.items() for p in dict.fromkeys(장소) if p and p not in t]
        항목.append(_항목('세 파일에 코스 장소가 모두 나옴', not 빠짐, '; '.join(빠짐[:4]) or f'장소 {len(set(장소))}곳 × 3파일'))
        # 결재 파일·제안서는 공개용이라 경고를 빼고(산출물.공개묶음), 경고는 5단계_묶음.json에 보존하는 설계
        경고 = [str(w.get('경고ID') or '') for w in 확정.get('남은경고') or [] if w.get('경고ID')]
        보존 = {str(w.get('경고')) for w in 묶음.get('남은경고') or []}
        안나옴 = [w for w in dict.fromkeys(경고) if w not in 보존]
        항목.append(_항목('남은 경고가 묶음 기록에 모두 보존됨', not 안나옴, ', '.join(안나옴[:6]) or f'3단계 경고 {len(set(경고))}개 모두 보존'))
        from app.하네스.채점_4단계 import 내부표시
        내부 = [f'{n}: {m.group(0)}' for n, t in 글.items() for m in 내부표시.finditer(t)]
        항목.append(_항목('공개 파일에 내부 표시 없음', not 내부, '; '.join(list(dict.fromkeys(내부))[:4]) or '없음'))

    return {
        '단계': 5, '상태': '오류' if 실행.get('오류') else '완료', '안내': '',
        '경과초': 실행.get('경과초'), '받은글자': 0, '쓴글자': 0,
        '목표글자': {'받은글자': 'AI 없음', '쓴글자': 'AI 없음'},
        '항목': 항목, '전체통과': all(h['결과'] == '통과' for h in 항목), '오류': None,
    }
