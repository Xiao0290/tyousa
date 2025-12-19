from __future__ import annotations

import json
import logging
import os
from pathlib import Path

import pandas as pd
import typer

from tyousa.cache import SQLiteCache
from tyousa.excel import ExcelWriter
from tyousa.models import CandidateMetrics
from tyousa.providers.geocode import GoogleGeocoder
from tyousa.providers.google_poi import GooglePoiProvider
from tyousa.providers.stats import StatsCalculator, StatsProviderFactory, TrendProvider
from tyousa.sample_data import create_sample_assets
from tyousa.utils import CandidateLoader, ensure_output_dir

app = typer.Typer(help="Coin laundry site scoring automation")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")


@app.command()
def prepare_samples(  # noqa: B008
    output_dir: Path = typer.Option(  # noqa: B008
        Path("example"), help="Directory to write sample template and RichReport files"
    )
):
    """Generate sample Excel assets locally to avoid tracking binaries in git."""
    template_path, richreport_path = create_sample_assets(output_dir)
    typer.echo(f"Template written to {template_path}")
    typer.echo(f"RichReport sample written to {richreport_path}")


@app.command()
def geocode(address: str):
    """Resolve an address to latitude and longitude using Google Geocoding API."""
    cache = SQLiteCache(Path(".cache/geocode.sqlite"))
    geocoder = GoogleGeocoder(cache)
    lat, lon = geocoder.geocode(address)
    typer.echo(json.dumps({"lat": lat, "lon": lon}, ensure_ascii=False))


@app.command()
def fetch_stats(  # noqa: B008
    candidate_csv: Path = typer.Argument(..., help="Path to candidates.csv"),  # noqa: B008
    richreport_root: Path | None = typer.Option(  # noqa: B008
        None, help="Directory containing RichReport files"
    ),
):
    """Fetch E~K statistics for candidates using RichReport or jSTAT API."""
    loader = CandidateLoader()
    candidates = loader.load(candidate_csv)
    factory = StatsProviderFactory(jstat_api_key=os.getenv("JSTAT_API_KEY"))

    results: list[CandidateMetrics] = []
    for item in candidates:
        provider = factory.get_provider(
            richreport_path=(
                (richreport_root / Path(item.richreport_path)) if item.richreport_path else None
            )
        )
        stats_result = _fetch_stats(provider, item.lat or 0.0, item.lon or 0.0)
        metrics = StatsCalculator.compute_metrics(stats_result)
        results.append(
            CandidateMetrics(
                candidate_id=item.id,
                address=item.address,
                lat=item.lat or 0.0,
                lon=item.lon or 0.0,
                stats=metrics,
            )
        )

    df = pd.DataFrame([r.to_csv_row() for r in results])
    output_path = Path("outputs/metrics.csv")
    ensure_output_dir(output_path)
    df.to_csv(output_path, index=False)
    typer.echo(f"Saved stats to {output_path}")


@app.command()
def fetch_poi(  # noqa: B008
    candidate_csv: Path = typer.Argument(..., help="Path to candidates.csv"),  # noqa: B008
):
    """Fetch Google Places metrics for candidates."""
    loader = CandidateLoader()
    candidates = loader.load(candidate_csv)
    cache = SQLiteCache(Path(".cache/places.sqlite"))
    poi_provider = GooglePoiProvider(cache)

    results: list[CandidateMetrics] = []
    for item in candidates:
        if item.lat is None or item.lon is None:
            raise typer.BadParameter("lat/lon is required for fetch-poi")
        poi = poi_provider.fetch((item.lat, item.lon))
        results.append(
            CandidateMetrics(
                candidate_id=item.id,
                address=item.address,
                lat=item.lat,
                lon=item.lon,
                poi=poi,
            )
        )

    df = pd.DataFrame([r.to_csv_row() for r in results])
    output_path = Path("outputs/poi.csv")
    ensure_output_dir(output_path)
    df.to_csv(output_path, index=False)
    typer.echo(f"Saved POI metrics to {output_path}")


@app.command()
def fill_excel(  # noqa: B008
    metrics_path: Path = typer.Argument(..., help="Path to metrics.json or metrics.csv"),  # noqa: B008
    template_path: Path = typer.Option(  # noqa: B008
        Path("example/template.xlsx"), help="Excel template path (generate via prepare-samples)"
    ),
    preserve_manual: bool = typer.Option(True, help="Skip cells that already have values"),
):
    """Write metrics into the candidate sheet of the Excel template."""
    metrics = _load_metrics(metrics_path)
    writer = ExcelWriter(template_path=template_path, preserve_manual=preserve_manual)
    output_path = Path("outputs/filled.xlsx")
    writer.write(metrics, output_path)
    typer.echo(f"Wrote filled workbook to {output_path}")


@app.command()
def run(  # noqa: B008
    candidate_csv: Path = typer.Argument(..., help="Path to candidates.csv"),  # noqa: B008
    template_path: Path = typer.Option(  # noqa: B008
        Path("example/template.xlsx"), help="Excel template path (generate via prepare-samples)"
    ),
    richreport_root: Path | None = typer.Option(  # noqa: B008
        Path("example"), help="Directory containing RichReport files"
    ),
    preserve_manual_col: bool = typer.Option(True, help="Skip cells already filled manually"),
):
    """End-to-end pipeline: geocode -> stats -> poi -> excel."""
    candidate_loader = CandidateLoader()
    candidates = candidate_loader.load(candidate_csv)

    geocode_cache = SQLiteCache(Path(".cache/geocode.sqlite"))
    places_cache = SQLiteCache(Path(".cache/places.sqlite"))
    geocoder = GoogleGeocoder(geocode_cache)
    poi_provider = GooglePoiProvider(places_cache)
    stats_factory = StatsProviderFactory(jstat_api_key=os.getenv("JSTAT_API_KEY"))
    trend_provider = TrendProvider()

    metrics_list: list[CandidateMetrics] = []

    for item in candidates:
        lat, lon = item.lat, item.lon
        if (lat is None or lon is None) and item.address:
            lat, lon = geocoder.geocode(item.address)
        if lat is None or lon is None:
            raise typer.BadParameter(f"Candidate {item.id} missing coordinates")

        stats_provider = stats_factory.get_provider(
            richreport_path=(
                (richreport_root / Path(item.richreport_path)) if item.richreport_path else None
            )
        )
        stats_result = _fetch_stats(stats_provider, lat, lon)
        stats_metrics = StatsCalculator.compute_metrics(stats_result)
        stats_metrics.trend_index = trend_provider.fetch_trend_index(lat, lon)

        poi_metrics = poi_provider.fetch((lat, lon))

        metrics_list.append(
            CandidateMetrics(
                candidate_id=item.id,
                address=item.address,
                lat=lat,
                lon=lon,
                stats=stats_metrics,
                poi=poi_metrics,
            )
        )

    output_metrics_path = Path("outputs/metrics.csv")
    ensure_output_dir(output_metrics_path)
    pd.DataFrame([m.to_csv_row() for m in metrics_list]).to_csv(output_metrics_path, index=False)

    writer = ExcelWriter(template_path=template_path, preserve_manual=preserve_manual_col)
    writer.write(metrics_list, Path("outputs/filled.xlsx"))

    log_path = Path("logs/run.log")
    ensure_output_dir(log_path)
    with log_path.open("a", encoding="utf-8") as f:
        for m in metrics_list:
            f.write(f"Processed {m.candidate_id}\n")

    typer.echo("Pipeline completed. Outputs written to outputs/ directory")


def _load_metrics(path: Path) -> list[CandidateMetrics]:
    if path.suffix.lower() == ".json":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [_metrics_from_dict(item) for item in raw]
    if path.suffix.lower() == ".csv":
        df = pd.read_csv(path)
        metrics: list[CandidateMetrics] = []
        for _, row in df.iterrows():
            stats_kwargs = {
                "households_600": row.get("households_600"),
                "households_2000": row.get("households_2000"),
                "rental_share_600": row.get("rental_share_600"),
                "rental_share_2000": row.get("rental_share_2000"),
                "apartment_share_600": row.get("apartment_share_600"),
                "small_household_share_600": row.get("small_household_share_600"),
                "family_share_2000": row.get("family_share_2000"),
                "trend_index": row.get("trend_index"),
            }
            from tyousa.models import PoiMetrics, StatsMetrics

            poi_kwargs = {
                "count_competitors_600": row.get("count_competitors_600", 0),
                "count_competitors_2000": row.get("count_competitors_2000", 0),
                "nearest_competitor_distance_m": row.get("nearest_competitor_distance_m"),
                "strong_competitor_600": row.get("strong_competitor_600"),
                "strong_competitor_2000": row.get("strong_competitor_2000"),
                "nearest_station_distance_m": row.get("nearest_station_distance_m"),
                "nearest_anchor_distance_m": row.get("nearest_anchor_distance_m"),
                "main_road_distance_m": row.get("main_road_distance_m"),
                "parking_anchor_300m": row.get("parking_anchor_300m"),
            }
            metrics.append(
                CandidateMetrics(
                    candidate_id=str(row.get("id")),
                    address=row.get("address"),
                    lat=float(row.get("lat")),
                    lon=float(row.get("lon")),
                    stats=StatsMetrics(**_clean_na(stats_kwargs)),
                    poi=PoiMetrics(**_clean_na(poi_kwargs)),
                )
            )
        return metrics
    raise typer.BadParameter("Unsupported metrics format; use .json or .csv")


def _clean_na(data: dict) -> dict:
    return {k: (None if pd.isna(v) else v) for k, v in data.items()}


def _metrics_from_dict(data: dict) -> CandidateMetrics:
    from tyousa.models import PoiMetrics, StatsMetrics

    return CandidateMetrics(
        candidate_id=data.get("candidate_id"),
        address=data.get("address"),
        lat=data.get("lat"),
        lon=data.get("lon"),
        stats=StatsMetrics(**data.get("stats", {})),
        poi=PoiMetrics(**data.get("poi", {})),
    )


def _fetch_stats(provider, lat: float, lon: float):
    try:
        return provider.fetch(lat, lon)  # type: ignore[arg-type]
    except TypeError:
        return provider.fetch()  # type: ignore[call-arg]


if __name__ == "__main__":
    app()
