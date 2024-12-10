import pandas as pd
import numpy as np
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox, QWidget, QAbstractScrollArea, QHBoxLayout, QLabel, QPushButton,QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSignal

class AutoValueCell(QWidget):
    value_changed = pyqtSignal()

    def __init__(self, value, compute_callback, parent=None):
        """
        A custom widget for table cells that includes a value and an "Auto" button.

        :param value: Initial value to display.
        :param compute_callback: A function that computes the automatic value.
        :param parent: Parent widget.
        """
        super().__init__(parent)
        self.compute_callback = compute_callback
        self.is_auto = False
        self.old_manual = 0

        # Layout for the widget
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Label to display the value
        self.value_label = QLineEdit(str(value))
        self.value_label.textChanged.connect(self.emit_value_changed)
        layout.addWidget(self.value_label)

        # Button to toggle "Auto" mode
        self.auto_button = QPushButton("Auto")
        self.auto_button.setFixedSize(40, 20)  # Small button
        self.auto_button.clicked.connect(self.toggle_auto)
        layout.addWidget(self.auto_button)

    def emit_value_changed(self):
        self.value_changed.emit()

    def toggle_auto(self):
        """
        Toggles between manual and automatic mode.
        """
        if not self.is_auto:
            # Compute and set the automatic value

            # QLineEdit
            auto_value = self.compute_callback()
            self.old_manual = self.value_label.text()
            self.value_label.setText(str(auto_value))
            self.value_label.setStyleSheet("color: gray;")  # Indicate auto mode
            self.value_label.setReadOnly(True)
            self.is_auto = True

            # Button
            self.auto_button.setText("Manual")
        else:
            # Switch back to manual mode

            # QLineEdit
            self.value_label.setStyleSheet("color: black;")  # Indicate manual mode
            self.value_label.setReadOnly(False)
            self.value_label.setText(self.old_manual)
            self.is_auto = False

            # Button
            self.auto_button.setText("Auto")

        self.emit_value_changed()

class DataTableWidget(QTableWidget):
    dataframe_updated = pyqtSignal(int, int)

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

                def compute_auto_value():
                    return 88

                if isinstance(value, np.bool):
                    item = QTableWidgetItem()
                    item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                    item.setCheckState(Qt.Checked if value else Qt.Unchecked)
                    item.setTextAlignment(Qt.AlignCenter)

                    # self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                    # self.setColumnWidth(col,1)
                    self.setItem(row, col, item)
                elif column[-1] == "_":
                    cell_widget = AutoValueCell(value, compute_auto_value)
                    cell_widget.value_changed.connect(lambda item=cell_widget,r=row,c=col: self.update_dataframe_from_table(item, r,c))
                    self.setCellWidget(row, col, cell_widget)
                else:
                    # self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Interactive)  # Column 0: Manual resizing
                    self.setItem(row, col, QTableWidgetItem(str(value)))


        self.updating = False

    def update_dataframe_from_table(self, item, row=None, col=None):
        if not self.updating:
            row = row if row != None else item.row()
            col = col if col != None else item.column()

            if self.dataframe.columns[col] == "Plot_temp":
                if item.flags() & Qt.ItemIsUserCheckable:
                    self.dataframe.iloc[row,col] = item.checkState() == Qt.Checked

            if self.dataframe.columns[col] in ["Coeff_","Fractional_"]:
                try:
                    self.dataframe.iloc[row,col] = float(item.value_label.text())
                except Exception as e:
                    print("Wrong input, error: ", e)
                    return

            self.dataframe_updated.emit(row,col)