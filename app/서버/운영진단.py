"""저장된 오류를 운영자용 짧은 원인·조치로 분류한다. 외부 호출 없음."""


def 오류안내(detail):
    detail = detail if isinstance(detail, dict) else {}
    values = detail.get('원인', [])
    causes = [x for x in values if isinstance(x, dict)] if isinstance(values, list) else []
    text = ' '.join(str(x.get('메시지', '')) for x in [detail, *causes]).lower()
    kind = str(detail.get('종류', ''))
    status = str(detail.get('HTTP상태', ''))
    # SDK의 겉 오류보다 하위 OS 오류를 먼저 본다.
    if 'winerror 206' in text:
        return ('지침·자료가 Windows 명령행 길이 한도를 넘었습니다.',
                '지침을 파일로 전달하는 수정 버전으로 서버를 재시작한 뒤 새 기획을 실행하세요.')
    if 'timeout' in kind.lower() or '시간초과' in kind or 'timed out' in text or '제한 시간' in text or '응답하지 않아' in text:
        return ('AI 응답 제한 시간을 초과했습니다.', 'AI 서비스 상태와 연결을 확인한 뒤 새 실행을 시도하세요.')
    if status in ('401', '403') or any(x in text for x in ('authentication', 'unauthorized', 'invalid api key', 'not logged in')):
        return ('AI 인증 또는 접근 권한이 거부됐습니다.', '서버의 AI 로그인·키·모델 접근 권한을 확인하세요.')
    if status == '429' or any(x in text for x in ('rate limit', 'quota exceeded', 'usage limit')):
        return ('AI 사용량 또는 호출 한도에 도달했습니다.', '사용량·호출 한도와 재시도 가능 시점을 확인하세요.')
    if kind == 'CLINotFoundError':
        return ('Claude 실행 파일을 시작하지 못했습니다.', '상세 오류와 서버의 Claude SDK·실행 파일 경로를 확인하세요.')
    if any(x in text for x in ('connection refused', 'connection error', 'getaddrinfo', 'network is unreachable')):
        return ('AI 서버에 연결하지 못했습니다.', '서버의 네트워크·프록시와 AI 서비스 상태를 확인하세요.')
    return ('상세 오류 기록을 확인해야 합니다.', '아래 상세 오류 원문에서 메시지와 하위 원인을 확인하세요.')
