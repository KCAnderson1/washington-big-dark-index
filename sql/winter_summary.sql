SELECT
    community,
    region,
    AVG(requested_latitude) AS latitude,
    AVG(requested_longitude) AS longitude,
    AVG(daylight_hours) AS avg_daylight_hours,
    AVG(sunshine_hours) AS avg_sunshine_hours,
    AVG(sunshine_share) * 100 AS sunshine_share_pct,
    AVG(CASE WHEN precipitation_mm >= 1.0 THEN 1.0 ELSE 0.0 END) * 100
        AS wet_day_pct,
    SUM(precipitation_mm) / COUNT(DISTINCT winter_year)
        AS avg_winter_precipitation_mm,
    AVG(solar_energy_mj_m2) AS avg_solar_energy_mj_m2,
    COUNT(*) AS winter_day_records
FROM winter_weather
GROUP BY community, region
ORDER BY community;
