from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFormLayout, QLineEdit, 
                               QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy)
from database.db_manager import DatabaseManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TunnelSchedule V0.1 - 隧洞施工进度计算系统")
        self.resize(1024, 768)
        
        # 初始化数据库管理器
        self.db = DatabaseManager() 

        # 核心部件
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # 标题
        self.title_label = QLabel("欢迎使用 TunnelSchedule V0.1")
        self.title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #333; margin-bottom: 10px;")
        self.layout.addWidget(self.title_label)

        # 选项卡控件
        self.tabs = QTabWidget()
        
        # 创建单独的 Tab 页面容器
        self.tab_project_info = QWidget()
        
        self.tabs.addTab(self.tab_project_info, "1. 项目基础信息")
        self.tabs.addTab(QWidget(), "2. 支洞与工作面划分 (开发中)")
        self.tabs.addTab(QWidget(), "3. 衬砌策略与计算 (开发中)")
        self.tabs.addTab(QWidget(), "4. 横道图与结果导出 (开发中)")
        
        self.layout.addWidget(self.tabs)

        # --- 初始化各个 Tab 的 UI ---
        self.init_tab_project_info()

        # 底部状态栏
        self.statusBar().showMessage("系统就绪 | 数据库连接正常")

    def init_tab_project_info(self):
        """构建第一个 Tab：项目基础信息的界面"""
        layout = QVBoxLayout(self.tab_project_info)
        
        # 使用表单布局非常适合做输入界面
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignRight) if hasattr(self, 'Qt') else None
        
        # 输入框定义
        self.input_project_name = QLineEdit()
        self.input_project_name.setPlaceholderText("例如：某水库长隧洞引水工程")
        
        self.input_start_station = QLineEdit()
        self.input_start_station.setPlaceholderText("例如：0.00 (必须填写纯数字)")
        
        self.input_end_station = QLineEdit()
        self.input_end_station.setPlaceholderText("例如：15000.00 (必须填写纯数字)")
        
        # 将输入框加入表单
        form_layout.addRow("项目名称 (必填):", self.input_project_name)
        form_layout.addRow("全局起点桩号 (必填):", self.input_start_station)
        form_layout.addRow("全局终点桩号 (必填):", self.input_end_station)
        
        layout.addLayout(form_layout)
        
        # 按钮层 (居中摆放)
        btn_layout = QHBoxLayout()
        self.btn_save_project = QPushButton("保存项目信息")
        self.btn_save_project.setMinimumSize(150, 40) # 设置按钮大小
        self.btn_save_project.setStyleSheet("""
            QPushButton {
                background-color: #2196F3; 
                color: white; 
                font-size: 14px; 
                font-weight: bold; 
                border-radius: 5px;
            }
            QPushButton:hover { background-color: #1976D2; }
        """)
        
        # 【核心逻辑】绑定点击事件到我们自己写的函数上
        self.btn_save_project.clicked.connect(self.save_project) 
        
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btn_layout.addWidget(self.btn_save_project)
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        layout.addLayout(btn_layout)
        
        # 添加一个弹性空间，把上面的表单和按钮顶在上方，不要散落全屏
        layout.addStretch() 

    def save_project(self):
        """处理点击保存按钮后的逻辑"""
        # 1. 获取输入框的文本，并去掉首尾空格
        name = self.input_project_name.text().strip()
        start_str = self.input_start_station.text().strip()
        end_str = self.input_end_station.text().strip()
        
        # 2. 基础数据非空校验
        if not name or not start_str or not end_str:
            QMessageBox.warning(self, "输入错误", "请将所有必填项填写完整！")
            return
        
        # 3. 数据类型和业务逻辑校验
        try:
            start_station = float(start_str)
            end_station = float(end_str)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "桩号必须是有效的数字（不能包含字母或汉字）！")
            return
        
        if start_station >= end_station:
            QMessageBox.warning(self, "输入错误", "隧洞终点桩号必须大于起点桩号！")
            return
        
        # 4. 调用数据库管理器存入数据
        success, msg = self.db.add_project(name, start_station, end_station)
        
        # 5. 反馈结果给用户
        if success:
            QMessageBox.information(self, "成功", msg)
            self.statusBar().showMessage(f"已保存当前项目：'{name}'")
        else:
            QMessageBox.critical(self, "数据库错误", msg)