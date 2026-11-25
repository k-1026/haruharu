"""Gemini가 지침·조사자료를 읽을 수 있는 제한된 조회 도구. 파일 쓰기·실행 없음."""
from pathlib import Path, PurePosixPath


_허용폴더=('지침','research','inventory','.claude/agents','.claude/skills')
_허용확장자={'.md','.txt','.csv','.json','.html','.tsv'}


def 저장소도구(root):
    root=Path(root).resolve()

    def 안전한경로(relative_path):
        if not isinstance(relative_path,str) or not relative_path.strip():
            raise ValueError('저장소 상대 경로가 필요합니다.')
        relative=PurePosixPath(relative_path.replace('\\','/'))
        if relative.is_absolute() or '..' in relative.parts or ':' in relative_path:
            raise ValueError('저장소 밖의 경로는 읽을 수 없습니다.')
        path=(root/Path(*relative.parts)).resolve()
        try:clean=path.relative_to(root).as_posix()
        except ValueError:raise ValueError('저장소 밖의 경로는 읽을 수 없습니다.') from None
        if not any(clean==base or clean.startswith(base+'/') for base in _허용폴더):
            raise ValueError('지침·조사자료 경로만 읽을 수 있습니다.')
        return path

    def 읽을파일(path):
        return path.is_file() and path.suffix.lower() in _허용확장자

    def read_repository_file(relative_path: str) -> str:
        """Read a text instruction or research file from this repository.

        Args:
            relative_path: Repository relative path, for example 지침/README.md.
        """
        path=안전한경로(relative_path)
        if not 읽을파일(path):raise ValueError('읽을 수 있는 텍스트 자료 파일이 아닙니다.')
        with path.open(encoding='utf-8-sig',errors='replace') as handle:
            content=handle.read(100001)
        return content[:100000]+('\n[이후 내용 생략: 검색 도구로 필요한 부분을 찾으세요.]' if len(content)>100000 else '')

    def search_repository_text(phrase: str, relative_path: str = '지침') -> str:
        """Find lines containing a phrase in text instruction or research files.

        Args:
            phrase: Literal text to search for.
            relative_path: Repository relative directory or text file to search.
        """
        if not isinstance(phrase,str) or not phrase or len(phrase)>120:raise ValueError('검색어는 1~120자로 입력하세요.')
        target=안전한경로(relative_path)
        candidates=[target] if target.is_file() else target.rglob('*') if target.is_dir() else []
        result=[]
        for file in candidates:
            try:file=안전한경로(file.relative_to(root).as_posix())
            except ValueError:continue
            if not 읽을파일(file) or file.stat().st_size>2000000:continue
            for number,line in enumerate(file.read_text(encoding='utf-8-sig',errors='replace').splitlines(),1):
                if phrase.casefold() in line.casefold():
                    result.append(f'{file.relative_to(root).as_posix()}:{number}: {line[:300]}')
                    if len(result)>=50:return '\n'.join(result)+'\n[결과 50개까지만 표시]'
        return '\n'.join(result) or '검색 결과 없음'

    def list_repository_files(pattern: str) -> str:
        """List matching instruction or research files using a repository relative glob.

        Args:
            pattern: Glob such as 지침/3_코스검토/*.md.
        """
        if not isinstance(pattern,str) or not pattern or len(pattern)>200:
            raise ValueError('파일 검색 패턴을 입력하세요.')
        normalized=pattern.replace('\\','/')
        if normalized.startswith('/') or '..' in PurePosixPath(normalized).parts or ':' in normalized:
            raise ValueError('저장소 상대 패턴만 사용할 수 있습니다.')
        prefix=normalized.split('/',1)[0]
        if prefix not in {base.split('/')[0] for base in _허용폴더}:
            raise ValueError('지침·조사자료 패턴만 사용할 수 있습니다.')
        results=[]
        for file in root.glob(normalized):
            try:path=안전한경로(file.relative_to(root).as_posix())
            except ValueError:continue
            if 읽을파일(path):results.append(path.relative_to(root).as_posix())
            if len(results)>=100:break
        return '\n'.join(sorted(results)) or '일치하는 파일 없음'

    return read_repository_file,search_repository_text,list_repository_files
