from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QLabel, QPushButton, QTabWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TunnelSchedule V0.1 - 隧洞施工进度计算系统")
        self.resize(1024, 768)

        # 核心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 标题
        self.title_label = QLabel("欢迎使用 TunnelSchedule V0.1")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333;")
        self.layout.addWidget(self.title_label)

        # 选项卡控件 (未来用来分模块：基础数据、计算参数、排期计算、图表展示)
        self.tabs = QTabWidget()
        self.tabs.addTab(QWidget(), "1. 项目基础信息")
        self.tabs.addTab(QWidget(), "2. 支洞与工作面划分")
        self.tabs.addTab(QWidget(), "3. 衬砌策略与计算")
        self.tabs.addTab(QWidget(), "4. 横道图与结果导出")
        
        self.layout.addWidget(self.tabs)

        # 底部状态栏
        self.statusBar().showMessage("系统就绪 | 数据库连接正常")