"""
时间索引 —— 按日期/小时分桶，支持时间范围查询

Phase 1: 海马体进化
解决"昨天做了什么"这类时间维度的记忆检索。

v2: 分离timestamps/ids双列表，消除add()中的O(n)列表推导
"""
import time
import bisect
from datetime import datetime, timedelta
from typing import Optional

from .dna import DNA


class TemporalIndex:
    """时间索引：按日期/小时分桶，支持时间范围和情景查询（海马体优化版 v2）"""

    def __init__(self):
        self.by_date: dict[str, list[str]] = {}      # "2026-06-03" -> [dna_ids]
        self.by_hour: dict[str, list[str]] = {}       # "2026-06-03T14" -> [dna_ids]
        self.by_episode: dict[str, list[str]] = {}    # episode_id -> [dna_ids]
        self._dna_map: dict[str, DNA] = {}            # dna_id -> DNA（用于时间过滤）
        # 🧠 v2: 双列表分离，避免每次bisect前O(n)列表推导
        self._sorted_ts: list[float] = []    # 排序时间戳
        self._sorted_ids: list[str] = []     # 对应的DNA ID

    def add(self, dna: DNA) -> None:
        """添加DNA到时间索引"""
        self._dna_map[dna.id] = dna

        dt = datetime.fromtimestamp(dna.created_at)
        date_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%Y-%m-%dT%H")

        if dna.id not in self.by_date.setdefault(date_key, []):
            self.by_date[date_key].append(dna.id)
        if dna.id not in self.by_hour.setdefault(hour_key, []):
            self.by_hour[hour_key].append(dna.id)

        if dna.episode_id:
            if dna.id not in self.by_episode.setdefault(dna.episode_id, []):
                self.by_episode[dna.episode_id].append(dna.id)

        # 🧠 v2: O(log n)二分 + O(n)插入（无需额外列表推导）
        idx = bisect.bisect_left(self._sorted_ts, dna.created_at)
        self._sorted_ts.insert(idx, dna.created_at)
        self._sorted_ids.insert(idx, dna.id)

    def remove(self, dna_id: str) -> None:
        """从索引中移除DNA"""
        dna = self._dna_map.pop(dna_id, None)
        if not dna:
            return

        dt = datetime.fromtimestamp(dna.created_at)
        date_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%Y-%m-%dT%H")

        if date_key in self.by_date and dna_id in self.by_date[date_key]:
            self.by_date[date_key].remove(dna_id)
        if hour_key in self.by_hour and dna_id in self.by_hour[hour_key]:
            self.by_hour[hour_key].remove(dna_id)
        if dna.episode_id and dna.episode_id in self.by_episode:
            if dna_id in self.by_episode[dna.episode_id]:
                self.by_episode[dna.episode_id].remove(dna_id)

        # 🧠 v2: 从双列表中移除
        if dna_id in self._sorted_ids:
            idx = self._sorted_ids.index(dna_id)
            self._sorted_ts.pop(idx)
            self._sorted_ids.pop(idx)

    def rebuild(self, dnas: list[DNA]) -> None:
        """用DNA列表重建整个索引"""
        self.by_date.clear()
        self.by_hour.clear()
        self.by_episode.clear()
        self._dna_map.clear()
        self._sorted_ts.clear()
        self._sorted_ids.clear()
        for dna in dnas:
            self._dna_map[dna.id] = dna
            dt = datetime.fromtimestamp(dna.created_at)
            date_key = dt.strftime("%Y-%m-%d")
            hour_key = dt.strftime("%Y-%m-%dT%H")
            if dna.id not in self.by_date.setdefault(date_key, []):
                self.by_date[date_key].append(dna.id)
            if dna.id not in self.by_hour.setdefault(hour_key, []):
                self.by_hour[hour_key].append(dna.id)
            if dna.episode_id:
                if dna.id not in self.by_episode.setdefault(dna.episode_id, []):
                    self.by_episode[dna.episode_id].append(dna.id)
        # 🧠 v2: 批量排序构建双列表
        sorted_pairs = sorted([(d.created_at, d.id) for d in dnas], key=lambda x: x[0])
        self._sorted_ts = [ts for ts, _ in sorted_pairs]
        self._sorted_ids = [did for _, did in sorted_pairs]

    def query_by_date(self, date_str: str) -> list[str]:
        """查询某天的所有DNA ID"""
        return list(self.by_date.get(date_str, []))

    def query_by_hour(self, hour_key: str) -> list[str]:
        """查询某小时的所有DNA ID（格式: "2026-06-03T14"）"""
        return list(self.by_hour.get(hour_key, []))

    def query_by_range(self, start: datetime, end: datetime) -> list[str]:
        """查询时间范围内的DNA ID（按天遍历）"""
        results = set()
        current = start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = end.replace(hour=23, minute=59, second=59, microsecond=999999)

        while current <= end_date:
            date_key = current.strftime("%Y-%m-%d")
            for dna_id in self.by_date.get(date_key, []):
                dna = self._dna_map.get(dna_id)
                if dna and start.timestamp() <= dna.created_at <= end.timestamp():
                    results.add(dna_id)
            current += timedelta(days=1)

        return list(results)

    def query_recent(self, hours: int = 24) -> list[str]:
        """查询最近N小时的DNA ID（海马体优化：O(log n) 二分查找）"""
        cutoff = time.time() - hours * 3600
        # 🧠 v2: 直接在时间戳列表上二分，无O(n)列表推导
        start_idx = bisect.bisect_right(self._sorted_ts, cutoff)
        return self._sorted_ids[start_idx:]

    def query_by_episode(self, episode_id: str) -> list[str]:
        """查询某个情景下的所有DNA ID"""
        return list(self.by_episode.get(episode_id, []))

    def query_today(self) -> list[str]:
        """查询今天的所有DNA ID"""
        today = datetime.now().strftime("%Y-%m-%d")
        return self.query_by_date(today)

    def get_date_list(self) -> list[str]:
        """获取所有有记录的日期列表（排序）"""
        return sorted(self.by_date.keys())

    def get_hour_list(self, date_str: str = None) -> list[str]:
        """获取某天所有有记录的小时列表"""
        if date_str:
            return sorted([k for k in self.by_hour if k.startswith(date_str)])
        return sorted(self.by_hour.keys())

    def stats(self) -> dict:
        """索引统计信息"""
        return {
            "total_dnas": len(self._dna_map),
            "dates": len(self.by_date),
            "hours": len(self.by_hour),
            "episodes": len(self.by_episode),
        }
