"""담당자 화면용 코스 요약. 저장 기록을 읽기만 하고 AI를 호출하지 않는다.
검사 코드·경고ID·원문은 관리자 창 몫이라 여기 넣지 않는다."""
import json
import re
from urllib.parse import quote
from 장소정보 import 좌표, 진입안내, 권역위치, 대표위치, 장소안내
from 단계연결 import JSON_읽기
from 운영검토 import 출발가능요일

미정이름={'숙박':'숙박 시간','2일차오전':'2일차 자유시간'}


def _짧게(name):
    return re.sub(r'\s*\([^)]*\)','',str(name or '').replace('대구광역시 ','')).strip()


def 지도링크(이름, point):
    """좌표가 있을 때만 그 위치를 여는 카카오맵 링크. 이름 검색 링크는 엉뚱한 곳을 열 수 있어 만들지 않는다."""
    if not point:return None
    return 'https://map.kakao.com/link/map/'+quote(f'{이름},{point[0]},{point[1]}',safe=',')


def 코스요약(코스, 조건):
    meals={(m.get('안','공통'),m.get('칸ID')):m for m in 코스.get('식사목록',[]) if isinstance(m,dict)}
    일정=[];확인=[]
    for i,row in enumerate(코스.get('칸목록',[]),1):
        meal=meals.get((row.get('안','공통'),row.get('칸ID')),{})
        후보=[]
        제외={_짧게(x.get('대상명','')) for x in (코스.get('운영검토기록') or {}).get('운영확인',[])
              if x.get('처리')=='제외' and (x.get('안','공통'),x.get('칸ID'))==(row.get('안','공통'),row.get('칸ID'))}
        for name in dict.fromkeys(x for x in (meal.get('추천후보') or []) if isinstance(x,str)):
            if _짧게(name) in 제외:continue
            candidate=좌표(name)
            후보명=_짧게(name)
            후보.append({'이름':후보명,'좌표':list(candidate) if candidate else None,'지도링크':지도링크(후보명,candidate)})
        자유식=meal.get('방식')=='자유식' or str(row.get('장소명','')).startswith('자유식')
        위치=대표위치(meal.get('권역',''),시간칸=row.get('시간칸','')) or 대표위치(row.get('장소명',''),시간칸=row.get('시간칸',''))
        권역=(위치 if 위치 and 위치.get('종류')=='권역대표점' else None) or 권역위치(meal.get('권역') or row.get('장소명',''))
        식사권역=자유식 or bool(권역 and (row.get('시간칸') in ['점심','저녁'] or '권역 후보:' in row.get('장소명','')))
        if 자유식:
            표시명='자유식 · '+_짧게(meal.get('권역') or row.get('장소명','')).replace('자유식 · ','')
            point=None  # 자유식은 권역이라 한 점으로 찍지 않는다.
        else:
            표시명=_짧게(row.get('장소명'));point=좌표(row.get('장소명',''))
            if not point and 위치:point=위치['중심']
        위치설명=위치['설명'] if 위치 else '시설 대표 위치 · 정확한 입구는 별도 확인' if point else ''
        if 위치 and row.get('시간칸')=='숙박':표시명='숙박 · '+위치['이름']+' 권역 (업체 미지정)'
        if not 표시명:표시명=미정이름.get(row.get('시간칸'),'장소 미정')
        시각=(row.get('시각') or {}).get('값','') if isinstance(row.get('시각'),dict) else ''
        일정.append({'순번':i,'일차':row.get('일차','미정'),'시각':시각,'시간칸':row.get('시간칸',''),
                    '장소명':row.get('장소명',''),'표시명':표시명,'좌표':list(point) if point else None,
                    '지도링크':지도링크(표시명,point),'진입안내':진입안내(row.get('장소명','')),'식당후보':후보,
                    '식사권역':식사권역,'식사방식':meal.get('방식','미정'),'권역표시':권역,
                    '위치설명':위치설명,'위치유형':위치.get('종류','') if 위치 else '시설대표점' if point else '',
                    '위치근거URL':위치.get('근거URL','') if 위치 else '',
                    '입구확인':bool(위치.get('입구확인')) if 위치 else False})
        일정[-1]['장소안내']=장소안내(row.get('장소명',''),시간칸=row.get('시간칸',''))
        if not 시각:확인.append(f"{미정이름.get(row.get('시간칸'),표시명)} 미정")
        if point is None and not 자유식 and row.get('시간칸') not in ['숙박','2일차오전']:확인.append('좌표 미확인: '+표시명)
    try:
        days=출발가능요일(코스,코스.get('운영검토기록') or {},None,조건)['안별']
        가능=days.get('공통') if '공통' in days else next(iter(days.values()),None)
    except Exception:
        가능=None
    return {'조건':조건,'일정':일정,'출발가능요일':가능,'확인할것':list(dict.fromkeys(확인)),'코스있음':bool(일정)}


def 요약_불러오기(실행서비스, 시험id):
    try:
        코스=JSON_읽기(실행서비스.저장소.파일(시험id+'/3단계_결과.md')['본문'])  # 실제 AI 답은 앞말·```json 블록이 붙는다
        입력=json.loads(실행서비스.저장소.파일(시험id+'/3단계_입력.json')['본문'])
    except (ValueError,OSError,KeyError):
        return {'조건':{},'일정':[],'출발가능요일':None,'확인할것':['이 기록에는 아직 코스가 없습니다.'],'코스있음':False}
    if not isinstance(코스,dict):코스={}
    return 코스요약(코스,입력.get('코스작성조건',{}) if isinstance(입력,dict) else {})
