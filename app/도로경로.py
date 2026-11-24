"""명시적으로 실행할 때만 도보 경로를 수집한다. 화면 조회·AI 실행과 분리한 캐시."""
import argparse
import json
import math
import time
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen

서버='https://routing.openstreetmap.de/routed-foot/route/v1/foot/'
출처='https://routing.openstreetmap.de/about.html'


def 점검(p):
    return isinstance(p,(list,tuple)) and len(p)==2 and all(isinstance(x,(int,float)) and math.isfinite(x) for x in p) and abs(p[0])<=90 and abs(p[1])<=180


def 키(a,b):return ';'.join(','.join(f'{v:.6f}' for v in p) for p in [a,b])


def 거리(a,b):
    return math.hypot((a[0]-b[0])*111320,(a[1]-b[1])*111320*math.cos(math.radians((a[0]+b[0])/2)))


def 경로검사(data,a,b):
    if data.get('code')!='Ok':raise ValueError('도보 경로 없음')
    route=data['routes'][0];geom=route['geometry'];snaps=data['waypoints']
    if geom.get('type')!='LineString':raise ValueError('선 경로가 아님')
    points=[[p[1],p[0]] for p in geom['coordinates']]
    if len(points)<2 or not all(점검(p) for p in points):raise ValueError('경로 좌표 오류')
    if len(snaps)!=2 or any(not 0<=s.get('distance',9999)<=150 for s in snaps):raise ValueError('대표점에서 도로가 너무 멂')
    if 거리(a,points[0])>150 or 거리(b,points[-1])>150:raise ValueError('경로 끝점 불일치')
    if not 0<route.get('distance',0)<100000:raise ValueError('경로 길이 확인 필요')
    seconds=route.get('duration')
    if not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds<=0:seconds=None
    return {'from':list(a),'to':list(b),'profile':'foot','points':points,'distance':route['distance'],
            'durationSeconds':seconds,
            'snapDistances':[s['distance'] for s in snaps],'source':출처,
            'fetchedAt':datetime.now().astimezone().isoformat(timespec='seconds')}


def 요청(url):
    req=Request(url,headers={'User-Agent':'Haruharu-local-route-preview/1.0'})
    with urlopen(req,timeout=20) as response:return json.load(response)


def 경로수집(stops,cache,묻기=요청,쉬기=1.1,시간보완=False):
    result={'source':출처,'attribution':'© OpenStreetMap contributors · FOSSGIS OSRM (foot)',
            'routes':dict(cache.get('routes',{})),'failures':{}}
    points=[]
    for s in stops:
        p=s.get('좌표') or (s.get('권역표시') or {}).get('중심')
        if not p and s.get('식사권역'):
            candidates=[c['좌표'] for c in s.get('식당후보',[]) if 점검(c.get('좌표'))]
            if candidates:p=[sum(c[k] for c in candidates)/len(candidates) for k in [0,1]]
        points.append(p if 점검(p) else None)
    requested=False
    for i in range(1,len(stops)):
        a,b=points[i-1:i+1]
        if not a or not b or stops[i-1].get('일차')!=stops[i].get('일차'):continue
        key=키(a,b)
        existing=result['routes'].get(key,{})
        if existing.get('profile')=='foot' and (not 시간보완 or existing.get('durationSeconds')):continue
        if requested and 쉬기:time.sleep(쉬기)
        requested=True
        coords=';'.join(f'{p[1]},{p[0]}' for p in [a,b])
        url=서버+coords+'?overview=full&geometries=geojson&steps=false'
        try:result['routes'][key]=경로검사(묻기(url),a,b)
        except (ValueError,KeyError,IndexError,TypeError,OSError) as error:result['failures'][key]=str(error)
    return result


def main():
    parser=argparse.ArgumentParser(description='저장 코스 대표점의 도보 경로만 수집. AI 호출 없음')
    parser.add_argument('--기록id',required=True);parser.add_argument('--안',default='A')
    parser.add_argument('--시간보완',action='store_true')
    args=parser.parse_args();root=Path(__file__).resolve().parent
    import 기획기록
    from 담당자요약 import 코스요약
    record=기획기록.읽기(root/'runs',args.기록id)
    plans=[r for r in record['코스안'] if r.get('안id')==args.안]
    course=max(plans,key=lambda r:r.get('버전',1))['코스']
    stops=코스요약(course,{})['일정'];target=root/'담당자화면/road-routes.json'
    cache=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    result=경로수집(stops,cache,시간보완=args.시간보완);temp=target.with_suffix('.json.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(target)
    print(json.dumps({'저장경로':str(target),'경로수':len(result['routes']),'실패':result['failures']},ensure_ascii=False))


if __name__=='__main__':main()
