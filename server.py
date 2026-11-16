"""
대시보드용 로컬 서버.

사용법 (이 폴더에서):
    python server.py

그다음 브라우저에서 아래 주소를 엽니다:
    http://localhost:8000/dashboard.html

이 서버는 이 폴더의 파일을 그대로 보여 줍니다.
dashboard.html이 run_log.jsonl과 run_control.json을 2초마다 다시 읽을 수 있도록
캐시를 끈 상태로 응답합니다. 자기 컴퓨터(localhost)에서만 접근할 수 있습니다.
종료하려면 이 창에서 Ctrl+C를 누르세요.
"""

import functools
import http.server
import json
import os
import socketserver
import sys
from datetime import datetime, timezone

PORT = 8000
ROOT = os.path.dirname(os.path.abspath(__file__))


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # 로그 파일이 계속 바뀌므로 브라우저가 캐시하지 않게 한다
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def do_POST(self):
        # 대시보드의 실행/중지 버튼: {"running": true|false} 를 run_control.json에 기록
        if self.path != "/control":
            self.send_error(404, "Not found")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            if not isinstance(data.get("running"), bool):
                raise ValueError("running must be true or false")
            payload = {"running": data["running"],
                       "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
            with open(os.path.join(ROOT, "run_control.json"), "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            body = json.dumps({"ok": True, **payload}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (ValueError, json.JSONDecodeError) as e:
            self.send_error(400, str(e))

    def log_message(self, fmt, *args):
        # 2초마다 들어오는 요청 로그는 화면을 어지럽히므로 생략
        pass


def ensure_files():
    # 로그 파일과 제어 파일이 없으면 만든다 (파일을 따로 준비할 필요 없음)
    log_path = os.path.join(ROOT, "run_log.jsonl")
    if not os.path.exists(log_path):
        open(log_path, "w", encoding="utf-8").close()
    ctl_path = os.path.join(ROOT, "run_control.json")
    if not os.path.exists(ctl_path):
        with open(ctl_path, "w", encoding="utf-8") as f:
            json.dump({"running": True, "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
                      f, ensure_ascii=False, indent=2)


def main():
    ensure_files()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    handler = functools.partial(NoCacheHandler, directory=ROOT)
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", port), handler) as httpd:
        print(f"대시보드 서버 실행 중: http://localhost:{port}/dashboard.html")
        print(f"폴더: {ROOT}")
        print("종료: Ctrl+C")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n서버를 종료합니다.")


if __name__ == "__main__":
    main()
