"""로컬 서버 시작. 실제 서버 코드는 서버/관리자조회.py에 있다."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.서버.관리자조회 import main

if __name__ == '__main__':
    main()
