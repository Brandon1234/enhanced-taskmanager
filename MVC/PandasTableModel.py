from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
class PandasTableModel(QtGui.QStandardItemModel):
    def __init__(self, data, parent=None):
        QtGui.QStandardItemModel.__init__(self, parent)
        self._data = data
        toolTipValues = {'Process' : "The name of the running process", 
            'CPU (%)' : "Percentage of your processor that the process is using", 
            'Memory (MB)' : "Amount of memory being used by the process", 
            'Disk Read (MB)' : "Amount of information being read from your disk", 
            'Disk Write (MB)' : "Amount of information being written to your disk", 
            'Files' : "The number of files being accessed by the program", 
            'Network Connections' : "Where or with whom the process is connecting too", 
            'Create Time' : "The time the process was created", 
            'Verified Publisher' : "This is the organization who made the program",
            'relative_create_time' : "You shouldn't be seeing this"}
        for col in data.columns:
            data_col = [QtGui.QStandardItem("{}".format(x)) for x in data[col].values]
            toolTip = toolTipValues[col]
            temp = 0
            for cell in data_col:
                data_col[temp].setToolTip(toolTip)
                temp += 1
                
            self.appendColumn(data_col) 

        # self.horizontalHeaderItem(10).setToolTip(toolTipValues['Process'])

        return

    def rowCount(self, parent=None):
        return len(self._data.index)

    def columnCount(self, parent=None):
        return self._data.columns.size

    def headerData(self, x, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self._data.columns[x]
        if orientation == Qt.Vertical and role == Qt.DisplayRole:
            return self._data.index[x]
        return None
