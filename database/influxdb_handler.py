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

    def db_to_df(self, start, stop):
        def string_to_date(date_str):
            # From string to local timezone
            dt = datetime.fromisoformat(date_str).replace(tzinfo=ZoneInfo("Europe/Paris"))
            # From local datetime to UTC
            dt = dt.astimezone(ZoneInfo("UTC"))
            # Apply format compatible with Flux
            dt = dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            return dt

        start = string_to_date(start)
        stop = string_to_date(stop)

        query = """
        import "date"
        from(bucket: "{db_bucket}")
            |> range(start: {start}, stop: {stop})
        """.format(db_bucket=self.bucket, start=start, stop=stop)

        fluxtable_json = self.flux_to_points_obj(self.query_api.query(query, org=self.org))

        self.db_df = pd.DataFrame([vars(row) for row in fluxtable_json])

        # Convert _time column to datetime in UTC
        self.db_df["_time"] = pd.to_datetime(self.db_df["_time"], utc=True)

        # Convert _time column to Europe/Paris timezone
        self.db_df["_time"] = self.db_df["_time"].dt.tz_convert("Europe/Paris")

        # self.db_df.to_pickle("test.pkl") # Save
        # self.db_df = pd.read_pickle("test.pkl") # Load

        return self.db_df
