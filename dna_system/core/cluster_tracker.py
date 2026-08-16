"""
簇命中追踪器 -- 记录每次簇命中，支持高频簇识别

Phase 4 辅助模块：为 Phase 6 预测预加载提供数据基础。
"""
import time
import json
from pathlib import Path
from collections import Counter


# 最大记录数
_MAX_LOG_SIZE = 500
# 热簇时间窗口（秒）
_DEFAULT_WINDOW_SECS = 24 * 3600  # 24小时


class ClusterHitTracker:
    """簇命中追踪器"""

    def __init__(self, persist_path: str = None):
        self.hit_log: list[dict] = []  # [{timestamp, cluster_id, context, query}]
        self.persist_path = persist_path
        # 加载已有记录
        if persist_path:
            self._load()

    def record_hit(self, cluster_id: int, context: str = "", query: str = ""):
        """
        记录一次簇命中

        Args:
            cluster_id: 命中的簇ID
            context: 上下文描述
            query: 触发查询文本
        """
        self.hit_log.append({
            "timestamp": time.time(),
            "cluster_id": cluster_id,
            "context": context[:100],
            "query": query[:100],
        })
        # 限制大小
        if len(self.hit_log) > _MAX_LOG_SIZE:
            self.hit_log = self.hit_log[-_MAX_LOG_SIZE:]

    def get_hot_clusters(self, window_secs: int = _DEFAULT_WINDOW_SECS, top_n: int = 5) -> list[dict]:
        """
        获取最近N秒内高频命中簇

        Args:
            window_secs: 时间窗口（秒），默认24小时
            top_n: 返回前N个

        Returns:
            [{cluster_id, hit_count, last_hit}] 按命中次数降序
        """
        cutoff = time.time() - window_secs
        recent = [h for h in self.hit_log if h["timestamp"] >= cutoff]

        counter = Counter()
        last_hit_map = {}
        for h in recent:
            cid = h["cluster_id"]
            counter[cid] += 1
            last_hit_map[cid] = max(last_hit_map.get(cid, 0), h["timestamp"])

        result = []
        for cid, count in counter.most_common(top_n):
            result.append({
                "cluster_id": cid,
                "hit_count": count,
                "last_hit": last_hit_map[cid],
            })
        return result

    def get_cluster_hit_count(self, cluster_id: int, window_secs: int = _DEFAULT_WINDOW_SECS) -> int:
        """获取某个簇在时间窗口内的命中次数"""
        cutoff = time.time() - window_secs
        return sum(1 for h in self.hit_log
                   if h["cluster_id"] == cluster_id and h["timestamp"] >= cutoff)

    def get_recent_hits(self, limit: int = 20) -> list[dict]:
        """获取最近的命中记录"""
        return self.hit_log[-limit:]

    def clear(self):
        """清空记录"""
        self.hit_log.clear()

    def save(self):
        """持久化到文件"""
        if not self.persist_path:
            import warnings
            warnings.warn("ClusterHitTracker.save() called without persist_path, data will not be persisted",
                          stacklevel=2)
            return
        Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(self.hit_log, f, ensure_ascii=False)

    def _load(self):
        """从文件加载"""
        p = Path(self.persist_path)
        if not p.exists():
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                self.hit_log = data[-_MAX_LOG_SIZE:]
        except (json.JSONDecodeError, TypeError):
            self.hit_log = []

    def stats(self) -> dict:
        """统计信息"""
        total = len(self.hit_log)
        if total == 0:
            return {"total_hits": 0, "unique_clusters": 0, "hot_clusters": []}

        unique_cids = set(h["cluster_id"] for h in self.hit_log)
        hot = self.get_hot_clusters(top_n=3)

        return {
            "total_hits": total,
            "unique_clusters": len(unique_cids),
            "hot_clusters": hot,
        }
