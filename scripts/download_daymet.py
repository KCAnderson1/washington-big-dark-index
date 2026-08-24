"""Download daily Daymet weather data for Washington communities.

The script requests the same variables and 1991-2020 period for every
community listed in data/locations.csv, then combines the responses into
one analysis-ready CSV file.
"""

from io import StringIO
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCATIONS_FILE = PROJECT_ROOT / "data" / "locations.csv"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIRECTORY / "daymet_daily_1991_2020.csv"

DAYMET_URL = "https://daymet.ornl.gov/single-pixel/api/data"
YEARS = list(range(1991, 2021))
VARIABLES = "dayl,prcp,srad"


def find_data_header(response_text):
    """Return the line where the CSV column headings begin."""
    lines = response_text.splitlines()

    for index, line in enumerate(lines):
        if line.lower().startswith("year,yday"):
            return "\n".join(lines[index:])

    raise ValueError("The Daymet response did not contain a CSV header.")


def simplify_column_names(dataframe):
    """Replace Daymet's unit-bearing headings with concise names."""
    rename_map = {}

    for column in dataframe.columns:
        normalized = column.strip().lower()

        if normalized.startswith("dayl"):
            rename_map[column] = "daylight_seconds"
        elif normalized.startswith("prcp"):
            rename_map[column] = "precipitation_mm"
        elif normalized.startswith("srad"):
            rename_map[column] = "solar_radiation_w_m2"

    return dataframe.rename(columns=rename_map)


def download_location(location):
    """Download and prepare Daymet data for one community."""
    parameters = {
        "lat": location.latitude,
        "lon": location.longitude,
        "vars": VARIABLES,
        "years": ",".join(str(year) for year in YEARS),
    }

    request_url = "{}?{}".format(DAYMET_URL, urlencode(parameters))

    with urlopen(request_url, timeout=120) as response:
        response_text = response.read().decode("utf-8")

    csv_text = find_data_header(response_text)
    weather = pd.read_csv(StringIO(csv_text))
    weather = simplify_column_names(weather)

    weather["community"] = location.community
    weather["region"] = location.region
    weather["latitude"] = location.latitude
    weather["longitude"] = location.longitude

    first_day = pd.to_datetime(weather["year"].astype(str), format="%Y")
    weather["date"] = first_day + pd.to_timedelta(weather["yday"] - 1, unit="D")
    weather["month"] = weather["date"].dt.month
    weather["daylight_hours"] = weather["daylight_seconds"] / 3600
    weather["solar_energy_mj_m2"] = (
        weather["solar_radiation_w_m2"] * weather["daylight_seconds"] / 1_000_000
    )

    ordered_columns = [
        "community",
        "region",
        "latitude",
        "longitude",
        "date",
        "year",
        "month",
        "yday",
        "daylight_hours",
        "precipitation_mm",
        "solar_radiation_w_m2",
        "solar_energy_mj_m2",
    ]

    return weather[ordered_columns]


def main():
    """Download all locations and save one combined file."""
    locations = pd.read_csv(LOCATIONS_FILE)
    downloaded_data = []

    for location in locations.itertuples(index=False):
        print("Downloading {}...".format(location.community))
        downloaded_data.append(download_location(location))
        time.sleep(1)

    combined = pd.concat(downloaded_data, ignore_index=True)
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_FILE, index=False)

    print("Saved {:,} rows to {}".format(len(combined), OUTPUT_FILE))


if __name__ == "__main__":
    main()
