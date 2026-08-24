"""Download historical weather data for the Washington Big Dark Index.

This version uses a consistent 15-year comparison period, saves progress after
every community, and resumes automatically if the API temporarily rate-limits
a request.
"""

import json
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCATIONS_FILE = PROJECT_ROOT / "data" / "locations.csv"
OUTPUT_DIRECTORY = PROJECT_ROOT / "data" / "raw"
OUTPUT_FILE = OUTPUT_DIRECTORY / "weather_daily_2006_2020.csv"

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
START_DATE = "2006-01-01"
END_DATE = "2020-12-31"
DAILY_VARIABLES = [
    "daylight_duration",
    "sunshine_duration",
    "precipitation_sum",
    "shortwave_radiation_sum",
]


def request_json(request_url):
    """Request JSON with retries for temporary failures and rate limits."""
    for attempt in range(1, 5):
        try:
            with urlopen(request_url, timeout=90) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            if error.code == 429:
                wait_seconds = int(error.headers.get("Retry-After", "120"))
                print(
                    "  Rate limit reached. Waiting {} seconds...".format(
                        wait_seconds
                    ),
                    flush=True,
                )
            else:
                wait_seconds = attempt * 15
                print(
                    "  Server error {}. Retrying in {} seconds...".format(
                        error.code, wait_seconds
                    ),
                    flush=True,
                )
        except (URLError, TimeoutError):
            wait_seconds = attempt * 15
            print(
                "  Request timed out. Retrying in {} seconds...".format(
                    wait_seconds
                ),
                flush=True,
            )

        if attempt < 4:
            time.sleep(wait_seconds)

    raise RuntimeError("The weather request failed after four attempts.")


def download_location(location):
    """Download and prepare historical weather data for one community."""
    parameters = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "daily": ",".join(DAILY_VARIABLES),
        "timezone": "America/Los_Angeles",
        "models": "era5",
    }
    request_url = "{}?{}".format(ARCHIVE_URL, urlencode(parameters))
    payload = request_json(request_url)

    if payload.get("error"):
        raise RuntimeError(payload.get("reason", "Unknown API error"))

    weather = pd.DataFrame(payload["daily"])
    weather = weather.rename(
        columns={
            "time": "date",
            "daylight_duration": "daylight_seconds",
            "sunshine_duration": "sunshine_seconds",
            "precipitation_sum": "precipitation_mm",
            "shortwave_radiation_sum": "solar_energy_mj_m2",
        }
    )

    weather["date"] = pd.to_datetime(weather["date"])
    weather["community"] = location.community
    weather["region"] = location.region
    weather["requested_latitude"] = location.latitude
    weather["requested_longitude"] = location.longitude
    weather["grid_latitude"] = payload["latitude"]
    weather["grid_longitude"] = payload["longitude"]
    weather["elevation_m"] = payload["elevation"]
    weather["year"] = weather["date"].dt.year
    weather["month"] = weather["date"].dt.month
    weather["daylight_hours"] = weather["daylight_seconds"] / 3600
    weather["sunshine_hours"] = weather["sunshine_seconds"] / 3600
    weather["sunshine_share"] = (
        weather["sunshine_seconds"] / weather["daylight_seconds"]
    )

    return weather[
        [
            "community",
            "region",
            "requested_latitude",
            "requested_longitude",
            "grid_latitude",
            "grid_longitude",
            "elevation_m",
            "date",
            "year",
            "month",
            "daylight_hours",
            "sunshine_hours",
            "sunshine_share",
            "precipitation_mm",
            "solar_energy_mj_m2",
        ]
    ]


def main():
    """Download locations, saving after each successful request."""
    locations = pd.read_csv(LOCATIONS_FILE)
    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        combined = pd.read_csv(OUTPUT_FILE)
        completed = set(combined["community"].unique())
        print("Resuming an existing download.", flush=True)
    else:
        combined = pd.DataFrame()
        completed = set()

    for location in locations.itertuples(index=False):
        if location.community in completed:
            print("Skipping {} (already saved).".format(location.community))
            continue

        print("Downloading {}...".format(location.community), flush=True)
        community_weather = download_location(location)
        combined = pd.concat([combined, community_weather], ignore_index=True)
        combined.to_csv(OUTPUT_FILE, index=False)
        print("  Saved {}.".format(location.community), flush=True)
        time.sleep(10)

    print("Finished with {:,} rows in {}".format(len(combined), OUTPUT_FILE))


if __name__ == "__main__":
    main()
