from ui.ui import MainWindow
from PyQt5 import QtWidgets
import sys

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    main = MainWindow()
    '''
    creating a tab instead of a window
    window_tabs = QTabWidget()
    window_tabs.addTab(main, "Processes")
    screen_resolution = QtWidgets.QDesktopWidget().screenGeometry()
    screen_width, screen_height = screen_resolution.width(), screen_resolution.height()
    window_tabs.setGeometry(0, 0, int(screen_width/2), int(screen_height*0.90))
    window_tabs.show()
    '''
    main.resize(1200, 750)
    main.show()
    sys.exit(app.exec_())

