# 文件路径：core/calculator.py

class ExcavationCalculator:
    def __init__(self, db_manager, project_id):
        self.db = db_manager
        self.project_id = project_id

        # 内部缓存
        self.segments = []
        self.speed_map = {}
        self.adits = []
        self.global_start = 0
        self.global_end = 0

    def load_data(self):
        """从数据库加载计算所需的所有基础数据"""
        # 加载项目边界
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT start_station, end_station FROM projects WHERE id=?", (self.project_id,))
        proj = cursor.fetchone()
        self.global_start, self.global_end = proj[0], proj[1]

        # 加载分段与支洞
        self.segments = self.db.get_segments(self.project_id)
        self.adits = self.db.get_adits(self.project_id)

        # 加载速度字典 (RockType -> Speed)
        speeds = self.db.get_speed_configs()
        self.speed_map = {row[0]: row[1] for row in speeds}
        conn.close()

    def _get_dig_time(self, start_st, end_st):
        """计算任意两个桩号之间，纯开挖所需的总时间（月）"""
        if abs(start_st - end_st) < 0.001:
            return 0.0

        direction_start = min(start_st, end_st)
        direction_end = max(start_st, end_st)
        total_time = 0.0

        for seg in self.segments:
            seg_s = min(seg[1], seg[2])
            seg_e = max(seg[1], seg[2])
            rock = seg[3]

            # 计算该地质分段与目标区间的重叠长度
            overlap_s = max(direction_start, seg_s)
            overlap_e = min(direction_end, seg_e)

            if overlap_s < overlap_e:
                dist = overlap_e - overlap_s
                if rock not in self.speed_map or self.speed_map[rock] <= 0:
                    raise ValueError(
                        f"严重错误：找不到围岩类别 '{rock}' 的开挖速度，或速度设置为 0！请在 Tab 3 中补充完整。")
                total_time += dist / self.speed_map[rock]

        return total_time

    def _find_meeting_point(self, adit_L, adit_R, dominant_name):
        """二分法寻找精确的贯通交汇桩号"""
        st_L, t_L = adit_L[2], adit_L[3]
        st_R, t_R = adit_R[2], adit_R[3]

        # 偏移量计算（主导方工期额外延长 1 个月）
        offset = 0.0
        if dominant_name == adit_L[1]:
            offset = 1.0  # 左侧主导，左侧完工时间晚 1 个月
        elif dominant_name == adit_R[1]:
            offset = -1.0  # 右侧主导，右侧完工时间晚 1 个月

        def f(m):
            # 差异方程：左侧到达 M 的绝对时间 - 右侧到达 M 的绝对时间 - 政策偏移量
            time_L = t_L + self._get_dig_time(st_L, m)
            time_R = t_R + self._get_dig_time(st_R, m)
            return time_L - time_R - offset

        # 边界校验 (如果其中一方还没开工，另一方就把整段挖通了的情况)
        if f(st_L) > 0: return st_L  # 右侧单边干完了全部
        if f(st_R) < 0: return st_R  # 左侧单边干完了全部

        # 核心：二分法逼近
        low, high = st_L, st_R
        while high - low > 0.001:  # 精度控制在 1mm
            mid = (low + high) / 2.0
            if f(mid) > 0:
                high = mid
            else:
                low = mid
        return (low + high) / 2.0

    def run_calculation(self, strategy_map):
        """
        执行全局计算
        strategy_map 格式: {(左支洞名, 右支洞名): "主导支洞名"}
        返回: list of dict (包含每个工作面的详细结果)
        """
        self.load_data()
        if not self.adits:
            raise ValueError("没有找到支洞数据，无法进行计算！")

        results = []

        # 1. 计算头部边界 (起点 -> 第一个支洞)
        first_adit = self.adits[0]
        if first_adit[2] > self.global_start + 0.001:
            duration = self._get_dig_time(first_adit[2], self.global_start)
            results.append({
                "adit_id": first_adit[0], "adit_name": first_adit[1], "direction": "上游",
                "calc_start": first_adit[2], "calc_end": self.global_start,
                "duration": duration, "finish_time": first_adit[3] + duration,
                "is_dominant": 0, "buffer_days": 0
            })

        # 2. 计算中部区间 (支洞与支洞之间的对向相遇)
        for i in range(len(self.adits) - 1):
            adit_L = self.adits[i]
            adit_R = self.adits[i + 1]

            # 获取前端配置的主导策略
            dominant = strategy_map.get((adit_L[1], adit_R[1]), "-- 默认相遇点 --")

            # 求解相遇点
            meeting_st = self._find_meeting_point(adit_L, adit_R, dominant)

            # 记录左侧工作面成果 (往下游挖)
            dur_L = self._get_dig_time(adit_L[2], meeting_st)
            buffer_L = 30 if dominant == adit_L[1] else 0
            results.append({
                "adit_id": adit_L[0], "adit_name": adit_L[1], "direction": "下游",
                "calc_start": adit_L[2], "calc_end": meeting_st,
                "duration": dur_L + (buffer_L / 30.0), "finish_time": adit_L[3] + dur_L + (buffer_L / 30.0),
                "is_dominant": 1 if buffer_L > 0 else 0, "buffer_days": buffer_L
            })

            # 记录右侧工作面成果 (往上游挖)
            dur_R = self._get_dig_time(adit_R[2], meeting_st)
            buffer_R = 30 if dominant == adit_R[1] else 0
            results.append({
                "adit_id": adit_R[0], "adit_name": adit_R[1], "direction": "上游",
                "calc_start": adit_R[2], "calc_end": meeting_st,
                "duration": dur_R + (buffer_R / 30.0), "finish_time": adit_R[3] + dur_R + (buffer_R / 30.0),
                "is_dominant": 1 if buffer_R > 0 else 0, "buffer_days": buffer_R
            })

        # 3. 计算尾部边界 (最后一个支洞 -> 终点)
        last_adit = self.adits[-1]
        if last_adit[2] < self.global_end - 0.001:
            duration = self._get_dig_time(last_adit[2], self.global_end)
            results.append({
                "adit_id": last_adit[0], "adit_name": last_adit[1], "direction": "下游",
                "calc_start": last_adit[2], "calc_end": self.global_end,
                "duration": duration, "finish_time": last_adit[3] + duration,
                "is_dominant": 0, "buffer_days": 0
            })

        return results


class LiningCalculator:
    def __init__(self, db_manager, project_id):
        self.db = db_manager
        self.project_id = project_id

        # 加载基础数据
        conn = self.db.get_connection()
        proj = conn.cursor().execute("SELECT start_station, end_station FROM projects WHERE id=?",
                                     (self.project_id,)).fetchone()
        conn.close()
        self.global_start, self.global_end = proj[0], proj[1]

        self.segments = self.db.get_segments(self.project_id)
        self.adits = self.db.get_adits(self.project_id)

        # 加载【衬砌】速度字典
        speeds = self.db.get_speed_configs(method="衬砌")
        self.speed_map = {row[0]: row[1] for row in speeds}

        # 加载开挖结果字典 (用于推导衬砌开工时间和开挖贯通点)
        # 格式: {(支洞名, 方向): (最终到达桩号, 完工时间)}
        ex_data = self.db.get_excavation_results(self.project_id)
        self.ex_dict = {(r[0], r[1]): (r[2], r[3]) for r in ex_data}

    def _get_lining_time(self, start_st, end_st):
        """计算任意两点间纯衬砌的时间"""
        if abs(start_st - end_st) < 0.001: return 0.0
        dir_s, dir_e = min(start_st, end_st), max(start_st, end_st)
        total_time = 0.0

        for seg in self.segments:
            seg_s, seg_e = min(seg[1], seg[2]), max(seg[1], seg[2])
            overlap_s, overlap_e = max(dir_s, seg_s), min(dir_e, seg_e)
            if overlap_s < overlap_e:
                dist = overlap_e - overlap_s
                rock = seg[3]
                if rock not in self.speed_map or self.speed_map[rock] <= 0:
                    raise ValueError(f"缺少围岩 '{rock}' 的【衬砌】进尺速度！请在 Tab 4 配置。")
                total_time += dist / self.speed_map[rock]
        return total_time

    def run_calculation(self, strategy_list):
        """
        执行衬砌计算。
        strategy_list 格式: [{'strategy': 1/2/3, 'custom_m': float_val}, ...] 对应各个区间
        """
        if not self.adits: raise ValueError("没有支洞数据！")
        if not self.ex_dict: raise ValueError("没有找到开挖排期成果！请先在 Tab 3 完成开挖计算。")

        results = []

        # 1. 头部边界 (从起点 -> 第一个支洞)
        adit_first = self.adits[0]
        if adit_first[2] > self.global_start + 0.001:
            ex_res = self.ex_dict.get((adit_first[1], '上游'))
            if not ex_res: raise ValueError(f"缺失 {adit_first[1]} 上游的开挖数据！")

            start_time = ex_res[1]  # 衬砌必须等这段开挖完全结束
            time_cost = self._get_lining_time(self.global_start, adit_first[2])
            results.append({
                "adit_id": adit_first[0], "adit_name": adit_first[1], "direction": "上游",
                "calc_start": self.global_start, "calc_end": adit_first[2],  # 衬砌从远端退回支洞
                "duration": time_cost, "finish_time": start_time + time_cost,
                "is_dominant": 0, "buffer_days": 0, "strategy": 1, "custom_m": None
            })

        # 2. 中部对向区间
        for i in range(len(self.adits) - 1):
            adit_L, adit_R = self.adits[i], self.adits[i + 1]
            st_L, st_R = adit_L[2], adit_R[2]
            strat_data = strategy_list[i]

            # --- 确定衬砌分界点 M ---
            if strat_data['strategy'] == 1:
                M = (st_L + st_R) / 2.0
            elif strat_data['strategy'] == 2:
                ex_L = self.ex_dict.get((adit_L[1], '下游'))
                if not ex_L: raise ValueError(f"缺失 {adit_L[1]} 下游的开挖数据！")
                M = ex_L[0]  # 使用开挖真实的贯通点
            else:
                M = strat_data['custom_m']

            # --- 确定衬砌开工时间 (该区间必须全部挖通) ---
            ex_L = self.ex_dict.get((adit_L[1], '下游'), (0, 0))
            ex_R = self.ex_dict.get((adit_R[1], '上游'), (0, 0))
            start_time = max(ex_L[1], ex_R[1])  # 取两端开挖最晚的完工时间

            # 左侧支洞负责 M -> st_L (倒退)
            time_L = self._get_lining_time(M, st_L)
            results.append({
                "adit_id": adit_L[0], "adit_name": adit_L[1], "direction": "下游",
                "calc_start": M, "calc_end": st_L,
                "duration": time_L, "finish_time": start_time + time_L,
                "is_dominant": 0, "buffer_days": 0, "strategy": strat_data['strategy'], "custom_m": M
            })

            # 右侧支洞负责 M -> st_R (倒退)
            time_R = self._get_lining_time(M, st_R)
            results.append({
                "adit_id": adit_R[0], "adit_name": adit_R[1], "direction": "上游",
                "calc_start": M, "calc_end": st_R,
                "duration": time_R, "finish_time": start_time + time_R,
                "is_dominant": 0, "buffer_days": 0, "strategy": strat_data['strategy'], "custom_m": M
            })

        # 3. 尾部边界 (最后一个支洞 -> 终点)
        adit_last = self.adits[-1]
        if adit_last[2] < self.global_end - 0.001:
            ex_res = self.ex_dict.get((adit_last[1], '下游'))
            if not ex_res: raise ValueError(f"缺失 {adit_last[1]} 下游的开挖数据！")

            start_time = ex_res[1]
            time_cost = self._get_lining_time(self.global_end, adit_last[2])
            results.append({
                "adit_id": adit_last[0], "adit_name": adit_last[1], "direction": "下游",
                "calc_start": self.global_end, "calc_end": adit_last[2],
                "duration": time_cost, "finish_time": start_time + time_cost,
                "is_dominant": 0, "buffer_days": 0, "strategy": 1, "custom_m": None
            })

        return results