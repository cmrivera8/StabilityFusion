import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QWidget, QAbstractScrollArea, QHBoxLayout, QLabel, QPushButton,QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal
from engineering_notation import EngNumber

class AutoValueCell(QWidget):
    value_changed = pyqtSignal()

    def __init__(self, measurement, item_type, row, col, value, auto_value_method, parent=None):
        """
        A custom widget for table cells that includes a value and an "Auto" button.

        :param value: Initial value to display.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.is_auto = False
        self.old_manual = 0

        # Layout for the widget
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label to display the value
        self.value_label = QLineEdit(str(value))
        self.value_label.returnPressed.connect(self.emit_value_changed)
        layout.addWidget(self.value_label)

        # Button to toggle "Auto" mode
        self.auto_button = QPushButton("Auto")
        self.auto_button.measurement = measurement
        self.auto_button.item_type = item_type
        self.auto_button.row = row
        self.auto_button.col = col
        self.auto_button.setFixedSize(40, 20)  # Small button
        self.auto_button.clicked.connect(auto_value_method)
        layout.addWidget(self.auto_button)

    def emit_value_changed(self):
        try:
            self.value_label.setText(self.value_label.text())
        except Exception as e:
            pass
        self.value_changed.emit()

class DataTableWidget(QTableWidget):
    dataframe_updated = pyqtSignal(int, int)
    auto_value_request = pyqtSignal(object)

    def __init__(self, dataframe: pd):
        super().__init__()

        self.dataframe = dataframe
        self.updating = False # To prevent circular updates

        self.setColumnCount(len(dataframe.columns))
        self.setRowCount(len(dataframe))

        self.setHorizontalHeaderLabels(dataframe.columns)

        # Enable table properties
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(False)

        # Auto-resize columns to fill available space
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)

        # Populate table with initial data
        self.update_table_from_dataframe()

        # Enable properties
        self.itemChanged.connect(self.update_dataframe_from_table)

    def update_table_from_dataframe(self):
        self.updating = True
        self.setRowCount(len(self.dataframe))
        self.setColumnCount(len(self.dataframe.columns))

        for row in range(len(self.dataframe)):
            for col, column in enumerate(self.dataframe.columns):
                value = self.dataframe.iloc[row,col]

                if str(value) in ['True', 'False']:
                    value = np.bool(value == 'True') if isinstance(value, str) else value
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Checked if value else Qt.Unchecked)
                    item.setTextAlignment(Qt.AlignCenter)

                    # self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                    # self.setColumnWidth(col,1)
                    self.setItem(row, col, item)
                elif column[-1] == "_":
                    measurement = self.dataframe.iloc[row,1]
                    item_type = self.dataframe.columns[col]
                    cell_widget = AutoValueCell(measurement, item_type, row, col, value, self.connect_auto_value)
                    cell_widget.value_changed.connect(lambda item=cell_widget,r=row,c=col: self.update_dataframe_from_table(item, r,c))
                    self.setCellWidget(row, col, cell_widget)
                else:
                    # self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)  # Column 0: Manual resizing
                    self.setItem(row, col, QTableWidgetItem(str(value)))

        self.updating = False

    def connect_auto_value(self):
        self.auto_value_request.emit(self.sender())

    def update_dataframe_from_table(self, item, row=None, col=None):
        if not self.updating:
            row = row if row != None else item.row()
            col = col if col != None else item.column()

            if self.dataframe.columns[col] in ["Plot_temp", "Plot_adev"]:
                if item.flags() & Qt.ItemIsUserCheckable:
                    self.dataframe.iloc[row,col] = str(item.checkState() == Qt.Checked)

            if self.dataframe.columns[col] in ["Coeff_","Fractional_"]:
                try:
                    self.dataframe.iloc[row,col] = item.value_label.text()
                except Exception as e:
                    print("Wrong input, error: ", e)
                    return

            self.dataframe_updated.emit(row,col)