from PyQt5.QtWidgets import QMainWindow
from .mainwindow_uic import Ui_MainWindow


class MainWindowView(QMainWindow, Ui_MainWindow):
    """
    The model of Navigation agent
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.setupUi(self)