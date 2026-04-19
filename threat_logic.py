from __future__ import annotations

import math
import os
import re
import warnings
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable

os.environ.setdefault("MPLCONFIGDIR", "/tmp/matplotlib")
warnings.filterwarnings("ignore", message="Unable to import Axes3D.*")

import matplotlib
matplotlib.use("Agg")
from matplotlib import colors as mcolors
from matplotlib import pyplot as plt
from matplotlib.ticker import FuncFormatter, MultipleLocator

PLATFORM_DISPLAY_ORDER = ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]

COLOR_HEX = {
    "Green": "#1b7f46",
    "Yellow": "#c78c0a",
    "Red": "#c03a2b",
}

THREAT_FILL = {
    "Green": mcolors.to_rgba(COLOR_HEX["Green"], 0.16),
    "Yellow": mcolors.to_rgba(COLOR_HEX["Yellow"], 0.16),
    "Red": mcolors.to_rgba(COLOR_HEX["Red"], 0.16),
}


@dataclass(frozen=True)
class Platform:
    name: str
    latitude: float
    longitude: float
    depth_m: float


@dataclass(frozen=True)
class Assessment:
    platform: Platform
    distance_nm: float
    platform_threat: str
    platform_reason: str | None
    subsea_threat: str
    subsea_reason: str | None


PLATFORMS = {
    "Hibernia": Platform("Hibernia", 46.7504, -48.7819, 78.0),
    "Hebron": Platform("Hebron", 46.5440, -48.5180, 93.0),
    "Sea Rose": Platform("Sea Rose", 46.7895, -48.1460, 107.0),
    "Terra Nova": Platform("Terra Nova", 46.4000, -48.4000, 91.0),
}


def ordered_platforms() -> Iterable[Platform]:
    for name in PLATFORM_DISPLAY_ORDER:
        yield PLATFORMS[name]


def parse_coordinate(raw_value: str, kind: str) -> float:
    value = _parse_coordinate_input(raw_value, kind)
    if kind == "longitude":
        value = -value
    _validate_coordinate_range(value, kind)
    return value


def parse_heading(raw_value: str) -> float:
    heading = _parse_decimal_input(raw_value, "Heading is required.", "Heading must be a decimal number.")
    return heading % 360.0


def parse_keel_depth(raw_value: str) -> float:
    value = _parse_decimal_input(raw_value, "Keel depth is required.", "Keel depth must be a decimal number.")
    if value <= 0:
        raise ValueError("Keel depth must be greater than zero.")
    return value


def _parse_decimal_input(raw_value: str, empty_message: str, invalid_message: str) -> float:
    text = (raw_value or "").strip()
    if not text:
        raise ValueError(empty_message)
    if not re.fullmatch(r"-?(?:\d+\.?\d*|\.\d+)", text):
        raise ValueError(invalid_message)
    return float(text)


def _parse_unsigned_decimal_input(raw_value: str, empty_message: str, invalid_message: str) -> float:
    text = (raw_value or "").strip()
    if not text:
        raise ValueError(empty_message)
    if not re.fullmatch(r"(?:\d+\.?\d*|\.\d+)", text):
        raise ValueError(invalid_message)
    return float(text)


def _parse_coordinate_input(raw_value: str, kind: str) -> float:
    text = (raw_value or "").strip()
    if not text:
        raise ValueError(f"{kind.title()} is required.")
    if not re.fullmatch(r"\d+(?:\.\d+){0,2}", text):
        raise ValueError(f"{kind.title()} must use digits and decimal points only.")

    dot_count = text.count(".")
    if dot_count == 0:
        return float(text)
    if dot_count == 1:
        degrees_text, remainder_text = text.split(".")
        if len(remainder_text) == 2 and float(remainder_text) < 60.0:
            return _degrees_minutes_seconds_to_decimal(float(degrees_text), float(remainder_text), 0.0, kind)
        return float(text)

    degrees_text, minutes_text, seconds_text = text.split(".")
    return _degrees_minutes_seconds_to_decimal(float(degrees_text), float(minutes_text), float(seconds_text), kind)


def _degrees_minutes_seconds_to_decimal(degrees: float, minutes: float, seconds: float, kind: str) -> float:
    if not 0.0 <= minutes < 60.0:
        raise ValueError(f"{kind.title()} minutes must be between 0 and 59.")
    if not 0.0 <= seconds < 60.0:
        raise ValueError(f"{kind.title()} seconds must be between 0 and 59.")
    return degrees + (minutes / 60.0) + (seconds / 3600.0)


def assess_mission(latitude: float, longitude: float, heading_deg: float, keel_depth_m: float) -> list[Assessment]:
    results: list[Assessment] = []
    for platform in ordered_platforms():
        distance_nm = distance_to_track_nm(
            start_lat=latitude,
            start_lon=longitude,
            heading_deg=heading_deg,
            point_lat=platform.latitude,
            point_lon=platform.longitude,
        )
        platform_threat, platform_reason = classify_platform(distance_nm, keel_depth_m, platform.depth_m)
        subsea_threat, subsea_reason = classify_subsea(distance_nm, keel_depth_m, platform.depth_m)
        results.append(
            Assessment(
                platform=platform,
                distance_nm=distance_nm,
                platform_threat=platform_threat,
                platform_reason=platform_reason,
                subsea_threat=subsea_threat,
                subsea_reason=subsea_reason,
            )
        )
    return results


def distance_to_track_nm(
    start_lat: float,
    start_lon: float,
    heading_deg: float,
    point_lat: float,
    point_lon: float,
) -> float:
    point_x, point_y = nm_offset(point_lat, point_lon, start_lat, start_lon)
    direction_x, direction_y = heading_unit_vector(heading_deg)
    along_track = (point_x * direction_x) + (point_y * direction_y)
    if along_track < 0:
        return math.hypot(point_x, point_y)
    return abs((point_x * direction_y) - (point_y * direction_x))


def nm_offset(lat: float, lon: float, origin_lat: float, origin_lon: float) -> tuple[float, float]:
    mean_lat_rad = math.radians((lat + origin_lat) / 2.0)
    x_nm = (lon - origin_lon) * 60.0 * math.cos(mean_lat_rad)
    y_nm = (lat - origin_lat) * 60.0
    return x_nm, y_nm


def heading_unit_vector(heading_deg: float) -> tuple[float, float]:
    heading_rad = math.radians(heading_deg)
    return math.sin(heading_rad), math.cos(heading_rad)


def classify_platform(distance_nm: float, keel_depth_m: float, platform_depth_m: float) -> tuple[str, str | None]:
    if keel_depth_m >= (1.1 * platform_depth_m):
        return "Green", "Iceberg will ground before reaching the platform."
    if distance_nm < 5.0:
        return "Red", "Track passes within 5 nautical miles."
    if distance_nm <= 10.0:
        return "Yellow", "Track passes between 5 and 10 nautical miles."
    return "Green", "Track stays more than 10 nautical miles away."


def classify_subsea(distance_nm: float, keel_depth_m: float, platform_depth_m: float) -> tuple[str, str | None]:
    if distance_nm > 25.0:
        return "Green", "Does not intersect the 25 nautical mile subsea zone."
    keel_ratio = keel_depth_m / platform_depth_m
    if keel_ratio >= 1.1:
        return "Green", "Iceberg will ground before reaching the subsea asset."
    if keel_ratio >= 0.9:
        return "Red", "Keel depth is between 90% and 110% of the water depth."
    if keel_ratio >= 0.7:
        return "Yellow", "Keel depth is between 70% and 90% of the water depth."
    return "Green", "Insufficient keel depth to threaten the subsea asset."


def render_track_preview_png(
    latitude: float,
    longitude: float,
    heading_deg: float,
    assessments: list[Assessment],
) -> bytes:
    figure, axis = plt.subplots(figsize=(7.4, 8.6), constrained_layout=True)
    _draw_track_plot(axis, latitude, longitude, heading_deg, assessments)

    buffer = BytesIO()
    figure.savefig(buffer, format="png", dpi=180, facecolor="white")
    plt.close(figure)
    return buffer.getvalue()


def render_report_pdf(
    latitude: float,
    longitude: float,
    heading_deg: float,
    keel_depth_m: float,
    assessments: list[Assessment],
) -> bytes:
    figure = plt.figure(figsize=(8.5, 11.0), constrained_layout=True)
    grid = figure.add_gridspec(14, 1)
    header_axis = figure.add_subplot(grid[0:2, 0])
    plot_axis = figure.add_subplot(grid[2:10, 0])
    table_axis = figure.add_subplot(grid[10:, 0])

    _draw_report_header(header_axis, latitude, longitude, heading_deg, keel_depth_m)
    _draw_track_plot(plot_axis, latitude, longitude, heading_deg, assessments)
    _draw_assessment_table(table_axis, assessments)

    buffer = BytesIO()
    figure.savefig(buffer, format="pdf", facecolor="white")
    plt.close(figure)
    return buffer.getvalue()


def _draw_report_header(
    axis,
    latitude: float,
    longitude: float,
    heading_deg: float,
    keel_depth_m: float,
) -> None:
    axis.axis("off")
    axis.text(
        0.0,
        0.86,
        "Iceberg Threat Assessment",
        fontsize=18,
        fontweight="bold",
        color="#0f172a",
        ha="left",
        va="top",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.48,
        (
            f"Start {format_coordinate_label(latitude, 'latitude')}, {format_coordinate_label(longitude, 'longitude')}    "
            f"Heading {heading_deg:.0f}°    Keel depth {keel_depth_m:.1f} m"
        ),
        fontsize=10.5,
        color="#334155",
        ha="left",
        va="top",
        transform=axis.transAxes,
    )
    axis.text(
        0.0,
        0.16,
        "Track map and threat summary for Hibernia, Hebron, Sea Rose, and Terra Nova.",
        fontsize=9.5,
        color="#64748b",
        ha="left",
        va="top",
        transform=axis.transAxes,
    )


def _draw_track_plot(
    axis,
    latitude: float,
    longitude: float,
    heading_deg: float,
    assessments: list[Assessment],
) -> None:
    bounds, end_latitude, end_longitude = _build_plot_bounds(latitude, longitude, heading_deg, assessments)

    axis.set_facecolor("#ffffff")
    axis.set_xlim(bounds["lon_min"], bounds["lon_max"])
    axis.set_ylim(bounds["lat_min"], bounds["lat_max"])
    axis.set_title("Iceberg track and platform positions", fontsize=12, pad=16, color="#0f172a")
    axis.grid(which="major", color="#94a3b8", linewidth=0.8, alpha=0.72)

    for spine in axis.spines.values():
        spine.set_visible(False)

    axis.xaxis.set_major_locator(MultipleLocator(bounds["lon_step"]))
    axis.yaxis.set_major_locator(MultipleLocator(bounds["lat_step"]))
    axis.xaxis.set_major_formatter(FuncFormatter(lambda value, _: _format_geo_tick(value, "longitude")))
    axis.yaxis.set_major_formatter(FuncFormatter(lambda value, _: _format_geo_tick(value, "latitude")))

    axis.tick_params(axis="x", top=True, labeltop=True, bottom=False, labelbottom=False, pad=6, labelsize=9)
    axis.tick_params(axis="y", right=True, labelright=True, left=False, labelleft=False, pad=10, labelsize=9)

    for label in axis.get_yticklabels():
        label.set_rotation(270)
        label.set_va("center")
        label.set_ha("center")

    axis.plot(
        [longitude, end_longitude],
        [latitude, end_latitude],
        color="#0f172a",
        linewidth=1.5,
        zorder=2,
    )
    axis.scatter([longitude], [latitude], s=34, color="#0f172a", zorder=3)
    axis.annotate(
        "A",
        xy=(longitude, latitude),
        xytext=(0, 10),
        textcoords="offset points",
        ha="center",
        va="bottom",
        fontsize=12,
        fontweight="bold",
        color="#0f172a",
    )
    axis.text(
        0.015,
        0.02,
        "A = iceberg start",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#475569",
    )

    for assessment in assessments:
        platform = assessment.platform
        axis.scatter(
            [platform.longitude],
            [platform.latitude],
            s=42,
            facecolors="#ffffff",
            edgecolors="#0f172a",
            linewidths=1.1,
            zorder=3,
        )
        axis.annotate(
            platform.name,
            xy=(platform.longitude, platform.latitude),
            xytext=(8, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9.5,
            color="#0f172a",
        )


def _draw_assessment_table(axis, assessments: list[Assessment]) -> None:
    axis.axis("off")
    axis.text(
        0.0,
        1.04,
        "Threat summary",
        fontsize=12,
        fontweight="bold",
        color="#0f172a",
        transform=axis.transAxes,
        va="bottom",
    )

    rows = [
        [
            assessment.platform.name,
            f"{assessment.distance_nm:.2f} nm",
            f"{assessment.platform.depth_m:.0f} m",
            assessment.platform_threat,
            assessment.subsea_threat,
        ]
        for assessment in assessments
    ]
    headers = ["Platform", "Distance to Track", "Water Depth", "Platform", "Subsea"]
    table = axis.table(
        cellText=rows,
        colLabels=headers,
        colWidths=[0.24, 0.20, 0.16, 0.20, 0.20],
        loc="center",
        cellLoc="left",
    )
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.0, 1.5)

    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor("#cbd5e1")
        cell.set_linewidth(0.8)
        if row == 0:
            cell.set_facecolor("#e2e8f0")
            cell.set_text_props(weight="bold", color="#0f172a")
            continue
        cell.set_text_props(color="#0f172a")
        if col == 3:
            cell.set_facecolor(THREAT_FILL[rows[row - 1][3]])
        elif col == 4:
            cell.set_facecolor(THREAT_FILL[rows[row - 1][4]])
        else:
            cell.set_facecolor("#ffffff")


def _build_plot_bounds(
    latitude: float,
    longitude: float,
    heading_deg: float,
    assessments: list[Assessment],
) -> tuple[dict[str, float], float, float]:
    direction_x, direction_y = heading_unit_vector(heading_deg)
    offsets = [
        nm_offset(assessment.platform.latitude, assessment.platform.longitude, latitude, longitude)
        for assessment in assessments
    ]
    max_distance = max((math.hypot(x_nm, y_nm) for x_nm, y_nm in offsets), default=30.0)
    ray_length_nm = max(35.0, max_distance + 12.0)
    end_latitude, end_longitude = latlon_from_nm_offset(
        direction_x * ray_length_nm,
        direction_y * ray_length_nm,
        latitude,
        longitude,
    )

    latitudes = [latitude, end_latitude, *(assessment.platform.latitude for assessment in assessments)]
    longitudes = [longitude, end_longitude, *(assessment.platform.longitude for assessment in assessments)]

    lat_span = max(max(latitudes) - min(latitudes), 0.35)
    lon_span = max(max(longitudes) - min(longitudes), 0.35)
    lat_step = _choose_tick_step(lat_span)
    lon_step = _choose_tick_step(lon_span)
    lat_pad = max(lat_step * 0.55, lat_span * 0.12)
    lon_pad = max(lon_step * 0.55, lon_span * 0.12)

    bounds = {
        "lat_step": lat_step,
        "lon_step": lon_step,
        "lat_min": math.floor((min(latitudes) - lat_pad) / lat_step) * lat_step,
        "lat_max": math.ceil((max(latitudes) + lat_pad) / lat_step) * lat_step,
        "lon_min": math.floor((min(longitudes) - lon_pad) / lon_step) * lon_step,
        "lon_max": math.ceil((max(longitudes) + lon_pad) / lon_step) * lon_step,
    }
    return bounds, end_latitude, end_longitude


def latlon_from_nm_offset(
    x_nm: float,
    y_nm: float,
    origin_lat: float,
    origin_lon: float,
) -> tuple[float, float]:
    latitude = origin_lat + (y_nm / 60.0)
    mean_lat_rad = math.radians((latitude + origin_lat) / 2.0)
    longitude = origin_lon + (x_nm / (60.0 * math.cos(mean_lat_rad)))
    return latitude, longitude


def _choose_tick_step(span: float) -> float:
    for step in (0.1, 0.25, 0.5, 1.0, 2.0):
        if span / step <= 6.0:
            return step
    return 5.0


def _format_geo_tick(value: float, kind: str) -> str:
    absolute = abs(value)
    degrees = int(absolute)
    minutes = int(round((absolute - degrees) * 60.0))
    if minutes == 60:
        degrees += 1
        minutes = 0

    if kind == "latitude":
        hemisphere = "N" if value >= 0 else "S"
    else:
        hemisphere = "E" if value >= 0 else "W"

    return f"{degrees}°{minutes:02d}'{hemisphere}"


def format_coordinate_label(value: float, kind: str) -> str:
    absolute = abs(value)
    degrees = int(absolute)
    minutes_float = (absolute - degrees) * 60.0
    minutes = int(minutes_float)
    seconds = round((minutes_float - minutes) * 60.0)

    if seconds == 60:
        minutes += 1
        seconds = 0
    if minutes == 60:
        degrees += 1
        minutes = 0

    if kind == "latitude":
        hemisphere = "N" if value >= 0 else "S"
    else:
        hemisphere = "E" if value >= 0 else "W"

    return f'{degrees}°{minutes:02d}\'{seconds:02d}"{hemisphere}'


def _validate_coordinate_range(value: float, kind: str) -> None:
    limit = 90.0 if kind == "latitude" else 180.0
    if not -limit <= value <= limit:
        raise ValueError(f"{kind.title()} must be between {-limit:g} and {limit:g}.")
