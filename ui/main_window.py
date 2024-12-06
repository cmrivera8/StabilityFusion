from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QSizePolicy, QScrollArea
import pyqtgraph as pg
from pyqtgraph.dockarea import *
import numpy as np
import pandas as pd

from ui.parameter_tree import ParameterTreeWidget
from ui.temporal_widget import TemporalWidget
from ui.adev_widget import AllanDeviationWidget
from ui.table_widget import DataTableWidget
from database.influxdb_handler import InfluxDBHandler

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
        dock_params = Dock("Parameters", size=(200, 400))
        self.param_tree = ParameterTreeWidget()
        dock_params.addWidget(self.param_tree)

        # Temporal traces
        dock_temp_plot = Dock("Temporal traces", size=(200, 400))
        self.temp_widget = TemporalWidget()
        dock_temp_plot.addWidget(self.temp_widget)

        # Allan deviation
        dock_adev_plot = Dock("Allan deviation", size=(200, 400))
        dock_adev_plot.addWidget(AllanDeviationWidget())

        # Column headers
        columns = [
            "Main", "Name", "Description",
            "Coeff_", "Fractional_", "Plot_temp", "Plot_adev"
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

        #
        self.param_tree.connect_get_data_action(self.get_data)

    def get_data(self):
        start = self.param_tree.param.child("Data acquisition", "Start").value()
        stop = self.param_tree.param.child("Data acquisition", "Stop").value()
        self.influxdb_data = self.influxdb.db_to_df(start, stop, "")

        # Update table with new data
        influx_df = self.influxdb_data
        measurements = influx_df["_measurement"].unique()
        for measurement in measurements:
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

        self.data_table_widget.update_table_from_dataframe()

        # Update plots with new data
        self.update_plots()

    def update_plots(self):
        print("updating plots...")
        df = self.influxdb_data
        for measurement in df["_measurement"].unique():
            measurement_df = df[df["_measurement"] == measurement]

            time = pd.to_datetime(measurement_df["_time"])
            value = measurement_df["_value"]
            self.add_temporal_trace(time,value,measurement)

    def add_temporal_trace(self,x,y,title):
        self.temp_widget.addWidget(np.arange(len(x.to_numpy())),y.to_numpy(),title)

    def handle_dataframe_update(self, row, col):
        option = self.table_df.columns[col]

        if option == "Plot_temp":
            measurement = self.table_df.iloc[row,1]
            value = self.table_df.iloc[row,col]
            self.temp_widget.plots[measurement]["widget"].setVisible(value)