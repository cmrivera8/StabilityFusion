import pandas as pd
from pathlib import Path
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

    async def fetch_block(self, query, client):
        async with self.semaphore: # Limit concurrent tasks (currently to 3)
            block_df = await client.query_api().query_data_frame(query, org=self.org)

        if isinstance(block_df, list):
            block_df = pd.concat(block_df, ignore_index=True, sort=False)

        return block_df if not block_df.empty else None

    async def db_to_df(self, start: datetime, stop: datetime, avg_window=None, measurement=None):
        # Divide request in 1h blocks
        block_duration = timedelta(hours=1)
        total_duration = stop - start
        num_blocks = (total_duration // block_duration) + 1
        current_start = start

        # Define measurements to be fetched
        measurement_query = None
        if measurement:
            if isinstance(measurement, str):
                measurement = [measurement]
            measurement_query = """
                |> filter(fn: (r) => contains(value: r._measurement, set: {}))
            """.format(str(measurement).replace("\n","").replace("\'","\""))

        queries = []
        for _ in range(num_blocks):
            current_stop = min(current_start + block_duration, stop)

            start_str = current_start.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            stop_str = current_stop.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            current_start = current_stop

            if start_str == stop_str:
                continue

            query = """
            import "date"
            from(bucket: "{db_bucket}")
                |> range(start: {start}, stop: {stop})
            """.format(db_bucket=self.bucket, start=start_str, stop=stop_str)

            # Fetch specific measurements
            if measurement_query:
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
            queries.append(query)

        self.semaphore = asyncio.Semaphore(3)

        # Run all tasks concurrently
        async with InfluxDBClientAsync(url=self.url, token=self.token, org=self.org) as client:
            tasks = [self.fetch_block(query, client) for query in queries]
            df_list = await tqdm.gather(*tasks, desc="Fetching data")
            # df_list = await asyncio.gather(*tasks)

        # Remove None
        df_list = [df for df in df_list if df is not None]

        # Empty fetch
        if len(df_list) == 0:
            return None

        # Reset state of semaphore, it must be create in the same thread
        self.semaphore = None

        if not df_list:
            return None

        #  Post-process the DataFrame
        self.db_df = pd.concat(df_list, ignore_index=True)
        self.db_df = self.db_df.drop(columns=["result", "table", "_start", "_stop"], errors="ignore")
        self.db_df["_time"] = pd.to_datetime(self.db_df["_time"].values, utc=True)
        self.db_df["_time"] = self.db_df["_time"].dt.tz_convert("Europe/Paris")

        return self.db_df
