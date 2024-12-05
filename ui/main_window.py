from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QSplitter, QWidget, QSizePolicy, QScrollArea
import pyqtgraph as pg
from ui.parameter_tree import ParameterTreeWidget
import numpy as np

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("StabilityFusion - by: Carlos RIVERA")

        # Main widget
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        # Layout
        layout = QHBoxLayout()
        self.central_widget.setLayout(layout)

        # Create a QSplitter for horizontal resizing
        splitter = QSplitter()
        layout.addWidget(splitter)

        # Parameter tree
        self.param_tree = ParameterTreeWidget()
        splitter.addWidget(self.param_tree)

        # Plot widget (Temporal traces)
        #  Scrollable area for plots
        scroll_area = QScrollArea()
        self.temporal_plot_container = QWidget()
        self.temporal_plot_layout = QVBoxLayout(self.temporal_plot_container)
        self.temporal_plot_layout.setContentsMargins(0, 0, 0, 0)

        # Add the container widget to the scroll area
        scroll_area.setWidget(self.temporal_plot_container)
        scroll_area.setWidgetResizable(True)  # Enable resizing
        scroll_area.setMinimumWidth(500)
        splitter.addWidget(scroll_area)

        self.test = pg.PlotWidget(title="Temporal traces 0")
        self.temporal_plot_layout.addWidget(self.test)

        self.plot_temporal_traces = pg.PlotWidget(title="Temporal traces")
        self.temporal_plot_layout.addWidget(self.plot_temporal_traces)

        # Add initial traces
        self.trace1 = self.plot_temporal_traces.plot([], [], pen="r", name="Trace 1")  # Red line
        self.trace2 = self.plot_temporal_traces.plot([], [], pen="b", name="Trace 2")  # Blue line

        # Generate some example data and update traces
        self.x_data = np.linspace(0, 10, 100)
        self.y1_data = np.sin(self.x_data)
        self.y2_data = np.cos(self.x_data)

        self.update_traces()

        # Plot widget (Allan deviation)
        self.plot_allan_deviation = pg.PlotWidget(title="Allan deviation")
        splitter.addWidget(self.plot_allan_deviation)

        # Connect action to add temporal trace
        self.param_tree.connect_add_trace_action(self.add_temporal_trace)

        # Keep track of added plots
        self.plot_widgets = []

    def add_temporal_trace(self):
        """Add a new temporal trace dynamically."""
        new_plot = pg.PlotWidget(title=f"Temporal Trace {len(self.plot_widgets) + 1}")
        new_plot.setMinimumHeight(150)  # Set a minimum height for each plot
        self.temporal_plot_layout.addWidget(new_plot)
        self.plot_widgets.append(new_plot)

        # Ensure all plots resize dynamically
        for i in range(len(self.plot_widgets)):
            self.temporal_plot_layout.setStretch(i, 1)  # Assign equal stretch factors to all plots

        # Optionally, populate the plot with example data
        x = range(100)
        y = [i ** 0.5 for i in x]
        new_plot.plot(x, y, pen="r")
        new_plot.setLabel('left', 'Value')
        new_plot.setLabel('bottom', 'Time')
        new_plot.showGrid(x=True, y=True)  # Enable grid by default

    def update_traces(self):
        """Update the data for the traces."""
        self.trace1.setData(self.x_data, self.y1_data)
        self.trace2.setData(self.x_data, self.y2_data)