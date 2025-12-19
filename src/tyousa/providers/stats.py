from __future__ import annotations

import logging
from pathlib import Path

from tyousa.models import StatsMetrics, StatsResult
from tyousa.providers.richreport import RichReportProvider

logger = logging.getLogger(__name__)


class StatsCalculator:
    @staticmethod
    def compute_metrics(result: StatsResult) -> StatsMetrics:
        snap_600 = result.by_radius.get(600)
        snap_2000 = result.by_radius.get(2000)
        metrics = StatsMetrics()

        if snap_600:
            metrics.households_600 = snap_600.households_total
            metrics.rental_share_600 = _rental_share(snap_600)
            metrics.apartment_share_600 = _safe_divide(
                snap_600.apartment_households, snap_600.main_households
            )
            metrics.small_household_share_600 = _safe_divide(
                snap_600.one_person + snap_600.two_person, snap_600.households_total
            )
        if snap_2000:
            metrics.households_2000 = snap_2000.households_total
            metrics.rental_share_2000 = _rental_share(snap_2000)
            metrics.family_share_2000 = _safe_divide(
                snap_2000.three_person
                + snap_2000.four_person
                + snap_2000.five_person
                + snap_2000.six_plus,
                snap_2000.households_total,
            )
        return metrics


class StatsProviderFactory:
    def __init__(self, jstat_api_key: str | None) -> None:
        self.jstat_api_key = jstat_api_key

    def get_provider(self, richreport_path: Path | None):
        if self.jstat_api_key:
            from tyousa.providers.jstat_api import JstatApiProvider

            return JstatApiProvider(self.jstat_api_key)
        if richreport_path:
            return RichReportProvider(richreport_path)
        raise RuntimeError("No stats provider available; supply JSTAT_API_KEY or richreport_path")


class TrendProvider:
    """Placeholder trend provider to allow future extensions."""

    def fetch_trend_index(self, lat: float, lon: float) -> float | None:
        return None


def _rental_share(snapshot) -> float | None:
    denominator = snapshot.housing_households
    if denominator == 0:
        return None
    if snapshot.owner_households:
        return _safe_divide(snapshot.housing_households - snapshot.owner_households, denominator)
    if snapshot.private_rental_households is not None:
        return _safe_divide(snapshot.private_rental_households, denominator)
    return None


def _safe_divide(num: float, den: float) -> float | None:
    if den == 0:
        return None
    return num / den
