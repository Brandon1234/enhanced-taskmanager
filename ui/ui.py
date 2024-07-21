from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMainWindow, QLabel, QHBoxLayout, QVBoxLayout, QCheckBox, QTableView, QTabWidget, QMenu, QWidget, QGroupBox
from PyQt5.QtCore import QRunnable, QThread, QThreadPool, Qt, QTimer, QSize, QEventLoop
from PyQt5.QtGui import QFont, QStandardItemModel
import sys, time
import pandas as pd
import math
from threading import Thread
from Sensors.ProcessSensor import ProcessSensor
from MVC.PandasTableModel import PandasTableModel


# TODO Change connections list to be vertical rather than horizental

 # Custom aggregation function to combine the values in the files column
def agg_files(files):
    #totalFiles = "Total: "
    total = 0
    uniqueFiles = {"Total" : 0}
    for value in files.to_numpy():
        # DO a quick check to see if any of the files are still loading
        if value == "Loading...":
            return "Loading..."

        if value != "":
            # get unique values for each file type
            commaSplit = value.split(",")
            # If there is only the "Total" file count then skip the other things
            if len(commaSplit) == 2:
                num = [int(num) for num in value.split() if num.isdigit()]
                if len(num) > 0:
                    uniqueFiles["Total"] += int(num[0])
                
            else:
                for line in commaSplit:
                    # print(line)
                    # split each individual file category to get the number and add them together
                    colonSplit = line.split(":")
                    # 0th index is the file type
                    # 1th index is the total num of files

                    # check to see if the file type has been recorded already
                    if colonSplit[0] not in uniqueFiles.keys():
                        uniqueFiles[colonSplit[0]] = int(colonSplit[1])
                    else:
                        uniqueFiles[colonSplit[0]] += int(colonSplit[1])

    totalFiles = ""
    for key in uniqueFiles:
        totalFiles += key + ": " + str(uniqueFiles[key]) + ", "
    totalFiles = totalFiles[:-2]
    return totalFiles

# Custom aggregation function to combine the values in the Network Connection column
def agg_connections(connections):
    uniqueConnections = {}
    for value in connections.to_numpy():
        if value != "":
            commaSplit = value.split(",")
            # print(commaSplit)
            if commaSplit[0] != "Loading...":
                for line in commaSplit:
                    # 0th index is 'Connections to'
                    # each remaining index should be nth 'connectionName' n+1th numOfConnections
                    colonSplit = line.split(":")
                    if colonSplit[0] == "Connections to":
                        colonSplit.pop(0)
                    # print(colonSplit)
                    # check for blocked connections '-'
                    if colonSplit[0] == " -":
                        print("Blocked")
                        # Do nothing on blocked connection I guess
                    elif colonSplit[0] not in uniqueConnections.keys():
                        # if the connection is just to a country and doesn't have a number of connections:
                        if len(colonSplit) == 1:
                            uniqueConnections[colonSplit[0]] = -1
                        else:
                            uniqueConnections[colonSplit[0]] = int(colonSplit[1])
                    else:
                        # if the connection is just to a country and doesn't have a number of connections:
                        if len(colonSplit) == 1:
                            uniqueConnections[colonSplit[0]] = -1
                        else:
                            uniqueConnections[colonSplit[0]] += int(colonSplit[1])
            else:
                toReturn = "Loading..."
                return toReturn
    if uniqueConnections == {}:
        return ""
    toReturn = "Connections to:"
    for key in uniqueConnections:
        # check for countries in the connection
        if uniqueConnections[key] == -1:
            toReturn += key + ", "
        else:
            toReturn += key + " : " + str(uniqueConnections[key]) + ", "
    
    toReturn = toReturn[:-2]

    return toReturn

# Custom aggregation function to combine the values in the Create Time column
def agg_time(times):
    currentTime = time.localtime()
    currentTimeInt = time.mktime(currentTime)
    currHighest = 0
    currLowest = 99999999999

    for values in times.to_numpy():
        valueTime = time.mktime(values)
        if valueTime > currHighest:
            currHighest = valueTime
        
        if valueTime < currLowest:
            currLowest = valueTime

    currHighest = math.floor((currentTimeInt - currHighest) / 60)
    currLowest = math.floor((currentTimeInt - currLowest) / 60)

    if currHighest == currLowest:
        if currHighest == 0:
            return "Just now"
        elif currHighest < 60:
            return str(math.floor(currHighest)) + " minutes ago"
        elif currHighest < 1440:
            return str(math.floor(currHighest / 60)) + " hours ago"
        else:
            return str(math.floor((currHighest / 1440))) + " days ago"

    highestString = ""
    if currHighest == 0:
        highestString = "Just now"
    elif currHighest < 60:
        highestString = str(math.floor(currHighest)) + " minutes ago"
    elif currHighest < 1440:
        highestString = str(math.floor(currHighest / 60)) + " hours ago"
    else:
        highestString = str(math.floor((currHighest / 1440))) + " days ago"

    
    lowestString = ""
    if currLowest == 0:
        lowestString = "Just now"
    elif currLowest < 60:
        lowestString = str(math.floor(currLowest)) + " minutes ago"
    elif currLowest < 1440:
        lowestString = str(math.floor(currLowest / 60)) + " hours ago"
    else:
        lowestString = str(math.floor((currLowest / 1440))) + " days ago"

    toReturn = "From " + highestString + " to " + lowestString
    return toReturn

# OLD AGGREGATION FUNCTION FOR WHEN IT USED TO SHOW Hours:Minutes:Seconds
#def agg_time(times):
    # get the lowest and highest times, return a range to display
#    currHighest = "00:00:00"
#    currLowest = "99:99:99"

#    for values in times.to_numpy():
#        if values > currHighest:
#            currHighest = values
        
#        if values < currLowest:
#            currLowest = values

#    toReturn = currLowest + " - " + currHighest
#    return toReturn

# Custom aggregation function to combine the values in the Verified Publisher column
def agg_publisher(publishers):
    publishersNames = []
    for values in publishers.to_numpy():
        if values not in publishersNames:
            publishersNames.append(values)

    toReturn = ""
    for name in publishersNames:
        # check for a missing publisher
        if name is not None:
            toReturn += name + ", "

    toReturn = toReturn[:-2]
    return toReturn

def calc_createTime(createTime):
    currentTime = time.localtime()
    createTimeInt = time.mktime(createTime)
    currentTimeInt = time.mktime(currentTime)
    difference = math.floor((currentTimeInt - createTimeInt) / 60) # divide by 60 for minutes

    # return a minutes value while it's under and hour, otherwise just return the hour value
    if difference == 0:
        return "Just now"
    elif difference < 60:
        return str(math.floor(difference)) + " minutes ago"
    elif difference < 1440:
        return str(math.floor(difference / 60)) + " hours ago"
    else:
        return str(math.floor((difference / 1440))) + " days ago"

    return "Never, this is an error"
#--------------
# Sort based on Integer Values
#--------------
class MySortFilterProxyModel(QtCore.QSortFilterProxyModel):
    def lessThan(self, left_index, right_index):
        left_data = self.sourceModel().data(left_index)
        right_data = self.sourceModel().data(right_index)
        try:
            return float(left_data) < float(right_data)
        except (ValueError, TypeError):
            return left_data < right_data
#--------------


class QThreadWrapper(QThread):
    def __init__(self, mw):
        super().__init__()
        self.mw = mw
        self.stats_timer = None
        self.stats_timer_interval = 10000
        self.files_timer = None
        self.files_timer_interval = 120000
        self.cons_timer = None
        self.cons_timer_interval = 120000
        self.update_timer = None
        self.update_timer_interval = 12000
        self.publisher_timer = None
        self.publisher_timer_interval = 120000
        self.recent_proc_time = 10 * 60  # 10 minutes
        # Special timer only for the study
        self.study_timer_connections = None
        self.study_timer_files = None
        self.study_timer_interval = 30000 # 30 seconds instead of 2 mins

    def run(self):
        self.update_timer = QTimer()
        self.update_timer.setInterval(self.update_timer_interval)
        self.update_timer.timeout.connect(self.mw.update_model)
        self.update_timer.start()

        self.stats_timer = QTimer()
        self.stats_timer.setInterval(self.stats_timer_interval)
        self.stats_timer.timeout.connect(self.mw.wrapped_update_process_counters)
        self.stats_timer.start()

        self.files_timer = QTimer()
        self.files_timer.setInterval(self.files_timer_interval)
        self.files_timer.timeout.connect(self.mw.wrapped_update_open_files)
        self.files_timer.start()

        self.cons_timer = QTimer()
        self.cons_timer.setInterval(self.cons_timer_interval)
        self.cons_timer.timeout.connect(self.mw.wrapped_update_net_connections)
        self.cons_timer.start()

        self.publisher_timer = QTimer()
        self.publisher_timer.setInterval(self.publisher_timer_interval)
        self.publisher_timer.timeout.connect(self.mw.wrapped_update_publishers)
        self.publisher_timer.start()

        self.study_timer_connections = QTimer()
        self.study_timer_connections.setInterval(self.study_timer_interval)
        self.study_timer_connections.timeout.connect(self.mw.wrapped_update_study_connections)
        self.study_timer_connections.start()

        self.study_timer_files = QTimer()
        self.study_timer_files.setInterval(self.study_timer_interval)
        self.study_timer_files.timeout.connect(self.mw.wrapped_update_files_connections)
        self.study_timer_files.start()

        loop = QEventLoop()
        loop.exec_()

class DisplayTabsWidget(QWidget):
    def __init__(self, parent):
        super(QWidget, self).__init__(parent)
        self.layout = QVBoxLayout(self)
        
        #Initialize Tabs in theory
        # This should create the tab widgets
        self.tabs = QTabWidget()
        self.tab1 = InformationWindow()
        #self.tab2 = OptionsWindow()
        self.tabs.resize(300, 200)

        # Set up the layout 
        self.tab1_layout = QtWidgets.QVBoxLayout()
        
        # This should actually create the tab buttons and their labels
        self.tabs.addTab(self.tab1, "Information") #TODO come up with better names
        #self.tabs.addTab(self.tab2, "Settings")

        # This should be where the contents of each tab widget is assigned, which should work with the classes hopefully
        self.tab1.layout = InformationWindow()
        #self.tab2.layout = OptionsWindow()

        # Add tabs to widget
        self.layout.addWidget(self.tabs)
        self.setLayout(self.layout)

        self.show()

class testWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)

        self.label = QLabel("TEsting")
        font = self.label.font()
        font.setPointSize(30)
        self.label.setFont(font)
        
        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

# unverified publishers

class OptionsWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(QWidget, self).__init__(parent)
        self.hide_win_checkBox = QCheckBox(text="Hide Windows processes")
        self.show_new_checkBox = QCheckBox(text="Show new processes only")
        self.merge_same_checkBox = QCheckBox(text="Merge instances of the same process")
        self.hide_win_proc = True

        self.hide_win_checkBox.stateChanged.connect(InformationWindow.on_hide_win_state_change)
        self.show_new_checkBox.stateChanged.connect(InformationWindow.on_show_new_state_change)
        self.merge_same_checkBox.stateChanged.connect(InformationWindow.on_merge_same_state_change)
        cb_layout = QHBoxLayout()
        cb_layout.addWidget(self.hide_win_checkBox)
        cb_layout.addWidget(self.show_new_checkBox)
        cb_layout.addWidget(self.merge_same_checkBox)
        
        options_layout = QVBoxLayout()
        options_layout.addLayout(cb_layout)

        self.setLayout(options_layout)

class InformationWindow(QtWidgets.QWidget):
    def __init__(self, parent=None):
        super(InformationWindow, self).__init__(parent)
        self.ps = ProcessSensor()
        self.files, self.connections  = None, None
        self.orchestrator_thread = None
        self.stats_timer = None
        self.stats_timer_interval = 10000
        self.files_timer = None
        self.files_timer_interval = 120000
        self.cons_timer = None
        self.cons_timer_interval = 120000
        self.update_timer = None
        self.update_timer_interval = 12000
        self.publisher_timer = None
        self.publisher_timer_interval = 120000
        self.recent_proc_time = 5 * 60  # 5 minutes

        self.ps.init_process_counters()

        ###UI Stuff
        self.hide_win_proc, self.show_new_proc, self.show_verified_proc, self.show_with_network_connections_proc, self.merge_same_proc = False, False, False, False, False
        # self.simple_time = False
        self.pdtable = QTableView()
        self.pdtable.setMouseTracking(True)

        # self.pdtable.itemEntered.connect(self.mouseOverInformation)
        self.pdtable.setAlternatingRowColors(True)
        self.pdtable.verticalHeader().setVisible(False)
        font = QFont("Courier New", 8)
        self.pdtable.setFont(font)
        #-----Modified by Danyal-------
        screen_resolution = QtWidgets.QDesktopWidget().screenGeometry()
        screen_width, screen_height = screen_resolution.width(), screen_resolution.height()
        self.setGeometry(0, 0, int(screen_width/2), int(screen_height*0.9))
        #self.pdtable.setSortingEnabled(True)

        #self.menu_bar = self.menuBar()
        #self.view_menu = self.menu_bar.addMenu('View')
        #self.hide_microsoft = QtWidgets.QAction('Hide Microsoft Processes', self)
        #self.hide_microsoft.setCheckable(True)
        #self.hide_microsoft.triggered.connect(self.on_hide_win_state_change)
        #self.view_menu.addAction(self.hide_microsoft)
        #self.new_processes = QtWidgets.QAction('Show new processes only', self)
        #self.new_processes.setCheckable(True)
        #self.new_processes.triggered.connect(self.on_show_new_state_change)
        #self.view_menu.addAction(self.new_processes)
        #self.merge_same_processes = QtWidgets.QAction('Merge instances of the same process', self)
        #self.merge_same_processes.setCheckable(True)
        #self.merge_same_processes.triggered.connect(self.on_merge_same_state_change)
        #self.view_menu.addAction(self.merge_same_processes)

        #------------------------------


        self.hide_win_checkBox = QCheckBox(text="Windows processes")
        self.hide_win_checkBox.setChecked(True)
        self.show_new_checkBox = QCheckBox(text="Processes older than 5 minutes")
        self.show_new_checkBox.setChecked(True)
        self.hide_verified_checkBox = QCheckBox(text="Verified publishers")
        self.hide_verified_checkBox.setChecked(True)
        self.show_network_checkBox = QCheckBox(text="Identified network connections")
        self.show_network_checkBox.setChecked(True)
        # self.simple_time_checkBox = QCheckBox(text="Simplify Create Time")
        # self.simple_time_checkBox.setChecked(True)
        self.merge_same_checkBox = QCheckBox(text="Merge instances of the same process")
        self.merge_same_checkBox.setChecked(False)
        self.hide_win_checkBox.stateChanged.connect(self.on_hide_win_state_change)
        self.show_new_checkBox.stateChanged.connect(self.on_show_new_state_change)
        self.show_network_checkBox.stateChanged.connect(self.on_show_network_state_change)
        self.hide_verified_checkBox.stateChanged.connect(self.on_show_verified_state_change)
        # self.simple_time_checkBox.stateChanged.connect(self.on_simple_time_state_change)
        self.merge_same_checkBox.stateChanged.connect(self.on_merge_same_state_change)
        

        # Creates groupboxes to hold the checkboxes
        includeCheckboxGroupBox = QGroupBox("Include")
        includeCheckboxGroupBox.setCheckable(False)

        includeGroupBoxLayout = QHBoxLayout()

        includeGroupBoxLayout.addWidget(self.hide_win_checkBox)
        includeGroupBoxLayout.addWidget(self.show_new_checkBox)
        includeGroupBoxLayout.addWidget(self.show_network_checkBox)
        includeGroupBoxLayout.addWidget(self.hide_verified_checkBox)
        # includeGroupBoxLayout.addWidget(self.simple_time_checkBox)

        includeCheckboxGroupBox.setLayout(includeGroupBoxLayout)

        settingsCheckboxGroupBox = QGroupBox("Settings")
        settingsGroupBoxLayout = QHBoxLayout()

        settingsGroupBoxLayout.addWidget(self.merge_same_checkBox)

        settingsCheckboxGroupBox.setLayout(settingsGroupBoxLayout)

        cb_layout = QHBoxLayout()
        cb_layout.addWidget(includeCheckboxGroupBox)
        cb_layout.addWidget(settingsCheckboxGroupBox)

        main_layout = QVBoxLayout()
        main_layout.addLayout(cb_layout)
        main_layout.addWidget(self.pdtable)
        # self.widget.setLayout(main_layout)

        self.model = PandasTableModel(self.ps.df[['Process', 'CPU (%)', 'Memory (MB)', 'Disk Read (MB)',
                                                  'Disk Write (MB)', 'Files', 'Network Connections', 'Create Time',
                                                  'Verified Publisher']].copy(deep=True))
        #self.pdtable.setModel(self.model)
        
        #self.setCentralWidget(self.pdtable)
        #self.setLayout(main_layout)
        #--------Danyal
        self.current_sort_order = Qt.AscendingOrder  # keep track of the current sort order
        self.current_sort_column = None # keep track of the clicked column
        self.proxy_model = MySortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortRole(QtCore.Qt.EditRole)
        #self.model.setSortRole(QtCore.Qt.EditRole)
        self.pdtable.setModel(self.proxy_model)
        self.pdtable.setSortingEnabled(True)
        self.pdtable.horizontalHeader().sectionClicked.connect(self.sort_by_column)
        self.pdtable.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.pdtable.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.pdtable.horizontalHeader().setSectionsMovable(True)
        self.pdtable.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeToContents)
        self.pdtable.resizeColumnsToContents()
        #--------------
        
        # Tooltip setup
        #headerModel = QStandardItemModel()
        #headerView = self.pdtable.horizontalHeader()
        #for i in range(headerView.count()):
        #    key = headerView.horizontalHeader.model().headerData(i, QtCore.Qt.Horizontal)
        #    print(key)
        #    toolTip = toolTipValues.get(key)
        #    headerView.horizontalHeaderItem(i).setToolTip(toolTip)
        #    print(toolTip)
        
        #fire up threads for blocking vals
        Thread(target=self.ps.update_publisher_names).start()
        Thread(target=self.ps.update_open_files).start()
        Thread(target=self.ps.update_net_connections).start()
        #load recurring timers
        self.orchestrator_thread = QThreadWrapper(self)
        self.orchestrator_thread.start()
        #self.startSensingThreads()

        self.setLayout(main_layout)

        #-----Added by Danyal-----

    # Checkboxes that start as initially checked need the opposite of value of the box state
    def on_show_new_state_change(self):
        self.show_new_proc = not self.show_new_checkBox.isChecked()
        self.wrapped_update_model()

    def on_hide_win_state_change(self):
        # print(self.hide_win_proc)
        self.hide_win_proc = not self.hide_win_checkBox.isChecked()
        self.wrapped_update_model()

    def on_show_network_state_change(self):
        self.show_with_network_connections_proc = not self.show_network_checkBox.isChecked()
        self.wrapped_update_model()
    
    def on_show_verified_state_change(self):
        self.show_verified_proc = not self.hide_verified_checkBox.isChecked()
        self.wrapped_update_model()
    
    # def on_simple_time_state_change(self):
    #     self.simple_time = not self.simple_time_checkBox.isChecked()
    #     self.wrapped_update_model()

    def on_merge_same_state_change(self):
        self.merge_same_proc = self.merge_same_checkBox.isChecked()
        self.wrapped_update_model()

    def sort_by_column(self, column_index):
        if column_index == self.current_sort_column:
        # Reverse the sort order
            if self.current_sort_order == Qt.AscendingOrder:
                self.current_sort_order = Qt.DescendingOrder
            else:
                self.current_sort_order = Qt.AscendingOrder
        else:
            # Update the sort column and sort order
            self.current_sort_column = column_index
            self.current_sort_order = Qt.AscendingOrder
            
        #self.model.sort(self.current_sort_column, self.current_sort_order)
        self.proxy_model.sort(self.current_sort_column, self.current_sort_order)
        self.pdtable.horizontalHeader().setSortIndicator(column_index, self.current_sort_order)
        #self.pdtable.horizontalHeader().setSortIndicator(self.current_sort_column, self.current_sort_order)
        self.pdtable.setModel(self.proxy_model)

    def update_sort(self):
        # Re-sort the data based on the current sort column and order
        if self.current_sort_column is not None:
            #self.model.sort(self.current_sort_column, self.current_sort_order, numeric=True)
            self.proxy_model.sort(self.current_sort_column, self.current_sort_order)
            self.pdtable.horizontalHeader().setSortIndicator(self.current_sort_column, self.current_sort_order)
            #self.pdtable.setModel(self.proxy_model)


        #-------------------------
    '''   
    def on_merge_same_state_change(self):
        self.merge_same_proc = self.merge_same_checkBox.isChecked()
        self.wrapped_update_model()

    def on_show_new_state_change(self):
        self.show_new_proc = self.show_new_checkBox.isChecked()
        self.wrapped_update_model()

    def on_hide_win_state_change(self):
        self.hide_win_proc = self.hide_win_checkBox.isChecked()
        self.wrapped_update_model()
    '''
    #def startSensingThreads(self):
        #self.startStatsUpdateThread()
        #self.startUpdateThread()
        #self.startFilesUpdateThread()
        #self.startConUpdateThread()
        #self.startPublisherUpdateThread()

    def startUpdateThread(self):
        self.update_timer = QTimer()
        self.update_timer.setInterval(self.update_timer_interval)
        self.update_timer.timeout.connect(self.update_model)
        self.update_timer.start()

    def update_model(self):
        Thread(target=self.wrapped_update_model()).start()


    def wrapped_update_model(self):
        filtered_df = self.ps.df[['Process', 'CPU (%)', 'Memory (MB)', 'Disk Read (MB)',
                                               'Disk Write (MB)', 'Files', 'Network Connections', 'Create Time',
                                               'Verified Publisher']].copy(deep=True)

        #TODO: Do it for process threads
        filtered_df.loc[filtered_df['CPU (%)'] > 0, 'CPU (%)'] = round(filtered_df['CPU (%)'] / self.ps.cpus, 2)

        if self.hide_win_proc:
            filtered_df = filtered_df[filtered_df['Verified Publisher'] != "Microsoft Corporation"]

        # Sorting is done on the integer value for create time, but the actual display is the text column
        if self.show_new_proc:
            cur_time = int(time.time()) - self.recent_proc_time
            filtered_df = filtered_df[filtered_df['Create Time'] > time.localtime(cur_time)]

        if self.show_with_network_connections_proc:
            filtered_df = filtered_df[filtered_df['Network Connections'] == ""]

        if self.show_verified_proc:
            filtered_df = filtered_df[filtered_df['Verified Publisher'] == ""]

        if self.merge_same_proc:
            filtered_df = filtered_df.groupby(by='Process').agg({'CPU (%)' : 'sum', 'Memory (MB)' : 'sum', 'Disk Read (MB)' : 'sum', 'Disk Write (MB)' : 'sum', 'Files' : lambda w: agg_files(w), 'Network Connections' : lambda x: agg_connections(x), 'Create Time' : lambda y: agg_time(y), 'Verified Publisher' : lambda z: agg_publisher(z)}).reset_index()
        else:  
            #Update the relative_create_time based on the current time and the acual create time.
            # if the merge happens then the times will already be updated properly
            filtered_df['Create Time'] = filtered_df['Create Time'].apply(calc_createTime)
        
        #filtered_df.drop(['create_time'], axis=1, inplace=True)
        # filtered_df['create_time'] = time.strftime("%H:%M:%S", time.gmtime(filtered_df['create_time']))
        self.model = PandasTableModel(filtered_df)
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setSortRole(QtCore.Qt.EditRole)
        self.pdtable.setModel(self.proxy_model)
        #-----------Danyal
        self.update_sort()
        #-----------------

    def startStatsUpdateThread(self):
        self.stats_timer = QTimer()
        self.stats_timer.setInterval(self.stats_timer_interval)
        self.stats_timer.timeout.connect(self.wrapped_update_process_counters)
        self.stats_timer.start()

    def wrapped_update_process_counters(self):
        Thread(target = self.ps.update_process_counters).start()

    def startFilesUpdateThread(self):
        self.files_timer = QTimer()
        self.files_timer.setInterval(self.files_timer_interval)
        self.files_timer.timeout.connect(self.wrapped_update_open_files)
        self.files_timer.start()

    def wrapped_update_open_files(self):
        Thread(target = self.ps.update_open_files).start()

    def startConUpdateThread(self):
        self.cons_timer = QTimer()
        self.cons_timer.setInterval(self.cons_timer_interval)
        self.cons_timer.timeout.connect(self.wrapped_update_net_connections)
        self.cons_timer.start()

    def wrapped_update_net_connections(self):
        Thread(target = self.ps.update_net_connections).start()

    def startPublisherUpdateThread(self):
        self.publisher_timer = QTimer()
        self.publisher_timer.setInterval(self.publisher_timer_interval)
        self.publisher_timer.timeout.connect(self.wrapped_update_publishers)
        self.publisher_timer.start()

    def wrapped_update_publishers(self):
        Thread(target = self.ps.update_publisher_names).start()

    def wrapped_update_study_connections(self):
        Thread(target = self.ps.update_net_connections_study).start()

    def wrapped_update_files_connections(self):
        Thread(target = self.ps.update_open_files_study).start()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.title = 'TaskManager'
        self.left = 0
        self.top = 0
        self.width = 300
        self.height = 200
        self.setWindowTitle(self.title)
        self.setGeometry(self.left, self.top, self.width, self.height)
  
        self.tab_widget = DisplayTabsWidget(self)
        self.setCentralWidget(self.tab_widget)

        self.show()
