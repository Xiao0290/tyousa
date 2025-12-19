from pathlib import Path

from openpyxl import load_workbook

from tyousa.excel import ExcelWriter
from tyousa.models import CandidateMetrics, PoiMetrics, StatsMetrics
from tyousa.sample_data import create_template


def test_excel_writer_writes_values_and_preserves_percentages(tmp_path: Path):
    template = create_template(tmp_path / "template.xlsx")
    output = tmp_path / "filled.xlsx"

    metrics = [
        CandidateMetrics(
            candidate_id="OSK001",
            address="大阪市",
            lat=34.7,
            lon=135.5,
            stats=StatsMetrics(
                households_600=1200,
                households_2000=4800,
                rental_share_600=0.5,
                rental_share_2000=0.4,
                apartment_share_600=0.6,
                small_household_share_600=0.3,
                family_share_2000=0.5,
                trend_index=None,
            ),
            poi=PoiMetrics(
                count_competitors_600=2,
                count_competitors_2000=5,
                nearest_competitor_distance_m=180.0,
                nearest_station_distance_m=250.0,
                nearest_anchor_distance_m=400.0,
                parking_anchor_300m=1,
            ),
        )
    ]

    writer = ExcelWriter(template, preserve_manual=True)
    writer.write(metrics, output)

    book = load_workbook(output)
    sheet = book["候选点"]

    # Values written at starting row 5
    assert sheet["A5"].value == "OSK001"
    assert abs(sheet["G5"].value - 0.5) < 1e-6
    assert sheet["M5"].value == 2
    assert sheet["N5"].value == 5
    assert abs(sheet["O5"].value - 180.0) < 1e-6
