"""
智能加载器 -- 基于命中图预测预加载

Phase 6 核心模块：
- preload_for_context(context_text) — 根据上下文预加载相关簇
- learn(context_text, used_cluster_ids) — 学习命中关联
- get_hit_rate() — 获取预加载命中率
- 自动调节：命中率<50%时关闭该组合的预加载
"""
import json
import time
from pathlib import Path
from typing import Optional

from .hit_graph import HitGraph
from .topic_extractor import TopicExtractor
from .cluster_loader import ClusterLoader


# 预加载命中率阈值（低于此值关闭预加载）
_HIT_RATE_THRESHOLD = 0.5
# 最小学习次数（低于此次数不计算命中率）
_MIN_LEARNING_COUNT = 5
# 预加载命中统计窗口大小
_STATS_WINDOW = 100


class SmartLoader:
    """智能加载器 -- 基于命中图预测预加载"""

    def __init__(self, hit_graph: HitGraph, cluster_loader: ClusterLoader,
                 persist_path: str = None):
        self.hit_graph = hit_graph
        self.topic_extractor = TopicExtractor()
        self.cluster_loader = cluster_loader
        # 预加载统计
        self._preload_count: int = 0        # 预加载次数
        self._hit_count: int = 0            # 命中次数
        self._preload_history: list[dict] = []  # 最近N次预加载记录
        # 已关闭的预加载组合（话题元组 -> 关闭时间）
        self._disabled_combos: dict[tuple[str, ...], float] = {}
        # C2: 持久化路径
        self._persist_path = persist_path
        if persist_path:
            self._load_disabled_combos()

    def preload_for_context(self, context_text: str, dna_pool: list,
                            id_to_dna: dict, magnetic_engine=None) -> list:
        """
        根据上下文预加载相关簇

        流程：
        1. 提取话题
        2. 查命中图，获取高频关联簇
        3. 按需加载（跳过已加载的）

        Args:
            context_text: 上下文文本
            dna_pool: DNA池
            id_to_dna: ID到DNA的映射
            magnetic_engine: 磁吸引擎

        Returns:
            预加载的DNA列表
        """
        topics = self.topic_extractor.extract_topics(context_text)
        if not topics:
            return []

        # 检查组合是否被禁用
        combo_key = tuple(sorted(topics))
        if combo_key in self._disabled_combos:
            return []

        # 获取预加载簇ID
        preload_cids = self.hit_graph.get_preload_clusters(topics, threshold=_HIT_RATE_THRESHOLD)
        if not preload_cids:
            return []

        # W4: 使用公开API而非访问私有属性
        loaded = []
        if not self.cluster_loader.is_ready():
            return []

        already_loaded = self.cluster_loader.get_loaded_clusters()

        for cid in preload_cids:
            if cid in already_loaded:
                continue
            member_ids = self.cluster_loader.get_cluster_members(cid)
            if member_ids:
                self.cluster_loader.mark_cluster_loaded(cid)
                for did in member_ids:
                    dna = id_to_dna.get(did)
                    if dna and dna.is_alive:
                        loaded.append(dna)

        # 记录预加载事件
        self._record_preload(topics, preload_cids, len(loaded))

        return loaded

    def learn(self, context_text: str, used_cluster_ids: list[int]):
        """
        学习：记录这次的命中关联

        Args:
            context_text: 上下文文本
            used_cluster_ids: 实际使用的簇ID列表
        """
        topics = self.topic_extractor.extract_topics(context_text)
        if not topics or not used_cluster_ids:
            return

        for topic in topics:
            for cid in used_cluster_ids:
                self.hit_graph.record(topic, cid)

        # W3: 不再每次调用都写盘，由 hit_graph 的 dirty flag 控制
        # 保存将在 system.save() 时统一触发

    def get_hit_rate(self) -> float:
        """
        获取预加载命中率

        Returns:
            命中率 (0.0 ~ 1.0)
        """
        if self._preload_count < _MIN_LEARNING_COUNT:
            return 0.0
        return self._hit_count / self._preload_count

    def mark_preload_hit(self, cluster_ids: list[int]):
        """
        标记预加载的簇被实际使用（命中）

        C1修复: 命中计数按事件递增（与 _preload_count 对齐），
        而非按簇数量递增，确保 hit_rate = hit_count / preload_count 在 [0, 1]。

        Args:
            cluster_ids: 被使用的簇ID列表
        """
        if cluster_ids:
            self._hit_count += 1
            # 同步更新最近一次预加载记录的 hit 字段
            if self._preload_history:
                self._preload_history[-1]["hit"] = 1

    def check_and_adjust(self):
        """
        检查命中率并自动调节

        W1修复: 用 hit/preload 比率与阈值比较，而非只检查 hit==0。
        """
        if self._preload_count < _MIN_LEARNING_COUNT:
            return

        hit_rate = self.get_hit_rate()
        if hit_rate >= _HIT_RATE_THRESHOLD:
            return

        # 分析最近的预加载历史，找出低命中率的组合
        recent = self._preload_history[-_STATS_WINDOW:]
        combo_hits: dict[tuple[str, ...], dict] = {}

        for record in recent:
            combo = tuple(sorted(record.get("topics", [])))
            if not combo:
                continue
            if combo not in combo_hits:
                combo_hits[combo] = {"preload": 0, "hit": 0}
            combo_hits[combo]["preload"] += 1
            combo_hits[combo]["hit"] += record.get("hit", 0)

        # W1: 用比率判断，而非只看 hit==0
        now = time.time()
        for combo, stats in combo_hits.items():
            if stats["preload"] >= 3:
                combo_rate = stats["hit"] / stats["preload"]
                if combo_rate < _HIT_RATE_THRESHOLD:
                    self._disabled_combos[combo] = now

        # C2: 禁用组合变更后持久化
        self._save_disabled_combos()

    def enable_combo(self, topics: list[str]):
        """
        重新启用某个被禁用的预加载组合

        Args:
            topics: 话题列表
        """
        combo_key = tuple(sorted(topics))
        self._disabled_combos.pop(combo_key, None)
        # C2: 持久化
        self._save_disabled_combos()

    def get_disabled_combos(self) -> list[dict]:
        """获取被禁用的预加载组合"""
        return [
            {"topics": list(combo), "disabled_at": ts}
            for combo, ts in self._disabled_combos.items()
        ]

    def _record_preload(self, topics: list[str], cluster_ids: list[int], loaded_count: int):
        """记录预加载事件"""
        self._preload_count += 1
        self._preload_history.append({
            "timestamp": time.time(),
            "topics": topics,
            "cluster_ids": cluster_ids,
            "loaded_count": loaded_count,
            "hit": 0,  # 后续通过 mark_preload_hit 更新
        })
        # 限制历史大小
        if len(self._preload_history) > _STATS_WINDOW:
            self._preload_history = self._preload_history[-_STATS_WINDOW:]

        # 自动调节检查
        self.check_and_adjust()

    def _save_disabled_combos(self):
        """C2: 持久化禁用组合"""
        if not self._persist_path:
            return
        data = {
            "version": 1,
            "disabled_combos": [
                {"topics": list(combo), "disabled_at": ts}
                for combo, ts in self._disabled_combos.items()
            ],
        }
        Path(self._persist_path).parent.mkdir(parents=True, exist_ok=True)
        with open(self._persist_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _load_disabled_combos(self):
        """C2: 加载持久化的禁用组合"""
        p = Path(self._persist_path)
        if not p.exists():
            return
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, dict):
                return
            for entry in data.get("disabled_combos", []):
                topics = entry.get("topics", [])
                ts = entry.get("disabled_at", 0)
                if topics:
                    self._disabled_combos[tuple(sorted(topics))] = ts
        except (json.JSONDecodeError, TypeError, KeyError):
            pass

    def stats(self) -> dict:
        """统计信息"""
        return {
            "preload_count": self._preload_count,
            "hit_count": self._hit_count,
            "hit_rate": round(self.get_hit_rate(), 4),
            "disabled_combos": len(self._disabled_combos),
            "hit_graph": self.hit_graph.stats(),
        }
