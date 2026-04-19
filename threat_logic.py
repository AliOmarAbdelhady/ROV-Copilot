from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Iterable


PLATFORM_DISPLAY_ORDER = ["Hibernia", "Hebron", "Sea Rose", "Terra Nova"]

COLOR_HEX = {
    "Green": "#1b7f46",
    "Yellow": "#c78c0a",
    "Red": "#c03a2b",
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
    text = (raw_value or "").strip()
    if not text:
        raise ValueError(f"{kind.title()} is required.")

    normalized = (
        text.lower()
        .replace("°", " ")
        .replace("º", " ")
        .replace("o", " ")
        .replace("’", " ")
        .replace("'", " ")
        .replace("”", " ")
        .replace('"', " ")
        .replace(",", " ")
    )
    hemisphere = None
    for label, sign in (
        ("north", 1),
        ("n", 1),
        ("south", -1),
        ("s", -1),
        ("east", 1),
        ("e", 1),
        ("west", -1),
        ("w", -1),
    ):
        if re.search(rf"\b{label}\b", normalized):
            hemisphere = sign
            break

    values = re.findall(r"-?\d+(?:\.\d+)?", normalized)
    if not values:
        raise ValueError(f"Could not parse {kind}.")

    if len(values) == 1:
        absolute = abs(float(values[0]))
    else:
        degrees = abs(float(values[0]))
        minutes = float(values[1])
        seconds = float(values[2]) if len(values) > 2 else 0.0
        if not 0.0 <= minutes < 60.0:
            raise ValueError(f"{kind.title()} minutes must be between 0 and 59.")
        if not 0.0 <= seconds < 60.0:
            raise ValueError(f"{kind.title()} seconds must be between 0 and 59.")
        absolute = degrees + (minutes / 60.0) + (seconds / 3600.0)

    if hemisphere is not None:
        sign = hemisphere
    elif float(values[0]) < 0:
        sign = -1
    else:
        sign = 1

    value = sign * absolute
    _validate_coordinate_range(value, kind)
    return value


def parse_heading(raw_value: str) -> float:
    text = (raw_value or "").strip().lower().replace("°", " ").replace("o", " ")
    values = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not values:
        raise ValueError("Heading is required.")
    heading = float(values[0])
    return heading % 360.0


def parse_keel_depth(raw_value: str) -> float:
    text = (raw_value or "").strip().lower()
    values = re.findall(r"-?\d+(?:\.\d+)?", text)
    if not values:
        raise ValueError("Keel depth is required.")
    value = float(values[0])
    if value <= 0:
        raise ValueError("Keel depth must be greater than zero.")
    return value


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


def generate_track_svg(
    latitude: float,
    longitude: float,
    heading_deg: float,
    assessments: list[Assessment],
    width: int = 860,
    height: int = 560,
) -> str:
    padding = 56
    direction_x, direction_y = heading_unit_vector(heading_deg)
    points = [(0.0, 0.0)]
    for assessment in assessments:
        points.append(nm_offset(assessment.platform.latitude, assessment.platform.longitude, latitude, longitude))

    max_distance = max(math.hypot(x, y) for x, y in points[1:]) if len(points) > 1 else 30.0
    ray_length = max(35.0, max_distance + 12.0)
    ray_end = (direction_x * ray_length, direction_y * ray_length)
    points.append(ray_end)

    min_x = min(x for x, _ in points)
    max_x = max(x for x, _ in points)
    min_y = min(y for _, y in points)
    max_y = max(y for _, y in points)
    span_x = max(max_x - min_x, 1.0)
    span_y = max(max_y - min_y, 1.0)
    plot_width = width - (padding * 2)
    plot_height = height - (padding * 2)
    scale = min(plot_width / span_x, plot_height / span_y)

    def project(x_nm: float, y_nm: float) -> tuple[float, float]:
        x_px = padding + ((x_nm - min_x) * scale)
        y_px = height - padding - ((y_nm - min_y) * scale)
        return x_px, y_px

    grid_step = 5.0
    grid_lines = []
    x_tick = math.floor(min_x / grid_step) * grid_step
    while x_tick <= max_x:
        x_px, _ = project(x_tick, 0.0)
        grid_lines.append(
            f'<line x1="{x_px:.1f}" y1="{padding}" x2="{x_px:.1f}" y2="{height - padding}" class="grid" />'
        )
        x_tick += grid_step

    y_tick = math.floor(min_y / grid_step) * grid_step
    while y_tick <= max_y:
        _, y_px = project(0.0, y_tick)
        grid_lines.append(
            f'<line x1="{padding}" y1="{y_px:.1f}" x2="{width - padding}" y2="{y_px:.1f}" class="grid" />'
        )
        y_tick += grid_step

    start_x, start_y = project(0.0, 0.0)
    end_x, end_y = project(*ray_end)

    platform_layers = []
    for assessment in assessments:
        x_nm, y_nm = nm_offset(
            assessment.platform.latitude,
            assessment.platform.longitude,
            latitude,
            longitude,
        )
        px, py = project(x_nm, y_nm)
        outer_color = COLOR_HEX[assessment.subsea_threat]
        inner_color = COLOR_HEX[assessment.platform_threat]
        label_dx = 12 if x_nm <= 0 else -12
        anchor = "start" if label_dx > 0 else "end"
        platform_layers.append(
            "\n".join(
                [
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="11" fill="none" stroke="{outer_color}" stroke-width="4" />',
                    f'<circle cx="{px:.1f}" cy="{py:.1f}" r="6" fill="{inner_color}" stroke="#f8f6ef" stroke-width="2" />',
                    f'<text x="{px + label_dx:.1f}" y="{py - 12:.1f}" text-anchor="{anchor}" class="label">{assessment.platform.name}</text>',
                    f'<text x="{px + label_dx:.1f}" y="{py + 6:.1f}" text-anchor="{anchor}" class="small-label">{assessment.distance_nm:.1f} nm</text>',
                ]
            )
        )

    return f"""
<svg viewBox="0 0 {width} {height}" role="img" aria-label="Iceberg trajectory plot" class="plot">
  <defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto">
      <polygon points="0 0, 8 3, 0 6" fill="#162238"></polygon>
    </marker>
  </defs>
  <rect x="0" y="0" width="{width}" height="{height}" rx="24" class="plot-bg"></rect>
  {''.join(grid_lines)}
  <rect x="{padding}" y="{padding}" width="{plot_width}" height="{plot_height}" class="frame"></rect>
  <line x1="{start_x:.1f}" y1="{start_y:.1f}" x2="{end_x:.1f}" y2="{end_y:.1f}" class="track" marker-end="url(#arrowhead)" />
  <circle cx="{start_x:.1f}" cy="{start_y:.1f}" r="8" class="iceberg"></circle>
  <text x="{start_x + 12:.1f}" y="{start_y - 14:.1f}" class="label">Iceberg</text>
  <text x="{start_x + 12:.1f}" y="{start_y + 4:.1f}" class="small-label">Heading {heading_deg:.0f}°</text>
  {''.join(platform_layers)}
  <g class="legend">
    <rect x="{width - 218}" y="28" width="186" height="102" rx="16" class="legend-box"></rect>
    <text x="{width - 198}" y="54" class="legend-title">Marker legend</text>
    <circle cx="{width - 178}" cy="78" r="10" fill="none" stroke="#c03a2b" stroke-width="4"></circle>
    <circle cx="{width - 178}" cy="78" r="6" fill="#1b7f46" stroke="#f8f6ef" stroke-width="2"></circle>
    <text x="{width - 158}" y="82" class="small-label">Outer ring: subsea threat</text>
    <circle cx="{width - 178}" cy="106" r="6" fill="#c78c0a" stroke="#f8f6ef" stroke-width="2"></circle>
    <text x="{width - 158}" y="110" class="small-label">Inner dot: platform threat</text>
  </g>
  <text x="{padding}" y="{height - 16}" class="axis-label">Relative nautical miles from iceberg start</text>
</svg>
""".strip()


def _validate_coordinate_range(value: float, kind: str) -> None:
    limit = 90.0 if kind == "latitude" else 180.0
    if not -limit <= value <= limit:
        raise ValueError(f"{kind.title()} must be between {-limit:g} and {limit:g}.")
