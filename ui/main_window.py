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

# 解决 Matplotlib 中文显示方块的问题
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

        self.title_label = QLabel("TunnelSchedule V0.1")
        self.title_label.setStyleSheet("font-size: 28px; font-weight: bold; color: #2C3E50;")
        self.layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("Developer: TONY SHI | 因为自己淋过雨，所以想给别人撑把伞。")
        self.subtitle_label.setStyleSheet("font-size: 14px; color: #7F8C8D; font-style: italic; margin-bottom: 15px;")
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

        self.init_tab_project_info()
        self.init_tab_data_entry()
        self.init_tab_strategy()
        self.init_tab_lining()
        self.init_tab_results()

        self.statusBar().showMessage("系统就绪 | 数据库连接正常 | 当前未载入项目")

        # 初始锁死后面的 Tab
        self.tabs.setTabEnabled(1, False)
        self.tabs.setTabEnabled(2, False)
        self.tabs.setTabEnabled(3, False)
        self.tabs.setTabEnabled(4, False)

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
        self.btn_load_project.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; border-radius: 5px; } QPushButton:hover { background-color: #45A049; }")
        self.btn_load_project.clicked.connect(self.open_project_dialog)

        self.btn_save_project = QPushButton("保存项目信息")
        self.btn_save_project.setMinimumSize(150, 40)
        self.btn_save_project.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; border-radius: 5px; } QPushButton:hover { background-color: #1976D2; }")
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
        dialog.exec()
        selected_proj = dialog.get_selected_project()

        if selected_proj:
            try:
                self.current_project_id = selected_proj[0]
                self.input_project_name.setText(str(selected_proj[1]))
                self.input_start_station.setText(str(selected_proj[2]))
                self.input_end_station.setText(str(selected_proj[3]))
                QApplication.processEvents()

                self.statusBar().showMessage(f"已载入项目：{selected_proj[1]}")

                # 解锁所有 Tab
                for i in range(1, 5): self.tabs.setTabEnabled(i, True)
                self.refresh_all_tabs()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"载入异常：\n{str(e)}")

    def save_project(self):
        name = self.input_project_name.text().strip()
        start_str = self.input_start_station.text().strip()
        end_str = self.input_end_station.text().strip()

        if not name or not start_str or not end_str:
            QMessageBox.warning(self, "输入错误", "请将所有必填项填写完整！")
            return
        try:
            start_station = float(start_str)
            end_station = float(end_str)
        except ValueError:
            QMessageBox.warning(self, "输入错误", "桩号必须是有效的数字！")
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
            for i in range(1, 5): self.tabs.setTabEnabled(i, True)
            self.refresh_all_tabs()
        else:
            QMessageBox.critical(self, "数据库错误", msg)

    # ================== 统一数据刷新中心 ==================
    def refresh_all_tabs(self):
        self.refresh_tab2_data()
        self.refresh_tab3_data()
        self.refresh_tab4_data()
        self.refresh_tab5_data()

    # ================== Tab 2：支洞与分段配置 ==================
    def init_tab_data_entry(self):
        layout = QVBoxLayout(self.tab_data_entry)
        splitter = QSplitter(Qt.Vertical)

        group_adit = QGroupBox("1. 施工支洞配置 (Adits)")
        layout_adit = QVBoxLayout(group_adit)
        btn_paste_adit = QPushButton("📋 从 Excel 复制粘贴 (格式: 名称 | 交叉桩号 | 进洞时间[可选])")
        btn_paste_adit.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        btn_paste_adit.clicked.connect(lambda: self.paste_from_excel('adit'))
        layout_adit.addWidget(btn_paste_adit)

        self.table_adits = QTableWidget()
        self.table_adits.setColumnCount(4)
        self.table_adits.setHorizontalHeaderLabels(["数据库ID", "支洞名称", "交叉桩号", "进洞时间(月)"])
        header_adit = self.table_adits.horizontalHeader()
        header_adit.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_adit.setSectionResizeMode(1, QHeaderView.Stretch)
        header_adit.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_adit.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout_adit.addWidget(self.table_adits)
        splitter.addWidget(group_adit)

        group_seg = QGroupBox("2. 隧洞地质分段配置 (Segments)")
        layout_seg = QVBoxLayout(group_seg)
        btn_paste_seg = QPushButton("📋 从 Excel 复制粘贴 (格式: 起点 | 终点 | 围岩类别)")
        btn_paste_seg.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        btn_paste_seg.clicked.connect(lambda: self.paste_from_excel('segment'))
        layout_seg.addWidget(btn_paste_seg)

        self.table_segments = QTableWidget()
        self.table_segments.setColumnCount(4)
        self.table_segments.setHorizontalHeaderLabels(["数据库ID", "起点桩号", "终点桩号", "围岩类别"])
        header_seg = self.table_segments.horizontalHeader()
        header_seg.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header_seg.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_seg.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_seg.setSectionResizeMode(3, QHeaderView.Stretch)
        layout_seg.addWidget(self.table_segments)
        splitter.addWidget(group_seg)

        layout.addWidget(splitter)

    def refresh_tab2_data(self):
        if not self.current_project_id: return
        try:
            self.table_adits.clearContents()
            self.table_segments.clearContents()

            adits = self.db.get_adits(self.current_project_id)
            self.table_adits.setRowCount(len(adits))
            for r, row in enumerate(adits):
                for c in range(4): self.table_adits.setItem(r, c,
                                                            QTableWidgetItem(str(row[c] if row[c] is not None else "")))

            segments = self.db.get_segments(self.current_project_id)
            self.table_segments.setRowCount(len(segments))
            for r, row in enumerate(segments):
                for c in range(4): self.table_segments.setItem(r, c, QTableWidgetItem(
                    str(row[c] if row[c] is not None else "")))
        except Exception as e:
            QMessageBox.critical(self, "表格刷新失败", f"Tab 2 渲染错误:\n{str(e)}")

    # ================== Tab 3：开挖策略与计算 ==================
    def init_tab_strategy(self):
        layout = QVBoxLayout(self.tab_strategy)
        splitter = QSplitter(Qt.Vertical)

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

        group_clash = QGroupBox("2. 相邻支洞对向开挖贯通策略 (相距15m控制)")
        layout_clash = QVBoxLayout(group_clash)

        self.table_strategy = QTableWidget()
        self.table_strategy.setColumnCount(4)
        self.table_strategy.setHorizontalHeaderLabels(
            ["开挖对向区间", "左侧施工支洞", "右侧施工支洞", "设定主导支洞 (不退让)"])
        header_strat = self.table_strategy.horizontalHeader()
        header_strat.setSectionResizeMode(0, QHeaderView.Stretch)
        header_strat.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header_strat.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header_strat.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout_clash.addWidget(self.table_strategy)

        self.btn_calculate = QPushButton("▶ 启动开挖排期计算")
        self.btn_calculate.setStyleSheet(
            "background-color: #E91E63; color: white; font-size: 16px; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_calculate.clicked.connect(self.execute_calculation)
        layout_clash.addWidget(self.btn_calculate)

        splitter.addWidget(group_clash)
        layout.addWidget(splitter)

    def refresh_tab3_data(self):
        if not self.current_project_id: return
        try:
            self.table_speeds.clearContents()
            speeds = self.db.get_speed_configs()
            self.table_speeds.setRowCount(len(speeds))
            for r, row in enumerate(speeds):
                self.table_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
                self.table_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))

            adits = self.db.get_adits(self.current_project_id)
            if len(adits) < 2:
                self.table_strategy.setRowCount(0)
                return

            self.table_strategy.clearContents()
            self.table_strategy.setRowCount(len(adits) - 1)

            for i in range(len(adits) - 1):
                left_name, right_name = adits[i][1], adits[i + 1][1]
                span_desc = f"{left_name} ➜ ⟵ {right_name}"

                self.table_strategy.setItem(i, 0, QTableWidgetItem(span_desc))
                self.table_strategy.setItem(i, 1, QTableWidgetItem(left_name))
                self.table_strategy.setItem(i, 2, QTableWidgetItem(right_name))

                combo_box = QComboBox()
                combo_box.addItems(["-- 默认相遇点 --", left_name, right_name])
                self.table_strategy.setCellWidget(i, 3, combo_box)
        except Exception as e:
            QMessageBox.critical(self, "表格刷新失败", f"Tab 3 渲染错误:\n{str(e)}")

    def execute_calculation(self):
        if not self.current_project_id: return

        strategy_map = {}
        row_count = self.table_strategy.rowCount()
        for i in range(row_count):
            left_name = self.table_strategy.item(i, 1).text()
            right_name = self.table_strategy.item(i, 2).text()
            combo = self.table_strategy.cellWidget(i, 3)
            if combo: strategy_map[(left_name, right_name)] = combo.currentText()

        try:
            calculator = ExcavationCalculator(self.db, self.current_project_id)
            results = calculator.run_calculation(strategy_map)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "计算中止", f"计算过程中发生错误：\n{str(e)}\n{traceback.format_exc()}")
            return

        success, msg = self.db.clear_and_save_work_faces(self.current_project_id, results)
        if not success:
            QMessageBox.critical(self, "数据库错误", msg)
            return

        report = "【开挖排期计算战报】\n\n"
        max_finish_time = 0.0

        for res in results:
            length = abs(res['calc_end'] - res['calc_start'])
            if res['finish_time'] > max_finish_time: max_finish_time = res['finish_time']

            flag = "★[主导]" if res['is_dominant'] else ""
            report += (f"[{res['adit_name']} - 向{res['direction']}] {flag}\n"
                       f"   负责桩号: {res['calc_start']:.2f} ~ {res['calc_end']:.2f} (长 {length:.2f}m)\n"
                       f"   施工用时: {res['duration']:.2f} 个月 | 贯通节点: 第 {res['finish_time']:.2f} 个月\n"
                       f"----------------------------------------\n")

        report += f"\n🏆 【全线总评估】\n隧洞开挖全线贯通时间为：第 {max_finish_time:.2f} 个月"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("计算完成")
        msg_box.setText("开挖核心网络推演已完成，成果已保存至数据库！")
        msg_box.setDetailedText(report)
        msg_box.setStyleSheet("QTextEdit { min-width: 500px; min-height: 400px; font-family: Consolas, '微软雅黑'; }")
        msg_box.exec()

        # 解锁 4, 5 并刷新全局
        self.tabs.setTabEnabled(3, True)
        self.tabs.setTabEnabled(4, True)
        self.refresh_all_tabs()

    # ================== Tab 4：衬砌策略与排期 ==================
    def init_tab_lining(self):
        layout = QVBoxLayout(self.tab_lining)
        splitter = QSplitter(Qt.Vertical)

        group_speed = QGroupBox("1. 围岩衬砌工效设置")
        layout_speed = QVBoxLayout(group_speed)
        btn_paste = QPushButton("📋 从 Excel 复制粘贴 (格式: 围岩类别 | 进尺速度(m/月))")
        btn_paste.setStyleSheet("background-color: #FF9800; color: white; font-weight: bold; padding: 5px;")
        btn_paste.clicked.connect(lambda: self.paste_from_excel('lining_speed'))
        layout_speed.addWidget(btn_paste)

        self.table_lining_speeds = QTableWidget()
        self.table_lining_speeds.setColumnCount(2)
        self.table_lining_speeds.setHorizontalHeaderLabels(["围岩类别 (如: III)", "衬砌进尺速度 (m/月)"])
        self.table_lining_speeds.horizontalHeader().setStretchLastSection(True)
        layout_speed.addWidget(self.table_lining_speeds)
        splitter.addWidget(group_speed)

        group_strat = QGroupBox("2. 相邻支洞主洞衬砌分界点策略")
        layout_strat = QVBoxLayout(group_strat)
        self.table_lining_strat = QTableWidget()
        self.table_lining_strat.setColumnCount(4)
        self.table_lining_strat.setHorizontalHeaderLabels(
            ["衬砌对接区间", "左支洞桩号", "右支洞桩号", "分界点策略配置"])
        self.table_lining_strat.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_lining_strat.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        layout_strat.addWidget(self.table_lining_strat)

        self.btn_calc_lining = QPushButton("▶ 启动衬砌排期计算")
        self.btn_calc_lining.setStyleSheet(
            "background-color: #9C27B0; color: white; font-size: 16px; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_calc_lining.clicked.connect(self.execute_lining_calculation)
        layout_strat.addWidget(self.btn_calc_lining)

        splitter.addWidget(group_strat)
        layout.addWidget(splitter)

    def refresh_tab4_data(self):
        if not self.current_project_id: return
        try:
            self.table_lining_speeds.clearContents()
            speeds = self.db.get_speed_configs(method="衬砌")
            self.table_lining_speeds.setRowCount(len(speeds))
            for r, row in enumerate(speeds):
                self.table_lining_speeds.setItem(r, 0, QTableWidgetItem(str(row[0])))
                self.table_lining_speeds.setItem(r, 1, QTableWidgetItem(str(row[1])))

            adits = self.db.get_adits(self.current_project_id)
            if len(adits) < 2:
                self.table_lining_strat.setRowCount(0)
                return

            self.table_lining_strat.clearContents()
            self.table_lining_strat.setRowCount(len(adits) - 1)

            for i in range(len(adits) - 1):
                left, right = adits[i], adits[i + 1]
                self.table_lining_strat.setItem(i, 0, QTableWidgetItem(f"{left[1]} ➜ ⟵ {right[1]}"))
                self.table_lining_strat.setItem(i, 1, QTableWidgetItem(str(left[2])))
                self.table_lining_strat.setItem(i, 2, QTableWidgetItem(str(right[2])))

                widget_container = QWidget()
                h_layout = QHBoxLayout(widget_container)
                h_layout.setContentsMargins(0, 0, 0, 0)

                combo = QComboBox()
                combo.addItems(["1-物理中点分界", "2-开挖贯通点分界", "3-自定义桩号分界"])

                line_edit = QLineEdit()
                line_edit.setPlaceholderText("输入具体桩号")
                line_edit.setEnabled(False)

                combo.currentIndexChanged.connect(lambda idx, le=line_edit: le.setEnabled(idx == 2))

                h_layout.addWidget(combo)
                h_layout.addWidget(line_edit)
                self.table_lining_strat.setCellWidget(i, 3, widget_container)

        except Exception as e:
            QMessageBox.critical(self, "错误", f"Tab 4 刷新失败:\n{str(e)}")

    def execute_lining_calculation(self):
        if not self.current_project_id: return

        strategy_list = []
        for i in range(self.table_lining_strat.rowCount()):
            st_L = float(self.table_lining_strat.item(i, 1).text())
            st_R = float(self.table_lining_strat.item(i, 2).text())

            container = self.table_lining_strat.cellWidget(i, 3)
            combo = container.layout().itemAt(0).widget()
            line_edit = container.layout().itemAt(1).widget()

            strat_idx = combo.currentIndex() + 1
            custom_m = None

            if strat_idx == 3:
                try:
                    custom_m = float(line_edit.text().strip())
                    if custom_m <= st_L or custom_m >= st_R:
                        QMessageBox.warning(self, "错误", f"第 {i + 1} 行自定义桩号 {custom_m} 必须在左右支洞之间！")
                        return
                    if (custom_m - st_L) < 100 or (st_R - custom_m) < 100:
                        rep = QMessageBox.question(self, "距离警告",
                                                   f"第 {i + 1} 行的衬砌分界点距离某侧支洞不足 100m！\n是否坚持使用该分界点？",
                                                   QMessageBox.Yes | QMessageBox.No)
                        if rep == QMessageBox.No: return
                except ValueError:
                    QMessageBox.warning(self, "错误", f"第 {i + 1} 行请填入有效的数字桩号！")
                    return

            strategy_list.append({'strategy': strat_idx, 'custom_m': custom_m})

        try:
            calculator = LiningCalculator(self.db, self.current_project_id)
            results = calculator.run_calculation(strategy_list)
        except Exception as e:
            import traceback
            QMessageBox.critical(self, "衬砌计算中止", f"{str(e)}\n{traceback.format_exc()}")
            return

        success, msg = self.db.clear_and_save_work_faces(self.current_project_id, results, method="衬砌")
        if not success:
            QMessageBox.critical(self, "数据库保存失败", msg)
            return

        report = "【衬砌排期计算战报】\n\n"
        max_time = 0.0
        for res in results:
            if res['finish_time'] > max_time: max_time = res['finish_time']
            strat_name = ["物理中点", "开挖贯通点", "自定义桩号"][res['strategy'] - 1]
            report += (f"[{res['adit_name']} - 负责向 {res['direction']} 退打衬砌]\n"
                       f"   分界策略: {strat_name} (起衬桩号: {res['calc_start']:.2f})\n"
                       f"   施工用时: {res['duration']:.2f} 个月 | 完工节点: 第 {res['finish_time']:.2f} 个月\n"
                       f"----------------------------------------\n")
        report += f"\n🏆 【全线总评估】\n隧洞工程全线最终完工时间：第 {max_time:.2f} 个月"

        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("衬砌排期完成")
        msg_box.setText("衬砌网络推演完成，倒退逻辑已生效！")
        msg_box.setDetailedText(report)
        msg_box.setStyleSheet("QTextEdit { min-width: 500px; min-height: 400px; }")
        msg_box.exec()

        # 刷新全局
        self.refresh_all_tabs()

    # ================== Tab 5：成果展示导出 ==================
    def init_tab_results(self):
        layout = QVBoxLayout(self.tab_results)

        self.label_summary = QLabel("【项目全局评估】 暂无数据，请先完成排期计算。")
        self.label_summary.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #E91E63; background-color: #FCE4EC; padding: 10px; border-radius: 5px;")
        layout.addWidget(self.label_summary)

        self.result_sub_tabs = QTabWidget()
        layout.addWidget(self.result_sub_tabs)

        tab_table = QWidget()
        layout_table = QVBoxLayout(tab_table)
        btn_export = QPushButton("💾 将成果表格导出为 Excel")
        btn_export.setStyleSheet(
            "background-color: #009688; color: white; font-size: 14px; font-weight: bold; padding: 8px;")
        btn_export.clicked.connect(self.export_to_excel)
        layout_table.addWidget(btn_export)

        self.table_results = QTableWidget()
        self.table_results.setColumnCount(8)
        self.table_results.setHorizontalHeaderLabels([
            "工作面名称", "方向", "工序", "起点桩号", "终点桩号",
            "开工时间(月)", "完工时间(月)", "施工历时(月)"
        ])
        self.table_results.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout_table.addWidget(self.table_results)
        self.result_sub_tabs.addTab(tab_table, "📊 详细成果表格")

        tab_chart = QWidget()
        layout_chart = QVBoxLayout(tab_chart)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        layout_chart.addWidget(self.canvas)

        btn_refresh_chart = QPushButton("🔄 刷新折线图")
        btn_refresh_chart.clicked.connect(self.refresh_tab5_data)
        layout_chart.addWidget(btn_refresh_chart)

        self.result_sub_tabs.addTab(tab_chart, "📈 施工形象进度图 (时距图)")

    def refresh_tab5_data(self):
        if not self.current_project_id: return
        try:
            data = self.db.get_all_work_faces(self.current_project_id)
            if not data: return

            self.table_results.setRowCount(len(data))
            max_excavate_time = 0.0
            max_lining_time = 0.0

            for r, row in enumerate(data):
                adit, direction, method, st_start, st_end, t_start, t_end, duration, is_dom, buf = row

                self.table_results.setItem(r, 0, QTableWidgetItem(adit))
                self.table_results.setItem(r, 1, QTableWidgetItem(direction))
                self.table_results.setItem(r, 2, QTableWidgetItem(method))
                self.table_results.setItem(r, 3, QTableWidgetItem(f"{st_start:.2f}"))
                self.table_results.setItem(r, 4, QTableWidgetItem(f"{st_end:.2f}"))
                self.table_results.setItem(r, 5, QTableWidgetItem(f"{t_start:.2f}"))
                self.table_results.setItem(r, 6, QTableWidgetItem(f"{t_end:.2f}"))
                self.table_results.setItem(r, 7, QTableWidgetItem(f"{duration:.2f}"))

                if method == '开挖' and t_end > max_excavate_time: max_excavate_time = t_end
                if method == '衬砌' and t_end > max_lining_time: max_lining_time = t_end

            self.label_summary.setText(f"【项目全局评估】 全线开挖贯通时间：第 {max_excavate_time:.2f} 个月 | "
                                       f"全线衬砌完工时间：第 {max_lining_time:.2f} 个月")

            self.figure.clear()
            ax = self.figure.add_subplot(111)

            unique_adits = list(set([row[0] for row in data]))
            colors = plt.cm.get_cmap('tab10', len(unique_adits))
            color_map = {adit: colors(i) for i, adit in enumerate(unique_adits)}

            legend_handles, legend_labels = [], []

            for row in data:
                adit, direction, method, st_start, st_end, t_start, t_end = row[0], row[1], row[2], row[3], row[4], row[
                    5], row[6]

                x_vals = [t_start, t_end]
                y_vals = [st_start, st_end]
                line_style = '-' if method == '开挖' else '--'
                line_width = 2.5 if method == '开挖' else 2.0

                line, = ax.plot(x_vals, y_vals, color=color_map[adit], linestyle=line_style, linewidth=line_width,
                                alpha=0.8)

                label_name = f"{adit} ({method})"
                if label_name not in legend_labels:
                    legend_labels.append(label_name)
                    legend_handles.append(line)

            ax.set_title("隧洞施工形象进度时距图", fontsize=14, fontweight='bold')
            ax.set_xlabel("施工时间 (月)", fontsize=12)
            ax.set_ylabel("隧洞桩号", fontsize=12)
            ax.grid(True, linestyle=':', alpha=0.6)
            ax.legend(legend_handles, legend_labels, loc='center left', bbox_to_anchor=(1, 0.5))
            self.figure.tight_layout()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.critical(self, "生成成果失败", f"渲染图表出错:\n{str(e)}")

    def export_to_excel(self):
        if self.table_results.rowCount() == 0:
            QMessageBox.warning(self, "警告", "表格中没有数据可导出！")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "导出 Excel", "隧洞施工排期成果.xlsx", "Excel Files (*.xlsx)")
        if not file_path: return

        try:
            headers = [self.table_results.horizontalHeaderItem(i).text() for i in
                       range(self.table_results.columnCount())]
            data = []
            for row in range(self.table_results.rowCount()):
                row_data = []
                for col in range(self.table_results.columnCount()):
                    item = self.table_results.item(row, col)
                    text_val = item.text() if item else ""
                    try:
                        row_data.append(float(text_val))
                    except ValueError:
                        row_data.append(text_val)
                data.append(row_data)

            df = pd.DataFrame(data, columns=headers)
            df.to_excel(file_path, index=False)
            QMessageBox.information(self, "导出成功", f"成果已保存至：\n{file_path}")
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"保存出错：\n{str(e)}")

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

                elif target_type in ['speed', 'lining_speed'] and len(cols) >= 2:
                    rock, speed = cols[0].strip(), float(cols[1].strip())
                    method_name = "衬砌" if target_type == 'lining_speed' else "开挖"
                    if self.db.add_speed_config(self.current_project_id, rock, speed, method=method_name)[0]:
                        success_count += 1
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
            self.close()

    def get_selected_project(self):
        return self.selected_data