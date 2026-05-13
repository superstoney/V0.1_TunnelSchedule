import sys
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel,
                               QPushButton, QTabWidget, QFormLayout, QLineEdit,
                               QMessageBox, QHBoxLayout, QSpacerItem, QSizePolicy,
                               QDialog, QTableWidget, QTableWidgetItem, QHeaderView,
                               QAbstractItemView, QSplitter, QGroupBox, QComboBox, QFileDialog)
from PySide6.QtCore import Qt

# === 引入 Matplotlib 用于绘制折线图 ===
import matplotlib

matplotlib.use('QtAgg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# 解决中文显示问题
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei']
plt.rcParams['axes.unicode_minus'] = False

from database.db_manager import DatabaseManager
from core.calculator import ExcavationCalculator, LiningCalculator


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

        # 标题栏
        self.title_label = QLabel("TunnelSchedule V0.1")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2C3E50;")
        self.layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("专业水利工程施工进度辅助设计系统")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #7F8C8D; font-style: italic; margin-bottom: 10px;")
        self.layout.addWidget(self.subtitle_label)

        self.tabs = QTabWidget()
        self.tab_project_info = QWidget()
        self.tab_data_entry = QWidget()
        self.tab_strategy = QWidget()
        self.tab_lining = QWidget()
        self.tab_results = QWidget()

        self.tabs.addTab(self.tab_project_info, "1. 项目基础信息")
        self.tabs.addTab(self.tab_data_entry, "2. 支洞与工作面划分")
        self.tabs.addTab(self.tab_strategy, "3. 开挖策略与计算")
        self.tabs.addTab(self.tab_lining, "4. 衬砌策略与排期")
        self.tabs.addTab(self.tab_results, "5. 成果展示导出")

        self.layout.addWidget(self.tabs)

        # 初始化所有Tab页
        self.init_tab_project_info()
        self.init_tab_data_entry()
        self.init_tab_strategy()
        self.init_tab_lining()
        self.init_tab_results()

        self.statusBar().showMessage("系统就绪 | 数据库连接正常 | 当前未载入项目")

        # 初始锁死后面的 Tab
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
        self.btn_load_project.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_load_project.clicked.connect(self.open_project_dialog)

        self.btn_save_project = QPushButton("保存项目信息")
        self.btn_save_project.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_save_project.clicked.connect(self.save_project)

        self.btn_del_project = QPushButton("🗑️ 删除当前项目")
        self.btn_del_project.setStyleSheet(
            "background-color: #F44336; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_del_project.setEnabled(False)
        self.btn_del_project.clicked.connect(self.delete_project)

        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_load_project)
        btn_layout.addWidget(self.btn_save_project)
        btn_layout.addWidget(self.btn_del_project)
        btn_layout.addStretch()

        layout.addLayout(btn_layout)
        layout.addStretch()

    def open_project_dialog(self):
        projects = self.db.get_all_projects()
        if not projects:
            QMessageBox.information(self, "提示", "当前数据库中没有历史项目。")
            return

        dialog = ProjectSelectDialog(projects, self)
        dialog.exec()
        selected_proj = dialog.get_selected_project()

        if selected_proj:
            try:
                self.current_project_id = selected_proj[0]
                self.input_project_name.setText(str(selected_proj[1]))
                self.input_start_station.setText(str(selected_proj[2]))
                self.input_end_station.setText(str(selected_proj[3]))
                self.btn_del_project.setEnabled(True)
                QApplication.processEvents()

                self.statusBar().showMessage(f"已载入项目：{selected_proj[1]}")
                for i in range(1, 5): self.tabs.setTabEnabled(i, True)
                self.refresh_all_tabs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"载入异常：\n{str(e)}")

    def save_project(self):
        name = self.input_project_name.text().strip()
        start_str = self.input_start_station.text().strip()
        end_str = self.input_end_station.text().strip()

        if not name or not start_str or not end_str:
            QMessageBox.warning(self, "错误", "请将所有必填项填写完整！")
            return
        try:
            start_station = float(start_str)
            end_station = float(end_str)
        except ValueError:
            QMessageBox.warning(self, "错误", "桩号必须是数字！")
            return

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
            self.btn_del_project.setEnabled(True)
            for i in range(1, 5): self.tabs.setTabEnabled(i, True)
            self.refresh_all_tabs()

    def delete_project(self):
        if not self.current_project_id: return
        rep = QMessageBox.warning(self, "危险操作", "确定要彻底删除该项目及名下所有支洞、分段和排期成果吗？",
                                  QMessageBox.Yes | QMessageBox.No)
        if rep == QMessageBox.Yes:
            success, msg = self.db.delete_project(self.current_project_id)
            if success:
                self.current_project_id = None
                self.input_project_name.clear()
                self.input_start_station.clear()
                self.input_end_station.clear()
                self.btn_del_project.setEnabled(False)
                for i in range(1, 5): self.tabs.setTabEnabled(i, False)
                self.refresh_all_tabs()
                self.statusBar().showMessage("项目已删除。")
                QMessageBox.information(self, "已删除", msg)
            else:
                QMessageBox.critical(self, "错误", msg)

    # ================== Tab 2：支洞与工作面划分 ==================
    def init_tab_data_entry(self):
        layout = QVBoxLayout(self.tab_data_entry)
        splitter = QSplitter(Qt.Vertical)

        # 支洞管理
        group_adit = QGroupBox("1. 施工支洞配置 (Adits)")
        layout_adit = QVBoxLayout(group_adit)
        tool_layout_adit = QHBoxLayout()
        btn_add_adit = QPushButton("➕ 添加行");
        btn_add_adit.clicked.connect(lambda: self.add_ui_row_adit())
        btn_del_adit = QPushButton("❌ 删除行");
        btn_del_adit.clicked.connect(lambda: self.del_ui_row(self.table_adits))
        btn_paste_adit = QPushButton("📋 从 Excel 粘贴");
        btn_paste_adit.clicked.connect(lambda: self.paste_from_excel('adit'))
        btn_save_adit = QPushButton("💾 验证并保存支洞");
        btn_save_adit.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_save_adit.clicked.connect(self.save_adits_to_db)

        for btn in [btn_add_adit, btn_del_adit, btn_paste_adit, btn_save_adit]: tool_layout_adit.addWidget(btn)
        tool_layout_adit.addStretch()
        layout_adit.addLayout(tool_layout_adit)

        self.table_adits = QTableWidget()
        self.table_adits.setColumnCount(4)
        self.table_adits.setHorizontalHeaderLabels(["数据库ID", "支洞名称", "与主洞交叉桩号", "进洞时间(月)"])
        self.table_adits.setColumnHidden(0, True)
        self.table_adits.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_adit.addWidget(self.table_adits)
        splitter.addWidget(group_adit)

        # 地质分段
        group_seg = QGroupBox("2. 隧洞地质分段配置 (Segments)")
        layout_seg = QVBoxLayout(group_seg)
        tool_layout_seg = QHBoxLayout()
        btn_add_seg = QPushButton("➕ 添加行");
        btn_add_seg.clicked.connect(lambda: self.add_ui_row_segment())
        btn_del_seg = QPushButton("❌ 删除行");
        btn_del_seg.clicked.connect(lambda: self.del_ui_row(self.table_segments))
        btn_paste_seg = QPushButton("📋 从 Excel 粘贴");
        btn_paste_seg.clicked.connect(lambda: self.paste_from_excel('segment'))
        btn_save_seg = QPushButton("💾 验证并保存地质分段");
        btn_save_seg.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold;")
        btn_save_seg.clicked.connect(self.save_segments_to_db)

        for btn in [btn_add_seg, btn_del_seg, btn_paste_seg, btn_save_seg]: tool_layout_seg.addWidget(btn)
        tool_layout_seg.addStretch()
        layout_seg.addLayout(tool_layout_seg)

        self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(4)
        self.table_segments.setHorizontalHeaderLabels(["数据库ID", "起点桩号", "终点桩号", "围岩类别"])
        self.table_segments.setColumnHidden(0, True)
        self.table_segments.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_seg.addWidget(self.table_segments)
        splitter.addWidget(group_seg)

        layout.addWidget(splitter)

    def add_ui_row_adit(self, name="", station="", time=""):
        r = self.table_adits.rowCount()
        self.table_adits.insertRow(r)
        self.table_adits.setItem(r, 1, QTableWidgetItem(str(name)))
        self.table_adits.setItem(r, 2, QTableWidgetItem(str(station)))
        self.table_adits.setItem(r, 3, QTableWidgetItem(str(time)))

    def add_ui_row_segment(self, start="", end="", rock=""):
        r = self.table_segments.rowCount()
        self.table_segments.insertRow(r)
        self.table_segments.setItem(r, 1, QTableWidgetItem(str(start)))
        self.table_segments.setItem(r, 2, QTableWidgetItem(str(end)))
        combo = QComboBox();
        combo.setEditable(True)
        combo.addItems(["III", "IV", "V", "II", "I"])
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
            st_text = self.table_adits.item(r, 2).text().strip() if self.table_adits.item(r, 2) else ""
            tm_text = self.table_adits.item(r, 3).text().strip() if self.table_adits.item(r, 3) else "0"
            if not name: QMessageBox.warning(self, "错误", f"第{r + 1}行名称为空"); return
            try:
                data.append({'name': name, 'station': float(st_text), 'time': float(tm_text)})
            except:
                QMessageBox.warning(self, "错误", f"第{r + 1}行桩号格式错误"); return

        success, msg = self.db.save_adits_batch(self.current_project_id, data)
        if success:
            QMessageBox.information(self, "成功", msg)
        else:
            QMessageBox.critical(self, "失败", msg)

    def save_segments_to_db(self):
        if not self.current_project_id: return
        data = []
        for r in range(self.table_segments.rowCount()):
            st_text = self.table_segments.item(r, 1).text().strip() if self.table_segments.item(r, 1) else ""
            ed_text = self.table_segments.item(r, 2).text().strip() if self.table_segments.item(r, 2) else ""
            combo = self.table_segments.cellWidget(r, 3)
            rock = combo.currentText().strip() if combo else ""
            if not rock: QMessageBox.warning(self, "错误", f"第{r + 1}行围岩为空"); return
            try:
                data.append({'start': float(st_text), 'end': float(ed_text), 'rock': rock})
            except:
                QMessageBox.warning(self, "错误", f"第{r + 1}行桩号格式错误"); return

        # 【新增】：项目起止边界校验功能
        if data:
            conn = self.db.get_connection()
            proj = conn.cursor().execute("SELECT start_station, end_station FROM projects WHERE id=?",
                                         (self.current_project_id,)).fetchone()
            conn.close()
            if proj:
                min_st = min([min(d['start'], d['end']) for d in data])
                max_st = max([max(d['start'], d['end']) for d in data])
                p_start, p_end = min(proj[0], proj[1]), max(proj[0], proj[1])

                if abs(min_st - p_start) > 0.001 or abs(max_st - p_end) > 0.001:
                    rep = QMessageBox.warning(self, "边界不匹配警告",
                                              f"围岩分段的起止桩号与项目全局边界不一致！\n\n项目设置边界: {p_start} ~ {p_end}\n地质分段边界: {min_st} ~ {max_st}\n\n是否坚持保存？",
                                              QMessageBox.Yes | QMessageBox.No)
                    if rep == QMessageBox.No: return

        success, msg = self.db.save_segments_batch(self.current_project_id, data)
        if success:
            QMessageBox.information(self, "成功", msg)
        else:
            QMessageBox.critical(self, "失败", msg)

    def refresh_tab2_data(self):
        if not self.current_project_id: return
        self.table_adits.setRowCount(0);
        self.table_segments.setRowCount(0)
        for row in self.db.get_adits(self.current_project_id): self.add_ui_row_adit(row[1], row[2], row[3])
        for row in self.db.get_segments(self.current_project_id): self.add_ui_row_segment(row[1], row[2], row[3])

    # ================== Tab 3：开挖策略与计算 ==================
    def init_tab_strategy(self):
        layout = QVBoxLayout(self.tab_strategy)
        splitter = QSplitter(Qt.Vertical)

        group_speed = QGroupBox("1. 围岩开挖工效设置 (修改后请务必点击保存)")
        layout_speed = QVBoxLayout(group_speed)
        btn_layout = QHBoxLayout()
        btn_paste = QPushButton("📋 从 Excel 粘贴");
        btn_paste.clicked.connect(lambda: self.paste_from_excel('speed'))
        btn_add = QPushButton("➕ 添加行");
        btn_add.clicked.connect(self.add_excavate_speed_row)
        btn_del = QPushButton("➖ 删除行");
        btn_del.clicked.connect(self.delete_excavate_speed_row)
        btn_save = QPushButton("💾 验证并保存开挖工效");
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_excavate_speed_data)
        for b in [btn_paste, btn_add, btn_del, btn_save]: btn_layout.addWidget(b)
        layout_speed.addLayout(btn_layout)

        self.table_speeds = QTableWidget()
        self.table_speeds.setColumnCount(2)
        self.table_speeds.setHorizontalHeaderLabels(["围岩类别 (如: III)", "进尺速度 (m/月)"])
        self.table_speeds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_speed.addWidget(self.table_speeds)
        splitter.addWidget(group_speed)

        group_clash = QGroupBox("2. 开挖对向贯通策略")
        layout_clash = QVBoxLayout(group_clash)
        self.table_strategy = QTableWidget()
        self.table_strategy.setColumnCount(4)
        self.table_strategy.setHorizontalHeaderLabels(["对接区间", "左支洞", "右支洞", "主导工作面"])
        self.table_strategy.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout_clash.addWidget(self.table_strategy)

        self.btn_calculate = QPushButton("▶ 启动开挖计算")
        self.btn_calculate.setStyleSheet("background-color: #E91E63; color: white; padding: 10px; font-weight: bold;")
        self.btn_calculate.clicked.connect(self.execute_calculation)
        layout_clash.addWidget(self.btn_calculate)

        splitter.addWidget(group_clash)
        layout.addWidget(splitter)

    def add_excavate_speed_row(self):
        self.table_speeds.insertRow(self.table_speeds.rowCount())

    def delete_excavate_speed_row(self):
        for item in sorted(set(i.row() for i in self.table_speeds.selectedItems()), reverse=True):
            self.table_speeds.removeRow(item)

    def save_excavate_speed_data(self):
        """读取表格数据、执行错误检查（防重、防漏）并保存到数据库"""
        if not self.current_project_id:
            QMessageBox.warning(self, "警告", "当前未载入任何项目！")
            return

        def clean_rock(r_str):
            if not r_str: return ""
            s = str(r_str).strip().upper()
            mapping = {'Ⅰ': 'I', 'Ⅱ': 'II', 'Ⅲ': 'III', 'Ⅳ': 'IV', 'Ⅴ': 'V', 'Ⅵ': 'VI'}
            for k, v in mapping.items():
                s = s.replace(k, v)
            return s

        speed_list = []
        seen_rocks = set()

        for r in range(self.table_speeds.rowCount()):
            rock_item = self.table_speeds.item(r, 0)
            speed_item = self.table_speeds.item(r, 1)

            rock_raw = rock_item.text().strip() if rock_item else ""
            speed_str = speed_item.text().strip() if speed_item else ""

            if not rock_raw and not speed_str: continue

            if rock_raw and not speed_str:
                QMessageBox.warning(self, "数据缺失", f"第 {r + 1} 行缺失速度数据，请补充完整！");
                return
            if not rock_raw and speed_str:
                QMessageBox.warning(self, "数据缺失", f"第 {r + 1} 行缺失围岩类别，请补充完整！");
                return

            try:
                speed = float(speed_str)
                if speed <= 0: raise ValueError
            except ValueError:
                QMessageBox.warning(self, "数据错误", f"第 {r + 1} 行的速度 [{speed_str}] 无效，必须大于0！");
                return

            norm_rock = clean_rock(rock_raw)
            if norm_rock in seen_rocks:
                QMessageBox.warning(self, "重复项", f"第 {r + 1} 行的围岩类别 '{rock_raw}' 与前面重复！");
                return
            seen_rocks.add(norm_rock)

            speed_list.append((norm_rock, speed))

        if not speed_list:
            QMessageBox.warning(self, "提示", "没有检测到有效的工效数据需要保存。");
            return

        segments = self.db.get_segments(self.current_project_id)
        required_rocks = set(clean_rock(seg[3]) for seg in segments if seg[3])
        missing_rocks = required_rocks - seen_rocks

        if missing_rocks:
            missing_str = ", ".join(missing_rocks)
            QMessageBox.warning(self, "工效配置不完整 (严重阻断)",
                                f"您在【Tab 2 地质分段】中使用了以下围岩，但在本表格中缺少对应开挖速度：\n\n"
                                f"❌ 缺失类别：[ {missing_str} ]\n\n请补充完整后再保存！")
            return

        success, msg = self.db.save_all_speed_configs(speed_list, method="开挖")
        if success:
            QMessageBox.information(self, "成功", "开挖工效数据已通过校验并成功保存！")
            self.refresh_tab3_data()
        else:
            QMessageBox.critical(self, "错误", msg)

    def refresh_tab3_data(self):
        if not self.current_project_id: return
        self.table_speeds.clearContents()
        speeds = self.db.get_speed_configs(method="开挖")
        self.table_speeds.setRowCount(len(speeds))
        for r, row in enumerate(speeds):
            self.table_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))

        adits = self.db.get_adits(self.current_project_id)
        self.table_strategy.setRowCount(max(0, len(adits) - 1))
        for i in range(len(adits) - 1):
            L, R = adits[i][1], adits[i + 1][1]
            self.table_strategy.setItem(i, 0, QTableWidgetItem(f"{L} ➜ ⟵ {R}"))
            self.table_strategy.setItem(i, 1, QTableWidgetItem(L))
            self.table_strategy.setItem(i, 2, QTableWidgetItem(R))
            cb = QComboBox();
            cb.addItems(["-- 默认 --", L, R])
            self.table_strategy.setCellWidget(i, 3, cb)

    def execute_calculation(self):
        if not self.current_project_id: return
        strategy_map = {}
        for i in range(self.table_strategy.rowCount()):
            L, R = self.table_strategy.item(i, 1).text(), self.table_strategy.item(i, 2).text()
            cb = self.table_strategy.cellWidget(i, 3)
            if cb: strategy_map[(L, R)] = cb.currentText()
        try:
            results = ExcavationCalculator(self.db, self.current_project_id).run_calculation(strategy_map)
            success, msg = self.db.clear_and_save_work_faces(self.current_project_id, results)
            if success: QMessageBox.information(self, "完成", "开挖计算成功！"); self.refresh_all_tabs()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # ================== Tab 4：衬砌策略与排期 ==================
    def init_tab_lining(self):
        layout = QVBoxLayout(self.tab_lining)
        splitter = QSplitter(Qt.Vertical)

        group_speed = QGroupBox("1. 衬砌分段工效设置 (按桩号区间)")
        layout_speed = QVBoxLayout(group_speed)

        btn_layout = QHBoxLayout()
        btn_paste = QPushButton("📋 从 Excel 粘贴 (起|终|速)");
        btn_paste.clicked.connect(lambda: self.paste_from_excel('lining_speed'))
        btn_add = QPushButton("➕ 添加行");
        btn_add.clicked.connect(lambda: self.table_lining_speeds.insertRow(self.table_lining_speeds.rowCount()))
        btn_del = QPushButton("➖ 删除行");
        btn_del.clicked.connect(lambda: self.del_ui_row(self.table_lining_speeds))
        btn_save = QPushButton("💾 验证并保存衬砌工效");
        btn_save.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_save.clicked.connect(self.save_lining_speed_data)

        for b in [btn_paste, btn_add, btn_del, btn_save]: btn_layout.addWidget(b)
        layout_speed.addLayout(btn_layout)

        self.table_lining_speeds = QTableWidget();
        self.table_lining_speeds.setColumnCount(3)
        self.table_lining_speeds.setHorizontalHeaderLabels(["分段起点桩号", "分段终点桩号", "衬砌速度 (m/月)"])
        self.table_lining_speeds.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_speed.addWidget(self.table_lining_speeds)
        splitter.addWidget(group_speed)

        group_strat = QGroupBox("2. 衬砌对接分界策略")
        layout_strat = QVBoxLayout(group_strat)
        self.table_lining_strat = QTableWidget();
        self.table_lining_strat.setColumnCount(4)
        self.table_lining_strat.setHorizontalHeaderLabels(["对接区间", "左桩号", "右桩号", "分界点设定"])
        self.table_lining_strat.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout_strat.addWidget(self.table_lining_strat)

        self.btn_calc_lining = QPushButton("▶ 启动衬砌计算")
        self.btn_calc_lining.setStyleSheet("background-color: #9C27B0; color: white; padding: 10px; font-weight: bold;")
        self.btn_calc_lining.clicked.connect(self.execute_lining_calculation)
        layout_strat.addWidget(self.btn_calc_lining)

        splitter.addWidget(group_strat);
        layout.addWidget(splitter)

    def save_lining_speed_data(self):
        if not self.current_project_id: return
        data = []
        for r in range(self.table_lining_speeds.rowCount()):
            st_text = self.table_lining_speeds.item(r, 0).text().strip() if self.table_lining_speeds.item(r, 0) else ""
            ed_text = self.table_lining_speeds.item(r, 1).text().strip() if self.table_lining_speeds.item(r, 1) else ""
            sp_text = self.table_lining_speeds.item(r, 2).text().strip() if self.table_lining_speeds.item(r, 2) else ""

            if not st_text and not ed_text and not sp_text: continue
            if not st_text or not ed_text or not sp_text:
                QMessageBox.warning(self, "错误", f"第 {r + 1} 行数据不完整！");
                return
            try:
                data.append({'start': float(st_text), 'end': float(ed_text), 'speed': float(sp_text)})
            except:
                QMessageBox.warning(self, "错误", f"第 {r + 1} 行格式有误，必须全为数字！");
                return

        # 【新增】：衬砌分段的项目边界校验
        if data:
            conn = self.db.get_connection()
            proj = conn.cursor().execute("SELECT start_station, end_station FROM projects WHERE id=?",
                                         (self.current_project_id,)).fetchone()
            conn.close()
            if proj:
                min_st = min([min(d['start'], d['end']) for d in data])
                max_st = max([max(d['start'], d['end']) for d in data])
                p_start, p_end = min(proj[0], proj[1]), max(proj[0], proj[1])

                if abs(min_st - p_start) > 0.001 or abs(max_st - p_end) > 0.001:
                    rep = QMessageBox.warning(self, "边界不匹配警告",
                                              f"衬砌分段的起止桩号与项目全局边界不一致！\n\n项目设置边界: {p_start} ~ {p_end}\n当前衬砌边界: {min_st} ~ {max_st}\n\n建议修改。是否坚持保存？",
                                              QMessageBox.Yes | QMessageBox.No)
                    if rep == QMessageBox.No: return

        success, msg = self.db.save_lining_speeds_batch(self.current_project_id, data)
        if success:
            QMessageBox.information(self, "成功", msg); self.refresh_tab4_data()
        else:
            QMessageBox.critical(self, "失败", msg)

    def refresh_tab4_data(self):
        if not self.current_project_id: return
        self.table_lining_speeds.clearContents()
        speeds = self.db.get_lining_speeds(self.current_project_id)
        self.table_lining_speeds.setRowCount(len(speeds))
        for r, row in enumerate(speeds):
            self.table_lining_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
            self.table_lining_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))
            self.table_lining_speeds.setItem(r, 2, QTableWidgetItem(str(row[2])))

        adits = self.db.get_adits(self.current_project_id)
        self.table_lining_strat.setRowCount(max(0, len(adits) - 1))
        for i in range(len(adits) - 1):
            L, R = adits[i], adits[i + 1]
            self.table_lining_strat.setItem(i, 0, QTableWidgetItem(f"{L[1]} ➜ ⟵ {R[1]}"))
            self.table_lining_strat.setItem(i, 1, QTableWidgetItem(str(L[2])))
            self.table_lining_strat.setItem(i, 2, QTableWidgetItem(str(R[2])))
            container = QWidget();
            h = QHBoxLayout(container);
            h.setContentsMargins(0, 0, 0, 0)
            cb = QComboBox();
            cb.addItems(["1-物理中点", "2-开挖贯通点", "3-自定义"])
            le = QLineEdit();
            le.setPlaceholderText("桩号");
            le.setEnabled(False)
            cb.currentIndexChanged.connect(lambda idx, e=le: e.setEnabled(idx == 2))
            h.addWidget(cb);
            h.addWidget(le);
            self.table_lining_strat.setCellWidget(i, 3, container)

    def execute_lining_calculation(self):
        if not self.current_project_id: return
        strategy_list = []
        for i in range(self.table_lining_strat.rowCount()):
            c = self.table_lining_strat.cellWidget(i, 3).layout()
            idx = c.itemAt(0).widget().currentIndex() + 1
            val = c.itemAt(1).widget().text().strip()
            strategy_list.append({'strategy': idx, 'custom_m': float(val) if val else None})
        try:
            res = LiningCalculator(self.db, self.current_project_id).run_calculation(strategy_list)
            self.db.clear_and_save_work_faces(self.current_project_id, res, method="衬砌")
            QMessageBox.information(self, "完成", "衬砌排期完成！");
            self.refresh_all_tabs()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    # ================== 统一粘贴与数据同步 ==================
    def paste_from_excel(self, target_type):
        if not self.current_project_id: return
        text = QApplication.clipboard().text().strip()
        if not text: return
        lines = text.split('\n')

        if target_type == 'adit':
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 2: self.add_ui_row_adit(cols[0], cols[1], cols[2] if len(cols) > 2 else "0")

        elif target_type == 'segment':
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 3: self.add_ui_row_segment(cols[0], cols[1], cols[2])

        elif target_type == 'speed':
            data = []
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 2:
                    try:
                        data.append((cols[0].strip(), float(cols[1].strip())))
                    except:
                        continue
            self.db.save_all_speed_configs(data, method="开挖")
            self.refresh_all_tabs()

        elif target_type == 'lining_speed':
            data = []
            for l in lines:
                cols = l.split('\t')
                if len(cols) >= 3:
                    try:
                        data.append({'start': float(cols[0]), 'end': float(cols[1]), 'speed': float(cols[2])})
                    except:
                        continue
            self.db.save_lining_speeds_batch(self.current_project_id, data)
            self.refresh_all_tabs()

    def refresh_all_tabs(self):
        self.refresh_tab2_data()
        self.refresh_tab3_data()
        self.refresh_tab4_data()
        self.refresh_tab5_data()

    # ================== Tab 5：成果展示 ==================
    def init_tab_results(self):
        layout = QVBoxLayout(self.tab_results)
        self.label_summary = QLabel("【项目全局评估】")
        self.label_summary.setStyleSheet("font-weight: bold; color: #E91E63; font-size: 16px;")
        layout.addWidget(self.label_summary)
        self.result_sub_tabs = QTabWidget();
        layout.addWidget(self.result_sub_tabs)

        t1 = QWidget();
        l1 = QVBoxLayout(t1)
        btn = QPushButton("💾 导出成果 Excel");
        btn.clicked.connect(self.export_to_excel)
        l1.addWidget(btn)
        self.table_results = QTableWidget();
        self.table_results.setColumnCount(8)
        self.table_results.setHorizontalHeaderLabels(["名称", "方向", "工序", "起点", "终点", "开工", "完工", "历时"])
        l1.addWidget(self.table_results);
        self.result_sub_tabs.addTab(t1, "📊 表格数据")

        t2 = QWidget();
        l2 = QVBoxLayout(t2)
        self.figure = Figure();
        self.canvas = FigureCanvas(self.figure)
        l2.addWidget(self.canvas);
        self.result_sub_tabs.addTab(t2, "📈 进度时距图")

    def refresh_tab5_data(self):
        if not self.current_project_id: return
        data = self.db.get_all_work_faces(self.current_project_id)
        if not data: return
        self.table_results.setRowCount(len(data))
        max_e = max_l = 0.0
        for r, row in enumerate(data):
            for c in range(8): self.table_results.setItem(r, c, QTableWidgetItem(
                f"{row[c]:.2f}" if isinstance(row[c], float) else str(row[c])))
            if row[2] == '开挖':
                max_e = max(max_e, row[6])
            else:
                max_l = max(max_l, row[6])
        self.label_summary.setText(f"全线开挖贯通：第 {max_e:.2f} 月 | 衬砌全线完工：第 {max_l:.2f} 月")

        self.figure.clear();
        ax = self.figure.add_subplot(111)
        adits = list(set(r[0] for r in data))
        cmap = plt.get_cmap('tab10')
        color_map = {a: cmap(i % 10) for i, a in enumerate(adits)}
        for row in data:
            ax.plot([row[5], row[6]], [row[3], row[4]], color=color_map[row[0]],
                    ls='-' if row[2] == '开挖' else '--', lw=2 if row[2] == '开挖' else 1.5, alpha=0.7)
        ax.set_title("施工形象进度时距图");
        ax.set_xlabel("时间 (月)");
        ax.set_ylabel("桩号");
        ax.grid(True, alpha=0.3)
        self.canvas.draw()

    def export_to_excel(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出成果", "隧洞排期.xlsx", "Excel (*.xlsx)")
        if path:
            headers = [self.table_results.horizontalHeaderItem(i).text() for i in range(8)]
            rows = [[self.table_results.item(r, c).text() for c in range(8)] for r in
                    range(self.table_results.rowCount())]
            pd.DataFrame(rows, columns=headers).to_excel(path, index=False)
            QMessageBox.information(self, "成功", "已导出至 Excel")


class ProjectSelectDialog(QDialog):
    def __init__(self, projects_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("项目载入");
        self.resize(500, 300)
        self.projects_data = projects_data;
        self.selected_data = None
        l = QVBoxLayout(self);
        self.table = QTableWidget()
        self.table.setColumnCount(4);
        self.table.setHorizontalHeaderLabels(["ID", "名称", "起点", "终点"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows);
        self.table.setRowCount(len(projects_data))
        for r, p in enumerate(projects_data):
            for c in range(4): self.table.setItem(r, c, QTableWidgetItem(str(p[c])))
        l.addWidget(self.table);
        self.table.itemDoubleClicked.connect(self.on_load)

    def on_load(self):
        if self.table.selectedItems(): self.selected_data = self.projects_data[
            self.table.selectedItems()[0].row()]; self.close()

    def get_selected_project(self):
        return self.selected_data


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())