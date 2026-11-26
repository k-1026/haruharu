"""기관 데이터 파일을 받아 에이전트가 읽을 수 있는 CSV로 맞춘다. 규칙은 지침/2_수요근거/입력_형식.md."""

import csv
import shutil
from pathlib import Path

허용 = {".csv", ".xlsx"}
거절 = {".pdf": "PDF", ".hwp": "HWP", ".hwpx": "HWP"}


def 파일_받기(원본경로: str, 실행: Path) -> list[Path]:
    """원본을 실행 폴더에 복사해 두고, 에이전트에 줄 CSV 경로 목록을 돌려준다.

    받을 수 없는 형식이면 ValueError (메시지는 담당자에게 그대로 보여 준다).
    """
    원본 = Path(원본경로.strip().strip('"'))
    if not 원본.is_file():
        raise ValueError(f"파일을 찾을 수 없습니다: {원본}")
    확장자 = 원본.suffix.lower()
    if 확장자 in 거절:
        raise ValueError(f"{거절[확장자]} 파일은 받지 않습니다. 표를 엑셀이나 CSV로 옮겨 올려 주세요.")
    if 확장자 not in 허용:
        raise ValueError("CSV 또는 XLSX 파일만 올릴 수 있습니다.")

    보관 = 실행 / "기관데이터"
    보관.mkdir(parents=True, exist_ok=True)
    복사본 = 보관 / 원본.name
    shutil.copy2(원본, 복사본)  # 원본은 수정하지 않는다

    if 확장자 == ".csv":
        return [복사본]
    return _xlsx를_csv로(복사본, 보관)


def _xlsx를_csv로(xlsx: Path, 폴더: Path) -> list[Path]:
    from openpyxl import load_workbook

    책 = load_workbook(xlsx, data_only=True, read_only=True)  # 수식은 저장된 값만
    결과 = []
    for 시트 in 책.worksheets:
        경로 = 폴더 / f"{xlsx.stem}_{시트.title}.csv"
        with 경로.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.writer(f)
            for 행 in 시트.iter_rows(values_only=True):
                w.writerow(["" if 칸 is None else 칸 for 칸 in 행])
        결과.append(경로)
    return 결과
