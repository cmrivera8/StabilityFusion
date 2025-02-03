import pandas as pd
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime, timedelta
from influxdb_client import InfluxDBClient
from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
from tqdm.asyncio import tqdm
import asyncio

from utils.file_tools import load_config

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
        self.semaphore = None

    async def fetch_block(self, query):
        async with self.semaphore:  # Limit concurrent tasks (currently to 3)
            async with InfluxDBClientAsync(url=self.url, token=self.token, org=self.org) as client:
                block_df = await client.query_api().query_data_frame(query,org=self.org)

        if block_df.empty:
            return None

        # Drop unused columns
        for col in ["result", "table", "_start", "_stop"]:
            block_df =block_df.drop(columns=col)

        # Convert _time columns to datetime in UTC
        block_df["_time"] = pd.to_datetime(block_df["_time"], format='mixed', utc=True)

        # Convert _time columns to Europe/Paris timezone
        block_df["_time"] = block_df["_time"].dt.tz_convert("Europe/Paris")

        return block_df


    async def db_to_df(self, start: datetime, stop: datetime, avg_window=None, measurement=None):
        # Divide request in 1h blocks
        block_duration = timedelta(hours=1)
        total_duration = stop-start
        use_progress = total_duration > block_duration
        num_blocks = (total_duration//block_duration)+1
        current_start = start

        # Define measurements to be fetched
        measurement_query = None
        if not measurement is None:
            if isinstance(measurement, str):
                measurement = [measurement]
            measurement_query = f"""
                |> filter(fn: (r) => contains(value: r._measurement, set: {str(measurement).replace("\n","").replace("\'","\"")}))
            """

        tasks = []

        # Semaphore must be create in the same thread
        self.semaphore = asyncio.Semaphore(3)
        for _ in range(num_blocks):
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

            # Using query_data_frame
            query += """
            |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
            """

            # Create a task for the current block
            tasks.append(self.fetch_block(query))
            current_start = current_stop

        # Run all tasks concurrently
        df_list = await tqdm.gather(*tasks, desc="Fetching data")

        # Remove None
        df_list = [item for item in df_list if not item is None]

        # Empty fetch
        if len(df_list) == 0:
            return None

        # Reset state of semaphore, it must be create in the same thread
        self.semaphore = None

        # Combine all chunks into the final DataFrame
        self.db_df = pd.concat(df_list, ignore_index=True) if len(df_list) != 0 else None

        return self.db_df
