import pyqtgraph as pg
import numpy as np

class AllanDeviationWidget(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        self.adev_widget = self.addPlot()

        self.adev_widget.setLogMode(x=True, y=True)
        self.adev_widget.setLabel('left', "Allan deviation")
        self.adev_widget.setLabel('bottom', "Integration time", units='s')
        self.adev_widget.getAxis('bottom').enableAutoSIPrefix(False)
        self.adev_widget.showGrid(x=True, y=True, alpha=0.5)

        self.plots = {}

    def updateWidget(self, taus, devs, error_bars, title, color):
        taus_log10 = np.log10(taus)
        devs_log10 = np.log10(devs)
        err_lo = devs_log10 - np.log10(devs - error_bars[0])
        err_hi = np.log10(devs + error_bars[1]) - devs_log10

        # Check if the plots already exists
        if title in self.plots:
            self.plots[title]["data"].setData(taus, devs)
            self.plots[title]["error"].setData(x=taus_log10, y=devs_log10, top=err_hi, bottom=err_lo)
            self.updateErrorBarVisibility(self.plots[title])
            return self.plots[title]

        # Create new curve and error bars
        self.adev_widget.addLegend(offset=(0,0),labelTextSize= "8pt")
        plot_data = self.adev_widget.plot(taus, devs, pen=pg.mkPen(color=color, width=1.5), name=title)

        error_data = pg.ErrorBarItem(x=0,y=0,beam=0.05,pen=pg.mkPen(color=color))
        error_data.setData(x=taus_log10, y=devs_log10, top=err_hi, bottom=err_lo)
        self.adev_widget.addItem(error_data)

        # Store plot
        self.plots[title] = {"widget": self.adev_widget, "data": plot_data, "error": error_data}

        # Connect visibility changes of the curve to update error bar visibility
        plot_data.visibleChanged.connect(lambda plot=self.plots[title]: self.updateErrorBarVisibility(plot))

    def updateErrorBarVisibility(self, plot):
        """Update the visibility of the error bars based on the visibility of the curve."""
        plot["error"].setVisible(plot["data"].isVisible())
        plot["widget"].enableAutoRange(axis='y')
        plot["widget"].setAutoVisible(y=True)