from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QSizePolicy, QScrollArea, QInputDialog
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import copy
import os
import json
from scipy.stats import linregress
from tqdm import tqdm
from datemath import datemath
import re
import asyncio

from ui.parameter_tree import ParameterTreeWidget
from ui.temporal_widget import TemporalWidget
from ui.adev_widget import AllanDeviationWidget
from ui.table_widget import DataTableWidget
from database.influxdb_handler import InfluxDBHandler
from data_processing.moving_average import moving_average
from data_processing.allan_deviation import get_stab
from data_processing.utils import resample_data

# Preset serialization
class DataEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, np.ndarray):
            return o.tolist()
        return o.__dict__

class MainWindow(QMainWindow):
    def __init__(self, influxdb: InfluxDBHandler):
        super().__init__()

        self.influxdb = influxdb
        self.influxdb_data_temp = None
        self.influxdb_data_adev = None
        self.data_avail_dct = {}

        self.setWindowTitle("StabilityFusion - by: Carlos RIVERA")

        # Docking widget
        area = DockArea()
        self.setCentralWidget(area)

        # Parameter tree
        dock_params = Dock("Parameters", size=(150, 400))
        self.param_tree = ParameterTreeWidget()
        dock_params.addWidget(self.param_tree)

        # Temporal traces
        dock_temp_plot = Dock("Temporal traces", size=(200, 400))
        self.temp_widget = TemporalWidget()
        dock_temp_plot.addWidget(self.temp_widget)

        # Allan deviation
        dock_adev_plot = Dock("Allan deviation", size=(200, 400))
        self.adev_widget = AllanDeviationWidget()
        dock_adev_plot.addWidget(self.adev_widget)

        # Column headers
        columns = [
            "Main", "Name", "Description", "Coeff_",
            "Fractional_", "Plot_temp", "Plot_adev"
        ]

        # Create an empty dataframe with only column headers
        self.table_df = pd.DataFrame(columns=columns)

        dock_table = Dock("Data", size=(200, 100))
        self.data_table_widget = DataTableWidget(self.table_df)
        self.data_table_widget.dataframe_updated.connect(self.handle_dataframe_update)
        dock_table.addWidget(self.data_table_widget)

        # Combine docks
        area.addDock(dock_params,'left')
        area.addDock(dock_temp_plot,'right')
        area.addDock(dock_adev_plot,'right')
        area.addDock(dock_table,'bottom')

        # Connect signals
        self.adev_widget.update_table.connect(self.update_adev_visibility)
        self.temp_widget.region_updated.connect(self.link_regions)
        self.data_table_widget.auto_value_request.connect(self.compute_auto_value)
        self.param_tree.param.sigTreeStateChanged.connect(self.param_change)

        # Populate presets combobox
        self.populate_presets()

    def param_change(self, params, changes):
        if self.param_tree.params_changing:
            return

        param = changes[0][0]
        data = changes[0][2]

        # Data acquisition
        if param.name() == 'Get data':
            self.get_temporal_data()
            self.populate_main_measurement()
            self.update_table()
            self.update_temporal_plot()
            self.autoset_region()
            self.autoscale_x_axis()
            if self.param_tree.param.child("Data processing", "Allan deviation", "Auto calculate").value():
                self.update_adev_plot()

        if param.name() == 'Clear data':
            self.influxdb_data_temp = None
            self.influxdb_data_adev = None
            self.data_avail_dct = {}

        # Data processing
        if param.name() == 'Moving Average':
            self.update_temporal_plot()

        if param.parent().name() == 'Allan deviation':
            if param.name() == 'Zoom region':
                self.zoom_region()
                return
            if param.name() == 'Calculate':
                self.update_adev_plot()
                return
            if param.name() in ["Start", "Stop", "Region size"]:
                self.link_regions(param)

        # Global settings
        if param.parent().name() == 'Global settings':
            plot_type = self.param_tree.param.child('Global settings','Plot type').value()
            plots = self.temp_widget.plots if plot_type == "Temporal" else self.adev_widget.plots

            plot_content = 'data' if plot_type == 'Allan deviation' else 'widget'
            table_col = 'Plot_temp' if plot_type == 'Temporal' else 'Plot_adev'

            if param.name() == 'Show all':
                [plots[key][plot_content].setVisible(True) for key in plots.keys()]
                self.table_df[table_col] = True
            if param.name() == 'Hide all':
                [plots[key][plot_content].setVisible(False) for key in plots.keys()]
                self.table_df[table_col] = False

            # Update table
            self.update_table()

        # Presets
        if param.parent().name() == 'Presets':
            if param.name() == 'Name':
                self.param_tree.params_changing = True
                self.add_preset()
                self.param_tree.params_changing = False
            if param.name() == 'Save':
                self.save_preset()
            if param.name() == 'Load':
                self.load_preset()
            if param.name() == 'Remove':
                self.remove_preset()

    def string_to_date(self, date_str):
        # From string to local timezone
        dt = datetime.fromisoformat(date_str).replace(tzinfo=ZoneInfo("Europe/Paris"))
        # From local datetime to UTC
        dt = dt.astimezone(ZoneInfo("UTC"))
        return dt

    def date_math(self, param):
        if any([val in param for val in ['y', 'Y', 'M', 'm', 'd', 'D', 'w', 'h', 'H', 's', 'S', 'now']]):
            param = str(
                datemath(param)
                    .astimezone(ZoneInfo("Europe/Paris")) # From UTC to Paris
                    .strftime("%Y-%m-%dT%H:%M:%S") # From datetime to string
                )
        return param

    def smart_fetch(self, start: datetime, end: datetime, measurement_list, avg_window, mode, main_df):
        # Helper functions
        def extend_limits(start,end):
            # Extend the range and round to the nearest hour
            adjusted_start = (start - pd.Timedelta(minutes=60)).replace(minute=0, second=0, microsecond=0)
            adjusted_end = (end + pd.Timedelta(minutes=60)).replace(minute=0, second=0, microsecond=0)
            return adjusted_start, adjusted_end

        def create_avail_df(start,end):
            df = pd.DataFrame(
                {
                    'time': pd.date_range(start=start, end=end, freq='1s'),
                    'cached': False,
                    'avg_window': ""
                })
            return df

        def extend_avail_df(start,end,existing_df):
            new_df = create_avail_df(start,end)
            new_df = pd.concat([existing_df, new_df], ignore_index=True)
            new_df = new_df.sort_values(by='time').drop_duplicates(subset='time', keep='first')
            return new_df

        def range_between_df(start,end,df):
            return all(create_avail_df(start, end)['time'].between(df['time'].min(),df['time'].max()))

        # Create dictionary per mode and measurement
        if not mode in self.data_avail_dct.keys():
            self.data_avail_dct[mode] = {}

        for measurement in (pbar := tqdm(measurement_list)):
            # Add measurement to the dictionary if it doesn't exist
            if not measurement in self.data_avail_dct[mode].keys():
                adjusted_start, adjusted_end = extend_limits(start,end)
                self.data_avail_dct[mode][measurement] = create_avail_df(adjusted_start,adjusted_end)

            # Define dataframes shorter name
            df_avail = self.data_avail_dct[mode][measurement]

            # Is the requested range within the dataframe limits? if not, extend the dataframe.
            extend_start, extend_end = start, end
            if not range_between_df(extend_start, extend_end, df_avail):
                extend_start, extend_end = extend_limits(extend_start,extend_end)
                df_avail = extend_avail_df(extend_start, extend_end, df_avail)

            # Is the requested range marked as cached?
            # If the mode is adev, check also if the avg_window size has changed
            if mode == "adev":
                not_cached = df_avail.query("time >= @start and time <= @end and (cached == False or avg_window != @avg_window)")
                avg_window_changed = any(df_avail.query("time >= @start and time <= @end and avg_window != @avg_window"))
            else:
                not_cached = df_avail.query("time >= @start and time <= @end and cached == False")
                avg_window_changed = False


            pbar.set_description("Using cached data for '{}'.".format(measurement))
            if not not_cached.empty:
                pbar.set_description("Fetching '{}' data.".format(measurement))

                # Fetch missing data
                fetch_start = not_cached['time'].iloc[0] - timedelta(seconds=5)
                fetch_stop = not_cached['time'].iloc[-1] + timedelta(seconds=5)

                avg_window_fetch = int(avg_window) if not avg_window == "" else None

                new_df = asyncio.run(self.influxdb.db_to_df(fetch_start, fetch_stop, measurement=measurement, avg_window=avg_window_fetch))

                # If the avg_window has changed for the region, drop old data
                if avg_window_changed and not (main_df is None):
                    rows_to_drop = main_df.query("_measurement == @measurement and _time >= @fetch_start and _time <= @fetch_stop").index
                    if not rows_to_drop.empty:
                        main_df.drop(rows_to_drop, inplace=True)

                main_df = pd.concat([main_df, new_df], ignore_index=True).sort_values(by='_time')

                # Mark the region as saved
                df_avail.loc[df_avail['time'].isin(not_cached['time']),['name','cached','avg_window']] = [measurement, True, str(avg_window)]

                # If the mode is "adev", plot availability
                if mode == "adev":
                    self.update_availability_plot(measurement)

            # Save changes to dictionary
            self.data_avail_dct[mode][measurement] = df_avail

        return main_df

    def get_param_dt_limits(self):
        start = self.param_tree.param.child("Data acquisition", "Start").value()
        stop = self.param_tree.param.child("Data acquisition", "Stop").value()

        # Process natural language date information
        start = self.date_math(start)
        stop = self.date_math(stop)
        #

        # String to datetime
        start = self.string_to_date(start)
        stop = self.string_to_date(stop)
        #
        return start, stop

    def get_temporal_data(self):
        influx_df = self.influxdb_data_temp

        start, stop = self.get_param_dt_limits()

        # Calculate moving average window
        avg_window = max(int((stop.timestamp()-start.timestamp())/1000), 1)
        #
        measurement_list = [None] # Fetch all available measurements
        influx_df = self.smart_fetch(start, stop, measurement_list, avg_window, "temporal", influx_df)

        # Sort by measurement name (Natural sorting function)
        def natural_sort(series):
            convert = lambda text: int(text) if text.isdigit() else text.lower()
            alphanum_key = lambda key: [convert(c) for c in re.split('([0-9]+)', key)]
            return series.map(lambda x: tuple(alphanum_key(x)))
        influx_df = influx_df.sort_values(by="_measurement", key=natural_sort)

        # Populate table measurements
        measurements = influx_df["_measurement"].unique()

        for i, measurement in enumerate(measurements):
            # Check if row exists
            if self.table_df["Name"].eq(measurement).any():
                continue
            # Add a row with individual column values
            self.table_df.loc[len(self.table_df)] = [
                False, # Main
                measurement, # Name
                "", # Description
                "1", # Coeff_
                "1", # Fractional_
                True, # Plot_temp
                True if i == 0 else False, # Plot_adev (first one is visible)
                ]

        self.influxdb_data_temp = influx_df

    def autoset_region(self):
        # Available data (temporal plot)
        start, stop = self.get_param_dt_limits()
        start = start.astimezone(ZoneInfo("Europe/Paris"))
        stop = stop.astimezone(ZoneInfo("Europe/Paris"))

        # Parameters
        region_param = self.param_tree.param.child("Data processing", "Allan deviation", "Region size")
        start_param = self.param_tree.param.child("Data processing", "Allan deviation", "Start")

        # Only auto-set if the region is currently outside the limits of the fetched data
        region = list(self.temp_widget.plots.values())[0]['region'].getRegion()
        region_start = region[0]
        region_stop = region[1]

        # Skip is region is already within the data
        if (start.timestamp() < region_start) and (stop.timestamp() > region_stop):
            return

        # When new data fetched, make a 10% or 1h size region in the center
        new_start = str((start + (stop-start)/2)).split("+")[0]
        start_param.setValue(new_start)

        # Convert to timestamp
        start = start.timestamp()
        stop = stop.timestamp()

        region_size = (stop-start)*0.1 # 10% of the data
        region_param.setValue(region_size)

    def autoscale_x_axis(self):
        start, stop = self.get_param_dt_limits()
        # Autoscale temporal plot
        for plot in self.temp_widget.plots.values():
            plot["widget"].setXRange(start.timestamp(),stop.timestamp())
            plot["widget"].enableAutoRange(axis='x')

    def update_adev_visibility(self, plot):
        self.table_df.loc[self.table_df['Name'] == plot['data'].name(), "Plot_adev"] = plot["data"].isVisible()
        self.update_table()

    def update_table(self):
        self.data_table_widget.update_table_from_dataframe()

    def param_to_datetime(self, param):
        value = param.value()
        return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    def link_regions(self, sender):
        if self.param_tree.params_changing:
            return

        self.param_tree.params_changing = True

        if isinstance(sender, pg.LinearRegionItem):
            new_region = sender.getRegion()
        else:
            start = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Start"))
            stop = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Stop"))

            region_size = self.param_tree.param.child("Data processing", "Allan deviation", "Region size").value()

            if sender != None and "Region" in sender.name():
                stop = start+timedelta(seconds=float(region_size))

            new_region = [value.timestamp() for value in [start,stop]]

        # Update all regions
        for key, plot in self.temp_widget.plots.items():
            plot["region"].setRegion(new_region)

        # Update parameter tree
        start, stop = [datetime.fromtimestamp(value) for value in new_region]

        self.param_tree.param.child("Data processing", "Allan deviation", "Start").setValue(start.strftime("%Y-%m-%d %H:%M:%S") )
        self.param_tree.param.child("Data processing", "Allan deviation", "Stop").setValue(stop.strftime("%Y-%m-%d %H:%M:%S") )
        self.param_tree.param.child("Data processing", "Allan deviation", "Region size").setValue((stop-start).total_seconds())

        self.param_tree.params_changing = False

        if self.param_tree.param.child("Data processing", "Allan deviation", "Auto calculate").value():
            self.update_adev_plot()

    def update_temporal_plot(self):
        moving_avg_window = self.param_tree.param.child("Data processing", "Moving Average").value()
        df = self.influxdb_data_temp
        first_plot = None

        measurements = df["_measurement"].unique()

        for measurement in measurements:
            measurement_df = df[df["_measurement"] == measurement]

            time = pd.to_datetime(measurement_df["_time"]).to_numpy()
            time = np.array([ts.timestamp() for ts in time])
            value = measurement_df["value"].to_numpy()

            # Sort by timestamp
            arg_sort = np.argsort(time)
            time = time[arg_sort]
            value = value[arg_sort]

            # Resample data to 1s
            if np.mean(np.diff(time)) < 1:
                resample_time, resample_value = resample_data(time,value)
            else:
                resample_time = time
                resample_value = value

            ## Temporal
            # Apply moving average
            avg_value = moving_average(resample_value, moving_avg_window)
            #

            plot = self.temp_widget.updateWidget(resample_time,avg_value,measurement)

            # Link x-axis
            plot["widget"].setXLink(self.temp_widget.coverage_widget)

    def update_availability_plot(self, measurement):
        df_avail = self.data_avail_dct['adev'][measurement]

        x = (df_avail['time'].astype('int64')/1e9).to_numpy()
        y = df_avail['cached'].to_numpy()
        self.temp_widget.update_availability_plot(x, y, measurement)

    def update_adev_plot(self, measurement=None):
        start = self.string_to_date(self.param_tree.param.child("Data processing", "Allan deviation", "Start").value())
        stop = self.string_to_date(self.param_tree.param.child("Data processing", "Allan deviation", "Stop").value())

        # Check if requested range is contained
        if type(self.table_df.iloc[0,6]) == str:
            test_value = "'True'"
        else:
            test_value = "True"

        measurement_list = self.table_df.query(f"Plot_adev == {test_value}")['Name'].to_list() if measurement is None else measurement # Fetch and calculate only visible
        if not isinstance(measurement_list,list):
            measurement_list = [measurement_list]

        avg_window = self.param_tree.param.child('Data processing', 'Allan deviation', 'Initial tau (s)').value()
        df = self.influxdb_data_adev

        df = self.smart_fetch(start, stop, measurement_list, avg_window, "adev", df)
        self.influxdb_data_adev = df

        # Use timestamp
        start = start.timestamp()
        stop = stop.timestamp()

        for measurement in (pbar := tqdm(measurement_list)):
            pbar.set_description("Calculating ADev for '{}'.".format(measurement))

            measurement_df = df[df["_measurement"] == measurement]

            ## Allan deviation
            time = pd.to_datetime(measurement_df["_time"]).to_numpy()
            time = np.array([ts.timestamp() for ts in time])
            value = measurement_df["value"].to_numpy()

            # Sort by timestamp
            arg_sort = np.argsort(time)
            time = time[arg_sort]
            value = value[arg_sort]

            region = np.where((time > start) & (time < stop))
            if np.size(region) == 0:
                region = np.arange(len(time))

            if self.temp_widget.color_dct.get(measurement):
                color = self.temp_widget.color_dct[measurement]
            else:
                color=None

            # Apply coupling coefficient
            coeff = self.table_df.loc[self.table_df['Name'] == measurement]["Coeff_"].iloc[0]
            value = value*float(coeff)

            # Apply fractional factor
            factor = self.table_df.loc[self.table_df['Name'] == measurement]["Fractional_"].iloc[0]
            value = value/float(factor)

            # Calculate Allan deviation
            mode = self.param_tree.param.child("Data processing", "Allan deviation", "Mode").value().lower()

            taus, devs, error_bars = get_stab(time[region], value[region], mode)
            self.adev_widget.updateWidget(taus, devs, error_bars, measurement, color)

    def zoom_region(self):
        start = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Start")).timestamp()
        stop = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Stop")).timestamp()

        for _, plot in self.temp_widget.plots.items():
            plot["widget"].setXRange(start,stop)
            plot["widget"].enableAutoRange(axis='y')
            plot["widget"].setAutoVisible(y=True)

    def handle_dataframe_update(self, row, col):
        column_title = self.table_df.columns[col]
        measurement = self.table_df.iloc[row,1]
        value = self.table_df.iloc[row,col]

        adev_visible = (self.table_df.iloc[row,6] == 'True')
        if value in ['True', 'False']:
            value = (value == 'True')

        # Plot visibility
        ## Temporal
        if column_title == "Plot_temp":
            # Toggle visibility
            self.temp_widget.plots[measurement]["widget"].setVisible(value)
        ## Adev
        if column_title == "Plot_adev":
            # Check if the plot exists, if not, create it
            if not self.adev_widget.plots.get(measurement) and adev_visible:
                self.update_adev_plot(measurement)

            # Toggle visibility
            self.adev_widget.plots[measurement]["data"].setVisible(value)

        # Coupling and Fractional coefficient
        if column_title in ["Coeff_", "Fractional_"] and adev_visible:
            self.update_adev_plot(measurement)

    def populate_main_measurement(self):
        # From the fetched data, fill the combobox that defines the main measurement
        combobox = self.param_tree.param.child('Global settings', 'Main measurement')

        content = self.influxdb_data_temp['_measurement'].unique()
        combobox.setLimits(content)

    def populate_presets(self):
        # Populate the content of the presets combobox based on the file in "presets"
        combobox = self.param_tree.param.child("Presets", "Name")

        content = ["Default"]
        content.extend([file.replace(".json","") for file in os.listdir("presets") if not "tree" in file])
        content.append("New")

        combobox.setLimits(content)

    def save_preset(self):
        preset_name = self.param_tree.param.child("Presets", "Name").value()
        self.table_df.to_json("presets/"+preset_name+".json")

        # Convert from relative to absolute timestamp (From the current temporal data)
        def rel_to_abs(param,index):
            try:
                if any([val in param.value() for val in ['y', 'Y', 'M', 'm', 'd', 'D', 'w', 'h', 'H', 's', 'S', 'now']]):
                    df = self.influxdb_data_temp
                    first_meas = df["_measurement"].unique()[0]
                    df = df[df["_measurement"] == first_meas]

                    abs_val = df["_time"].sort_values().iloc[index].strftime("%Y-%m-%d %H:%M:%S")

                    param.setValue(abs_val)
            except Exception as e:
                print("Error at converting relative to absolute timestamp: ", e)

        rel_to_abs(self.param_tree.param.child("Data acquisition", "Start"),0)
        rel_to_abs(self.param_tree.param.child("Data acquisition", "Stop"),-1)

        # Save parameter tree state
        state = json.dumps(self.param_tree.param.saveState(), indent=4, cls=DataEncoder)
        filename = "presets/"+preset_name+"_tree.json"
        with open(filename, "w") as outfile:
            outfile.write(state)

    def load_preset(self):
        preset_name = self.param_tree.param.child("Presets", "Name").value()
        new_df = pd.read_json("presets/"+preset_name+".json", dtype=str)

        self.table_df.drop(self.table_df.index, inplace=True)
        self.table_df[self.table_df.columns] = new_df

        # Load parameter tree state
        filename = "presets/"+preset_name+"_tree.json"
        with open(filename, 'r') as openfile:
                state = json.loads(openfile.read())
        self.param_tree.params_changing = True
        self.param_tree.param.restoreState(state)
        self.param_tree.params_changing = False

        # Update plots and table
        self.get_temporal_data()
        self.populate_main_measurement()
        self.update_temporal_plot()
        self.autoscale_x_axis()
        self.link_regions(None)

        self.update_table()

        self.update_adev_plot()

    def remove_preset(self):
        preset_name = self.param_tree.param.child("Presets", "Name").value()
        os.remove("presets/"+preset_name+".json")
        os.remove("presets/"+preset_name+"_tree.json")
        self.populate_presets()

    def add_preset(self):
        combobox = self.param_tree.param.child("Presets", "Name")
        if combobox.value() == "New":
            text, ok = QInputDialog.getText(self, 'New preset name', 'Enter the name of the new preset:')

            if ok:
                # Add the new item before "New"
                current_values = copy.deepcopy(combobox.opts["limits"])
                current_values.insert(len(current_values)-1,str(text))
                combobox.setLimits(current_values)
                combobox.setValue(str(text))

                self.save_preset()

    def db_data_to_array(self, measurement):
        df = self.influxdb_data_adev
        measurement_df = df[df["_measurement"] == measurement]

        time = pd.to_datetime(measurement_df["_time"]).to_numpy()
        time = np.array([ts.timestamp() for ts in time])
        value = measurement_df["value"].to_numpy()

        start = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Start")).timestamp()
        stop = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Stop")).timestamp()

        region = np.where((time > start) & (time < stop))

        if np.size(region) == 0:
            region = np.arange(len(time))

        time = time[region]
        value = df.loc[df["_measurement"] == measurement]["value"].to_numpy()[region]

        return time, value

    def compute_auto_value(self, button):
        row = button.row
        col = button.col
        measurement = button.measurement
        item_type = button.item_type

        widget = self.data_table_widget.cellWidget(row, col)

        # Use region
        main_measurement = self.param_tree.param.child('Global settings', 'Main measurement').value()

        param_ts, param_val = self.db_data_to_array(measurement)
        freq_ts, freq_val = self.db_data_to_array(main_measurement)
        #

        if item_type == "Coeff_":
            # Using linear regression to find correlation
            _,x = resample_data(param_ts, param_val)
            _,y = resample_data(freq_ts, freq_val)
            min_len = min(len(x), len(y))
            slope, intercept, r_value, p_value, std_err = linregress(x[-min_len:],y[-min_len:])

            value = slope

        if item_type == "Fractional_":
            value = np.mean(param_val)

        def strip_zeros(value):
            formatted = "{:.3e}".format(value)
            if "e" in formatted:
                # Split into coefficient and exponent, then strip zeros from coefficient
                coeff, exp = formatted.split("e")
                coeff = coeff.rstrip("0").rstrip(".")

                # +003 -> 3
                if "+" in exp:
                    exp = exp.replace("+","").lstrip("0")

                # -003 -> -3
                if "-" in exp:
                    exp = "-"+exp.replace("-","").lstrip("0")

                return f"{coeff}e{exp}"
            else:
                return str(float(formatted))  # Remove unnecessary zeros for non-exponential form

        widget.value_label.setText(strip_zeros(value))

        # Apply value
        widget.value_label.returnPressed.emit()

        # Recalculate ADev plot
        self.update_adev_plot()
