"""자동시험 전용 경로. 실행 코드와 시험 간 견본 모듈을 검색할 수 있게 한다.

저장소 루트에서: python -m unittest discover -s app -p 'test_*.py'
"""
from pathlib import Path
import sys

for 경로 in (Path(__file__).resolve().parents[2], Path(__file__).resolve().parents[1], Path(__file__).resolve().parent):
    if str(경로) not in sys.path:
        sys.path.insert(0, str(경로))
