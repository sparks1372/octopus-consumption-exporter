#!/usr/bin/env python
import click
from influxdb import InfluxDBClient
import os
from dateutil import parser
from datetime import date, datetime, timedelta
import time
import requests
from urllib import parse
from dotenv import load_dotenv
from pathlib import Path

from influxdb.exceptions import InfluxDBClientError


def retrieve_paginated_data(api_key, url, from_date, to_date, page=None):
    args = {
        'period_from': from_date,
        'period_to': to_date,
    }
    if page:
        args['page'] = page
    response = requests.get(url, params=args, auth=(api_key, ''))
    response.raise_for_status()
    data = response.json()
    results = data.get('results', [])
    if data['next']:
        url_query = parse.urlparse(data['next']).query
        next_page = parse.parse_qs(url_query)['page'][0]
        results += retrieve_paginated_data(api_key, url, from_date, to_date, next_page)
    return results


def _get_query_date_range(connection: InfluxDBClient, series):
    result = connection.query(f'SELECT time, consumption FROM {series} ORDER BY DESC LIMIT 1')
    if 'series' in result.raw and len(result.raw['series']) > 0 and 'values' in result.raw['series'][0] and len(
            result.raw['series'][0]['values']) > 0:
        latest_time = result.raw['series'][0]['values'][0][0]
        click.echo(f"Latest entry for series {series} is on {latest_time}.")
        from_date = parser.parse(latest_time)
        to_date = datetime.now()
        return from_date.isoformat(), to_date.isoformat()
    elif 'series' in result.raw and len(result.raw['series']) > 0:
        # Something is wrong with series. Drop series if data already there.
        click.echo(f"Resetting series {series}. {result.raw}")
        try:
            connection.query(f' DROP SERIES FROM {series}')
        except InfluxDBClientError as e:
            if e.content == 'not implemented: DROP SERIES':
                # we are working against Influx V2 which doesn't support DROP SERIES, will have to be manually sorted
                click.echo(
                    f"{series} appears to be corrupted. Unfortunately V2 doesn't support DROP SERIES via the API so please drop {series} using the influx cli and try again.")
            raise
    else:
        click.echo(f"New series {series}.")
    from_date = parser.parse(os.getenv("SERIES_START_DATE")) if os.getenv(
        "SERIES_START_DATE") else date.today() - timedelta(days=1)
    to_date = datetime.now()
    if from_date > to_date:
        raise click.ClickException('Start date cannot be in the future.')
    return from_date.isoformat(), to_date.isoformat()


def _pull_electricity_consumption(connection, api_key):
    from_date, to_date = _get_query_date_range(connection, "electricity")

    click.echo(f"Loading electricity data between {from_date} to {to_date}.")
    e_mpan = os.getenv('ELECTRICITY_MPAN')
    if not e_mpan:
        raise click.ClickException('No mpan set for electricity meter.')

    e_serial = os.getenv('ELECTRICITY_SERIAL_NO')
    if not e_serial:
        raise click.ClickException('No serial number set for electricity meter.')

    e_url = f'https://api.octopus.energy/v1/electricity-meter-points/{e_mpan}/meters/{e_serial}/consumption/'

    e_consumption = retrieve_paginated_data(api_key, e_url, from_date, to_date)
    click.echo(f"Loaded electricity data, {len(e_consumption)} results found.")
    store_series(connection, 'electricity', e_consumption, conversion_factor=None)


def _pull_electricity_export(connection, api_key):
    e_mpan = os.getenv('EXPORT_MPAN')
    if not e_mpan:
        click.echo("Export MPAN not configured")
        return

    e_serial = os.getenv('EXPORT_SERIAL_NO')
    if not e_serial:
        raise click.ClickException('No serial number set for export meter.')

    e_url = f'https://api.octopus.energy/v1/electricity-meter-points/{e_mpan}/meters/{e_serial}/consumption/'

    from_date, to_date = _get_query_date_range(connection, "electricity_export")
    e_consumption = retrieve_paginated_data(api_key, e_url, from_date, to_date)
    click.echo(f"Loaded electricity export data between {from_date} to {to_date}. {len(e_consumption)} results found.")
    store_series(connection, 'electricity_export', e_consumption, conversion_factor=None)


def _pull_gas_consumption(connection, api_key):
    from_date, to_date = _get_query_date_range(connection, "gas")

    click.echo(f"Loading gas data between {from_date} to {to_date}.")
    volume_correction_factor = os.getenv('VOLUME_CORRECTION_FACTOR')
    if not volume_correction_factor:
        raise click.ClickException('No volume correction factor set.')
    volume_correction_factor = float(volume_correction_factor)

    g_mpan = os.getenv('GAS_MPAN')
    if not g_mpan:
        raise click.ClickException('No mpan set for gas meter.')

    g_serial = os.getenv('GAS_SERIAL_NO')
    if not g_serial:
        raise click.ClickException('No serial number set for gas meter.')

    g_url = f'https://api.octopus.energy/v1/gas-meter-points/{g_mpan}/meters/{g_serial}/consumption/'

    g_consumption = retrieve_paginated_data(api_key, g_url, from_date, to_date)
    click.echo(f"Loaded gas data, {len(g_consumption)} results found.")
    store_series(connection, 'gas', g_consumption, conversion_factor=volume_correction_factor)


def store_series(connection, series, metrics, conversion_factor=None):
    if series:
        def fields_for_measurement(measurement, conversion_factor=None):
            raw_consumption = measurement['consumption']
            return {
                'consumption': raw_consumption * conversion_factor if conversion_factor else raw_consumption,
                'raw_consumption': raw_consumption
            }

        def tags_for_measurement(measurement):
            return {
                'time_of_day': datetime.now().strftime('%H:%M'),
                'date': datetime.now().strftime("%d/%m/%Y")
            }

        measurements = [
            {
                'measurement': series,
                'tags': tags_for_measurement(measurement),
                'time': measurement['interval_end'],
                'fields': fields_for_measurement(measurement, conversion_factor),
            }
            for measurement in metrics
        ]
        connection.write_points(measurements)


def _get_influxdb_connection_details():
    return {'host': os.getenv("INFLUX_DB_HOST") if os.getenv("INFLUX_DB_HOST") else "localhost",
            'port': os.getenv("INFLUX_DB_PORT") if os.getenv("INFLUX_DB_PORT") else 8086,
            'username': os.getenv("INFLUX_DB_USER") if os.getenv("INFLUX_DB_USER") else "octopus-exporter",
            'password': os.getenv("INFLUX_DB_PASSWORD") if os.getenv("INFLUX_DB_PASSWORD") else "octopus-data",
            'database': os.getenv("INFLUX_DB_NAME") if os.getenv("INFLUX_DB_NAME") else "energy"}


def _get_influxdb_client():
    influxdb_connection_details = _get_influxdb_connection_details()
    client = InfluxDBClient(**influxdb_connection_details)
    return client


def _sleep_until_2am():
    today = datetime.today()
    future = datetime(today.year, today.month, today.day, 2, 0)
    if today.hour >= 2:
        future += timedelta(days=1)
    click.echo(f"Next data pull will be on {future}.")
    time.sleep((future - today).total_seconds())


@click.command()
def monitor():
    env_file = os.getenv('ENV_FILE', None)

    if env_file:
        dotenv_path = Path(env_file)
        load_dotenv(dotenv_path=dotenv_path)

    influx = _get_influxdb_client()

    api_key = os.getenv('OCTOPUS_API_KEY')
    if not api_key:
        raise click.ClickException('No Octopus API key set.')

    while True:
        _pull_electricity_consumption(influx, api_key)
        _pull_electricity_export(influx, api_key)
        _pull_gas_consumption(influx, api_key)
        _sleep_until_2am()


if __name__ == '__main__':
    monitor()
