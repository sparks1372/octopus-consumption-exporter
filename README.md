# Octopus Energy Consumption Exporter:

![Docker Build](https://github.com/sparks1372/octopus-consumption-exporter/workflows/build/badge.svg) ![GitHub release](https://img.shields.io/github/v/release/sparks1372/octopus-consumption-exporter)

Python script to pull energy consumption data from Octopus energy into InfluxDB. This can be used with Grafana dashboard
to monitor the energy usage. This has been forked
from [Keval Patel](https://github.com/kevalpatel2106/octopus-consumption-exporter) who did the vast majority of the work
but appears to be focusing on other priorities which has made changes a bit difficult to get merged.

### Environment variables:

These can either be set directly as environment variables passed to the docker container or python module in a `.env`
file by setting the `ENV_FILE` environment variable.

| Name                       | Note                                                                                                                                                                | Required | Default value    | 
|----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|------------------|
| `INFLUX_DB_NAME`           | Name of the database in influx DB where the data will be stored.                                                                                                    | ❌        | energy           |
| `INFLUX_DB_HOST`           | Host address of the InfluxDB                                                                                                                                        | ❌        | influxdb         | 
| `INFLUX_DB_PORT`           | Port on which influx DB is running                                                                                                                                  | ❌        | 8086             |
| `INFLUX_DB_USER`           | InfluxDB user if authentication set.                                                                                                                                | ❌        | octopus-exporter |
| `INFLUX_DB_PASSWORD`       | InfluxDB password if authentication set.                                                                                                                            | ❌        | octopus-data     |
| `OCTOPUS_API_KEY`          | API key for accessing Octopus Energy APIs. You can generate this key from [here](https://octopus.energy/dashboard/developer/).                                      | ✔️       | Requeired        |
| `ELECTRICITY_MPAN`         | MPAN for your electricity meter. [Here](https://www.comparethemarket.com/energy/content/mpan-number/) the guide on how to find it.                                  | ✔️       | Requeired        |
| `ELECTRICITY_SERIAL_NO`    | Serial number of your electricity meter. You will find it on your electricity meter.                                                                                | ✔️       | Requeired        |
| `GAS_MPAN`                 | MPAN for your gas meter. [Here](https://www.comparethemarket.com/energy/content/mpan-number/) the guide on how to find it.                                          | ✔️       | Requeired        |
| `GAS_SERIAL_NO`            | Serial number of your gas meter. You will find it on your gas meter.                                                                                                | ✔️       | Requeired        |
| `VOLUME_CORRECTION_FACTOR` | Factor to convert m3 into kWh. You will find this on your last gas bill from Octopus.                                                                               | ✔️       | Requeired        |
| `SERIES_START_DATE`        | Inital date from which the script will load the data. This date should be the date in the past.                                                                     | ❌        | Yesterday's date |
| `ENV_FILE`                 | The path of the env file to use to resolve environment variables above. Any variables set in the file will take precedence over those set in the parent environment | ❌        | N/A              |

## Usage:

### Commandline

After setting all the environment variables mentioned [here](#environment-variables), run following command from source
directory.

```
python3 consumption_exporter.py
```

### Docker compose:

You can define the docker container using docker compose in following way:

```
version: "3.7"

services:  
    octopusenergy-exporter:
        container_name: octopusenergy-exporter
        image: ghcr.io/sparks1372/octopus-consumption-exporter:latest
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

Or if you prefer to use a `.env` file:

```
version: "3.7"

services:  
    octopusenergy-exporter:
        container_name: octopusenergy-exporter
        image: ghcr.io/sparks1372/octopus-consumption-exporter:latest
        restart: unless-stopped
        volumes:
          - ~/.env:.env
        environment:
            ENV_FILE: .env 
        depends_on:
            - influxdb <-- Your influxdb service name
```

### InfluxDB V2 compatibility:

With the introduction of InfluxDB2 the authentication migrated to be token based and Flux as the query language. The
Flux language has now been deprecated and therefore makes upgrading the package to use the new InfluxDB 2 python client
somewhat pointless as it doesn't support InfluxQL. As a result, the way to get this package working against a V2 server
is to set up a user with V1 authentication (username/password).

#### Step 0 - Create a bucket

_Skip this step if you have used this package with Influx V1 and have just upgraded. This is only required for new
installations_

Databases have been merged with retention periods to
form [Buckets](https://docs.influxdata.com/influxdb/v1/concepts/glossary/#bucket) in V2. You will need to have a bucket
created in order to grant read and write permissions to your V1 auth user.

Run the following command to create a bucket with our default database name `energy` and an infinite retention period:

```
$ influx bucket create --name energy
ID                      Name    Retention       Shard group duration    Organization ID         Schema Type
<bucket-id>             energy  infinite        168h0m0s                xxxx                    implicit
```

If you want a different retention period, please check
the [command documentation](https://docs.influxdata.com/influxdb/v2/reference/cli/influx/bucket/create/).

#### Step 1 - Find your bucket id

Run the following command:

```
$ influx bucket list
ID                      Name                    Retention       Shard group duration    Organization ID         Schema Type
<bucket-id>             energy                  infinite        168h0m0s                xxxx                    implicit
```

This lists all buckets so find the one matching the database name you were using in V1 (default is `energy`) and note
the ID for the next step.

#### Step 2 - Create a user with V1 authentication

Using `bucket-id` returned in the previous step run the following command to create a user `octopus-exporter` with
password `octopus-data` (the default user/password):

```
$ influx v1 authorization create --username octopus-exporter --password octopus-data --read-bucket <bucket-id> --write-bucket <bucket-id>
```

You are now good to go :tada: