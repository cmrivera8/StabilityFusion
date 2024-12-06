import json
import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
from zoneinfo import ZoneInfo
from influxdb_client import InfluxDBClient

def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in configuration file: {config_path}")

class InfluxDBHandler:
    def __init__(self, config_path="config/settings.json"):
        # Load configuration
        self.config_path = Path(config_path)
        config = load_config(self.config_path)["influxdb"]

        self.url    = config["url"]
        self.token  = config["token"]
        self.org    = config["org"]
        self.bucket = config["bucket"]

        write_client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.query_api = write_client.query_api()

    def flux_to_points_obj(self, fluxtable):
        fluxtable_json = json.loads(fluxtable.to_json(), object_hook=lambda d: SimpleNamespace(**d))
        return fluxtable_json

    def db_to_df(self, start, stop, measurement, filter=None, aggregate=None, target_timezone_offset=-2):
        def string_to_date(string_date):
            if "." in string_date:
                date_format="%Y-%m-%d %H:%M:%S.%f"
            else:
                date_format="%Y-%m-%d %H:%M:%S"
            dt = datetime.strptime(string_date, date_format)
            dt = dt.replace(tzinfo=ZoneInfo("Europe/Paris"))
            return dt

        def date_to_string(input_date, date_format="%Y-%m-%dT%H:%M:%S.%f"):
            return datetime.strftime(input_date, format=date_format)+"Z"

        start = date_to_string(string_to_date(start))
        stop = date_to_string(string_to_date(stop))

        query = """
        import "date"
        from(bucket: "{db_bucket}")
            |> range(start: {start}, stop: {stop})
        """.format(db_bucket=self.bucket, start=start, stop=stop)

        # fluxtable_json = self.flux_to_points_obj(self.query_api.query(query, org=self.org))

        # self.db_df = pd.DataFrame([vars(row) for row in fluxtable_json])

        self.db_df = pd.read_pickle("test.pkl")

        return self.db_df

        # |> filter(fn: (r) => r._measurement == "{measurement}")
#     # Add moving average filter if required
#     if not filter == None:
#         query += "\n|> timedMovingAverage(every: 1s, period: {tau}s)".format(tau=filter)

#     if not aggregate == None:
#         query += """
#         |> aggregateWindow(every: {aggregate}ms, fn: mean, createEmpty: true)
#         |> fill(usePrevious: true)
#         """.format(aggregate=aggregate)
