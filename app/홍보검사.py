"""홍보 결과의 결정 가능한 표기·후보·ID 검사. 외부 AI나 네트워크를 쓰지 않는다."""
import json
import re
from pathlib import Path
from 장소정보 import 장소목록

ROOT=Path(__file__).resolve().parent.parent


def _표(path):
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('|'):
            yield [x.strip() for x in line.strip('|').split('|')]


def _문장(value):
    return json.dumps(value,ensure_ascii=False)


def _값(value):
    if isinstance(value,list):
        return [x for row in value for x in _값(row)]
    return re.findall(r'[A-Za-z][A-Za-z0-9_-]*|가정값|연결문장|미정',str(value))


def _참조(fact):
    if isinstance(fact,list):
        for item in fact:yield from _참조(item)
    else:yield fact


def 내용검사(promo,course,evidence=None):
    problems=[]
    # 알려진 상호와 명시적 제외 대상을 대조한다. 미등록 상호의 자동 인식·번역 검수는 별도다.
    allowed=set()
    for meal in course.get('식사목록',[]):
        allowed.update(x for x in meal.get('추천후보',[]) if isinstance(x,str))
        if meal.get('식당'):allowed.add(meal['식당'])
    known={re.sub(r'\s*\(.*?\)','',r['장소명']) for r in 장소목록() if r.get('장소유형')=='식당'}
    excluded={r['대상명'] for r in course.get('운영검토기록',{}).get('운영확인',[]) if r.get('처리')=='제외'}
    for field in ['대응표','문구목록','번역목록','코스카드']:
        text=_문장(promo.get(field))
        for name in sorted(known|excluded):
            if name and name in text and (name in excluded or not any(name in x for x in allowed)):
                problems.append(f'{field}: 3단계 추천후보·지정식당에 없는 상호 {name}')
    # 용어집 표마다 머리줄이 다르다(장소 표: 영어가 2번째 칸, 용어 표: 로마자 다음). 표마다 머리줄로 언어 칸을 찾는다.
    # 한 칸에 '표기 (쓰임) / 표기 (쓰임)'처럼 여러 표기가 있으면 그중 하나만 맞아도 통과한다.
    glossary=[];header=None
    for row in _표(ROOT/'지침/4_홍보검토/12_번역_용어집.md'):
        if all(set(x)<=set('-: ') for x in row):continue
        if '일본어' in row and ('영어' in row):header={name:i for i,name in enumerate(row)};continue
        if any(x in ('공식표기','상태') for x in row):header=None;continue
        if header and len(row)>=len(header):glossary.append((header,row))
    for row in promo.get('번역목록',[]):
        language={'영어권':'영어'}.get(row.get('언어'),row.get('언어'))
        source=next((r for r in promo.get('문구목록',[]) if (r.get('안','공통'),r.get('장면ID'))==(row.get('안','공통'),row.get('장면ID'))),{})
        original=_문장([source.get('제목',''),source.get('본문','')])
        translated=str(row.get('번역',''))
        for header,term in glossary:
            if language not in header:continue
            name=term[0].split('(')[0].strip()
            expected=term[header[language]].strip('` ')
            if not name or name not in original or expected in ['','—'] or expected.startswith('미확인'):continue
            choices=[re.sub(r'\s*\([^)]*\)\s*$','',x).strip('` ') for x in expected.split(' / ')]
            if not any(x and x in translated for x in choices):
                problems.append(f'번역 용어집 표기 불일치: {name} / {row.get("언어")} = {expected}')
    story=(ROOT/'지침/4_홍보검토/11_스토리_검증.md').read_text(encoding='utf-8')
    story_ids=set(re.findall(r'^\|\s*([A-Z]+-[A-Z0-9-]+)\s*\|',story,re.M))
    references={'가정값','연결문장','미정'}|story_ids
    if evidence is not None:
        for row in evidence:
            references.update(_값(row.get('출처ID',row.get('출처',''))))
    valid_r={r.get('근거ID') for r in evidence or []}
    for row in promo.get('문구목록',[]):
        for fact in _참조(row.get('사실근거')):
            if isinstance(fact,dict):
                rids=_값(fact.get('근거ID',[]));sids=_값(fact.get('출처ID',[]))
                for rid in rids:
                    if not re.fullmatch(r'R\d+',rid) or (evidence is not None and rid not in valid_r):
                        problems.append(f'사실근거: 잘못된 근거ID {rid}')
            else:sids=_값(fact) if fact else []
            for sid in sids:
                if sid not in references and not re.fullmatch(r'S\d+',sid) and not (not isinstance(fact,dict) and re.fullmatch(r'R\d+',sid) and (evidence is None or sid in valid_r)):
                    problems.append(f'사실근거: 허용되지 않은 출처ID {sid}')
    return list(dict.fromkeys(problems))
