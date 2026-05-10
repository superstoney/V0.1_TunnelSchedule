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

    def get_all_projects(self):
        """获取所有历史项目列表"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('SELECT id, project_name, start_station, end_station FROM projects ORDER BY id DESC')
            return cursor.fetchall()
        except Exception as e:
            print(f"查询历史项目失败: {e}")
            return []
        finally:
            conn.close()

    def update_project(self, project_id, project_name, start_station, end_station):
        """更新已存在的项目信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                UPDATE projects 
                SET project_name=?, start_station=?, end_station=? 
                WHERE id=?
            ''', (project_name, start_station, end_station, project_id))
            conn.commit()
            return True, "项目信息更新成功！"
        except Exception as e:
            conn.rollback()
            return False, f"更新失败: {str(e)}"
        finally:
            conn.close()

    # ================= Tab 2：支洞与地质分段数据操作 =================

    def add_adit(self, project_id, adit_name, intersection_station, available_time=0.0):
        """添加单条支洞信息（包含进洞时间）"""
        conn = self.get_connection()
        try:
            conn.cursor().execute('''
                INSERT INTO adits (project_id, adit_name, intersection_station, available_time)
                VALUES (?, ?, ?, ?)
            ''', (project_id, adit_name, intersection_station, available_time))
            conn.commit()
            return True, "支洞添加成功！"
        except Exception as e:
            conn.rollback()
            return False, f"添加失败: {str(e)}"
        finally:
            conn.close()

    def get_adits(self, project_id):
        """获取当前项目的所有支洞（包含进洞时间）"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, adit_name, intersection_station, available_time FROM adits WHERE project_id=? ORDER BY intersection_station ASC', (project_id,))
            return cursor.fetchall()
        except Exception as e:
            raise Exception(f"查询支洞失败: {str(e)}") # 【修改】：不要 return []，直接抛出异常
        finally:
            conn.close()

    def add_segment(self, project_id, start_station, end_station, rock_type):
        """添加单条地质分段信息"""
        conn = self.get_connection()
        try:
            conn.cursor().execute('''
                INSERT INTO geological_segments (project_id, start_station, end_station, rock_type)
                VALUES (?, ?, ?, ?)
            ''', (project_id, start_station, end_station, rock_type))
            conn.commit()
            return True, "地质分段添加成功！"
        except Exception as e:
            conn.rollback()
            return False, f"添加失败: {str(e)}"
        finally:
            conn.close()

    def get_segments(self, project_id):
        """获取当前项目的所有地质分段"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, start_station, end_station, rock_type FROM geological_segments WHERE project_id=? ORDER BY start_station ASC', (project_id,))
            return cursor.fetchall()
        except Exception as e:
            raise Exception(f"查询地质分段失败: {str(e)}") # 【修改】：直接抛出异常
        finally:
            conn.close()
            
    # ================= Tab 3：开挖策略与工效数据操作 =================

    def add_speed_config(self, project_id, rock_type, speed, method="开挖"):
        """添加围岩工效配置（支持覆盖更新）"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            # 检查是否已存在同类围岩
            cursor.execute("SELECT id FROM speed_configs WHERE rock_type=? AND method=?", (rock_type, method))
            row = cursor.fetchone()
            if row:
                cursor.execute("UPDATE speed_configs SET speed=? WHERE id=?", (speed, row[0]))
            else:
                cursor.execute("INSERT INTO speed_configs (rock_type, method, speed) VALUES (?, ?, ?)", (rock_type, method, speed))
            conn.commit()
            return True, "工效添加成功！"
        except Exception as e:
            conn.rollback()
            return False, f"添加失败: {str(e)}"
        finally:
            conn.close()

    def get_speed_configs(self):
        """获取所有工效配置"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT rock_type, speed FROM speed_configs WHERE method='开挖' ORDER BY rock_type")
            return cursor.fetchall()
        except Exception as e:
            raise Exception(f"查询工效失败: {str(e)}")
        finally:
            conn.close()
# 测试用
if __name__ == "__main__":
    db = DatabaseManager()
    db.init_database()