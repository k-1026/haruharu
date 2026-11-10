#!/usr/bin/env python3
"""VOC 분류 관제 프로그램 (표준 라이브러리만 사용).

사용법
  python board/control.py serve [--port 8765]   관제 화면(index.html)과 API를 띄운다
  python board/control.py grade                 채점만 한 번 실행해 board/status.json을 갱신한다

채점 기준은 .claude/agents/review-grader.md, 허용 태그는 CLAUDE.md 2번을 따른다.
  ① 범위 점수 : part_1~10.csv에 r_001~r_100이 빠짐없이 한 번씩 있는가
  ② 근거 점수 : evidence가 15자 이내이고 원문(archive/batch*/r_NNN.md)에 그대로 있는가
  ③ 형식 점수 : 태그가 허용 7개 안에 있고, 검토 비율 5% 이하, 검토 note 작성 여부
  묶음 점수가 모두 80 이상이면 통과, 하나라도 미만이면 재작업.
"""

import argparse
import collections
import csv
import json
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BOARD = Path(__file__).resolve().parent
ROOT = BOARD.parent  # D12 페인포인트 실습
PARTS = ROOT / "ax" / "demo" / "parts"
ARCHIVE = ROOT / "archive"
STATUS_FILE = BOARD / "status.json"
ACTION_LOG = BOARD / "actions.log"
INDEX_FILE = BOARD / "index.html"
PROGRESS_FILE = BOARD / "progress.json"  # 에이전트가 단계가 바뀔 때마다 갱신한다
REVIEW_FILE = BOARD / "review_check.json"  # 사람 대조·승인 기록
REVIEW_SIZE = 10
REVIEW_PASS_AGREE = 9

STEPS = ["준비", "분류", "저장 검사", "채점", "집계", "사람 대조·승인"]

ALLOWED_TAGS = ["P1", "P2", "P3", "H1", "H2", "해당없음", "검토"]
EXPECTED_IDS = [f"r_{i:03d}" for i in range(1, 101)]
EXPECTED_HEADER = ["voc_id", "tag", "evidence", "note"]
MAX_EVIDENCE_LEN = 15
REVIEW_LIMIT = 0.05
PASS_SCORE = 80


def clamp(value: float) -> int:
    return max(0, min(100, int(round(value))))


def load_sources() -> dict:
    """r_NNN -> 원문 전체 텍스트"""
    return {p.stem: p.read_text(encoding="utf-8", errors="replace") for p in ARCHIVE.glob("batch*/r_*.md")}


def read_parts() -> tuple[list, list]:
    """part_1~10.csv를 읽어 (파일 상태 목록, 행 목록)을 돌려준다."""
    files, rows = [], []
    for n in range(1, 11):
        path = PARTS / f"part_{n}.csv"
        info = {"file": path.name, "exists": path.exists(), "header_ok": False, "rows": 0}
        if path.exists():
            with path.open(encoding="utf-8-sig", newline="") as f:
                reader = csv.reader(f)
                header = next(reader, [])
                info["header_ok"] = header == EXPECTED_HEADER
                for raw in reader:
                    padded = (raw + ["", "", "", ""])[:4]
                    rows.append({"file": path.name, "voc_id": padded[0].strip(), "tag": padded[1].strip(),
                                 "evidence": padded[2].strip(), "note": padded[3].strip()})
                    info["rows"] += 1
        files.append(info)
    return files, rows


def grade() -> dict:
    sources = load_sources()
    files, rows = read_parts()
    issues = []

    # ① 범위 점수
    ids = [r["voc_id"] for r in rows]
    seen = set(ids)
    missing = [i for i in EXPECTED_IDS if i not in seen]
    duplicates = len(ids) - len(seen)
    for i in missing:
        issues.append(f"누락: {i}")
    dup_ids = sorted({i for i in ids if ids.count(i) > 1})
    for i in dup_ids:
        issues.append(f"중복: {i}")
    header_bad = [f["file"] for f in files if f["exists"] and not f["header_ok"]]
    for name in header_bad:
        issues.append(f"헤더 오류: {name}")
    missing_files = [f["file"] for f in files if not f["exists"]]
    for name in missing_files:
        issues.append(f"파일 없음: {name}")
    range_score = clamp(100 - 5 * len(missing) - 5 * duplicates - 5 * len(header_bad) - 5 * len(missing_files))

    # ② 근거 점수
    evidence_ok = []
    for r in rows:
        src = sources.get(r["voc_id"], "")
        ok = bool(r["evidence"]) and len(r["evidence"]) <= MAX_EVIDENCE_LEN and r["evidence"] in src
        r["evidence_ok"] = ok
        evidence_ok.append(ok)
        if not ok:
            issues.append(f"근거 확인 실패: {r['voc_id']} ({r['evidence'] or '빈칸'})")
    total = len(rows)
    valid_evidence = sum(evidence_ok)
    evidence_score = clamp(100 * valid_evidence / total) if total else 0

    # ③ 형식 점수
    tag_counts = {t: 0 for t in ALLOWED_TAGS}
    bad_tags = 0
    review_rows = 0
    for r in rows:
        if r["tag"] in tag_counts:
            tag_counts[r["tag"]] += 1
        else:
            bad_tags += 1
            issues.append(f"허용 외 태그: {r['voc_id']} ({r['tag']})")
        if r["tag"] == "검토":
            review_rows += 1
            if not r["note"]:
                issues.append(f"검토 이유 없음: {r['voc_id']}")
        elif r["note"]:
            issues.append(f"검토가 아닌데 note 있음: {r['voc_id']}")
    review_ratio = (review_rows / total) if total else 0.0
    format_score = 100 - 5 * bad_tags
    if review_ratio > REVIEW_LIMIT:
        format_score -= 10
    format_score -= 2 * sum(1 for r in rows if r["tag"] == "검토" and not r["note"])
    format_score -= sum(1 for r in rows if r["tag"] != "검토" and r["note"])
    format_score = clamp(format_score)

    scores = {
        "range": {"score": range_score, "pass": range_score >= PASS_SCORE},
        "evidence": {"score": evidence_score, "pass": evidence_score >= PASS_SCORE},
        "format": {"score": format_score, "pass": format_score >= PASS_SCORE},
    }
    verdict = "통과" if total == 100 and all(s["pass"] for s in scores.values()) else "재작업"

    return {
        "generated_at": int(time.time()),
        "verdict": verdict,
        "scores": scores,
        "review": {"count": review_rows, "total": total, "ratio": round(review_ratio, 4), "limit": REVIEW_LIMIT,
                   "within_limit": review_ratio <= REVIEW_LIMIT},
        "tag_counts": tag_counts,
        "parts": files,
        "evidence": {"valid": valid_evidence, "total": total},
        "issues": issues[:200],
        "issue_count": len(issues),
        "rows": [{k: r[k] for k in ("voc_id", "tag", "evidence", "note", "evidence_ok", "file")} for r in rows],
    }


def write_status(status: dict) -> None:
    STATUS_FILE.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def log_action(action: str, verdict: str) -> None:
    line = f"{int(time.time())}\t{action}\t{verdict}\n"
    with ACTION_LOG.open("a", encoding="utf-8") as f:
        f.write(line)


def read_progress() -> dict:
    """progress.json을 읽어 단계별 상태(done / active / pending)를 계산한다.

    progress.json 형식 예시:
      {"step": 2, "state": "running", "batch": 3, "batch_total": 10}
      - step  : 현재 단계 번호 (1~6)
      - state : "running"(진행 중) 또는 "done"(해당 단계 완료)
    파일이 없거나 깨졌으면 모든 단계를 대기 상태로 본다.
    """
    default = {"step": 0, "state": "idle", "batch": 0, "batch_total": 10}
    try:
        raw = json.loads(PROGRESS_FILE.read_text(encoding="utf-8")) if PROGRESS_FILE.exists() else {}
    except (ValueError, OSError):
        raw = {}
    step = raw.get("step", default["step"])
    state = raw.get("state", default["state"])
    if not isinstance(step, int) or not 0 <= step <= len(STEPS):
        step = 0
    steps = []
    for i, name in enumerate(STEPS, start=1):
        if i < step or (i == step and state == "done"):
            st = "done"
        elif i == step and state == "running":
            st = "active"
        else:
            st = "pending"
        steps.append({"no": i, "name": name, "state": st})
    return {
        "step": step,
        "state": state,
        "batch": raw.get("batch", 0),
        "batch_total": raw.get("batch_total", 10),
        "steps": steps,
    }


# ---------------------------------------------------------------------------
# 실행 / 중지: 분류 → 저장 검사 → 채점 → 집계 순서로 에이전트를 돌린다.
#   분류·채점은 Claude Code CLI(claude -p --agent <이름>)로 실행하고, 중지하면 프로세스 트리를 끊는다.
#   CONTROL_TEST_CMD 환경변수가 있으면 claude 대신 그 명령을 실행한다 (테스트용).
# ---------------------------------------------------------------------------

CLAUDE_CMD = os.environ.get("CONTROL_CLAUDE_CMD", "claude")
RUN_TIMEOUT_SEC = 60 * 60

TAGGER_PROMPT = (
    "review-tagger 에이전트 규칙에 따라 archive/batch*/r_001~r_100 리뷰를 10건씩 분류해 "
    "ax/demo/parts/part_1.csv ~ part_10.csv 를 저장하라. 묶음마다 board/progress.json 을 갱신하라. "
    "끝나면 태그별 건수를 한 줄로 보고하라."
)
GRADER_PROMPT = (
    "review-grader 에이전트 규칙에 따라 ax/demo/parts/part_1.csv ~ part_10.csv 를 채점하고 "
    "점수표를 보고하라. 시작과 끝에 board/progress.json 을 갱신하라. 다른 파일은 수정하지 마라."
)

RUN = {"state": "idle", "step": 0, "message": "대기 중", "started_at": None, "finished_at": None}
_run_lock = threading.Lock()
_stop_requested = threading.Event()
_current_proc = None


class Stopped(Exception):
    pass


def write_progress(step: int, state: str, batch: int = 0, batch_total: int = 10) -> None:
    PROGRESS_FILE.write_text(json.dumps({"step": step, "state": state, "batch": batch,
                                         "batch_total": batch_total}, ensure_ascii=False), encoding="utf-8")


def kill_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/T", "/F", "/PID", str(proc.pid)], capture_output=True)
    else:
        proc.kill()


def check_stop() -> None:
    if _stop_requested.is_set():
        raise Stopped()


OUTPUT_DIR = BOARD / "output"  # 실행 로그와 승인 결과 사본을 여기에 남긴다
LOG = collections.deque(maxlen=120)  # 에이전트 활동 로그 (화면에 표시)
RUN_LOG_FILE = {"path": None}  # 지금 실행의 로그 파일 경로


def log_line(text: str) -> None:
    line = f"{time.strftime('%H:%M:%S')}  {text}"
    LOG.append(line)
    path = RUN_LOG_FILE["path"]
    if path is not None:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")


def restore_last_log() -> None:
    """서버를 다시 켰을 때 가장 최근 실행 로그를 화면 로그에 불러온다."""
    files = sorted(OUTPUT_DIR.glob("run_*.log")) if OUTPUT_DIR.exists() else []
    if files:
        for line in files[-1].read_text(encoding="utf-8").splitlines()[-LOG.maxlen:]:
            LOG.append(line)


def summarize_event(raw: str) -> str:
    """claude stream-json 한 줄을 사람이 읽을 한 줄로 바꾼다."""
    line = raw.strip()
    if not line:
        return ""
    try:
        ev = json.loads(line)
    except ValueError:
        return line[:200]
    kind = ev.get("type")
    if kind == "assistant":
        parts = []
        for block in (ev.get("message") or {}).get("content") or []:
            if block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif block.get("type") == "tool_use":
                inp = block.get("input") or {}
                brief = inp.get("file_path") or inp.get("command") or inp.get("pattern") or inp.get("description") or ""
                parts.append(f"[도구 {block.get('name')}] {brief}")
        return " ".join(p for p in parts if p)[:300]
    if kind == "result":
        return "결과: " + str(ev.get("result", ""))[:200]
    return ""


def run_agent(prompt: str, agent: str) -> str:
    global _current_proc
    test_cmd = os.environ.get("CONTROL_TEST_CMD")
    if test_cmd:
        cmd, use_shell = test_cmd, True
    else:
        cmd = [CLAUDE_CMD, "-p", prompt, "--agent", agent, "--permission-mode", "acceptEdits",
               "--output-format", "stream-json", "--verbose"]
        use_shell = False
    proc = subprocess.Popen(cmd, cwd=ROOT, shell=use_shell, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding="utf-8", errors="replace", bufsize=1)
    _current_proc = proc
    log_line(f"[{agent}] 시작")
    timer = threading.Timer(RUN_TIMEOUT_SEC, kill_tree, args=(proc,))
    timer.start()
    chunks = []
    try:
        for raw in proc.stdout:
            chunks.append(raw)
            text = summarize_event(raw)
            if text:
                log_line(f"[{agent}] {text}")
        proc.wait()
    finally:
        timer.cancel()
        _current_proc = None
    check_stop()
    if proc.returncode != 0:
        log_line(f"[{agent}] 종료 코드 {proc.returncode}")
        raise RuntimeError(f"{agent} 실패 (종료 코드 {proc.returncode})")
    log_line(f"[{agent}] 완료")
    return "".join(chunks)


def set_run(**kwargs) -> None:
    RUN.update(kwargs)
    if kwargs.get("message"):
        log_line(f"[단계] {kwargs['message']}")


def pipeline() -> None:
    step = 2
    try:
        set_run(state="running", step=2, message="분류 에이전트 실행 중", started_at=int(time.time()), finished_at=None)
        write_progress(2, "running", 0)
        run_agent(TAGGER_PROMPT, "review-tagger")
        check_stop()

        set_run(step=3, message="저장 검사 중")
        step = 3
        write_progress(3, "running")
        files, _ = read_parts()
        if any(not f["exists"] for f in files):
            raise RuntimeError("part_1~10.csv 파일이 모두 있어야 합니다")
        write_progress(3, "done")
        check_stop()

        set_run(step=4, message="채점 에이전트 실행 중")
        step = 4
        write_progress(4, "running")
        run_agent(GRADER_PROMPT, "review-grader")
        write_progress(4, "done")
        check_stop()

        set_run(step=5, message="집계 중")
        step = 5
        write_progress(5, "running")
        status = grade()
        write_status(status)
        log_action("run", status["verdict"])
        write_progress(5, "done")

        # 6단계(사람 대조·승인)는 사용자가 직접 한다. 램프는 대기 상태로 켜 둔다.
        step = 6
        write_progress(6, "running")
        set_run(state="done", step=6, finished_at=int(time.time()),
                message=f"집계 완료: {status['verdict']} · 사람 대조·승인 대기")
    except Stopped:
        write_progress(step, "stopped")
        set_run(state="stopped", finished_at=int(time.time()), message=f"{step}단계에서 중지됨")
    except Exception as exc:  # 실패도 화면에 그대로 보여 준다
        write_progress(step, "stopped")
        set_run(state="error", finished_at=int(time.time()), message=f"{step}단계 오류: {exc}")


def read_review() -> dict:
    empty = {"items": [], "decided": 0, "agree": 0, "approved": False, "approved_at": None}
    if not REVIEW_FILE.exists():
        return empty
    try:
        return json.loads(REVIEW_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return empty


def save_review(payload: dict) -> tuple[int, dict]:
    """사람 대조 결과를 저장한다. 승인은 10건 중 9건 이상 동의일 때만 받는다."""
    status = json.loads(STATUS_FILE.read_text(encoding="utf-8")) if STATUS_FILE.exists() else {}
    rows = {r["voc_id"]: r for r in status.get("rows", [])}
    raw_items = payload.get("items") or []
    ids = [str(i.get("voc_id", "")) for i in raw_items]
    if len(ids) != len(set(ids)) or any(i not in rows for i in ids):
        return 400, {"ok": False, "message": "voc_id가 없거나 중복되었습니다. 먼저 집계를 끝내 주세요."}
    if len(ids) > REVIEW_SIZE:
        return 400, {"ok": False, "message": f"대조는 최대 {REVIEW_SIZE}건입니다."}
    items = []
    for i in raw_items:
        row = rows[str(i.get("voc_id"))]
        human = i.get("human") if i.get("human") in ("agree", "disagree") else None
        items.append({"voc_id": row["voc_id"], "ai_tag": row["tag"], "ai_evidence": row["evidence"],
                      "human": human})
    decided = sum(1 for it in items if it["human"])
    agree = sum(1 for it in items if it["human"] == "agree")
    approved = False
    approved_at = None
    if payload.get("approve"):
        if len(items) != REVIEW_SIZE or decided != REVIEW_SIZE:
            return 400, {"ok": False, "message": f"{REVIEW_SIZE}건을 모두 판정해야 승인할 수 있습니다."}
        if agree < REVIEW_PASS_AGREE:
            return 400, {"ok": False, "message": f"동의 {agree}건으로 기준({REVIEW_PASS_AGREE}건 이상)에 못 미칩니다."}
        approved, approved_at = True, int(time.time())
        write_progress(6, "done")
        log_action("approve", f"승인 (동의 {agree}/{REVIEW_SIZE})")
    record = {"items": items, "decided": decided, "agree": agree, "approved": approved, "approved_at": approved_at}
    text = json.dumps(record, ensure_ascii=False, indent=2)
    REVIEW_FILE.write_text(text, encoding="utf-8")
    if approved:
        OUTPUT_DIR.mkdir(exist_ok=True)
        (OUTPUT_DIR / f"review_approved_{time.strftime('%Y%m%d_%H%M%S')}.json").write_text(text, encoding="utf-8")
    return 200, {"ok": True, **record}


def start_run() -> bool:
    with _run_lock:
        if RUN["state"] == "running":
            return False
        LOG.clear()
        _stop_requested.clear()
        OUTPUT_DIR.mkdir(exist_ok=True)
        RUN_LOG_FILE["path"] = OUTPUT_DIR / f"run_{time.strftime('%Y%m%d_%H%M%S')}.log"
        set_run(state="running", message="시작 중")
        threading.Thread(target=pipeline, daemon=True).start()
        return True


def stop_run() -> bool:
    with _run_lock:
        if RUN["state"] != "running":
            return False
        _stop_requested.set()
    proc = _current_proc
    if proc is not None:
        kill_tree(proc)
    return True


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, data: dict) -> None:
        self._send(code, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_GET(self) -> None:  # noqa: N802
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX_FILE.read_bytes(), "text/html; charset=utf-8")
        elif self.path == "/api/status":
            if STATUS_FILE.exists():
                data = json.loads(STATUS_FILE.read_text(encoding="utf-8"))
            else:
                data = {"verdict": "없음", "message": "아직 채점하지 않았습니다. 재집계를 누르세요."}
            data["progress"] = read_progress()
            data["run"] = dict(RUN)
            data["log"] = list(LOG)
            data["review"] = read_review()
            self._json(200, data)
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/actions/grade":
            status = grade()
            write_status(status)
            log_action("grade", status["verdict"])
            self._json(200, {"ok": True, "verdict": status["verdict"]})
        elif self.path == "/api/run/start":
            if start_run():
                self._json(202, {"ok": True})
            else:
                self._json(409, {"ok": False, "message": "이미 실행 중입니다"})
        elif self.path == "/api/run/stop":
            if stop_run():
                self._json(200, {"ok": True})
            else:
                self._json(409, {"ok": False, "message": "실행 중인 작업이 없습니다"})
        elif self.path == "/api/review/save":
            length = int(self.headers.get("Content-Length", 0) or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except ValueError:
                self._json(400, {"ok": False, "message": "잘못된 요청입니다"})
                return
            code, body = save_review(payload)
            self._json(code, body)
        else:
            self._json(404, {"error": "unknown action"})

    def log_message(self, fmt: str, *args) -> None:  # 콘솔을 조용하게 유지
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="VOC 분류 관제")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("grade", help="채점만 한 번 실행")
    serve = sub.add_parser("serve", help="관제 화면 서버 실행")
    serve.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    if args.cmd == "grade":
        status = grade()
        write_status(status)
        log_action("grade", status["verdict"])
        print(f"재집계 완료: 판정 {status['verdict']}, 검토 {status['review']['count']}건, 문제 {status['issue_count']}건")
        return

    status = grade()
    write_status(status)
    log_action("startup_grade", status["verdict"])
    OUTPUT_DIR.mkdir(exist_ok=True)
    restore_last_log()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"관제 화면: http://127.0.0.1:{args.port}  (종료: Ctrl+C)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
