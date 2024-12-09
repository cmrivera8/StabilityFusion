import pyqtgraph as pg
import numpy as np

class AllanDeviationWidget(pg.GraphicsLayoutWidget):
    def __init__(self):
        super().__init__()
        self.adev_widget = self.addPlot()

        self.adev_widget.setLogMode(x=True, y=True)
        self.adev_widget.setLabel('left', "Allan deviation")
        self.adev_widget.setLabel('bottom', "Integration time", units='s')
        self.adev_widget.showGrid(x=True, y=True, alpha=1)

        self.plots = {}

    def updateWidget(self, taus, devs, error_bars, title):
        # Check if the plots already exists
        if title in self.plots:
            self.plots[title]["data"].setData(taus, devs)
            return self.plots[title]

        # Create new curve and error bars
        plot_data = self.adev_widget.plot(taus, devs, pen=pg.mkPen(color='g', width=1))

        taus_log10 = np.log10(taus)
        devs_log10 = np.log10(devs)
        err_lo = devs_log10 - np.log10(devs - error_bars[0])
        err_hi = np.log10(devs + error_bars[1]) - devs_log10

        error_data = pg.ErrorBarItem(x=0,y=0,beam=0.05,pen=pg.mkPen(color='g'))
        error_data.setData(x=taus_log10, y=devs_log10, top=err_hi, bottom=err_lo)
        self.adev_widget.addItem(error_data)

        # Store plot
        self.plots[title] = {"data": plot_data, "error": error_data}