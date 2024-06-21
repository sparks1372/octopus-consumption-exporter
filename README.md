# Octopus Energy Consumption Exporter:

![Docker Build](https://github.com/kevalpatel2106/octopus-consumption-exporter/workflows/build/badge.svg) ![GitHub release](https://img.shields.io/github/v/release/kevalpatel2106/octopus-consumption-exporter)

Python script to pull energy consumption data from Octopus energy into InfluxDB. This can be used with Graphana dashboard to monitor the enegy usage.

### Environment variables:

| Name | Note | Required | Default value | 
|----|----|----|----|
| `INFLUX_DB_NAME` | Name of the database in influx DB where the data will be stored. | ❌ | energy |
| `INFLUX_DB_HOST` | Host address of the InfluxDB | ❌ | influxdb | 
| `INFLUX_DB_PORT` | Port on which influx DB is running | ❌ | 8086 |
| `INFLUX_DB_USER` | InfluxDB user if authentication set. | ❌ | "" |
| `INFLUX_DB_PASSWORD` | InfluxDB password if authentication set. | ❌ | "" |
| `OCTOPUS_API_KEY` | API key for accessing Octopus Energy APIs. You can generate this key from [here](https://octopus.energy/dashboard/developer/). | ✔️ | Required |
| `ELECTRICITY_MPAN` | MPAN for your electricity meter. [Here](https://www.comparethemarket.com/energy/content/mpan-number/) the guide on how to find it. | ✔️ | Required |
| `ELECTRICITY_SERIAL_NO` | Serial number of your electricity meter. You will find it on your electricity meter. | ✔️ | Required |
| `EXPORT_MPAN` | MPAN for your electricity export meter. [Here](https://www.comparethemarket.com/energy/content/mpan-number/) the guide on how to find it. Export download will be skipped if not provided. | ❌ | None |
| `EXPORT_SERIAL_NO` | Serial number of your electricity export meter. You will find it on your electricity meter. | ✔️ (if EXPORT_MPAN is configured) | Required |
| `GAS_MPAN` | MPAN for your gas meter. [Here](https://www.comparethemarket.com/energy/content/mpan-number/) the guide on how to find it. | ✔️ | Required |
| `GAS_SERIAL_NO` | Serial number of your gas meter. You will find it on your gas meter. | ✔️ | Required |
| `VOLUME_CORRECTION_FACTOR` | Factor to convert m3 into kWh. You will find this on your last gas bill from Octopus. | ✔️ | Required |
| `SERIES_START_DATE` | Inital date from which the script will load the data. This date should be the date in the past. | ❌ | Yesterday's date |

## Usage:

### Commandline

After setting all the environment variables mentioned [here](#environment-variables), run following command from source directory.

```
python3 consumption_exporter.py
```

### Docker compose:

You can initate the docker container using docker compose in following way. 

```
version: "3.7"

services:  
    octopusenergy-exporter:
        container_name: octopusenergy-exporter
        image: ghcr.io/kevalpatel2106/octopus-consumption-exporter:latest
        restart: unless-stopped
        environment:
            INFLUX_DB_NAME: energy 
            INFLUX_DB_HOST: influxdb
            INFLUX_DB_PORT: 8086
            OCTOPUS_API_KEY: sk_live_abcdef28465
            ELECTRICITY_MPAN: 220000000000
            ELECTRICITY_SERIAL_NO: 22L3887905
            GAS_MPAN: 4189671708
            GAS_SERIAL_NO: E6S18826742181
            VOLUME_CORRECTION_FACTOR: 11.63580247
            SERIES_START_DATE: "2022-01-16"
        depends_on:
            - influxdb <-- Your influxdb service name
```
