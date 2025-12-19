from pathlib import Path

from tyousa.providers.richreport import RichReportProvider
from tyousa.sample_data import create_richreport


def test_richreport_parsing_produces_snapshots(tmp_path: Path):
    sample = create_richreport(tmp_path / "richreport_sample.xlsx")
    provider = RichReportProvider(sample)
    result = provider.fetch()

    snap_600 = result.by_radius[600]
    snap_2000 = result.by_radius[2000]

    assert snap_600.households_total == 1200
    assert snap_600.one_person == 400
    assert snap_2000.owner_households == 2100
    assert snap_2000.apartment_households == 2500
