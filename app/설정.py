"""로컬 .env와 프로세스 환경변수에서 실행 설정을 읽는다. 비밀값은 출력하지 않는다."""
import os
from pathlib import Path
import re


프로젝트 = Path(__file__).resolve().parent.parent
설정이름 = {
    'AI_PROVIDER', 'GEMINI_API_KEY', 'GEMINI_MODEL', 'CLAUDE_MODEL',
    'HARUHARU_DATA_DIR', 'HARUHARU_PLACES_FILE', 'HARUHARU_TRAVEL_FILE',
}


def 설정_읽기(root=None, environ=None):
    root=Path(root) if root is not None else 프로젝트
    values={}
    envfile=root/'.env'
    if envfile.is_file():
        for line in envfile.read_text(encoding='utf-8-sig').splitlines():
            line=line.strip()
            if not line or line.startswith('#'):continue
            if line.startswith('export '):line=line[7:].lstrip()
            name,separator,value=line.partition('=')
            name=name.strip()
            if not separator or not re.fullmatch(r'[A-Z][A-Z0-9_]*',name) or name not in 설정이름:continue
            value=value.strip()
            if len(value)>=2 and value[0]==value[-1] and value[0] in ('"',"'"):
                value=value[1:-1]
            else:
                value=value.split(' #',1)[0].strip()
            values[name]=value
    for name,value in (os.environ if environ is None else environ).items():
        if name in 설정이름:values[name]=value
    return values


def 자료_경로(settings, root=None):
    root=Path(root) if root is not None else 프로젝트
    location=settings.get('HARUHARU_DATA_DIR') or 'research/data'
    path=Path(location).expanduser()
    return (path if path.is_absolute() else root/path).resolve()


def 자료_파일(settings, name, default, root=None):
    filename=settings.get(name) or default
    if Path(filename).name!=filename or filename in ('.','..'):
        raise ValueError(f'{name}은 자료 폴더 안의 파일 이름만 지정하세요.')
    return 자료_경로(settings,root)/filename
