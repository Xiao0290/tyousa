from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from openpyxl import Workbook

from tyousa.excel import COLUMN_MAPPING

RICHREPORT_ROWS: tuple[tuple[str, int, int], ...] = (
    ("一般世帯総数", 1200, 4800),
    ("単身世帯数", 400, 1600),
    ("２人世帯数", 300, 1100),
    ("３人世帯数", 200, 700),
    ("４人世帯数", 150, 650),
    ("５人世帯数", 100, 500),
    ("６人以上世帯数", 50, 250),
    ("主世帯数", 1150, 4600),
    ("共同住宅世帯数", 700, 2500),
    ("住宅に住む一般世帯", 1050, 4300),
    ("持ち家世帯数", 500, 2100),
    ("民営の借家世帯数", 400, 1800),
)


def create_template(path: Path) -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "候选点"
    sheet.append(list(COLUMN_MAPPING.keys()))
    book.save(path)
    return path


def create_richreport(path: Path, rows: Iterable[tuple[str, int, int]] = RICHREPORT_ROWS) -> Path:
    book = Workbook()
    sheet = book.active
    sheet.title = "世帯数"
    sheet.append(["項目", "１次エリア", "２次エリア"])
    for label, value_600, value_2000 in rows:
        sheet.append([label, value_600, value_2000])
    book.save(path)
    return path


def create_sample_assets(output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    template_path = output_dir / "template.xlsx"
    richreport_path = output_dir / "richreport_sample.xlsx"
    create_template(template_path)
    create_richreport(richreport_path)
    return template_path, richreport_path
