import pyqtgraph as pg
from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout

class TemporalWidget(QScrollArea):
    def __init__(self):
        super().__init__()
        # Container for plots
        self.plot_container = QWidget()
        self.plot_layout = QVBoxLayout(self.plot_container)
        self.plot_layout.setContentsMargins(0, 0, 0, 0)

        # Set up scroll area
        self.setWidget(self.plot_container)
        self.setWidgetResizable(True)  # Enable resizing
        # self.setMinimumWidth(500)  # Set a minimum width for the scrollable area

        self.plots = {}

    def addWidget(self, x, y, title="Plot"):
        """
        Add a plot widget to the scrollable area with the given x and y values.

        Parameters:
            x (list or numpy.ndarray): X-axis values.
            y (list or numpy.ndarray): Y-axis values.
            title (str): Title of the plot.
        """

        # Check if the plots already exists
        if title in self.plots:
            return self.plots[title]

        # Create a new plot
        plot_widget = pg.PlotWidget(title=title)
        plot_widget.setMinimumHeight(150)
        plot_data = plot_widget.plot(x, y, pen=pg.mkPen(color='b', width=2))  # Customize line style

        # Set axis labels
        plot_widget.setLabel('left', 'Y-axis')
        plot_widget.setLabel('bottom', 'X-axis')

        # Add the plot to the layout
        self.plot_layout.addWidget(plot_widget)

        # Store plot and its data reference
        self.plots[title] = {"widget": plot_widget, "data": plot_data}

        return self.plots[title]

    def updateWidget(self, x, y, title):
        """
        Update the data of an existing plot.

        Parameters:
            x (list or numpy.ndarray): New X-axis values.
            y (list or numpy.ndarray): New Y-axis values.
            title (str): Title of the plot to update.
        """
        # Check if the plot exists
        if title not in self.plots:
            self.addWidget(x,y,title)

        self.plots[title]["data"].setData(x, y)