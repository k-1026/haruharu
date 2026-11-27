"""하네스 2단계·5단계 실행. 제품 코드를 부르기만 한다.

- 2단계: 담당자 화면(/plan/)과 같은 기획실행._단계작업을 1·2단계까지만 돌리고 멈춘다(3단계는 부르지 않음).
  가상설문 CSV는 화면과 같은 기관업로드.보관함으로 올린다. AI는 수요요약 1번.
- 5단계: 담당자 화면 '최종 산출물 만들기'의 핵심인 산출물.묶기 → 산출물.저장을 고정 4단계 결과로 부른다. AI 없음.
"""
import asyncio
import base64
import inspect
import json
import time
from datetime import datetime
from pathlib import Path

여기 = Path(__file__).resolve().parent
저장소 = 여기.parents[1]


def 잰함수(기본, 폴더):
    """제품의 AI 부르기 함수를 그대로 쓰고 앞뒤로 시간·글자 수만 잰다 → 하네스_크기.json."""
    from app.공통.run_stage import 에이전트_읽기
    호출 = []

    def 적기():
        (Path(폴더) / '하네스_크기.json').write_text(json.dumps({'호출': 호출}, ensure_ascii=False, indent=2), encoding='utf-8')

    def 부르기(에이전트, 요청):
        기록 = {'에이전트': 에이전트, '받은글자': len(에이전트_읽기(에이전트)[0]) + len(요청), '쓴글자': 0}
        시작 = time.monotonic()
        try:
            결과 = 기본(에이전트, 요청)
            if inspect.isawaitable(결과):
                결과 = asyncio.run(결과)
            기록['쓴글자'] = len(결과) if isinstance(결과, str) else 0
            return 결과
        except Exception as e:
            기록['오류'] = type(e).__name__
            raise
        finally:
            기록['경과초'] = round(time.monotonic() - 시작, 1)
            호출.append(기록)
            적기()
    적기()
    return 부르기


def 한번_2단계(상황, 작업루트, 실행함수=None):
    from app.공통 import 기획실행 as 모듈
    from app.서버.관리자실행 import 코스시험
    from app.서버.관리자조회 import 결과저장소
    from app.하네스.채점_2단계 import 채점
    루트 = Path(작업루트)
    폴더 = 루트 / datetime.now().strftime('%Y%m%d_%H%M%S') / '01회차'
    폴더.mkdir(parents=True, exist_ok=False)
    기획 = 모듈.기획실행(코스시험(결과저장소(루트)), 잰함수(실행함수 or 모듈._기본단계함수, 폴더))
    조건, 목표, 희망 = 모듈.입력_검사({**상황['조건'], '자동진행동의': True})
    진행 = {'기획id': '/'.join(폴더.parts[-2:]), '상태': '진행중', '시작시각': 모듈._지금(), '조건': 조건,
          '목표': 목표, '희망': 희망, '단계': [{'이름': n, '상태': '대기', **모듈.단계담당[i]} for i, n in enumerate(모듈.단계이름)],
          '일하는중': None, '시험id': None, '기록id': None}
    if 상황.get('기관자료'):
        csv = (저장소 / 상황['기관자료']).read_bytes()
        올림 = 기획.자료보관함.미리보기({'파일명': Path(상황['기관자료']).name, '내용': base64.b64encode(csv).decode()})
        자료 = 기획.자료보관함.선택(올림['업로드id'], 올림['시트'][0]['이름'], True, 조건)
        기획.자료보관함.실행에보존(자료, 폴더)
        진행['기관업로드'] = {k: 자료[k] for k in ['업로드id', '파일명', '시트', '확인']}
    작업 = 기획._단계작업(폴더, 진행)
    try:
        next(작업, None)  # 1단계 (코드)
        if 진행['상태'] != '멈춤':
            next(작업, None)  # 2단계 (AI 요약 1번) — 여기서 멈추고 3단계는 부르지 않는다
    finally:
        작업.close()
    (폴더 / '기획_진행.json').write_text(json.dumps(진행, ensure_ascii=False, indent=2), encoding='utf-8')
    점수 = 채점(폴더, 조건)
    점수['시험폴더'] = str(폴더)
    return 점수


def 한번_5단계(상황, 작업루트, 실행함수=None):
    """실행함수는 쓰지 않는다(5단계는 AI가 없음). 다른 단계와 모양을 맞추려고 받기만 한다."""
    from app.단계5_산출물.산출물 import 묶기, 저장, _필터키
    from app.하네스.채점_5단계 import 채점
    고정 = 여기 / '시험상황' / 상황['고정입력']
    읽기 = lambda 이름: json.loads((고정 / 이름).read_text(encoding='utf-8'))
    확정, 확인, 입력2 = 읽기('3단계_확정.json'), 읽기('확인.json'), 읽기('3단계_입력_요약.json')
    홍보 = 읽기(상황['4단계결과'])
    폴더 = Path(작업루트) / ('산출물_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    폴더.mkdir(parents=True, exist_ok=False)
    조건 = {'방문객': 입력2.get('조건', {}).get('방문객', '외국인'), **입력2.get('조건', {})}
    # 담당자가 표현 필터를 모두 '그대로둠'으로 확인했다고 본다 (화면에서 이 확인 없이는 만들 수 없음)
    처리 = {_필터키(f): '그대로둠' for f in 홍보.get('표현필터', [])}
    결과 = {'오류': None}
    시작 = time.monotonic()
    try:
        묶음 = 묶기(조건, 입력2, 확정, 홍보, 확인, 처리, None, [])
        결과['파일'] = 저장(묶음, 폴더)
    except Exception as e:
        결과['오류'] = f'{type(e).__name__}: {e}'[:300]
    결과['경과초'] = round(time.monotonic() - 시작, 2)
    (폴더 / '하네스_실행.json').write_text(json.dumps(결과, ensure_ascii=False, indent=2), encoding='utf-8')
    점수 = 채점(폴더, 확정)
    점수['시험폴더'] = str(폴더)
    return 점수
