from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

import requests

from tyousa.cache import SQLiteCache
from tyousa.models import PoiMetrics
from tyousa.utils import RetryConfig, backoff_times, distance_to_nearest

logger = logging.getLogger(__name__)


@dataclass
class GooglePlace:
    place_id: str
    location: tuple[float, float]
    rating: float | None
    user_ratings_total: int | None


class GooglePoiProvider:
    def __init__(self, cache: SQLiteCache, retry: RetryConfig | None = None) -> None:
        self.cache = cache
        self.retry = retry or RetryConfig()
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def _request(self, endpoint: str, params: dict) -> dict:
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for Places API")
        params = {**params, "key": self.api_key, "language": "ja"}
        for delay in backoff_times(self.retry):
            try:
                resp = requests.get(endpoint, params=params, timeout=self.retry.timeout)
                if resp.status_code == 429:
                    logger.warning("Places rate limited; sleeping %s", delay)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status in {"OK", "ZERO_RESULTS"}:
                    return data
                logger.warning("Places returned status %s", status)
            except requests.RequestException as exc:
                logger.error("Places request failed: %s", exc)
            time.sleep(delay)
        raise RuntimeError("Places API failed after retries")

    def _nearby(
        self,
        location: tuple[float, float],
        radius: int,
        keyword: str,
        place_type: str | None = None,
    ) -> list[GooglePlace]:
        lat, lon = location
        params: dict = {"location": f"{lat},{lon}", "radius": radius, "keyword": keyword}
        if place_type:
            params["type"] = place_type
        data = self._request("https://maps.googleapis.com/maps/api/place/nearbysearch/json", params)
        results: list[GooglePlace] = []
        for item in data.get("results", []):
            loc = item.get("geometry", {}).get("location", {})
            place = GooglePlace(
                place_id=item.get("place_id"),
                location=(float(loc.get("lat")), float(loc.get("lng"))),
                rating=item.get("rating"),
                user_ratings_total=item.get("user_ratings_total"),
            )
            results.append(place)
        return results

    def _bool_from_places(
        self,
        location: tuple[float, float],
        radius: int,
        keyword: str,
        place_type: str | None = None,
    ) -> int:
        key = f"poi:bool:{location}:{radius}:{keyword}:{place_type}"
        cached = self.cache.get(key)
        if cached is not None:
            return int(cached)
        has_any = int(len(self._nearby(location, radius, keyword, place_type)) > 0)
        self.cache.set(key, has_any, ttl_seconds=60 * 60 * 24 * 30)
        return has_any

    def fetch(self, location: tuple[float, float]) -> PoiMetrics:
        if not self.api_key:
            logger.info("GOOGLE_API_KEY missing; returning empty POI metrics")
            return PoiMetrics()

        cache_key = f"poi:{location}"
        cached = self.cache.get(cache_key)
        if cached:
            return PoiMetrics(**cached)

        competitors_600 = self._nearby(location, 600, keyword="コインランドリー")
        competitors_2000 = self._nearby(location, 2000, keyword="コインランドリー")

        nearest_competitor = distance_to_nearest(location, [c.location for c in competitors_2000])

        station_dist = self._nearest_distance(
            location, radius=2000, keyword="駅", place_type="train_station"
        )
        anchor_dist = self._nearest_distance(location, radius=2000, keyword="スーパー 薬局 家具")

        metrics = PoiMetrics(
            count_competitors_600=len(competitors_600),
            count_competitors_2000=len(competitors_2000),
            nearest_competitor_distance_m=nearest_competitor,
            nearest_station_distance_m=station_dist,
            nearest_anchor_distance_m=anchor_dist,
            parking_anchor_300m=self._bool_from_places(
                location, 300, keyword="駐車場", place_type="parking"
            ),
        )
        self.cache.set(cache_key, metrics.__dict__, ttl_seconds=60 * 60 * 24 * 7)
        return metrics

    def _nearest_distance(
        self,
        location: tuple[float, float],
        radius: int,
        keyword: str,
        place_type: str | None = None,
    ) -> float | None:
        places = self._nearby(location, radius, keyword=keyword, place_type=place_type)
        return distance_to_nearest(location, [p.location for p in places])
