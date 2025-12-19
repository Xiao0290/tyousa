from __future__ import annotations

import logging

from tyousa.models import StatsResult

logger = logging.getLogger(__name__)


class JstatApiProvider:
    """
    Placeholder for jSTAT MAP API integration.

    The actual API requires token management and area definition; this class currently logs a
    clear message so users know to rely on RichReportProvider until credentials are supplied.
    """

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def fetch(self, lat: float, lon: float) -> StatsResult:
        raise NotImplementedError(
            "JstatApiProvider not fully implemented. Provide richreport_path or extend this class."
        )
