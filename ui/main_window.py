from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QSizePolicy, QScrollArea, QInputDialog
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import copy
import os
import json
from engineering_notation import EngNumber
from scipy.stats import linregress

from ui.parameter_tree import ParameterTreeWidget
from ui.temporal_widget import TemporalWidget
from ui.adev_widget import AllanDeviationWidget
from ui.table_widget import DataTableWidget
from database.influxdb_handler import InfluxDBHandler
from data_processing.moving_average import moving_average
from data_processing.allan_deviation import get_stab
from data_processing.utils import resample_data

class MainWindow(QMainWindow):
    def __init__(self, influxdb: InfluxDBHandler):
        super().__init__()

        self.influxdb = influxdb
        self.influxdb_data = None
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
            self.get_data()
            self.update_table()
            self.update_temporal_plot()
            self.update_adev_plot()

        # Data processing
        if param.name() == 'Moving Average':
            self.update_temporal_plot()

        if param.parent().name() == 'Allan deviation':
            if param.name() == 'Zoom region':
                self.zoom_region()
                return
            self.link_regions(param)
            self.update_adev_plot()

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

    def get_data(self):
        start = self.param_tree.param.child("Data acquisition", "Start").value()
        stop = self.param_tree.param.child("Data acquisition", "Stop").value()
        self.influxdb_data = self.influxdb.db_to_df(start, stop)

        influx_df = self.influxdb_data
        measurements = influx_df["_measurement"].unique()
        for measurement in measurements:
            # Check if row exists
            if self.table_df["Name"].eq(measurement).any():
                continue
            # Add a row with individual column values
            self.table_df.loc[len(self.table_df)] = [
                False, # Main
                measurement, # Name
                "", # Description
                1, # Coeff_
                1, # Fractional_
                True, # Plot_temp
                True, # Plot_adev
                ]

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

        self.update_adev_plot()

    def update_temporal_plot(self):
        moving_avg_window = self.param_tree.param.child("Data processing", "Moving Average").value()
        df = self.influxdb_data
        first_plot = None
        for measurement in df["_measurement"].unique():
            measurement_df = df[df["_measurement"] == measurement]

            time = pd.to_datetime(measurement_df["_time"]).to_numpy()
            time = np.array([ts.timestamp() for ts in time])
            value = measurement_df["_value"].to_numpy()

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
            if first_plot == None:
                first_plot = plot["widget"]
            else:
                plot["widget"].setXLink(first_plot)

    def update_adev_plot(self, measurement=None):
        df = self.influxdb_data
        measurement_list = df["_measurement"].unique() if measurement == None else [measurement]

        for measurement in measurement_list:
            measurement_df = df[df["_measurement"] == measurement]

            time = pd.to_datetime(measurement_df["_time"]).to_numpy()
            time = np.array([ts.timestamp() for ts in time])
            value = measurement_df["_value"].to_numpy()

            ## Allan deviation
            start = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Start")).timestamp()
            stop = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Stop")).timestamp()

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
        option = self.table_df.columns[col]

        measurement = self.table_df.iloc[row,1]
        value = self.table_df.iloc[row,col]

        # Control plots visibility
        if option == "Plot_temp":
            self.temp_widget.plots[measurement]["widget"].setVisible(value)

        if option == "Plot_adev":
            self.adev_widget.plots[measurement]["data"].setVisible(value)

        if option in ["Coeff_","Fractional_"]:
            self.update_adev_plot(measurement)

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

        # Save parameter tree state
        state = json.dumps(self.param_tree.param.saveState())
        filename = "presets/"+preset_name+"_tree.json"
        with open(filename, "w") as outfile:
            outfile.write(state)

    def load_preset(self):
        preset_name = self.param_tree.param.child("Presets", "Name").value()
        new_df = pd.read_json("presets/"+preset_name+".json")

        new_df['Coeff_'] = new_df['Coeff_'].apply(lambda x: EngNumber(float(x)))
        new_df['Fractional_'] = new_df['Fractional_'].apply(lambda x: EngNumber(float(x)))

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
        self.get_data()
        self.update_temporal_plot()
        self.update_adev_plot()
        self.link_regions(None)

        self.update_table()

        for col in range(len(self.table_df.columns)):
            for row in range(len(self.table_df.index)):
                self.handle_dataframe_update(row,col)

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
        df = self.influxdb_data
        measurement_df = df[df["_measurement"] == measurement]

        time = pd.to_datetime(measurement_df["_time"]).to_numpy()
        time = np.array([ts.timestamp() for ts in time])
        value = measurement_df["_value"].to_numpy()

        start = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Start")).timestamp()
        stop = self.param_to_datetime(self.param_tree.param.child("Data processing", "Allan deviation", "Stop")).timestamp()

        region = np.where((time > start) & (time < stop))

        if np.size(region) == 0:
            region = np.arange(len(time))

        time = time[region]
        value = df.loc[df["_measurement"] == measurement]["_value"].to_numpy()[region]

        return time, value

    def compute_auto_value(self, button):
        row = button.row
        col = button.col
        measurement = button.measurement
        item_type = button.item_type

        widget = self.data_table_widget.cellWidget(row, col)

        # Use region
        param_ts, param_val = self.db_data_to_array(measurement)
        freq_ts, freq_val = self.db_data_to_array("counter")
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

        widget.value_label.setText(str(EngNumber(value)))

        # Apply value
        widget.value_label.returnPressed.emit()