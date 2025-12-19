from __future__ import annotations

import csv
import json
import logging
import math
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return haversine distance in meters between two WGS84 points."""
    radius_earth_m = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return radius_earth_m * c


def ensure_output_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: Path, data: dict) -> None:
    ensure_output_dir(path)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@dataclass
class CandidateRow:
    id: str
    address: str | None
    lat: float | None
    lon: float | None
    richreport_path: str | None
    notes: str | None


class CandidateLoader:
    def __init__(self) -> None:
        self._counter = 1

    def _generate_id(self) -> str:
        value = f"OSK{self._counter:03d}"
        self._counter += 1
        return value

    def load(self, path: Path) -> list[CandidateRow]:
        rows: list[CandidateRow] = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                candidate_id = row.get("id") or self._generate_id()
                lat = self._to_float(row.get("lat"))
                lon = self._to_float(row.get("lon"))
                rows.append(
                    CandidateRow(
                        id=candidate_id,
                        address=row.get("address") or None,
                        lat=lat,
                        lon=lon,
                        richreport_path=row.get("richreport_path") or None,
                        notes=row.get("notes") or None,
                    )
                )
        return rows

    @staticmethod
    def _to_float(value: str | None) -> float | None:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except ValueError:
            logger.warning("Invalid coordinate value: %s", value)
            return None


@dataclass
class RetryConfig:
    retries: int = 3
    backoff_factor: float = 1.2
    timeout: int = 15


def backoff_times(config: RetryConfig) -> Iterable[float]:
    delay = config.backoff_factor
    for _ in range(config.retries):
        yield delay
        delay *= config.backoff_factor


def distance_to_nearest(
    origin: tuple[float, float], points: Iterable[tuple[float, float]]
) -> float | None:
    best: float | None = None
    for lat, lon in points:
        dist = haversine_distance_m(origin[0], origin[1], lat, lon)
        if best is None or dist < best:
            best = dist
    return best
