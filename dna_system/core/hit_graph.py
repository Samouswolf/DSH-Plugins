"""
命中关联图 -- 记录话题与簇的关联关系

Phase 6 核心模块：通过记录"话题→簇ID"的命中次数，
为智能预加载提供数据基础。

持久化到 .dna/strands/hit_graph.json
"""
import json
import time
from pathlib import Path
from typing import Optional


class HitGraph:
    """命中关联图 -- 记录话题与簇的关联"""

    def __init__(self, persist_path: str = None):
        # edges: {(topic, cluster_id): hit_count}
        self.edges: dict[tuple[str, int], int] = {}
        # 话题总命中次数: {topic: total_count}
        self.topic_totals: dict[str, int] = {}
        # W2: 话题索引 {topic: set(cluster_id)} 加速 get_preload_clusters
        self._topic_index: dict[str, set[int]] = {}
        # 元数据
        self.last_updated: float = 0.0
        self.persist_path = persist_path
        # W3: dirty flag，只在有变更时标记
        self._dirty = False
        # 加载已有数据
        if persist_path:
            self._load()

    def record(self, topic: str, cluster_id: int):
        """
        记录一次命中

        Args:
            topic: 话题关键词
            cluster_id: 命中的簇ID
        """
        key = (topic, cluster_id)
        self.edges[key] = self.edges.get(key, 0) + 1
        self.topic_totals[topic] = self.topic_totals.get(topic, 0) + 1
        # W2: 更新话题索引
        if topic not in self._topic_index:
            self._topic_index[topic] = set()
        self._topic_index[topic].add(cluster_id)
        self.last_updated = time.time()
        # W3: 标记脏数据
        self._dirty = True

    def get_preload_clusters(self, topics: list[str], threshold: float = 0.5) -> list[int]:
        """
        根据话题列表，获取应该预加载的簇

        W2优化: 使用 _topic_index 索引，避免遍历所有 edges。

        Args:
            topics: 话题关键词列表
            threshold: 命中率阈值，默认0.5

        Returns:
            应预加载的簇ID列表（按命中率降序）
        """
        if not topics:
            return []

        # W2: 统计每个簇的加权得分（使用索引加速）
        cluster_scores: dict[int, float] = {}
        cluster_counts: dict[int, int] = {}

        for topic in topics:
            topic_total = self.topic_totals.get(topic, 0)
            if topic_total == 0:
                continue
            # W2: 只遍历该话题关联的簇，而非所有 edges
            candidate_cids = self._topic_index.get(topic, set())
            for cid in candidate_cids:
                count = self.edges.get((topic, cid), 0)
                if count > 0:
                    rate = count / topic_total
                    if rate >= threshold:
                        cluster_scores[cid] = cluster_scores.get(cid, 0.0) + rate
                        cluster_counts[cid] = cluster_counts.get(cid, 0) + 1

        # 只返回被多个话题共同推荐的簇（或只有一个话题时直接返回）
        if len(topics) > 1:
            # 至少被一半话题命中
            min_hits = max(1, len(topics) // 2)
            filtered = {cid: score for cid, score in cluster_scores.items()
                        if cluster_counts[cid] >= min_hits}
        else:
            filtered = cluster_scores

        # 按得分降序排列
        sorted_clusters = sorted(filtered.items(), key=lambda x: x[1], reverse=True)
        return [cid for cid, _ in sorted_clusters]

    def get_topic_clusters(self, topic: str, top_n: int = 5) -> list[dict]:
        """
        获取某个话题的高频关联簇

        Args:
            topic: 话题关键词
            top_n: 返回前N个

        Returns:
            [{cluster_id, hit_count, hit_rate}]
        """
        topic_total = self.topic_totals.get(topic, 0)
        if topic_total == 0:
            return []

        results = []
        # W2: 使用索引加速
        candidate_cids = self._topic_index.get(topic, set())
        for cid in candidate_cids:
            count = self.edges.get((topic, cid), 0)
            if count > 0:
                results.append({
                    "cluster_id": cid,
                    "hit_count": count,
                    "hit_rate": round(count / topic_total, 4),
                })

        results.sort(key=lambda x: x["hit_count"], reverse=True)
        return results[:top_n]

    def get_all_topics(self) -> list[str]:
        """获取所有已记录的话题"""
        return sorted(self.topic_totals.keys())

    def prune(self, min_hits: int = 2):
        """
        清理低频边（命中次数 < min_hits 的移除）

        W6修复: prune 后从 edges 重算 topic_totals，避免负值。

        Args:
            min_hits: 最小命中次数
        """
        to_remove = [key for key, count in self.edges.items() if count < min_hits]
        for key in to_remove:
            del self.edges[key]

        # W6: 从 edges 重算 topic_totals 和 _topic_index
        self._rebuild_topic_index()

        self.last_updated = time.time()
        self._dirty = True

    def _rebuild_topic_index(self):
        """W2/W6: 从 edges 重建 topic_totals 和 _topic_index"""
        self.topic_totals.clear()
        self._topic_index.clear()
        for (topic, cid), count in self.edges.items():
            self.topic_totals[topic] = self.topic_totals.get(topic, 0) + count
            if topic not in self._topic_index:
                self._topic_index[topic] = set()
            self._topic_index[topic].add(cid)

    def save(self):
        """持久化到文件（W3: 只在 dirty 时写盘）"""
        if not self.persist_path:
            return
        if not self._dirty:
            return

        data = {
            "version": 1,
            "last_updated": self.last_updated,
            "edges": [
                {"topic": t, "cluster_id": cid, "count": count}
                for (t, cid), count in self.edges.items()
            ],
            "topic_totals": self.topic_totals,
        }

        Path(self.persist_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self.persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        # W3: 写盘后清除 dirty flag
        self._dirty = False

    def force_save(self):
        """强制保存（忽略 dirty flag）"""
        old_dirty = self._dirty
        self._dirty = True
        self.save()
        # force_save 不改变 dirty 状态语义，save() 已清除

    def _load(self):
        """从文件加载"""
        p = Path(self.persist_path)
        if not p.exists():
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return

            self.last_updated = data.get("last_updated", 0.0)
            self.topic_totals = data.get("topic_totals", {})

            # 重建edges
            for edge in data.get("edges", []):
                topic = edge.get("topic", "")
                cid = edge.get("cluster_id", 0)
                count = edge.get("count", 0)
                if topic and count > 0:
                    self.edges[(topic, cid)] = count

            # W2: 重建话题索引
            self._topic_index.clear()
            for (topic, cid) in self.edges:
                if topic not in self._topic_index:
                    self._topic_index[topic] = set()
                self._topic_index[topic].add(cid)
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    def stats(self) -> dict:
        """统计信息"""
        return {
            "total_edges": len(self.edges),
            "total_topics": len(self.topic_totals),
            "total_hits": sum(self.topic_totals.values()),
            "last_updated": self.last_updated,
            "dirty": self._dirty,
        }
