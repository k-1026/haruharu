"""미검토 좌표만 주소/시설명으로 조회해 별도 후보 기록을 만든다. 자동 반영·AI 호출 없음."""
import csv,json,time
from datetime import datetime,date
from pathlib import Path
from 좌표받기 import 장소파일, 주소검색


def 수집(묻기=None,쉬기=1.1):
    with 장소파일().open(encoding='utf-8-sig',newline='') as file:places=list(csv.DictReader(file))
    results=[]
    broad={'근대골목','서문시장','서문시장 야시장','평화시장 닭똥집골목 (치킨 옵션)','근대골목 해설 투어'}
    for place in places:
        if place.get('좌표검토상태') in ['자료대조완료','사람확인완료'] and place.get('위도') and place.get('경도'):continue
        name=place['장소명'];row={'순번':place['순번'],'장소명':name,'주소':place.get('주소',''),
            '사용':'','검토자':'','검토상태':'검토대기','확인일':date.today().isoformat(),'출처':'OpenStreetMap Nominatim'}
        if name in broad:
            row.update({'검토상태':'진입점 자료 필요','이유':'넓은 권역/투어는 시설 하나의 좌표로 자동 확정하지 않습니다. 선택한 진입 기준의 시설명·공식 주소를 먼저 등록하세요.'})
        elif not place.get('주소'):
            row.update({'검토상태':'공식 주소 필요','이유':'동명이인 시설 오인을 피하려면 주소·구부터 확인해야 합니다.'})
        else:
            if results and 쉬기:time.sleep(쉬기)
            # 주소뿐 아니라 시설명도 질의에 포함한다. 반환값은 검토 후보일 뿐이다.
            try:
                lat,lon,precision,found=주소검색(name.split('(')[0].strip()+' '+place['주소'],묻기)
                row.update({'위도':lat,'경도':lon,'정밀도':precision,'찾은이름':found,
                            '검토상태':'검토대기' if lat else '찾지못함'})
            except Exception as error:row.update({'검토상태':'수집실패','이유':type(error).__name__})
        results.append(row)
    return results


def 실행():
    results=수집();folder=Path(__file__).resolve().parent/'runs';folder.mkdir(exist_ok=True)
    output=folder/('미검토좌표_후보_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.json')
    output.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'미검토 {len(results)}곳 후보/보완 사유: {output}')
    print('기존 장소·좌표를 변경하지 않았습니다. 도로 단위 결과는 위치 확정에 사용하지 마세요.')
