from __future__ import annotations

import logging
import os
import time

import requests

from tyousa.cache import SQLiteCache
from tyousa.utils import RetryConfig, backoff_times

logger = logging.getLogger(__name__)


class GoogleGeocoder:
    def __init__(self, cache: SQLiteCache, retry: RetryConfig | None = None) -> None:
        self.cache = cache
        self.retry = retry or RetryConfig()
        self.api_key = os.getenv("GOOGLE_API_KEY")

    def geocode(self, address: str) -> tuple[float, float]:
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY is required for geocoding")
        cache_key = f"geocode:{address}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached["lat"], cached["lon"]

        params = {"address": address, "key": self.api_key, "language": "ja"}
        for delay in backoff_times(self.retry):
            try:
                resp = requests.get(
                    "https://maps.googleapis.com/maps/api/geocode/json",
                    params=params,
                    timeout=self.retry.timeout,
                )
                if resp.status_code == 429:
                    logger.warning("Geocode rate limited; sleeping %s", delay)
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
                data = resp.json()
                if data.get("results"):
                    location = data["results"][0]["geometry"]["location"]
                    lat, lon = float(location["lat"]), float(location["lng"])
                    self.cache.set(
                        cache_key, {"lat": lat, "lon": lon}, ttl_seconds=60 * 60 * 24 * 30
                    )
                    return lat, lon
                raise RuntimeError(f"No geocode results for {address}")
            except requests.RequestException as exc:
                logger.error("Geocode failed for %s: %s", address, exc)
                time.sleep(delay)
        raise RuntimeError(f"Geocode failed after retries for {address}")
