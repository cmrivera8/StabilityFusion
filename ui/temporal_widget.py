import pyqtgraph as pg
from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal
import numpy as np

class TemporalWidget(QScrollArea):
    region_updated = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.updating = False

        # Available colors
        self.colors = iter(['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf']*3)
        self.color_dct = {}

        # Container for plots
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)

        # Set up scroll area
        self.setWidget(self.plot_container)
        self.setWidgetResizable(True)  # Enable resizing
        # self.setMinimumWidth(500)  # Set a minimum width for the scrollable area

        # Add availability plot
        self.coverage_widget = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.coverage_widget.setMaximumHeight(25)
        ## Hide ticks and labels
        self.coverage_widget.getAxis('bottom').setTicks([])
        self.coverage_widget.getAxis('left').setTicks([])
        self.coverage_widget.getAxis('bottom').setStyle(showValues=False)
        self.coverage_widget.getAxis('left').setStyle(showValues=False)

        self.coverage_plot = self.coverage_widget.plot(
                                [],
                                [],
                                pen=None,             # No line
                                symbol=None,          # No symbols
                                fillLevel=0,          # Fill down to y=0
                                brush=(0, 255, 0, 150)  # Green color with some transparency
                            )

        self.plot_layout.addWidget(self.coverage_widget)

        self.plots = {}

    def updateWidget(self, x, y, title="Plot"):
        # Check if the plots already exists
        if title in self.plots:
            self.plots[title]["data"].setData(x, y)
            return self.plots[title]

        # Create a new plot
        plot_widget = pg.PlotWidget(title=title, axisItems={'bottom': pg.DateAxisItem()})
        plot_widget.showGrid(x=True, y=True, alpha=0.5)
        plot_widget.setMinimumHeight(150)
        color = next(self.colors)
        self.color_dct[title] = color
        plot_data = plot_widget.plot(x, y, pen=pg.mkPen(color=color, width=2))

        # Region
        region = pg.LinearRegionItem([x[0],x[-1]], swapMode="block")
        region.setBrush(QtGui.QColor(255, 0, 0, 30))
        region.sigRegionChangeFinished.connect(self.update_measure_region)
        plot_widget.addItem(region)

        # Set axis labels
        plot_widget.setLabel('left', 'Y-axis')
        plot_widget.setLabel('bottom', 'Timestamp')

        # Add the plot to the layout
        self.plot_layout.addWidget(plot_widget)

        # Store plot and its data reference
        self.plots[title] = {"widget": plot_widget, "data": plot_data, "region": region, "color": color}

        return self.plots[title]

    def update_measure_region(self):
        if not self.updating:
            self.updating = True
            self.region_updated.emit(self.sender())
            self.updating = False