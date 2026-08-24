# Washington Big Dark Index

How different is winter darkness across Washington?

This project compares communities across the state using daily daylight,
precipitation, and solar-radiation estimates. The goal is to build a transparent
"Big Dark" index without reducing Washington winter to rainfall alone.

## Project question

Which Washington communities experience the most severe combination of limited
daylight, low solar exposure, and persistent wet weather between November and
February?

## Data source

Weather data come from the Open-Meteo Historical Weather API using the ERA5
reanalysis dataset. ERA5 combines observations and weather modeling to provide a
consistent, gap-free historical record.

- API documentation: https://open-meteo.com/en/docs/historical-weather-api
- Reanalysis model: ERA5
- Comparison period: 2006-2020

## Current measurements

- Average winter daylight hours
- Average daily solar energy
- Percentage of days with measurable precipitation
- Average winter precipitation
- Longest wet streak

## Repository structure

```text
data/
  locations.csv          Washington communities and coordinates
  raw/                   Downloaded weather data (created by the script)
scripts/
  download_weather.py    Reproducible data download
requirements.txt         Required Python packages
```

## Run the download

```bash
pip install -r requirements.txt
python scripts/download_weather.py
```

The script creates `data/raw/weather_daily_2006_2020.csv`.

## Status

Data collection and methodology development are in progress. Index weights and
rankings will be added only after the individual measurements have been examined.
