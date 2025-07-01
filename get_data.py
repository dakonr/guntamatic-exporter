import json
import requests
import influxdb_client, os, time
from influxdb_client import Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import pprint
from datetime import date, datetime

from slugify import slugify

HOST = os.environ.get(
    "BMK_HOST", "http://bmk30"
)  # hostname and protocol to heater (mostly http and bmk30)
KEY_PATH = os.environ.get(
    "KEY_PATH", "/daqdesc.cgi"
)  # Path to get the description of the values
VALUE_PATH = os.environ.get("VALUE_PATH", "/daqdata.cgi")  # Path to values


def get_env(key, default, cast=str):
    value = os.environ.get(key)
    if value is None:
        return default
    if cast is bool:
        return value.lower() in ("1", "true", "yes", "on")
    return cast(value)


INFLUXDB_HOST = get_env("INFLUXDB_HOST", "http://localhost:8086")
INFLUXDB_ORG = get_env("INFLUXDB_ORG", "influxdata")
INFLUXDB_TOKEN = get_env(
    "INFLUXDB_TOKEN",
    "changeme",
)
INFLUXDB_BUCKET = get_env("INFLUXDB_BUCKET", "heater")
INFLUXDB_MEASUREMENT_NAME = get_env(
    "INFLUXDB_MEASUREMENT_NAME", "heizung"
)  # Measurement name in InfluxDB, defaults to 'heizung'


def safe_list_get(l: list, idx: int, default):
    try:
        return l[idx]
    except IndexError:
        return default


def request_data(host: str, path: str) -> str:
    retry_counter = 0
    while retry_counter < 5:
        try:
            request = requests.get(host + path)
        except:
            pass

        if request.status_code == 200:
            return request.text
        retry_counter += 1
        time.sleep(5)
    if not request.status_code == 200:
        raise ConnectionError("Could not connect to host")


def collect_data(host: str, key_path: str, value_path: str) -> dict:
    result_dict = dict()
    result_dict["tags"] = {"user": "grafana", "device": "heater"}
    result_dict["fields"] = dict()
    keys = request_data(host, key_path)
    values = request_data(host, value_path)
    result_set = set(zip(str(keys).split("\n"), str(values).split("\n")))
    for element in result_set:
        key, *unit = element[0].split(";")
        result_dict["fields"][
            slugify(key, separator="_", replacements=[["ö", "oe"], ["ä", "ae"]])
        ] = element[
            1
        ]  # , 'unit': safe_list_get(unit, 0, None)}
    result_dict["time"] = datetime.utcnow().isoformat()
    result_dict["measurement"] = "heizung"
    if result_dict["fields"].get(""):
        result_dict["fields"].pop("")
    return result_dict


def write_to_influxdb(data: dict) -> None:
    client = influxdb_client.InfluxDBClient(
        url=INFLUXDB_HOST,
        token=INFLUXDB_TOKEN,
        org=INFLUXDB_ORG,
    )
    write_api = client.write_api(write_options=SYNCHRONOUS)
    point = (
        Point(INFLUXDB_MEASUREMENT_NAME)
        .tag("user", data["tags"]["user"])
        .tag("device", data["tags"]["device"])
        .time(data["time"], WritePrecision.NS)
    )
    pprint.pprint(data["fields"])
    for key, value in data["fields"].items():
        if key:
            point.field(key, value)
    write_api.write(bucket=INFLUXDB_BUCKET, record=point)
    client.close()


if __name__ == "__main__":
    data = collect_data(HOST, KEY_PATH, VALUE_PATH)
    write_to_influxdb(data)
