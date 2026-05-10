import sys
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFormLayout, QLineEdit, 
                               QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy,
                               QDialog, QTableWidget, QTableWidgetItem, QHeaderView, 
                               QAbstractItemView, QSplitter, QGroupBox, QComboBox)
from PySide6.QtCore import Qt, QTimer
from database.db_manager import DatabaseManager

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TunnelSchedule V0.1 - 隧洞施工进度计算系统")
        self.resize(1200, 800)
        
        self.db = DatabaseManager() 
        self.current_project_id = None 

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.title_label = QLabel("TunnelSchedule V0.1")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2C3E50;")
        self.layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Developer: TONY SHI | 清晰的表达源于清晰的思考。")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #7F8C8D; font-style: italic; margin-bottom: 15px;")
        self.layout.addWidget(self.subtitle_label)

        self.tabs = QTabWidget()
        self.tab_project_info = QWidget()
        self.tab_data_entry = QWidget() 
        self.tab_strategy = QWidget() # 【新增 Tab 3】
        
        self.tabs.addTab(self.tab_project_info, "1. 项目基础信息")
        self.tabs.addTab(self.tab_data_entry, "2. 支洞与工作面划分")
        self.tabs.addTab(self.tab_strategy, "3. 开挖策略与计算") # 新增模块
        self.tabs.addTab(QWidget(), "4. 衬砌策略与排期 (开发中)")
        self.tabs.addTab(QWidget(), "5. 成果展示导出 (开发中)")
        
        self.layout.addWidget(self.tabs)
        
        self.init_tab_project_info()
        self.init_tab_data_entry() 
        self.init_tab_strategy() # 初始化 Tab 3
        
        self.statusBar().showMessage("系统就绪 | 数据库连接正常 | 当前未载入项目")
        
        # 初始锁死后面的 Tab
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)

    # ================== Tab 1：项目基础信息 ==================
    def init_tab_project_info(self):
        layout = QVBoxLayout(self.tab_project_info)
        form_layout = QFormLayout()
        
        self.input_project_name = QLineEdit()
        self.input_start_station = QLineEdit()
        self.input_end_station = QLineEdit()
        
        form_layout.addRow("项目名称 (必填):", self.input_project_name)
        form_layout.addRow("全局起点桩号 (必填):", self.input_start_station)
        form_layout.addRow("全局终点桩号 (必填):", self.input_end_station)
        layout.addLayout(form_layout)
        
        btn_layout = QHBoxLayout()
        self.btn_load_project = QPushButton("打开项目库...")
        self.btn_load_project.setMinimumSize(150, 40)
        self.btn_load_project.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 5px; } QPushButton:hover { background-color: #45A049; }")
        self.btn_load_project.clicked.connect(self.open_project_dialog)
        
        self.btn_save_project = QPushButton("保存项目信息")
        self.btn_save_project.setMinimumSize(150, 40)
        self.btn_save_project.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; }")
        self.btn_save_project.clicked.connect(self.save_project) 
        
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        btn_layout.addWidget(self.btn_load_project)
        btn_layout.addWidget(self.btn_save_project)
        btn_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        
        layout.addLayout(btn_layout)
        layout.addStretch()

    def open_project_dialog(self):
        projects = self.db.get_all_projects()
        if not projects:
            QMessageBox.information(self, "提示", "当前数据库中没有历史项目。")
            return
            
        dialog = ProjectSelectDialog(projects, self)
        
        # 【终极修复方案】：通过手动强制提取数据并延迟刷新，避开 UI 线程锁死
        dialog.exec() 
        selected_proj = dialog.get_selected_project()
        if selected_proj:
            try:
                self.current_project_id = selected_proj[0]
                # 强制刷新 UI 控件
                self.input_project_name.setText(str(selected_proj[1]))
                self.input_start_station.setText(str(selected_proj[2]))
                self.input_end_station.setText(str(selected_proj[3]))
                QApplication.processEvents() # 强制应用更新
                
                self.statusBar().showMessage(f"已载入项目：{selected_proj[1]}")
                
                # 解锁后续 Tab
                self.tabs.setTabEnabled(1, True)
                self.tabs.setTabEnabled(2, True)
                
                # 读取表单数据
                self.refresh_all_tabs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"载入异常：\n{str(e)}")

    def save_project(self):
        name = self.input_project_name.text().strip()
        start_str = self.input_start_station.text().strip()
        end_str = self.input_end_station.text().strip()
        
        if not name or not start_str or not end_str: return
        try:
            start_station = float(start_str)
            end_station = float(end_str)
        except: return
            
        if self.current_project_id is None:
            success, msg = self.db.add_project(name, start_station, end_station)
            if success:
                latest_projs = self.db.get_all_projects()
                if latest_projs: self.current_project_id = latest_projs[0][0] 
        else:
            success, msg = self.db.update_project(self.current_project_id, name, start_station, end_station)
            
        if success:
            QMessageBox.information(self, "成功", msg)
            self.statusBar().showMessage(f"当前项目上下文：'{name}'")
            self.tabs.setTabEnabled(1, True)
            self.tabs.setTabEnabled(2, True)
            self.refresh_all_tabs()

    # ================== 统一数据刷新中心 ==================
    def refresh_all_tabs(self):
        """统一调度刷新所有依赖数据库的 Tab"""
        self.refresh_tab2_data()
        self.refresh_tab3_data()

    # ================== Tab 2：支洞与分段 (保持原样) ==================
    def init_tab_data_entry(self):
        layout = QVBoxLayout(self.tab_data_entry)
        splitter = QSplitter(Qt.Vertical)
        
        group_adit = QGroupBox("1. 施工支洞配置 (Adits)")
        layout_adit = QVBoxLayout(group_adit)
        btn_paste_adit = QPushButton("📋 从 Excel 复制粘贴 (格式: 名称 | 交叉桩号 | 进洞时间[可选])")
        btn_paste_adit.clicked.connect(lambda: self.paste_from_excel('adit'))
        layout_adit.addWidget(btn_paste_adit)
        self.table_adits = QTableWidget()
        self.table_adits.setColumnCount(4)
        self.table_adits.setHorizontalHeaderLabels(["数据库ID", "支洞名称", "交叉桩号", "进洞时间(月)"])
        self.table_adits.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout_adit.addWidget(self.table_adits)
        splitter.addWidget(group_adit)
        
        group_seg = QGroupBox("2. 隧洞地质分段配置 (Segments)")
        layout_seg = QVBoxLayout(group_seg)
        btn_paste_seg = QPushButton("📋 从 Excel 复制粘贴 (格式: 起点 | 终点 | 围岩类别)")
        btn_paste_seg.clicked.connect(lambda: self.paste_from_excel('segment'))
        layout_seg.addWidget(btn_paste_seg)
        self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(4)
        self.table_segments.setHorizontalHeaderLabels(["数据库ID", "起点桩号", "终点桩号", "围岩类别"])
        self.table_segments.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        layout_seg.addWidget(self.table_segments)
        splitter.addWidget(group_seg)

        layout.addWidget(splitter)

    def refresh_tab2_data(self):
        if not self.current_project_id: return
        self.table_adits.clearContents()
        self.table_segments.clearContents()

        adits = self.db.get_adits(self.current_project_id)
        self.table_adits.setRowCount(len(adits))
        for r, row in enumerate(adits):
            for c in range(4): self.table_adits.setItem(r, c, QTableWidgetItem(str(row[c] if row[c] is not None else "")))
            
        segments = self.db.get_segments(self.current_project_id)
        self.table_segments.setRowCount(len(segments))
        for r, row in enumerate(segments):
            for c in range(4): self.table_segments.setItem(r, c, QTableWidgetItem(str(row[c] if row[c] is not None else "")))

    # ================== Tab 3：开挖策略与计算 (全新模块) ==================
    def init_tab_strategy(self):
        layout = QVBoxLayout(self.tab_strategy)
        splitter = QSplitter(Qt.Vertical)
        
        # --- 上半部分：围岩工效配置 ---
        group_speed = QGroupBox("1. 围岩开挖工效设置")
        layout_speed = QVBoxLayout(group_speed)
        
        btn_paste_speed = QPushButton("📋 从 Excel 复制粘贴 (格式: 围岩类别 | 进尺速度(m/月))")
        btn_paste_speed.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        btn_paste_speed.clicked.connect(lambda: self.paste_from_excel('speed'))
        layout_speed.addWidget(btn_paste_speed)
        
        self.table_speeds = QTableWidget()
        self.table_speeds.setColumnCount(2)
        self.table_speeds.setHorizontalHeaderLabels(["围岩类别 (如: III)", "进尺速度 (m/月)"])
        self.table_speeds.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_speeds.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        layout_speed.addWidget(self.table_speeds)
        splitter.addWidget(group_speed)

        # --- 下半部分：贯通主导面配置 ---
        group_clash = QGroupBox("2. 相邻支洞对向开挖贯通策略 (相距15m控制)")
        layout_clash = QVBoxLayout(group_clash)
        
        self.table_strategy = QTableWidget()
        self.table_strategy.setColumnCount(4)
        self.table_strategy.setHorizontalHeaderLabels(["开挖对向区间", "左侧施工支洞", "右侧施工支洞", "设定主导支洞 (不退让)"])
        header_strat = self.table_strategy.horizontalHeader()
        header_strat.setSectionResizeMode(0, QHeaderView.Stretch)
        header_strat.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_strat.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_strat.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout_clash.addWidget(self.table_strategy)
        
        # 底部留一个计算按钮
        self.btn_calculate = QPushButton("▶ 启动开挖排期计算")
        self.btn_calculate.setStyleSheet("background-color: #E91E63; color: white; font-size: 16px; font-weight: bold; padding: 10px; border-radius: 5px;")
        layout_clash.addWidget(self.btn_calculate)
        
        splitter.addWidget(group_clash)
        layout.addWidget(splitter)

    def refresh_tab3_data(self):
        """刷新 Tab 3 数据，自动计算支洞区间"""
        if not self.current_project_id: return
        
        # 1. 刷新围岩速度配置
        self.table_speeds.clearContents()
        speeds = self.db.get_speed_configs()
        self.table_speeds.setRowCount(len(speeds))
        for r, row in enumerate(speeds):
            self.table_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))

        # 2. 自动生成支洞对向区间并渲染下拉框
        adits = self.db.get_adits(self.current_project_id)
        if len(adits) < 2:
            self.table_strategy.setRowCount(0)
            return
            
        self.table_strategy.clearContents()
        # 相邻支洞数量 = 支洞总数 - 1
        self.table_strategy.setRowCount(len(adits) - 1)
        
        for i in range(len(adits) - 1):
            left_name = adits[i][1]
            right_name = adits[i+1][1]
            span_desc = f"{left_name} ➜ ⟵ {right_name}"
            
            self.table_strategy.setItem(i, 0, QTableWidgetItem(span_desc))
            self.table_strategy.setItem(i, 1, QTableWidgetItem(left_name))
            self.table_strategy.setItem(i, 2, QTableWidgetItem(right_name))
            
            # 植入下拉框控件
            combo_box = QComboBox()
            combo_box.addItems(["-- 默认相遇点 --", left_name, right_name])
            self.table_strategy.setCellWidget(i, 3, combo_box)

    # ================== 统一粘贴调度器 ==================
    def paste_from_excel(self, target_type):
        if not self.current_project_id: return
        clipboard_text = QApplication.clipboard().text().strip()
        if not clipboard_text: return
            
        lines = clipboard_text.split('\n')
        success_count, error_count = 0, 0
        
        for idx, line in enumerate(lines):
            cols = line.split('\t') 
            try:
                if target_type == 'adit' and len(cols) >= 2:
                    name, station = cols[0].strip(), float(cols[1].strip())
                    time = float(cols[2].strip()) if len(cols) >= 3 and cols[2].strip() else 0.0
                    if self.db.add_adit(self.current_project_id, name, station, time)[0]: success_count += 1
                        
                elif target_type == 'segment' and len(cols) >= 3:
                    st_start, st_end, rock = float(cols[0].strip()), float(cols[1].strip()), cols[2].strip()
                    if self.db.add_segment(self.current_project_id, st_start, st_end, rock)[0]: success_count += 1
                        
                elif target_type == 'speed' and len(cols) >= 2:
                    rock, speed = cols[0].strip(), float(cols[1].strip())
                    if self.db.add_speed_config(self.current_project_id, rock, speed)[0]: success_count += 1
            except ValueError:
                error_count += 1
                
        self.refresh_all_tabs()
        QMessageBox.information(self, "导入结果", f"成功导入 {success_count} 条。\n跳过 {error_count} 行无效数据。")


class ProjectSelectDialog(QDialog):
    def __init__(self, projects_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("载入历史项目")
        self.resize(600, 400)
        self.projects_data = projects_data
        self.selected_data = None
        
        layout = QVBoxLayout(self)
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["项目ID", "项目名称", "起点桩号", "终点桩号"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        
        self.table.setRowCount(len(self.projects_data))
        for row, proj in enumerate(self.projects_data):
            for col in range(4): self.table.setItem(row, col, QTableWidgetItem(str(proj[col])))
        layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        self.btn_load = QPushButton("确定载入")
        self.btn_load.clicked.connect(self.on_load_clicked)
        layout.addLayout(btn_layout)
        btn_layout.addWidget(self.btn_load)
        self.table.itemDoubleClicked.connect(self.on_load_clicked)

    def on_load_clicked(self):
        items = self.table.selectedItems()
        if items:
            self.selected_data = self.projects_data[items[0].row()]
            # 【终极修复】：通过手动关闭窗口防止僵死
            self.close() 

    def get_selected_project(self):
        return self.selected_data