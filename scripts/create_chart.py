"""Create the primary ranking chart for the Washington Big Dark Index."""

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUMMARY_FILE = PROJECT_ROOT / "data" / "processed" / "big_dark_summary.csv"
IMAGE_DIRECTORY = PROJECT_ROOT / "images"
OUTPUT_FILE = IMAGE_DIRECTORY / "big_dark_ranking.png"


def main():
    """Render and save a horizontal ranking chart."""
    summary = pd.read_csv(SUMMARY_FILE).sort_values(
        "big_dark_index", ascending=True
    )

    colors = []
    for rank in summary["rank"]:
        if rank <= 3:
            colors.append("#172A3A")
        elif rank <= 8:
            colors.append("#4F6D7A")
        else:
            colors.append("#A9BBC5")

    fig, axis = plt.subplots(figsize=(11, 7.5))
    bars = axis.barh(
        summary["community"],
        summary["big_dark_index"],
        color=colors,
        height=0.7,
    )

    axis.set_xlim(0, 100)
    axis.set_xlabel("Big Dark Index (0–100)", fontsize=11, labelpad=10)
    axis.set_ylabel("")
    axis.xaxis.grid(True, color="#D9E1E5", linewidth=0.8)
    axis.yaxis.grid(False)
    axis.set_axisbelow(True)

    for bar, value in zip(bars, summary["big_dark_index"]):
        axis.text(
            value + 1,
            bar.get_y() + bar.get_height() / 2,
            "{:.1f}".format(value),
            va="center",
            fontsize=10,
            color="#23313B",
        )

    for edge in ["top", "right", "left"]:
        axis.spines[edge].set_visible(False)
    axis.spines["bottom"].set_color("#A9BBC5")
    axis.tick_params(axis="y", length=0, labelsize=10)
    axis.tick_params(axis="x", colors="#52636D")

    fig.suptitle(
        "Where Washington’s Big Dark Hits Hardest",
        x=0.12,
        y=0.975,
        ha="left",
        fontsize=20,
        fontweight="bold",
        color="#172A3A",
    )
    fig.text(
        0.12,
        0.925,
        "Comparing 14 complete November–February winters, 2006–2020",
        ha="left",
        fontsize=11,
        color="#52636D",
    )
    fig.text(
        0.12,
        0.025,
        "Index equally weights daylight, sunshine, cloudiness, wet-day frequency, and precipitation.\n"
        "Scores compare only the 13 Washington communities included in this analysis.",
        ha="left",
        fontsize=9,
        color="#52636D",
    )

    fig.subplots_adjust(left=0.2, right=0.94, top=0.87, bottom=0.14)
    IMAGE_DIRECTORY.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT_FILE, dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)

    print("Saved chart to {}".format(OUTPUT_FILE))


if __name__ == "__main__":
    main()
