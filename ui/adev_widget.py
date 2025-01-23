import pyqtgraph as pg
import numpy as np
from PyQt5.QtCore import pyqtSignal

class AllanDeviationWidget(pg.GraphicsLayoutWidget):
    update_table = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.adev_widget = self.addPlot()

        self.adev_widget.setLogMode(x=True, y=True)
        self.adev_widget.setLabel('left', "Allan deviation")
        self.adev_widget.setLabel('bottom', "Integration time", units='s')
        self.adev_widget.getAxis('bottom').enableAutoSIPrefix(False)
        self.adev_widget.getAxis('left').enableAutoSIPrefix(False)
        self.adev_widget.showGrid(x=True, y=True, alpha=0.5)

        # Plot settings
        self.error_bar_mode = "Fill between"

        self.plots = {}

    def updateWidget(self, taus, devs, error_bars, title, color):
        taus_log10 = np.log10(taus)
        devs_log10 = np.log10(devs)
        err_lo = devs_log10 - np.log10(devs - error_bars[0])
        err_hi = np.log10(devs + error_bars[1]) - devs_log10

        # Check if the plots already exists
        if title in self.plots:
            self.plots[title]["data"].setData(taus, devs)

            # Using Error bars
            self.plots[title]["error_bars"].setData(x=taus_log10, y=devs_log10, top=err_hi, bottom=err_lo)
            # Using fill between
            self.plots[title]["fill_between"].curves[0].setData(taus,devs+error_bars[1])
            self.plots[title]["fill_between"].curves[1].setData(taus,devs-error_bars[0])

            self.updateErrorBarVisibility(self.plots[title])
            return self.plots[title]

        # Create new curve and legend
        self.adev_widget.addLegend(offset=(1,0),labelTextSize= "8pt")
        plot_data = self.adev_widget.plot(taus, devs, pen=pg.mkPen(color=color, width=1.5), name=title)

        # Create error bars
        ## Using fill between
        brush_color = pg.mkColor(color)
        brush_color.setAlpha(100)

        curve_1 = self.adev_widget.plot(taus,devs+error_bars[1])
        curve_1.setVisible(False)
        curve_2 = self.adev_widget.plot(taus,devs-error_bars[0])
        curve_2.setVisible(False)
        fill_between = pg.FillBetweenItem(curve_1,curve_2,brush=pg.mkBrush(color=brush_color))
        self.adev_widget.addItem(fill_between)

        ## Using error bars
        error_bars = pg.ErrorBarItem(x=0,y=0,beam=0.05,pen=pg.mkPen(color=color))
        error_bars.setData(x=taus_log10, y=devs_log10, top=err_hi, bottom=err_lo)
        self.adev_widget.addItem(error_bars)

        # Store plot
        self.plots[title] = {"widget": self.adev_widget, "data": plot_data, "error_bars": error_bars, "fill_between": fill_between}

        # Connect visibility changes of the curve to update error bar visibility
        plot_data.visibleChanged.connect(lambda plot=self.plots[title]: self.updateErrorBarVisibility(plot))

        self.updateErrorBarVisibility(self.plots[title])

    def updateErrorBarVisibility(self, plot):
        """Update the visibility of the error bars based on the visibility of the curve."""

        if self.error_bar_mode == "Fill between":
            plot["fill_between"].setVisible(plot["data"].isVisible())
            plot["error_bars"].setVisible(False)

        if self.error_bar_mode == "Bars":
            plot["fill_between"].setVisible(False)
            plot["error_bars"].setVisible(plot["data"].isVisible())

        plot["widget"].enableAutoRange(axis='y')
        plot["widget"].setAutoVisible(y=True)

        # Update table dataframe
        self.update_table.emit(plot)