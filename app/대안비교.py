"""같은 코스 작성 응답에 포함된 B안을 등록한다. 새 AI 호출·필수 조건 변경 없음."""
import copy
import 기획기록 as 기록모듈
from 기획기준 import 지역반영


def _동선(코스):
    return [(x.get('일차'),x.get('시간칸'),x.get('장소명'),x.get('시각')) for x in 코스.get('칸목록',[]) if isinstance(x,dict)]


def 등록(기록, 제안, 출처시험id):
    def 없음(이유):
        기록['대안상태']={'상태':'미생성','이유':이유}
        return False
    if not isinstance(제안,dict) or not isinstance(제안.get('코스'),dict):
        return 없음('이번 응답에는 비교할 대안이 포함되지 않았어요. 기존 안을 복제하지 않았습니다.')
    if 기록모듈.안_찾기(기록,'B'):
        return 없음('이미 등록된 B안을 덮어쓰지 않았습니다.')
    a=next((x['코스'] for x in 기록['코스안'] if x['안id']=='A'),{})
    b=copy.deepcopy(제안['코스'])
    if not isinstance(b.get('칸목록'),list) or not b['칸목록'] or any(not isinstance(x,dict) for x in b['칸목록']):
        return 없음('대안 일정의 형식을 읽지 못해 원래 코스만 보존했어요.')
    if _동선(a)==_동선(b):
        return 없음('원래 코스와 다른 동선·일정이 확인되지 않아 대안을 따로 만들지 않았어요.')
    이유=str(제안.get('이유') or (b.get('대안설명') or {}).get('왜') or '').strip()
    if not 이유:return 없음('대안을 바꾸는 이유가 없어 비교안으로 등록하지 않았어요.')
    if 제안.get('바꾼조건') or b.get('바꾼조건'):
        return 없음('필수 조건을 바꾸는 대안은 담당자 승인 전 자동 등록하지 않았어요.')
    지역=지역반영(b,기록['조건'])
    if 지역 and 지역['반영']=='못지킴':return 없음('선택 지역을 벗어난 대안이라 자동 등록하지 않았어요.')
    체류=기록['조건'].get('체류기간')
    if 체류=='당일' and any(x.get('일차')==2 or x.get('시간칸')=='숙박' for x in b['칸목록']):
        return 없음('당일 조건에 숙박·둘째 날을 추가한 대안은 등록하지 않았어요.')
    바꾼=제안.get('바꾼희망') or {}
    if not isinstance(바꾼,dict) or any(k not in {x['id'] for x in 기록.get('희망',[])} for k in 바꾼):
        return 없음('대안이 가리키는 원래 희망을 확인하지 못했어요.')
    무엇=str(제안.get('무엇을') or (b.get('대안설명') or {}).get('무엇을') or '관광·식사 순서와 구성을 조정')
    b['대안설명']={**(b.get('대안설명') or {}),'무엇을':무엇,'왜':이유}
    기록모듈.안_추가(기록,'B','구성을 조정한 대안','코드:대안비교',바꾼희망=바꾼,이유=이유)
    기록모듈.안_찾기(기록,'B')['구성변경']=True
    기록모듈.추가(기록,'코스안',{'안id':'B','버전':1,'코스':b,'출처시험id':출처시험id},'코드:대안비교','같은 응답에서 받은 비교안')
    기록['대안상태']={'상태':'생성','이유':이유}
    return True
