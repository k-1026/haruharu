"""단계별 CLI 시작. 실제 실행 코드는 공통/orchestrator.py에 있다."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import argparse
import asyncio
from app.공통.orchestrator import 메인

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='1→2 기본 실행, 선택적으로 3→4 초안 통합시험')
    parser.add_argument('--통합시험', action='store_true', help='3·4단계 초안 통합시험 (실제 AI 호출)')
    asyncio.run(메인(parser.parse_args().통합시험))
