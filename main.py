# 程序的唯一启动入口
import sys
from PySide6.QtWidgets import QApplication
from database.db_manager import DatabaseManager
from ui.main_window import MainWindow

def main():
    # 1. 确保数据库已初始化
    db = DatabaseManager()
    db.init_database()

    # 2. 启动 GUI 应用
    app = QApplication(sys.argv)
    
    # 设置应用全局字体 (可选，提升中文显示效果)
    font = app.font()
    #font.setFamily("Microsoft YaHei")
    app.setFont(font)

    # 3. 显示主窗体
    window = MainWindow()
    window.show()

    # 4. 进入事件循环
    sys.exit(app.exec())

if __name__ == "__main__":
    main()