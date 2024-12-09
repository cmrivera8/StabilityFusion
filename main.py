from PyQt5.QtWidgets import QApplication, QDesktopWidget
from ui.main_window import MainWindow
from database.influxdb_handler import InfluxDBHandler
import sys

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Get the desktop widget and screen count
    desktop = QDesktopWidget()
    screen_count = desktop.screenCount()
    print("Screen count: ", screen_count)

    # Start database handles
    influxdb = InfluxDBHandler()
    window = MainWindow(influxdb)
    if screen_count > 1:
        screen_rect = desktop.screenGeometry(1) # Open on left screen
        window.move(screen_rect.left(),screen_rect.top())

    # Maximize at startup
    maximize = True
    if maximize:
        window.showMaximized()
    else:
        window.show()
    #

    window.show()

    sys.exit(app.exec_())
