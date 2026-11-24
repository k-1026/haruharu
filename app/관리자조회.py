"""로컬 실행 기록 조회·코스 조건 입력·3단계 시험 서버."""
import argparse
import json
import re
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

기준 = Path(__file__).resolve().parent
파일이름 = re.compile(r'(?:[1-5]단계_(?:결과(?:_\d+)?\.md|선택(?:_\d+)?\.json|전달_(?:준비|검사)\.json|입력\.json|담당자선택\.json)|3단계_(?:구조화|운영확인)\.json|코스작성조건_선택\.json|통합시험_상태\.json|기획_진행\.json|근거_추출\.json|AI_오류\.json|2단계_AI요약_원문\.md)\Z')


class 결과저장소:
    def __init__(self, 루트):
        self.루트 = Path(루트).resolve()

    def _경로(self, 키):
        if not isinstance(키, str) or '\\' in 키 or '\x00' in 키:
            raise ValueError('허용하지 않는 경로')
        조각 = 키.split('/')
        if not 키 or any(p in ['', '.', '..'] or ':' in p for p in 조각):
            raise ValueError('허용하지 않는 경로')
        경로 = self.루트.joinpath(*조각).resolve()
        if not 경로.is_relative_to(self.루트):
            raise ValueError('runs 밖의 경로')
        return 경로

    def _JSON(self, 폴더, 이름):
        경로 = 폴더 / 이름
        if not 경로.is_file():
            return {}, False
        try:
            내용 = self.파일(경로.relative_to(self.루트).as_posix())['본문']
            값 = json.loads(내용)
            return (값, False) if isinstance(값, dict) else ({}, True)
        except (ValueError, OSError, UnicodeError):
            return {}, True

    def _파일들(self, 폴더):
        결과 = []
        for 경로 in sorted(폴더.iterdir()):
            if 경로.is_file() and 파일이름.fullmatch(경로.name):
                try:
                    self._경로(경로.relative_to(self.루트).as_posix())
                    match = re.match(r'([1-5])단계_', 경로.name)
                    결과.append({'이름': 경로.name, '경로': 경로.relative_to(self.루트).as_posix(),
                               '단계': int(match[1]) if match else 0, '크기': 경로.stat().st_size})
                except (ValueError, OSError):
                    continue
        return 결과

    def _요약(self, 폴더):
        전달, 오류 = self._JSON(폴더, '3단계_전달_준비.json')
        선택, _ = self._JSON(폴더, '1단계_선택.json')
        검사 = 전달.get('검사결과')
        상태 = '읽기 오류' if 오류 else ('통과' if 검사 == ['통과'] else '실패' if 검사 else '기록 없음')
        return {'id': 폴더.relative_to(self.루트).as_posix(), '실행': 폴더.parent.name if '회차' in 폴더.name else 폴더.name,
                '회차': 폴더.name if '회차' in 폴더.name else '기본', '조건': 선택.get('조건') or 전달.get('조건') or {},
                '검사상태': 상태, '근거수': len(전달.get('근거목록') or []), '경고수': len(전달.get('경고목록') or []),
                '파일수': len(self._파일들(폴더))}

    def 목록(self):
        if not self.루트.is_dir():
            return []
        목록 = []
        for 실행 in sorted(self.루트.iterdir(), reverse=True):
            if not 실행.is_dir() or 실행.is_symlink() or not re.fullmatch(r'\d{8}_\d{6}', 실행.name):
                continue
            회차들 = [p for p in sorted(실행.iterdir()) if p.is_dir() and not p.is_symlink() and re.fullmatch(r'\d+회차', p.name)]
            for 폴더 in 회차들 or [실행]:
                목록.append(self._요약(폴더))
        return 목록

    def 상세(self, 키):
        폴더 = self._경로(키)
        if not 폴더.is_dir() or len(키.split('/')) > 2:
            raise FileNotFoundError('실행 기록 없음')
        결과 = self._요약(폴더)
        결과['파일'] = self._파일들(폴더)
        결과['통합시험'] = []
        for 하위 in sorted(폴더.iterdir()):
            if 하위.is_dir() and not 하위.is_symlink() and re.fullmatch(r'통합시험_\d{6}_\d+', 하위.name):
                결과['통합시험'].append(하위.relative_to(self.루트).as_posix())
                결과['파일'] += self._파일들(하위)
        return 결과

    def 파일(self, 키):
        경로 = self._경로(키)
        if not 파일이름.fullmatch(경로.name) or not 경로.is_file():
            raise FileNotFoundError('결과 파일 없음')
        if 경로.stat().st_size > 12 * 1024 * 1024:
            raise ValueError('조회 최대 크기 초과')
        return {'이름': 경로.name, '본문': 경로.read_text(encoding='utf-8-sig'),
                '형식': 경로.suffix.lstrip('.'), '경로': 키}


def 핸들러(저장소, 실행서비스=None, 기획서비스=None):
    from 관리자실행 import 코스시험
    from 기획실행 import 기획실행
    실행서비스 = 실행서비스 or 코스시험(저장소)
    기획서비스 = 기획서비스 or 기획실행(실행서비스)
    토큰 = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def 호스트확인(self):
            return self.headers.get('Host') in [f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}']

        def 응답(self, 상태, 본문, 타입='application/json; charset=utf-8'):
            데이터 = 본문 if isinstance(본문, bytes) else json.dumps(본문, ensure_ascii=False).encode('utf-8')
            self.send_response(상태)
            self.send_header('Content-Type', 타입)
            self.send_header('Content-Length', str(len(데이터)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(데이터)

        def do_GET(self):
            if not self.호스트확인():
                return self.응답(403, {'오류': '로컬 주소로 접속하세요.'})
            경로 = urlsplit(self.path)
            인자 = parse_qs(경로.query)
            try:
                if 경로.path == '/api/session':
                    return self.응답(200, {'token': 토큰})
                if 경로.path == '/api/places':
                    from 장소정보 import 장소목록
                    return self.응답(200, {'장소목록':장소목록()})
                if 경로.path == '/api/course':
                    return self.응답(200, 실행서비스.정보(인자.get('id', [''])[0]))
                if 경로.path == '/api/course/status':
                    return self.응답(200, 실행서비스.상태(인자.get('id', [''])[0]))
                if 경로.path == '/api/course/review':
                    return self.응답(200, 실행서비스.검토정보(인자.get('id',[''])[0]))
                if 경로.path == '/api/plan/status':
                    return self.응답(200, 기획서비스.상태(인자.get('id', [''])[0]))
                if 경로.path == '/api/plan/record':
                    return self.응답(200, 기획서비스.기록보기(인자.get('id', [''])[0], 인자.get('안', [None])[0], 인자.get('버전', [None])[0]))
                if 경로.path == '/api/plan/latest':
                    return self.응답(200, {'기획': 기획서비스.최근()})
                if 경로.path == '/api/plan/course':
                    from 담당자요약 import 요약_불러오기
                    키 = 인자.get('id', [''])[0]
                    저장소._경로(키)  # 잘못된 경로는 ValueError → 400
                    return self.응답(200, 요약_불러오기(실행서비스, 키))
                if 경로.path in ['/', '/plan', '/plan/', '/plan/plan.js', '/plan/plan.css']:
                    이름, 타입 = {'/plan.js': ('plan.js', 'text/javascript; charset=utf-8'),
                               '/plan.css': ('plan.css', 'text/css; charset=utf-8')}.get(
                        경로.path.removeprefix('/plan'), ('index.html', 'text/html; charset=utf-8'))
                    return self.응답(200, (기준 / '담당자화면' / 이름).read_bytes(), 타입)
                if 경로.path == '/api/runs':
                    return self.응답(200, 저장소.목록())
                if 경로.path == '/api/run':
                    return self.응답(200, 저장소.상세(인자.get('id', [''])[0]))
                if 경로.path == '/api/file':
                    return self.응답(200, 저장소.파일(인자.get('path', [''])[0]))
                자산 = {'/admin': ('로그.html', 'text/html; charset=utf-8'),
                      '/admin/': ('로그.html', 'text/html; charset=utf-8'),
                      '/admin/logs.js': ('로그.js','text/javascript; charset=utf-8'),
                      '/admin/logs.css': ('로그.css','text/css; charset=utf-8'),
                      '/admin/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                      '/admin/course.js': ('코스조건.js', 'text/javascript; charset=utf-8'),
                      '/admin/course.css': ('코스조건.css', 'text/css; charset=utf-8'),
                      '/admin/review.js': ('운영확인.js','text/javascript; charset=utf-8'),
                      '/admin/places.js': ('장소선택.js','text/javascript; charset=utf-8'),
                      '/admin/review.css': ('운영확인.css','text/css; charset=utf-8'),
                      '/admin/style.css': ('style.css', 'text/css; charset=utf-8')}
                if 경로.path in 자산:
                    이름, 타입 = 자산[경로.path]
                    return self.응답(200, (기준 / '관리자화면' / 이름).read_bytes(), 타입)
                return self.응답(404, {'오류': '없는 페이지'})
            except ValueError as 오류:
                return self.응답(400, {'오류': str(오류) if 경로.path.startswith(('/api/course', '/api/plan/status', '/api/plan/record')) else '기록 형식을 확인하세요.'})
            except (OSError, UnicodeError):
                return self.응답(404, {'오류': '기록을 읽을 수 없습니다. 경로와 저장 완료 여부를 확인하세요.'})

        def do_POST(self):
            # 제한된 본문을 먼저 읽는다. 본문을 남긴 채 403으로 연결을 닫으면
            # Windows에서 거부 응답 대신 연결 중단으로 보일 수 있다.
            try:
                크기=int(self.headers.get('Content-Length','0'))
                if not 0<크기<=65536:return self.응답(413,{'오류':'입력 크기를 확인하세요.'})
                self.connection.settimeout(5)
                본문=self.rfile.read(크기)
                if len(본문)!=크기:return self.응답(400,{'오류':'입력 본문을 끝까지 받지 못했습니다.'})
            except (ValueError,OSError):
                return self.응답(400,{'오류':'입력 본문을 읽지 못했습니다.'})
            if not self.호스트확인() or self.headers.get('Origin') != 'http://' + self.headers.get('Host', ''):
                return self.응답(403, {'오류': '이 관리자 화면에서 요청하세요.'})
            받은토큰 = self.headers.get('X-Admin-Token', '')
            if not 받은토큰.isascii() or not secrets.compare_digest(받은토큰, 토큰):
                return self.응답(403, {'오류': '화면을 새로고침한 뒤 다시 저장하세요.'})
            if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
                return self.응답(415, {'오류': 'JSON 요청이 필요합니다.'})
            try:
                값 = json.loads(본문.decode('utf-8'))
                if not isinstance(값, dict):
                    raise ValueError('입력 형식을 확인하세요.')
                if self.path == '/api/plan/revise':
                    return self.응답(202, 기획서비스.수정시작(값))
                if self.path == '/api/plan/start':
                    return self.응답(202, 기획서비스.시작(값))
                if self.path == '/api/course/save':
                    return self.응답(201, 실행서비스.저장(값.get('id'), 값.get('조건')))
                if self.path == '/api/course/start':
                    return self.응답(202, 실행서비스.시작(값.get('시험id')))
                if self.path == '/api/course/apply':
                    return self.응답(201, 실행서비스.수정반영(값.get('시험id'), 값.get('조건')))
                if self.path == '/api/course/review/save':
                    return self.응답(201, 실행서비스.검토반영(값.get('시험id'),값.get('확인내용')))
                return self.응답(404, {'오류': '없는 요청입니다.'})
            except (ValueError, UnicodeError) as 오류:
                return self.응답(400, {'오류': str(오류) if not isinstance(오류, (json.JSONDecodeError, UnicodeError)) else '입력 JSON을 확인하세요.'})
            except OSError:
                return self.응답(400, {'오류': '시험 기록을 읽거나 저장하지 못했습니다.'})

        def do_PUT(self):
            self.응답(405, {'오류': '지원하지 않는 요청입니다.'})

        do_DELETE = do_PUT

        def log_message(self, 형식, *인자):
            pass  # 브라우저 조회 때 원문·개인 입력을 콘솔 로그로 복제하지 않는다.

    return Handler


def main():
    parser = argparse.ArgumentParser(description='실행 기록 조회·코스 조건 입력·3단계 시험')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--runs', type=Path, default=기준 / 'runs')
    args = parser.parse_args()
    server = ThreadingHTTPServer(('127.0.0.1', args.port), 핸들러(결과저장소(args.runs)))
    print(f'관리자 결과 조회: http://127.0.0.1:{args.port}/admin/', flush=True)
    print('관리자: 읽기 전용 운영 로그 · 기획 시작 시에만 AI 실행 · 종료: Ctrl+C', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
