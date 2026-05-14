import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, 
                               QPushButton, QTabWidget, QFormLayout, QLineEdit, 
                               QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy,
                               QDialog, QTableWidget, QTableWidgetItem, QHeaderView, 
                               QAbstractItemView, QSplitter, QGroupBox, QComboBox, QFileDialog, QTextBrowser)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush  

import os
# 修正路径引入，确保单独运行也可加载模块
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

import matplotlib
matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False 

from database.db_manager import DatabaseManager
from core.calculator import ExcavationCalculator, LiningCalculator, normalize_rock

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TunnelSchedule V1.0 - 隧洞施工进度计算系统")
        self.resize(1200, 800)
        
        self.db = DatabaseManager() 
        self.current_project_id = None 

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        self.title_label = QLabel("TunnelSchedule V1.0")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2C3E50;")
        self.layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("水利工程长隧洞施工进度辅助设计系统")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #7F8C8D; font-style: italic; margin-bottom: 10px;")
        self.layout.addWidget(self.subtitle_label)

        self.tabs = QTabWidget()
        self.tab_project_info = QWidget()
        self.tab_data_entry = QWidget() 
        self.tab_strategy = QWidget() 
        self.tab_lining = QWidget()
        self.tab_results = QWidget() 
        
        self.tabs.addTab(self.tab_project_info, "1. 项目基础信息")
        self.tabs.addTab(self.tab_data_entry, "2. 施工通道与工作面")
        self.tabs.addTab(self.tab_strategy, "3. 开挖策略与计算") 
        self.tabs.addTab(self.tab_lining, "4. 衬砌策略与计算")  # 【修改名】
        self.tabs.addTab(self.tab_results, "5. 成果展示导出")
        
        self.layout.addWidget(self.tabs)
        
        self.init_tab_project_info()
        self.init_tab_data_entry() 
        self.init_tab_strategy() 
        self.init_tab_lining()
        self.init_tab_results()
        
        self.statusBar().showMessage("系统就绪 | 数据库连接正常 | 当前未载入项目")
        for i in range(1, 5): self.tabs.setTabEnabled(i, False)

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
        self.btn_load_project.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_load_project.clicked.connect(self.open_project_dialog)
        
        self.btn_save_project = QPushButton("保存项目信息")
        self.btn_save_project.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_save_project.clicked.connect(self.save_project) 

        self.btn_del_project = QPushButton("🗑️ 删除当前项目")
        self.btn_del_project.setStyleSheet("background-color: #F44336; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_del_project.setEnabled(False)
        self.btn_del_project.clicked.connect(self.delete_project)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_load_project)
        btn_layout.addWidget(self.btn_save_project)
        btn_layout.addWidget(self.btn_del_project)
        btn_layout.addStretch()
        layout.addLayout(btn_layout); layout.addStretch()

    def open_project_dialog(self):
        projects = self.db.get_all_projects()
        if not projects: return QMessageBox.information(self, "提示", "数据库无历史项目。")
        dialog = ProjectSelectDialog(projects, self); dialog.exec() 
        selected = dialog.get_selected_project()
        if selected:
            try:
                self.current_project_id = selected[0]
                self.input_project_name.setText(str(selected[1]))
                self.input_start_station.setText(str(selected[2]))
                self.input_end_station.setText(str(selected[3]))
                self.btn_del_project.setEnabled(True)
                self.statusBar().showMessage(f"已载入项目：{selected[1]}")
                for i in range(1, 5): self.tabs.setTabEnabled(i, True)
                self.refresh_all_tabs()
            except Exception as e: QMessageBox.critical(self, "错误", f"载入异常：\n{str(e)}")

    def save_project(self):
        name, start_str, end_str = self.input_project_name.text().strip(), self.input_start_station.text().strip(), self.input_end_station.text().strip()
        if not name or not start_str or not end_str: return
        try: start_st, end_st = float(start_str), float(end_str)
        except: return
        if self.current_project_id is None:
            success, msg = self.db.add_project(name, start_st, end_st)
            if success:
                latest = self.db.get_all_projects()
                if latest: self.current_project_id = latest[0][0] 
        else: success, msg = self.db.update_project(self.current_project_id, name, start_st, end_st)
        if success:
            QMessageBox.information(self, "成功", msg)
            self.btn_del_project.setEnabled(True)
            for i in range(1, 5): self.tabs.setTabEnabled(i, True)
            self.refresh_all_tabs()

    def delete_project(self):
        if not self.current_project_id: return
        if QMessageBox.warning(self, "警告", "确定删除项目及排期？", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            success, msg = self.db.delete_project(self.current_project_id)
            if success:
                self.current_project_id = None; self.input_project_name.clear(); self.input_start_station.clear(); self.input_end_station.clear()
                self.btn_del_project.setEnabled(False)
                for i in range(1, 5): self.tabs.setTabEnabled(i, False)
                self.refresh_all_tabs(); QMessageBox.information(self, "已删除", msg)

    # ================== Tab 2：通道与工作面划分 ==================
    def init_tab_data_entry(self):
        layout = QVBoxLayout(self.tab_data_entry); splitter = QSplitter(Qt.Vertical)
        group_adit = QGroupBox("1. 施工通道配置"); layout_adit = QVBoxLayout(group_adit)
        tl_adit = QHBoxLayout(); btn_add_adit = QPushButton("➕ 添加行"); btn_add_adit.clicked.connect(lambda: self.add_ui_row_adit())
        btn_del_adit = QPushButton("❌ 删除行"); btn_del_adit.clicked.connect(lambda: self.del_ui_row(self.table_adits))
        btn_paste_adit = QPushButton("📋 从 Excel 粘贴"); btn_paste_adit.clicked.connect(lambda: self.paste_from_excel('adit'))
        btn_save_adit = QPushButton("💾 验证并保存通道"); btn_save_adit.setStyleSheet("background-color: #2196F3; color: white;")
        btn_save_adit.clicked.connect(self.save_adits_to_db)
        for b in [btn_add_adit, btn_del_adit, btn_paste_adit, btn_save_adit]: tl_adit.addWidget(b)
        tl_adit.addStretch(); layout_adit.addLayout(tl_adit)
        
        self.table_adits = QTableWidget(); self.table_adits.setColumnCount(4)
        # 【修改】支洞名称 -> 施工通道名称
        self.table_adits.setHorizontalHeaderLabels(["数据库ID", "施工通道名称", "与主洞交叉桩号", "进洞时间(月)"])
        self.table_adits.setColumnHidden(0, True); self.table_adits.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_adit.addWidget(self.table_adits); splitter.addWidget(group_adit)
        
        group_seg = QGroupBox("2. 隧洞地质分段配置"); layout_seg = QVBoxLayout(group_seg)
        tl_seg = QHBoxLayout(); btn_add_seg = QPushButton("➕ 添加行"); btn_add_seg.clicked.connect(lambda: self.add_ui_row_segment())
        btn_del_seg = QPushButton("❌ 删除行"); btn_del_seg.clicked.connect(lambda: self.del_ui_row(self.table_segments))
        btn_paste_seg = QPushButton("📋 从 Excel 粘贴"); btn_paste_seg.clicked.connect(lambda: self.paste_from_excel('segment'))
        btn_save_seg = QPushButton("💾 验证并保存地质分段"); btn_save_seg.setStyleSheet("background-color: #2196F3; color: white;")
        btn_save_seg.clicked.connect(self.save_segments_to_db)
        for b in [btn_add_seg, btn_del_seg, btn_paste_seg, btn_save_seg]: tl_seg.addWidget(b)
        tl_seg.addStretch(); layout_seg.addLayout(tl_seg)
        
        self.table_segments = QTableWidget(); self.table_segments.setColumnCount(4)
        self.table_segments.setHorizontalHeaderLabels(["数据库ID", "起点桩号", "终点桩号", "围岩类别"])
        self.table_segments.setColumnHidden(0, True); self.table_segments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_seg.addWidget(self.table_segments); splitter.addWidget(group_seg)
        layout.addWidget(splitter)

    def add_ui_row_adit(self, name="", station="", time=""):
        r = self.table_adits.rowCount(); self.table_adits.insertRow(r)
        self.table_adits.setItem(r, 1, QTableWidgetItem(str(name)))
        self.table_adits.setItem(r, 2, QTableWidgetItem(str(station)))
        self.table_adits.setItem(r, 3, QTableWidgetItem(str(time)))

    def add_ui_row_segment(self, start="", end="", rock=""):
        r = self.table_segments.rowCount(); self.table_segments.insertRow(r)
        self.table_segments.setItem(r, 1, QTableWidgetItem(str(start)))
        self.table_segments.setItem(r, 2, QTableWidgetItem(str(end)))
        combo = QComboBox(); combo.setEditable(True); combo.addItems(["III", "IV", "V", "II", "I"])
        if rock: combo.setCurrentText(str(rock))
        self.table_segments.setCellWidget(r, 3, combo)

    def del_ui_row(self, table_widget):
        rows = set(item.row() for item in table_widget.selectedItems())
        for r in sorted(rows, reverse=True): table_widget.removeRow(r)

    def save_adits_to_db(self):
        if not self.current_project_id: return
        data = []
        for r in range(self.table_adits.rowCount()):
            name = self.table_adits.item(r, 1).text().strip() if self.table_adits.item(r, 1) else ""
            st = self.table_adits.item(r, 2).text().strip() if self.table_adits.item(r, 2) else ""
            tm = self.table_adits.item(r, 3).text().strip() if self.table_adits.item(r, 3) else "0"
            if not name: return QMessageBox.warning(self, "错误", f"第{r+1}行名称为空")
            try: data.append({'name': name, 'station': float(st), 'time': float(tm)})
            except: return QMessageBox.warning(self, "错误", f"第{r+1}行桩号格式错误")
        
        # 【新增逻辑】：按桩号强制排序
        if data: data.sort(key=lambda x: x['station'])

        success, msg = self.db.save_adits_batch(self.current_project_id, data)
        if success: 
            # 【流转引导提示】
            QMessageBox.information(self, "保存成功", "施工通道已按桩号自动排序并保存。\n\n【提示】：基础数据变更，请依次前往 Tab 3、Tab 4 更新策略并重新启动计算！")
            self.refresh_tab2_data()

    def save_segments_to_db(self):
        if not self.current_project_id: return
        data = []
        for r in range(self.table_segments.rowCount()):
            st = self.table_segments.item(r, 1).text().strip() if self.table_segments.item(r, 1) else ""
            ed = self.table_segments.item(r, 2).text().strip() if self.table_segments.item(r, 2) else ""
            combo = self.table_segments.cellWidget(r, 3); rock = combo.currentText().strip() if combo else ""
            if not st and not ed and not rock: continue
            if not st or not ed or not rock: return QMessageBox.warning(self, "错误", f"第{r+1}行不完整！")
            try: data.append({'start': float(st), 'end': float(ed), 'rock': rock, 's': min(float(st), float(ed)), 'e': max(float(st), float(ed))})
            except: return QMessageBox.warning(self, "错误", f"第{r+1}行桩号错误")

        if data:
            data.sort(key=lambda x: x['s'])
            conn = self.db.get_connection()
            proj = conn.cursor().execute("SELECT start_station, end_station FROM projects WHERE id=?", (self.current_project_id,)).fetchone()
            conn.close()
            if proj:
                p_start, p_end = min(proj[0], proj[1]), max(proj[0], proj[1])
                errors = []
                if abs(data[0]['s'] - p_start) > 0.001: errors.append(f"首段起点不符全局({p_start})")
                if abs(data[-1]['e'] - p_end) > 0.001: errors.append(f"末段终点不符全局({p_end})")
                for i in range(len(data)-1):
                    if abs(data[i]['e'] - data[i+1]['s']) > 0.001: errors.append(f"段落不连续: {data[i]['e']} -> {data[i+1]['s']}")
                if errors: return QMessageBox.warning(self, "阻断", "错误：\n" + "\n".join(errors))

        success, msg = self.db.save_segments_batch(self.current_project_id, data)
        if success: 
            # 【流转引导提示】
            QMessageBox.information(self, "保存成功", "地质分段校验通过并自动排序。\n\n【提示】：请前往 Tab 3 检查缺失的开挖工效，并重新计算排期！")
            self.refresh_tab2_data()

    def refresh_tab2_data(self):
        if not self.current_project_id: return
        self.table_adits.setRowCount(0); self.table_segments.setRowCount(0)
        for r in self.db.get_adits(self.current_project_id): self.add_ui_row_adit(r[1], r[2], r[3])
        for r in self.db.get_segments(self.current_project_id): self.add_ui_row_segment(r[1], r[2], r[3])

    # ================== Tab 3：开挖策略与计算 ==================
    def init_tab_strategy(self):
        layout = QVBoxLayout(self.tab_strategy); splitter = QSplitter(Qt.Vertical)
        group_speed = QGroupBox("1. 围岩开挖工效设置"); layout_speed = QVBoxLayout(group_speed)
        bl = QHBoxLayout()
        for b, f in [("📋 粘贴", lambda: self.paste_from_excel('speed')), ("➕ 添加", self.add_excavate_speed_row), ("➖ 删除", self.delete_excavate_speed_row)]:
            btn = QPushButton(b); btn.clicked.connect(f); bl.addWidget(btn)
        bs = QPushButton("💾 保存工效"); bs.setStyleSheet("background-color: #4CAF50; color: white;"); bs.clicked.connect(self.save_excavate_speed_data); bl.addWidget(bs)
        layout_speed.addLayout(bl)
        
        self.table_speeds = QTableWidget(); self.table_speeds.setColumnCount(2)
        # 【修改名】：进尺速度 -> 月开挖进尺
        self.table_speeds.setHorizontalHeaderLabels(["围岩类别", "月开挖进尺 (m)"])
        self.table_speeds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_speed.addWidget(self.table_speeds); splitter.addWidget(group_speed)

        group_clash = QGroupBox("2. 开挖对向贯通策略"); layout_clash = QVBoxLayout(group_clash)
        self.table_strategy = QTableWidget(); self.table_strategy.setColumnCount(4)
        # 【修改名】：左支洞 -> 左通道
        self.table_strategy.setHorizontalHeaderLabels(["对接区间", "左通道", "右通道", "主导工作面"])
        # 让表格填满
        self.table_strategy.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_clash.addWidget(self.table_strategy)
        
        bc = QPushButton("▶ 启动开挖计算"); bc.setStyleSheet("background-color: #E91E63; color: white; padding: 10px; font-weight: bold;")
        bc.clicked.connect(self.execute_calculation); layout_clash.addWidget(bc)
        splitter.addWidget(group_clash); layout.addWidget(splitter)

    def add_excavate_speed_row(self): self.table_speeds.insertRow(self.table_speeds.rowCount())
    def delete_excavate_speed_row(self):
        for i in sorted(set(it.row() for it in self.table_speeds.selectedItems()), reverse=True): self.table_speeds.removeRow(i)

    def save_excavate_speed_data(self):
        if not self.current_project_id: return
        def clean_rock(r):
            s = str(r).strip().upper()
            for k, v in {'Ⅰ':'I', 'Ⅱ':'II', 'Ⅲ':'III', 'Ⅳ':'IV', 'Ⅴ':'V', 'Ⅵ':'VI'}.items(): s = s.replace(k, v)
            return s
        speed_list, seen = [], set()
        for r in range(self.table_speeds.rowCount()):
            rk = self.table_speeds.item(r, 0).text().strip() if self.table_speeds.item(r, 0) else ""
            sp = self.table_speeds.item(r, 1).text().strip() if self.table_speeds.item(r, 1) else ""
            if not rk and not sp: continue
            if not rk or not sp: return QMessageBox.warning(self, "错误", "不完整")
            try:
                if float(sp) <= 0: raise ValueError
            except: return QMessageBox.warning(self, "错误", "非法速度")
            nr = clean_rock(rk)
            if nr in seen: return QMessageBox.warning(self, "错误", "重复围岩")
            seen.add(nr); speed_list.append((nr, float(sp)))
        if not speed_list: return
        missing = set(clean_rock(s[3]) for s in self.db.get_segments(self.current_project_id) if s[3]) - seen
        if missing: return QMessageBox.warning(self, "阻断", f"缺失围岩：{', '.join(missing)}")
        
        success, msg = self.db.save_all_speed_configs(speed_list, method="开挖")
        if success:
            # 【流转引导提示】
            QMessageBox.information(self, "成功", "开挖工效数据已保存！\n\n【提示】：请点击下方【▶ 启动开挖计算】更新底层排期！")
            self.refresh_tab3_data()

    def refresh_tab3_data(self):
        if not self.current_project_id: return
        self.table_speeds.clearContents(); speeds = self.db.get_speed_configs(method="开挖")
        self.table_speeds.setRowCount(len(speeds))
        for r, row in enumerate(speeds):
            self.table_speeds.setItem(r, 0, QTableWidgetItem(str(row[0]))); self.table_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))
        adits = self.db.get_adits(self.current_project_id)
        self.table_strategy.setRowCount(max(0, len(adits)-1))
        for i in range(len(adits)-1):
            L, R = adits[i][1], adits[i+1][1]
            self.table_strategy.setItem(i, 0, QTableWidgetItem(f"{L} ➜ ⟵ {R}"))
            self.table_strategy.setItem(i, 1, QTableWidgetItem(L)); self.table_strategy.setItem(i, 2, QTableWidgetItem(R))
            cb = QComboBox(); cb.addItems(["-- 默认 --", L, R]); self.table_strategy.setCellWidget(i, 3, cb)

    def execute_calculation(self):
        if not self.current_project_id: return
        smap = {}
        for i in range(self.table_strategy.rowCount()):
            cb = self.table_strategy.cellWidget(i, 3)
            if cb: smap[(self.table_strategy.item(i, 1).text(), self.table_strategy.item(i, 2).text())] = cb.currentText()
        try:
            res = ExcavationCalculator(self.db, self.current_project_id).run_calculation(smap)
            self.db.clear_and_save_work_faces(self.current_project_id, res)
            # 【流转引导提示】
            QMessageBox.information(self, "开挖计算完成", "全线开挖成果已刷新！\n\n【必须操作】：衬砌依赖于开挖成果，请前往 Tab 4 重新点击启动衬砌计算！")
            self.refresh_all_tabs()
        except Exception as e: QMessageBox.critical(self, "错误", str(e))

    # ================== Tab 4：衬砌策略与计算 ==================
    def init_tab_lining(self):
        layout = QVBoxLayout(self.tab_lining); splitter = QSplitter(Qt.Vertical)
        group_speed = QGroupBox("1. 衬砌分段工效"); layout_speed = QVBoxLayout(group_speed)
        bl = QHBoxLayout(); bp = QPushButton("📋 粘贴"); bp.clicked.connect(lambda: self.paste_from_excel('lining_speed'))
        ba = QPushButton("➕ 添加"); ba.clicked.connect(lambda: self.table_lining_speeds.insertRow(self.table_lining_speeds.rowCount()))
        bd = QPushButton("➖ 删除"); bd.clicked.connect(lambda: self.del_ui_row(self.table_lining_speeds))
        bs = QPushButton("💾 保存工效"); bs.setStyleSheet("background-color: #4CAF50; color: white;"); bs.clicked.connect(self.save_lining_speed_data)
        for b in [bp, ba, bd, bs]: bl.addWidget(b)
        layout_speed.addLayout(bl)
        
        self.table_lining_speeds = QTableWidget(); self.table_lining_speeds.setColumnCount(3)
        # 【修改名】：起点 -> 起点桩号，终点 -> 终点桩号，速度 -> 月衬砌进尺 (m)
        self.table_lining_speeds.setHorizontalHeaderLabels(["起点桩号", "终点桩号", "月衬砌进尺 (m)"])
        self.table_lining_speeds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_speed.addWidget(self.table_lining_speeds); splitter.addWidget(group_speed)

        group_strat = QGroupBox("2. 衬砌对接分界"); layout_strat = QVBoxLayout(group_strat)
        self.table_lining_strat = QTableWidget(); self.table_lining_strat.setColumnCount(4)
        # 【修改名】
        self.table_lining_strat.setHorizontalHeaderLabels(["对接区间", "左通道", "右通道", "分界点设定"])
        
        # 【完美解决下拉框文字遮挡】：设置所有列均匀拉伸
        self.table_lining_strat.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout_strat.addWidget(self.table_lining_strat)
        bc = QPushButton("▶ 启动衬砌计算"); bc.setStyleSheet("background-color: #9C27B0; color: white; padding: 10px; font-weight: bold;")
        bc.clicked.connect(self.execute_lining_calculation); layout_strat.addWidget(bc)
        splitter.addWidget(group_strat); layout.addWidget(splitter)

    def save_lining_speed_data(self):
        if not self.current_project_id: return
        data = []
        for r in range(self.table_lining_speeds.rowCount()):
            st = self.table_lining_speeds.item(r, 0).text().strip() if self.table_lining_speeds.item(r, 0) else ""
            ed = self.table_lining_speeds.item(r, 1).text().strip() if self.table_lining_speeds.item(r, 1) else ""
            sp = self.table_lining_speeds.item(r, 2).text().strip() if self.table_lining_speeds.item(r, 2) else ""
            if not st and not ed and not sp: continue
            if not st or not ed or not sp: return QMessageBox.warning(self, "错误", "不完整")
            try: data.append({'start': float(st), 'end': float(ed), 'speed': float(sp)})
            except: return QMessageBox.warning(self, "错误", "数字非法")
            
        success, msg = self.db.save_lining_speeds_batch(self.current_project_id, data)
        if success:
            QMessageBox.information(self, "保存成功", "衬砌分段工效已保存。\n\n【提示】：请点击下方【▶ 启动衬砌计算】以应用最新参数！")
            self.refresh_tab4_data()

    def refresh_tab4_data(self):
        if not self.current_project_id: return
        self.table_lining_speeds.clearContents(); speeds = self.db.get_lining_speeds(self.current_project_id)
        self.table_lining_speeds.setRowCount(len(speeds))
        for r, row in enumerate(speeds):
            self.table_lining_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table_lining_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))
            self.table_lining_speeds.setItem(r, 2, QTableWidgetItem(str(row[2])))
        adits = self.db.get_adits(self.current_project_id)
        self.table_lining_strat.setRowCount(max(0, len(adits)-1))
        for i in range(len(adits)-1):
            L, R = adits[i], adits[i+1]
            self.table_lining_strat.setItem(i,0, QTableWidgetItem(f"{L[1]} ➜ ⟵ {R[1]}"))
            self.table_lining_strat.setItem(i,1, QTableWidgetItem(str(L[2]))); self.table_lining_strat.setItem(i,2, QTableWidgetItem(str(R[2])))
            container = QWidget(); h = QHBoxLayout(container); h.setContentsMargins(0,0,0,0)
            cb = QComboBox(); cb.addItems(["1-物理中点", "2-开挖贯通点", "3-自定义"])
            le = QLineEdit(); le.setEnabled(False); cb.currentIndexChanged.connect(lambda idx, e=le: e.setEnabled(idx == 2))
            h.addWidget(cb); h.addWidget(le); self.table_lining_strat.setCellWidget(i, 3, container)

    def execute_lining_calculation(self):
        if not self.current_project_id: return
        slist = []
        for i in range(self.table_lining_strat.rowCount()):
            c = self.table_lining_strat.cellWidget(i, 3).layout()
            slist.append({'strategy': c.itemAt(0).widget().currentIndex() + 1, 'custom_m': float(c.itemAt(1).widget().text() or 0)})
        try:
            res = LiningCalculator(self.db, self.current_project_id).run_calculation(slist)
            self.db.clear_and_save_work_faces(self.current_project_id, res, method="衬砌")
            # 【流转引导提示】
            QMessageBox.information(self, "衬砌计算完成", "全线排期已全部锁定！\n\n【成功】：请前往 Tab 5 查看完整的施工成果报表与时距图。")
            self.refresh_all_tabs()
        except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def paste_from_excel(self, target_type):
        if not self.current_project_id: return
        text = QApplication.clipboard().text().strip()
        if not text: return
        lines = text.split('\n')
        if target_type == 'adit':
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 2: self.add_ui_row_adit(cols[0], cols[1], cols[2] if len(cols)>2 else "0")
        elif target_type == 'segment':
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 3: self.add_ui_row_segment(cols[0], cols[1], cols[2])
        elif target_type == 'speed':
            data = []
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 2:
                    try: data.append((cols[0].strip(), float(cols[1].strip())))
                    except: continue
            self.db.save_all_speed_configs(data, method="开挖"); self.refresh_all_tabs()
        elif target_type == 'lining_speed':
            data = []
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 3:
                    try: data.append({'start': float(cols[0]), 'end': float(cols[1]), 'speed': float(cols[2])})
                    except: continue
            self.db.save_lining_speeds_batch(self.current_project_id, data); self.refresh_all_tabs()

    def refresh_all_tabs(self):
        self.refresh_tab2_data(); self.refresh_tab3_data(); self.refresh_tab4_data(); self.refresh_tab5_data()

    # ================== Tab 5：成果展示与高级生成 ==================
    def init_tab_results(self):
        layout = QVBoxLayout(self.tab_results)
        self.label_summary = QLabel("【项目全局评估】")
        self.label_summary.setStyleSheet("font-weight: bold; color: #E91E63; font-size: 16px;")
        layout.addWidget(self.label_summary)
        self.result_sub_tabs = QTabWidget(); layout.addWidget(self.result_sub_tabs)
        
        t1 = QWidget(); l1 = QVBoxLayout(t1)
        btn_layout = QHBoxLayout()
        btn_export = QPushButton("💾 导出成果 Excel/CSV")
        btn_export.clicked.connect(self.export_to_excel)
        btn_report = QPushButton("📝 生成进度分析报告")
        btn_report.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_report.clicked.connect(self.generate_report)
        btn_layout.addWidget(btn_export); btn_layout.addWidget(btn_report); btn_layout.addStretch()
        l1.addLayout(btn_layout)
        
        self.table_results = QTableWidget(); self.table_results.setColumnCount(8)
        self.table_results.setHorizontalHeaderLabels(["施工通道", "方向", "工序", "起点桩号", "终点桩号", "开工月", "完工月", "历时"])
        l1.addWidget(self.table_results); self.result_sub_tabs.addTab(t1, "📊 表格数据")
        
        t2 = QWidget(); l2 = QVBoxLayout(t2)
        self.figure = Figure(); self.canvas = FigureCanvas(self.figure)
        l2.addWidget(self.canvas); self.result_sub_tabs.addTab(t2, "📈 进度时距图")

    def refresh_tab5_data(self):
        if not self.current_project_id: return
        data = self.db.get_all_work_faces(self.current_project_id)
        if not data: return
        
        self.table_results.setRowCount(len(data))
        max_e = max_l = 0.0
        
        base_colors = ["#F1F8E9", "#E3F2FD", "#FFF3E0", "#F3E5F5", "#FFEBEE", "#E0F2F1", "#FFF8E1"]
        adit_color_map = {}
        
        for r, row in enumerate(data):
            adit_name, direction, method = row[0], row[1], row[2]
            if method == '开挖': max_e = max(max_e, row[6])
            else: max_l = max(max_l, row[6])
                
            if adit_name not in adit_color_map:
                adit_color_map[adit_name] = base_colors[len(adit_color_map) % len(base_colors)]
            
            b_color = QColor(adit_color_map[adit_name])
            bg_brush = QBrush(b_color.darker(108) if direction == '上游' else b_color)

            for c in range(8):
                val = f"{row[c]:.2f}" if isinstance(row[c], float) else str(row[c])
                item = QTableWidgetItem(val)
                item.setBackground(bg_brush)
                self.table_results.setItem(r, c, item)
                
        self.label_summary.setText(f"全线开挖贯通：第 {max_e:.1f} 月 | 衬砌全线完工：第 {max_l:.1f} 月")
        
        self.figure.clear(); ax = self.figure.add_subplot(111)
        adits = self.db.get_adits(self.current_project_id)
        cmap = plt.get_cmap('tab10')
        line_color_map = {a: cmap(i % 10) for i, a in enumerate(list(adit_color_map.keys()))}
        
        def get_trajectory(m_type, st_start, st_end, t_start):
            t_pts, st_pts = [t_start], [st_start]
            if abs(st_start - st_end) < 0.001: return st_pts, t_pts
            is_fwd = st_end > st_start
            
            intervals = []
            if m_type == '开挖':
                sm = {normalize_rock(r[0]): r[1] for r in self.db.get_speed_configs("开挖")}
                for s in self.db.get_segments(self.current_project_id): intervals.append((min(s[1], s[2]), max(s[1], s[2]), sm.get(normalize_rock(s[3]), 1.0)))
            else:
                for s in self.db.get_lining_speeds(self.current_project_id): intervals.append((min(s[0], s[1]), max(s[0], s[1]), s[2]))
                    
            bounds = set([st_start, st_end])
            for s_min, s_max, _ in intervals:
                if min(st_start, st_end) < s_min < max(st_start, st_end): bounds.add(s_min)
                if min(st_start, st_end) < s_max < max(st_start, st_end): bounds.add(s_max)
                
            bounds = sorted(list(bounds), reverse=not is_fwd)
            curr_t = t_start
            
            for i in range(len(bounds)-1):
                s1, s2 = bounds[i], bounds[i+1]
                mid, sp = (s1 + s2) / 2.0, 1.0
                for s_min, s_max, s_val in intervals:
                    if s_min <= mid <= s_max: sp = s_val; break
                curr_t += (abs(s2 - s1) / sp) if sp > 0 else 0
                st_pts.append(s2); t_pts.append(curr_t)
            return st_pts, t_pts

        conn = self.db.get_connection()
        proj = conn.cursor().execute("SELECT start_station, end_station FROM projects WHERE id=?", (self.current_project_id,)).fetchone()
        conn.close()
        p_start, p_end = (min(proj[0], proj[1]), max(proj[0], proj[1])) if proj else (0, 0)

        excavation_meetings = set()
        lining_boundaries = set()
        global_max_t = 0.0
        global_max_st = 0.0

        for row in data:
            a_name, method, st_s, st_e, t_s, t_e = row[0], row[2], row[3], row[4], row[5], row[6]
            st_pts, t_pts = get_trajectory(method, st_s, st_e, t_s)
            
            if t_e > global_max_t:
                global_max_t = t_e
                global_max_st = st_e
                
            if method == '开挖':
                if abs(st_e - p_start) > 0.01 and abs(st_e - p_end) > 0.01:
                    excavation_meetings.add((round(st_e, 2), round(t_e, 2)))
            elif method == '衬砌':
                if abs(st_s - p_start) > 0.01 and abs(st_s - p_end) > 0.01:
                    lining_boundaries.add((round(st_s, 2), round(t_s, 2)))
            
            label = f"{a_name}-{method}"
            if label in ax.get_legend_handles_labels()[1]: label = ""
            ax.plot(st_pts, t_pts, color=line_color_map[a_name], 
                    ls='-' if method=='开挖' else '--', lw=2.5 if method=='开挖' else 1.5, alpha=0.8, label=label)

        max_time = max(max_e, max_l) if max(max_e, max_l) > 0 else 10
        
        for st, t in excavation_meetings:
            ax.plot(st, t, marker='o', color='#E67E22', markersize=5, zorder=4)
            ax.plot([st, st], [0, t], color='#E67E22', linestyle=':', lw=1.5, alpha=0.6, zorder=2)
        
        for st, t in lining_boundaries:
            ax.plot(st, t, marker='s', color='#8E44AD', markersize=5, zorder=4)
            ax.plot([st, st], [0, t], color='#8E44AD', linestyle=':', lw=1.5, alpha=0.6, zorder=2)

        critical_stations = set(st for st, t in excavation_meetings) | set(st for st, t in lining_boundaries)
        for st in critical_stations:
            ax.text(st, -max_time * 0.015, f"{st:.1f}", color='#34495E', fontsize=9, fontweight='bold',
                    ha='center', va='bottom', zorder=5, 
                    bbox=dict(facecolor='white', edgecolor='none', alpha=0.8, pad=0.5))

        # 【调整五角星及文字位置，彻底解决遮挡】
        # y轴向下增长，将文字放在五角星的下方（数值更大），留足空间
        if global_max_t > 0:
            ax.plot(global_max_st, global_max_t, marker='*', color='red', markersize=14, zorder=6)
            ax.text(global_max_st, global_max_t + max_time * 0.04, f"{global_max_t:.1f}月", 
                    color='red', fontsize=10, fontweight='bold', ha='center', va='top', zorder=6,
                    bbox=dict(facecolor='white', edgecolor='red', alpha=0.9, boxstyle='round,pad=0.4'))

        # 增加 Y 轴底部的留白(15%)，避免红星文字被 X轴切断
        ax.set_ylim(max_time * 1.15, -max_time * 0.12)
        ax.axhline(0, color='black', linewidth=1.2, linestyle='-', zorder=3)

        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        
        for adit in adits:
            a_name, a_st, a_time = adit[1], adit[2], adit[3]
            ax.vlines(x=a_st, ymin=0, ymax=a_time, color='#7f8c8d', linestyle='-', lw=2, alpha=0.8)
            ax.plot(a_st, a_time, 'ko', markersize=5)
            ax.text(a_st, -max_time * 0.07, f"{a_name}", va='center', ha='center', color='#2c3e50', fontsize=11, fontweight='bold')
            
        ax.set_title("隧洞施工进度时距图", fontsize=15, fontweight='bold', pad=35) 
        ax.set_xlabel("主洞桩号 (m)", fontsize=12)
        ax.set_ylabel("施工时间 (月)", fontsize=12)
        ax.grid(True, alpha=0.4, linestyle='--')
        
        handles, labels = ax.get_legend_handles_labels()
        by_label = dict(zip(labels, handles))
        if by_label:
            ax.legend(by_label.values(), by_label.keys(), loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., fontsize=9)
        self.figure.subplots_adjust(left=0.08, right=0.82, top=0.80, bottom=0.08)
        self.canvas.draw()

    # ================== AI 报告生成引擎 ==================
    def generate_report(self):
        if not self.current_project_id: return
        data = self.db.get_all_work_faces(self.current_project_id)
        if not data:
            QMessageBox.warning(self, "警告", "暂无排期数据，请先进行计算！"); return
        
        max_e = max_l = 0.0
        critical_task = None
        adit_summary = {}
        
        for row in data:
            adit = row[0]
            if adit not in adit_summary: adit_summary[adit] = {'ex': 0.0, 'li': 0.0}
            length = abs(row[4] - row[3])
            
            if row[2] == '开挖': 
                adit_summary[adit]['ex'] += length
                max_e = max(max_e, row[6])
            else: 
                adit_summary[adit]['li'] += length
                if row[6] >= max_l:
                    max_l = row[6]
                    critical_task = row

        report = []
        report.append("="*45)
        report.append("  隧洞排期引擎 - 整体施工进度辅助决策报告  ")
        report.append("="*45 + "\n")
        
        report.append("【一】 项目全局关键指标")
        report.append(f"经本次计算排期，全线共设 {len(adit_summary)} 个主攻施工通道节点。")
        report.append(f"➢ 全线【开挖贯通】时间节点预计为：第 {max_e:.2f} 月")
        report.append(f"➢ 全线【衬砌完工】时间节点预计为：第 {max_l:.2f} 月")
        report.append(f"总历时 {max_l:.2f} 个月。\n")
        
        report.append("【二】 各通道施工作业负载穿透分析")
        for adit, stats in adit_summary.items():
            report.append(f" 🔹 [{adit}] 工作区:")
            report.append(f"     - 承担主洞开挖掘进任务总量：{stats['ex']:.2f} m")
            report.append(f"     - 承担主洞二次衬砌任务总量：{stats['li']:.2f} m")
        report.append("\n")
        
        report.append("【三】 直线工期（Critical Path）精准定位")
        if critical_task:
            c_adit, c_dir, c_method, c_start, c_end, c_tend = critical_task[0], critical_task[1], critical_task[2], critical_task[3], critical_task[4], critical_task[6]
            report.append(f"基于多维度工效推演，判定本项目决定整体总工期的最终工作面（直线工期控制段）落在：")
            report.append(f"📍 核心标段：【{c_adit}】 通道往 【{c_dir}】方向的【{c_method}】作业区间。")
            report.append(f"📍 影响范围：主洞桩号 {c_start:.2f} m  至  {c_end:.2f} m。")
            report.append(f"该工作段于第 {c_tend:.2f} 月最终结束，全程不存在任何时间富裕缓冲。")
            report.append(f"\n【调度建议】：")
            report.append(f"该区域施工效率的波动将直接影响移交时间。建议优先保障该通道的资源倾斜、优化出渣动线，并提高衬砌台车的工序衔接紧凑度。")
        
        dlg = QDialog(self)
        dlg.setWindowTitle("进度分析智能评估报告")
        dlg.resize(650, 550)
        ly = QVBoxLayout(dlg)
        
        tb = QTextBrowser()
        tb.setText("\n".join(report))
        tb.setStyleSheet("font-size: 15px; line-height: 1.6; background-color: #F8F9FA; padding: 15px; border-radius: 8px;")
        ly.addWidget(tb)
        
        btn_copy = QPushButton("📋 一键复制报告至剪贴板")
        btn_copy.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px; font-weight: bold; font-size: 14px;")
        btn_copy.clicked.connect(lambda: QApplication.clipboard().setText(tb.toPlainText()) or QMessageBox.information(dlg, "成功", "报告已复制！可直接粘贴至Word。"))
        ly.addWidget(btn_copy)
        dlg.exec()

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出成果", "隧洞排期.xlsx", "Excel 工作簿 (*.xlsx);;CSV 文件 (*.csv)")
        if not path: return
        try:
            headers = [self.table_results.horizontalHeaderItem(i).text() for i in range(8)]
            rows = [[self.table_results.item(r, c).text() for c in range(8)] for r in range(self.table_results.rowCount())]
            df = pd.DataFrame(rows, columns=headers)
            
            if path.endswith('.csv'): df.to_csv(path, index=False, encoding='utf-8-sig')
            else: df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", f"数据已导出。")
        except ModuleNotFoundError as e:
            if 'openpyxl' in str(e):
                QMessageBox.critical(self, "缺少依赖模块", 
                    "导出 Excel 失败：未检测到 openpyxl 模块！\n\n请在 PyCharm 底部 Terminal 终端输入执行：\n"
                    "pip install openpyxl\n\n（或者下拉文件类型，选择 CSV 格式导出）")
        except Exception as e: QMessageBox.critical(self, "失败", str(e))

class ProjectSelectDialog(QDialog):
    def __init__(self, projects_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("项目载入"); self.resize(500, 300)
        self.projects_data = projects_data; self.selected_data = None
        l = QVBoxLayout(self); self.table = QTableWidget()
        self.table.setColumnCount(4); self.table.setHorizontalHeaderLabels(["ID", "名称", "起点", "终点"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows); self.table.setRowCount(len(projects_data))
        for r, p in enumerate(projects_data):
            for c in range(4): self.table.setItem(r, c, QTableWidgetItem(str(p[c])))
        l.addWidget(self.table); self.table.itemDoubleClicked.connect(self.on_load)
    def on_load(self):
        if self.table.selectedItems(): self.selected_data = self.projects_data[self.table.selectedItems()[0].row()]; self.close()
    def get_selected_project(self): return self.selected_data

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())