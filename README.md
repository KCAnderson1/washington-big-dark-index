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

Weather data come from Daymet Version 4, a NASA-supported dataset distributed by
the Oak Ridge National Laboratory Distributed Active Archive Center. Daymet
provides daily estimates at a 1 km spatial resolution.

- Dataset: https://doi.org/10.3334/ORNLDAAC/1840
- API documentation: https://daymet.ornl.gov/web_services.html
- Comparison period: 1991-2020

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
  raw/                   Downloaded Daymet data (created by the script)
scripts/
  download_daymet.py     Reproducible data download
requirements.txt         Required Python packages
```

## Run the download

```bash
pip install -r requirements.txt
python scripts/download_daymet.py
```

The script creates `data/raw/daymet_daily_1991_2020.csv`.

## Status

Data collection and methodology development are in progress. Index weights and
rankings will be added only after the individual measurements have been examined.
