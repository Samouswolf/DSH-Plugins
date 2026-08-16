"""
三级加载策略 -- 记忆按需加载

L0 核心：关键规则、团队流程，启动时必加载 (~20条)
L1 话题：当前游戏相关记忆，用户提到游戏名时加载
L2 深层：具体Bug细节，具体问题触发
"""
import time
from typing import Optional

from .semantic_cluster import SemanticCluster
from .brain_encoder import identify_game


# L0 核心簇的最大记忆数
_L0_MAX_MEMORIES = 30
# L1 话题簇的最大记忆数
_L1_MAX_MEMORIES = 60
# L2 深层簇的最大记忆数
_L2_MAX_MEMORIES = 100
# 单条记忆最大token数（超过则截断或跳过）
_MAX_MEMORY_TOKENS = 2000


class ClusterLoader:
    """三级加载策略管理器"""

    def __init__(self, cluster_engine: Optional[SemanticCluster] = None):
        self.cluster_engine = cluster_engine
        # 已加载的簇ID集合
        self._loaded_clusters: set[int] = set()
        # 加载历史
        self._load_history: list[dict] = []

    def set_cluster_engine(self, engine: SemanticCluster):
        """设置聚类引擎"""
        self.cluster_engine = engine

    def load_l0_core(self, dna_pool: list, id_to_dna: dict) -> list:
        """
        L0 核心加载：启动时必加载

        返回:
            L0 级别的 DNA 列表
        """
        if not self.cluster_engine or not self.cluster_engine._built:
            # 聚类未构建，回退：返回前N条高能量记忆
            sorted_pool = sorted(dna_pool, key=lambda d: d.lifetime, reverse=True)
            return sorted_pool[:_L0_MAX_MEMORIES]

        l0_clusters = self.cluster_engine.get_level_clusters("L0")
        loaded = []

        for cid, member_ids in l0_clusters.items():
            self._loaded_clusters.add(cid)
            for did in member_ids:
                dna = id_to_dna.get(did)
                if dna and dna.is_alive:
                    # 跳过超大记忆（代码文件等）
                    text_len = len(str(dna.content))
                    if text_len > _MAX_MEMORY_TOKENS * 2:  # 粗略估算
                        continue
                    loaded.append(dna)

        # 限制数量
        if len(loaded) > _L0_MAX_MEMORIES:
            loaded.sort(key=lambda d: d.lifetime, reverse=True)
            loaded = loaded[:_L0_MAX_MEMORIES]

        self._record_load("L0", len(loaded), "启动核心加载")
        return loaded

    def load_l1_topic(self, query_text: str, dna_pool: list, id_to_dna: dict,
                      magnetic_engine=None) -> tuple[list, Optional[int]]:
        """
        L1 话题加载：用户提到游戏名时加载

        Args:
            query_text: 用户输入文本
            dna_pool: DNA池
            id_to_dna: ID到DNA的映射
            magnetic_engine: 磁吸引擎（用于向量查询）

        Returns:
            (L1 级别的 DNA 列表, 命中的 cluster_id 或 None)
        """
        if not self.cluster_engine or not self.cluster_engine._built:
            return [], None

        # 识别游戏名
        game = identify_game(query_text)
        loaded = []
        hit_cid = None

        if game:
            # 按游戏名匹配簇
            for cid, meta in self.cluster_engine.cluster_meta.items():
                games = meta.get("games", {})
                if game in games and cid not in self._loaded_clusters:
                    self._loaded_clusters.add(cid)
                    hit_cid = cid
                    member_ids = self.cluster_engine.get_cluster(cid)
                    for did in member_ids:
                        dna = id_to_dna.get(did)
                        if dna and dna.is_alive:
                            loaded.append(dna)

        # 如果没找到游戏匹配，用向量查询
        if not loaded and magnetic_engine:
            cid, sim = self.cluster_engine.predict(query_text, magnetic_engine)
            if cid is not None and cid not in self._loaded_clusters and sim > 0.3:
                self._loaded_clusters.add(cid)
                hit_cid = cid
                member_ids = self.cluster_engine.get_cluster(cid)
                for did in member_ids:
                    dna = id_to_dna.get(did)
                    if dna and dna.is_alive:
                        loaded.append(dna)

        # 限制数量
        if len(loaded) > _L1_MAX_MEMORIES:
            loaded.sort(key=lambda d: d.lifetime, reverse=True)
            loaded = loaded[:_L1_MAX_MEMORIES]

        if loaded:
            self._record_load("L1", len(loaded), f"话题加载: {game or query_text[:30]}")
        return loaded, hit_cid

    def load_l2_deep(self, query_text: str, dna_pool: list, id_to_dna: dict,
                     magnetic_engine=None) -> list:
        """
        L2 深层加载：具体问题触发

        Args:
            query_text: 用户输入文本
            dna_pool: DNA池
            id_to_dna: ID到DNA的映射
            magnetic_engine: 磁吸引擎（用于向量查询）

        Returns:
            L2 级别的 DNA 列表
        """
        if not self.cluster_engine or not self.cluster_engine._built:
            return []

        loaded = []

        # 用向量查询找到最相关的簇
        if magnetic_engine:
            cid, sim = self.cluster_engine.predict(query_text, magnetic_engine)
            if cid is not None and cid not in self._loaded_clusters and sim > 0.4:
                self._loaded_clusters.add(cid)
                member_ids = self.cluster_engine.get_cluster(cid)
                for did in member_ids:
                    dna = id_to_dna.get(did)
                    if dna and dna.is_alive:
                        loaded.append(dna)

        # 限制数量
        if len(loaded) > _L2_MAX_MEMORIES:
            loaded.sort(key=lambda d: d.lifetime, reverse=True)
            loaded = loaded[:_L2_MAX_MEMORIES]

        if loaded:
            self._record_load("L2", len(loaded), f"深层加载: {query_text[:30]}")
        return loaded

    def get_cluster_members(self, cid: int) -> list[str]:
        """
        W4: 获取指定簇的成员ID列表（公开API）

        Args:
            cid: 簇ID

        Returns:
            成员DNA ID列表
        """
        if not self.cluster_engine or not self.cluster_engine._built:
            return []
        return self.cluster_engine.get_cluster(cid)

    def is_ready(self) -> bool:
        """
        W4: 聚类引擎是否就绪（公开API）

        Returns:
            是否已构建
        """
        return bool(self.cluster_engine and self.cluster_engine._built)

    def mark_cluster_loaded(self, cid: int):
        """
        W4: 标记簇已加载（公开API）

        Args:
            cid: 簇ID
        """
        self._loaded_clusters.add(cid)

    def get_loaded_clusters(self) -> set[int]:
        """获取已加载的簇ID集合"""
        return self._loaded_clusters.copy()

    def reset(self):
        """重置加载状态（新一轮会话开始时调用）"""
        self._loaded_clusters.clear()

    def get_unloaded_summary(self) -> dict:
        """获取未加载簇的摘要"""
        if not self.cluster_engine or not self.cluster_engine._built:
            return {"unloaded": 0, "details": []}

        details = []
        for cid, meta in self.cluster_engine.get_all_meta().items():
            if cid not in self._loaded_clusters:
                details.append({
                    "cluster_id": cid,
                    "label": meta["label"],
                    "level": meta["level"],
                    "size": meta["size"],
                    "keywords": meta["keywords"],
                })

        return {
            "unloaded": len(details),
            "details": details,
        }

    def _record_load(self, level: str, count: int, reason: str):
        """记录加载事件"""
        self._load_history.append({
            "timestamp": time.time(),
            "level": level,
            "count": count,
            "reason": reason,
        })
        # 只保留最近50条
        if len(self._load_history) > 50:
            self._load_history = self._load_history[-50:]

    def stats(self) -> dict:
        """加载统计"""
        return {
            "loaded_clusters": len(self._loaded_clusters),
            "load_history_count": len(self._load_history),
            "last_load": self._load_history[-1] if self._load_history else None,
        }
