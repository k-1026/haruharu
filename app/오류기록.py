"""입력·키·전체 SDK payload 없이 운영자가 확인할 오류 진단을 남긴다."""
from datetime import datetime
import json
from pathlib import Path
import re
import traceback

from 설정 import 설정_읽기


def 안전문장(value):
    text=str(value)
    for name,secret in 설정_읽기().items():
        if any(word in name for word in ('KEY','TOKEN','SECRET','PASSWORD')) and secret:
            text=text.replace(secret,'[가림]')
    text=re.sub(r'(?i)\bBearer\s+[^\s,;"\']+', 'Bearer [가림]',text)
    text=re.sub(r'(?i)((?:[\w-]*(?:api[_-]?key|token|secret|password)|authorization)\s*["\']?\s*[:=]\s*["\']?)[^\s,;"\'}]+',r'\1[가림]',text)
    text=re.sub(r'\b(?:sk-[A-Za-z0-9_-]+|AIza[A-Za-z0-9_-]+)\b','[가림]',text)
    text=re.sub(r'(https?://[^\s?]+)\?[^\s]+',r'\1?[가림]',text)
    return text[:4000]


def 진단(error,**context):
    result={'시각':datetime.now().astimezone().isoformat(),'종류':type(error).__name__,
            '메시지':안전문장(str(error))}
    for key in ('제공자','모델','단계','경과초'):
        if key in context:result[key]=안전문장(context[key]) if isinstance(context[key],str) else context[key]
    fields={'api_error_status':'HTTP상태','status_code':'HTTP상태','code':'코드',
            'terminal_reason':'종료이유','subtype':'결과종류','exit_code':'프로세스종료코드',
            'result':'제공자응답','stderr':'표준오류'}
    for attr,key in fields.items():
        value=getattr(error,attr,None)
        if isinstance(value,(str,int,float)) and not isinstance(value,bool):result[key]=안전문장(value) if isinstance(value,str) else value
    errors=getattr(error,'errors',None)
    if isinstance(errors,list):result['제공자오류']=[안전문장(x) for x in errors[:10] if isinstance(x,str)]
    # 상위 단계에서 받은 진단만 유지한다. 원본 data/요청 본문/환경/locals는 기록하지 않는다.
    saved=getattr(error,'AI진단',None)
    if isinstance(saved,dict):
        for key in ('제공자','모델','단계','경과초'):
            if key in saved:result[key]=saved[key]
    frames=traceback.extract_tb(error.__traceback__)
    if frames:result['호출위치']=[{'파일':Path(x.filename).name,'함수':x.name,'줄':x.lineno} for x in frames[-12:]]
    seen={id(error)};causes=[];cause=error.__cause__ or error.__context__
    while cause is not None and id(cause) not in seen and len(causes)<3:
        seen.add(id(cause));causes.append({'종류':type(cause).__name__,'메시지':안전문장(str(cause))})
        cause=cause.__cause__ or cause.__context__
    if causes:result['원인']=causes
    return result


def 저장(folder,error,**context):
    """동일 실행의 이전 오류를 보존한다. 기록 실패가 원래 오류를 덮지 않게 한다."""
    result=진단(error,**context)
    try:
        path=Path(folder)/'AI_오류.json'
        data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {'오류':[]}
        data['오류'].append(result)
        temporary=path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
        from 파일쓰기 import 바꿔쓰기
        바꿔쓰기(temporary, path)
    except (OSError,ValueError,TypeError,KeyError):
        result['기록주의']='진단 파일 저장 실패'
    return result
