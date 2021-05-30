import json
import requests
import time
import pprint
from datetime import date, datetime
from influxdb import InfluxDBClient
from slugify import slugify

HOST = 'http://bmk30' #hostname and protocol to heater (mostly http and bmk30)
KEY_PATH = '/daqdesc.cgi' #Path to get the description of the values
VALUE_PATH = '/daqdata.cgi' #Path to values

INFLUXDB_HOST = 'changeme' #your InfluxDB instance
INFLUXDB_PORT = 8086 #InfluxDB port
INFLUXDB_USER = 'changeme' #InfluxDB user
INFLUXDB_PASSWORD = 'changeme' #InfluxDB password
INFLUXDB_DATABASE = 'heater' #InfluxDB database
INFLUXDB_SSL = False
INFLUXDB_SSL_VERIFY = False

def safe_list_get (l: list, idx: int, default):
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
        raise ConnectionError('Could not connect to host')

def collect_data(host: str, key_path: str, value_path: str) -> dict:
    result_dict = dict()
    result_dict['tags'] = {'user': 'grafana', 'device': 'heater'}
    result_dict['fields'] = dict()
    keys = request_data(host, key_path)
    values = request_data(host, value_path)
    result_set = set(zip(str(keys).split('\n'), str(values).split('\n')))
    for element in result_set:
        key, *unit = element[0].split(';')
        result_dict['fields'][slugify(key, separator='_', replacements=[['ö', 'oe'], ['ä', 'ae']])] = element[1] #, 'unit': safe_list_get(unit, 0, None)}
    result_dict['time'] = datetime.utcnow().isoformat()
    result_dict['measurement'] = 'heizung'
    if result_dict['fields'].get(''):
        result_dict['fields'].pop('')
    return result_dict

def write_to_influxdb(data: dict) -> None:
    try:
        client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, username=INFLUXDB_USER, password=INFLUXDB_PASSWORD, ssl=INFLUXDB_SSL, verify_ssl=INFLUXDB_SSL_VERIFY)
        client.switch_database(INFLUXDB_DATABASE)
    except Exception as exp:
        print(exp)
    try:
        status = client.write_points([data])
        print(status)
    except Exception as exp:
        print(exp)

if __name__ == '__main__':
    data = collect_data(HOST, KEY_PATH, VALUE_PATH)
    write_to_influxdb(data)
