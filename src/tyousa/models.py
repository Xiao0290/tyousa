from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class StatsSnapshot:
    households_total: int
    one_person: int
    two_person: int
    three_person: int
    four_person: int
    five_person: int
    six_plus: int
    main_households: int
    apartment_households: int
    housing_households: int
    owner_households: int
    private_rental_households: int | None = None


@dataclass
class StatsResult:
    by_radius: dict[int, StatsSnapshot]


@dataclass
class StatsMetrics:
    households_600: int | None = None
    households_2000: int | None = None
    rental_share_600: float | None = None
    rental_share_2000: float | None = None
    apartment_share_600: float | None = None
    small_household_share_600: float | None = None
    family_share_2000: float | None = None
    trend_index: float | None = None


@dataclass
class PoiMetrics:
    count_competitors_600: int = 0
    count_competitors_2000: int = 0
    nearest_competitor_distance_m: float | None = None
    strong_competitor_600: int | None = None
    strong_competitor_2000: int | None = None
    nearest_station_distance_m: float | None = None
    nearest_anchor_distance_m: float | None = None
    main_road_distance_m: float | None = None
    parking_anchor_300m: int | None = None


@dataclass
class CandidateMetrics:
    candidate_id: str
    address: str | None
    lat: float
    lon: float
    stats: StatsMetrics = field(default_factory=StatsMetrics)
    poi: PoiMetrics = field(default_factory=PoiMetrics)

    def to_csv_row(self) -> dict[str, str | None]:
        return {
            "id": self.candidate_id,
            "address": self.address,
            "lat": self.lat,
            "lon": self.lon,
            "households_600": self.stats.households_600,
            "households_2000": self.stats.households_2000,
            "rental_share_600": self.stats.rental_share_600,
            "rental_share_2000": self.stats.rental_share_2000,
            "apartment_share_600": self.stats.apartment_share_600,
            "small_household_share_600": self.stats.small_household_share_600,
            "family_share_2000": self.stats.family_share_2000,
            "trend_index": self.stats.trend_index,
            "count_competitors_600": self.poi.count_competitors_600,
            "count_competitors_2000": self.poi.count_competitors_2000,
            "nearest_competitor_distance_m": self.poi.nearest_competitor_distance_m,
            "strong_competitor_600": self.poi.strong_competitor_600,
            "strong_competitor_2000": self.poi.strong_competitor_2000,
            "nearest_station_distance_m": self.poi.nearest_station_distance_m,
            "nearest_anchor_distance_m": self.poi.nearest_anchor_distance_m,
            "main_road_distance_m": self.poi.main_road_distance_m,
            "parking_anchor_300m": self.poi.parking_anchor_300m,
        }
