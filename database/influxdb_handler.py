import json
import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from tqdm import tqdm
import re

def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            content = f.read()
            # Remove comments only when they start a line or follow whitespace
            content = re.sub(r'^\s*//.*', '', content, flags=re.MULTILINE)
            content = '\n'.join(line for line in content.splitlines() if line.strip())
            config = json.loads(content)
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

    def db_to_df(self, start: datetime, stop: datetime, avg_window=None, measurement=None):
        # Divide request in 1h blocks
        block_duration = timedelta(hours=1)
        total_duration = stop-start
        use_progress = total_duration > block_duration
        num_blocks = (total_duration//block_duration)+1
        current_start = start

        # Testing
        # self.db_df = pd.read_pickle("test.pkl") # Load
        # return self.db_df

        # Define measurements to be fetched
        measurement_query = None
        if not measurement is None:
            if isinstance(measurement, str):
                measurement = [measurement]
            measurement_query = f"""
                |> filter(fn: (r) => contains(value: r._measurement, set: {str(measurement).replace("\n","").replace("\'","\"")}))
            """

        iterator = tqdm(range(num_blocks), desc="Fetching data (hours)") if use_progress else range(num_blocks)

        df_list = []

        for _ in iterator:
            current_stop = min(current_start + block_duration, stop)

            start_str = current_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            stop_str = current_stop.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

            if start_str == stop_str:
                continue

            query = """
            import "date"
            from(bucket: "{db_bucket}")
                |> range(start: {start}, stop: {stop})
            """.format(db_bucket=self.bucket, start=start_str, stop=stop_str)

            # Fetch specific measurements
            if not measurement_query is None:
                query += measurement_query

            # Apply moving average window
            if avg_window:
                query += f"""
                    |> timedMovingAverage(every: {avg_window}s, period: {avg_window}s)
                """
            #

            fluxtable_json = self.flux_to_points_obj(self.query_api.query(query, org=self.org))

            # Skip empty blocks
            if len(fluxtable_json) == 0:
                current_start = current_stop
                continue
            #

            block_df = pd.DataFrame([vars(row) for row in fluxtable_json])

            # Convert _start,_stop,_time columns to datetime in UTC
            for col in ["_start", "_stop", "_time"]:
                block_df[col] = pd.to_datetime(block_df[col], format='mixed', utc=True)

            # Convert "_start", "_stop", "_time" columns to Europe/Paris timezone
            for col in ["_start", "_stop", "_time"]:
                block_df[col] = block_df[col].dt.tz_convert("Europe/Paris")

            df_list.append(block_df)

            current_start = current_stop

        # Combine all chunks into the final DataFrame
        self.db_df = pd.concat(df_list, ignore_index=True)

        # Testing
        # self.db_df.to_pickle("test_2.pkl") # Save

        return self.db_df
