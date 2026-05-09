# SQLite建表与连接核心类
import sqlite3
import os

class DatabaseManager:
    def __init__(self, db_name="tunnel_schedule_v01.db"):
        # 确保数据库建立在项目根目录下
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(base_dir, db_name)
    
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)

    def init_database(self):
        """初始化数据库，创建所有必要的表"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # 开启外键支持 (SQLite默认关闭)
        cursor.execute("PRAGMA foreign_keys = ON;")

        # 创建 projects 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT NOT NULL,
                start_station REAL NOT NULL,
                end_station REAL NOT NULL,
                base_start_date DATE
            )
        ''')

        # 创建 geological_segments 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS geological_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                start_station REAL NOT NULL,
                end_station REAL NOT NULL,
                rock_type TEXT NOT NULL,
                sort_order INTEGER DEFAULT 0,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        ''')

        # 创建 adits 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER,
                adit_name TEXT NOT NULL,
                intersection_station REAL NOT NULL,
                available_time REAL DEFAULT 0,
                is_virtual INTEGER DEFAULT 0,
                FOREIGN KEY(project_id) REFERENCES projects(id)
            )
        ''')

        # 创建 speed_configs 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS speed_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rock_type TEXT NOT NULL,
                method TEXT NOT NULL,
                speed REAL NOT NULL
            )
        ''')

        # 创建 work_faces 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_faces (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                adit_id INTEGER,
                direction TEXT NOT NULL,
                method TEXT NOT NULL,
                start_time REAL DEFAULT 0,
                is_dominant INTEGER DEFAULT 0,
                buffer_days INTEGER DEFAULT 0,
                lining_strategy INTEGER DEFAULT 1,
                limit_station_override REAL,
                calc_start_station REAL,
                calc_end_station REAL,
                calc_work_duration REAL,
                calc_finish_time REAL,
                FOREIGN KEY(adit_id) REFERENCES adits(id)
            )
        ''')

        conn.commit()
        conn.close()
        print(f"数据库初始化成功: {self.db_path}")
        
    def add_project(self, project_name, start_station, end_station, base_start_date=None):
            """向 projects 表中插入一条新项目数据"""
            conn = self.get_connection()
            cursor = conn.cursor()
            try:
                # 使用参数化查询 (?, ?) 防止 SQL 注入
                cursor.execute('''
                    INSERT INTO projects (project_name, start_station, end_station, base_start_date)
                    VALUES (?, ?, ?, ?)
                ''', (project_name, start_station, end_station, base_start_date))
                conn.commit()
                return True, "项目基础信息保存成功！"
            except Exception as e:
                conn.rollback() # 发生错误时回滚事务
                return False, f"保存失败: {str(e)}"
            finally:
                conn.close()
# 测试用
if __name__ == "__main__":
    db = DatabaseManager()
    db.init_database()