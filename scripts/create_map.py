"""Create an interpolated Washington heat map of Big Dark Index scores."""

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.path import Path as PlotPath
import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FILE = PROJECT_ROOT / "data" / "processed" / "big_dark_summary.csv"
IMAGE_DIRECTORY = PROJECT_ROOT / "images"
OUTPUT_FILE = IMAGE_DIRECTORY / "big_dark_map.png"

CENSUS_QUERY_URL = (
    "https://tigerweb.geo.census.gov/arcgis/rest/services/"
    "Generalized_ACS2024/State_County/MapServer/8/query"
)

LABEL_OFFSETS = {
    "Forks": (10, 10),
    "Aberdeen": (10, -14),
    "Long Beach": (10, -17),
    "Port Angeles": (10, 16),
    "Bellingham": (10, 9),
    "Seattle": (10, 10),
    "Olympia": (10, -15),
    "Vancouver": (10, -17),
    "Spokane": (-10, 9),
    "Wenatchee": (10, 9),
    "Yakima": (10, -13),
    "Tri-Cities": (-10, -17),
    "Walla Walla": (10, 15),
}


def download_washington_boundary():
    """Return Washington's generalized Census boundary as GeoJSON."""
    parameters = {
        "where": "BASENAME='Washington'",
        "outFields": "BASENAME",
        "returnGeometry": "true",
        "outSR": "4326",
        "f": "geojson",
    }
    request_url = "{}?{}".format(CENSUS_QUERY_URL, urlencode(parameters))

    with urlopen(request_url, timeout=90) as response:
        boundary = json.loads(response.read().decode("utf-8"))

    if not boundary.get("features"):
        raise RuntimeError("The Census API did not return Washington's boundary.")

    return boundary["features"][0]["geometry"]


def polygon_rings(geometry):
    """Yield the exterior ring of every polygon in a GeoJSON geometry."""
    if geometry["type"] == "Polygon":
        polygons = [geometry["coordinates"]]
    elif geometry["type"] == "MultiPolygon":
        polygons = geometry["coordinates"]
    else:
        raise ValueError("Expected a Polygon or MultiPolygon geometry.")

    for polygon in polygons:
        yield polygon[0]


def inverse_distance_surface(summary, grid_longitude, grid_latitude):
    """Interpolate community scores using inverse-distance weighting."""
    sample_longitude = summary["longitude"].to_numpy()
    sample_latitude = summary["latitude"].to_numpy()
    sample_score = summary["big_dark_index"].to_numpy()

    longitude_scale = np.cos(np.deg2rad(summary["latitude"].mean()))
    delta_longitude = (
        grid_longitude[..., np.newaxis] - sample_longitude
    ) * longitude_scale
    delta_latitude = grid_latitude[..., np.newaxis] - sample_latitude
    distance = np.sqrt(delta_longitude ** 2 + delta_latitude ** 2)
    distance = np.maximum(distance, 0.03)

    weights = 1 / distance ** 2.4
    return np.sum(weights * sample_score, axis=2) / np.sum(weights, axis=2)


def washington_mask(geometry, grid_longitude, grid_latitude):
    """Return a Boolean grid identifying points inside Washington."""
    grid_points = np.column_stack(
        [grid_longitude.ravel(), grid_latitude.ravel()]
    )
    inside = np.zeros(len(grid_points), dtype=bool)

    for ring in polygon_rings(geometry):
        inside |= PlotPath(np.asarray(ring)).contains_points(grid_points)

    return inside.reshape(grid_longitude.shape)


def main():
    """Render and save an interpolated heat map with sample locations."""
    summary = pd.read_csv(SUMMARY_FILE)
    boundary = download_washington_boundary()

    longitude_values = np.linspace(-124.9, -116.7, 500)
    latitude_values = np.linspace(45.35, 49.15, 320)
    grid_longitude, grid_latitude = np.meshgrid(
        longitude_values, latitude_values
    )
    surface = inverse_distance_surface(
        summary, grid_longitude, grid_latitude
    )
    inside_washington = washington_mask(
        boundary, grid_longitude, grid_latitude
    )
    surface = np.ma.masked_where(~inside_washington, surface)

    color_scale = LinearSegmentedColormap.from_list(
        "big_dark_heat",
        ["#FFF2A8", "#FFB65C", "#F06467", "#A83A87", "#503078", "#17233A"],
    )

    fig, axis = plt.subplots(figsize=(12, 8))
    fig.patch.set_facecolor("white")
    axis.set_facecolor("#E8F1F4")

    levels = np.linspace(0, 100, 26)
    heat = axis.contourf(
        grid_longitude,
        grid_latitude,
        surface,
        levels=levels,
        cmap=color_scale,
        vmin=0,
        vmax=100,
        antialiased=True,
        zorder=1,
    )

    for ring in polygon_rings(boundary):
        longitudes = [coordinate[0] for coordinate in ring]
        latitudes = [coordinate[1] for coordinate in ring]
        axis.plot(
            longitudes,
            latitudes,
            color="#364A5A",
            linewidth=1.15,
            zorder=3,
        )

    axis.scatter(
        summary["longitude"],
        summary["latitude"],
        marker="D",
        s=44,
        facecolor="white",
        edgecolor="#17233A",
        linewidth=1.2,
        zorder=4,
    )

    for row in summary.itertuples(index=False):
        offset = LABEL_OFFSETS.get(row.community, (8, 8))
        horizontal_alignment = "right" if offset[0] < 0 else "left"
        axis.annotate(
            "{}  {:.0f}".format(row.community, row.big_dark_index),
            xy=(row.longitude, row.latitude),
            xytext=offset,
            textcoords="offset points",
            ha=horizontal_alignment,
            va="center",
            fontsize=9.2,
            fontweight="semibold",
            color="#17233A",
            bbox={
                "boxstyle": "round,pad=0.18",
                "facecolor": "white",
                "edgecolor": "none",
                "alpha": 0.82,
            },
            arrowprops={
                "arrowstyle": "-",
                "color": "#506576",
                "linewidth": 0.75,
            },
            zorder=5,
        )

    colorbar = fig.colorbar(
        heat,
        ax=axis,
        orientation="horizontal",
        shrink=0.48,
        pad=0.04,
        ticks=[0, 20, 40, 60, 80, 100],
    )
    colorbar.set_label("Big Dark Index (0–100)", fontsize=10)
    colorbar.outline.set_visible(False)

    axis.set_xlim(-124.9, -116.7)
    axis.set_ylim(45.35, 49.15)
    axis.set_aspect(1.47)
    axis.set_xticks([])
    axis.set_yticks([])
    for spine in axis.spines.values():
        spine.set_visible(False)

    fig.suptitle(
        "Washington’s Big Dark Has a West Side",
        x=0.08,
        y=0.97,
        ha="left",
        fontsize=21,
        fontweight="bold",
        color="#17233A",
    )
    fig.text(
        0.08,
        0.92,
        "An interpolated view of Big Dark Index scores from 13 sampled communities",
        ha="left",
        fontsize=11,
        color="#52636D",
    )
    fig.text(
        0.08,
        0.02,
        "Shading uses inverse-distance interpolation for visual context; it is not a statewide weather measurement.\n"
        "Diamond markers show sampled communities. Boundary source: U.S. Census Bureau TIGERweb.",
        ha="left",
        fontsize=9,
        color="#52636D",
    )

    fig.subplots_adjust(left=0.06, right=0.96, top=0.88, bottom=0.12)
    IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print("Saved map to {}".format(OUTPUT_FILE))


if __name__ == "__main__":
    main()
