"""
🧠 联想大脑 — 统一入口（精简版）

核心能力：
  1. 被动联想 — 关键词触发 → 拉出相关记忆
  2. 自动建联 — 新记忆进来 → 自动关联
  3. 虫洞展开 — 种子匹配 → 关联网络

使用方式：
  brain = Brain()
  brain.load("memory.json")
  results = brain.recall("贪吃蛇碰撞")
  brain.add("bug-001", "碰撞检测Bug", energy=0.6)
"""

from __future__ import annotations
import os
import time
from typing import Dict, List, Optional
from .brain_encoder import extract_dna, encode_game_memory, identify_game, identify_system
from .brain_resonance import magnetic_resonance, cross_game_resonance, compute_idf
from .brain_pool import BrainPool, MemoryEntity
from .brain_wormhole import wormhole_expand, smart_wormhole_expand, game_wormhole_expand


# ════════════════════════════════════════════════════════════
# 联想大脑
# ════════════════════════════════════════════════════════════

class Brain:
    """联想大脑 — 统一入口。整合四层记忆池、磁吸匹配、虫洞展开。"""

    def __init__(self, memory_dir: str = ".dna"):
        self.memory_dir = memory_dir
        self.pool = BrainPool()

        # IDF权重缓存
        self._idf_weights: Optional[Dict[str, float]] = None
        self._idf_dirty = True

        # 统计
        self._recall_count = 0

    # ── 持久化 ──

    def load(self, prefix: str = "brain"):
        """加载记忆池"""
        pool_path = os.path.join(self.memory_dir, f"{prefix}_pool.json")
        if os.path.exists(pool_path):
            self.pool = BrainPool.load(pool_path)
            self._idf_dirty = True

    def save(self, prefix: str = "brain"):
        """保存记忆池"""
        os.makedirs(self.memory_dir, exist_ok=True)
        pool_path = os.path.join(self.memory_dir, f"{prefix}_pool.json")
        self.pool.save(pool_path)

    # ── 添加记忆 ──

    def add(
        self,
        eid: str,
        text: str,
        energy: float = 0.5,
        pinned: bool = False,
        source: str = "manual",
        meta: Optional[Dict] = None,
    ) -> MemoryEntity:
        """添加一条记忆"""
        entity = self.pool.add(
            eid=eid, text=text, energy=energy,
            pinned=pinned, source=source, meta=meta,
        )
        self._idf_dirty = True
        return entity

    def add_hot(self, text: str) -> MemoryEntity:
        """添加热层记忆（当前会话）"""
        return self.pool.add_hot(text)

    # ── 被动联想 ──

    def recall(
        self,
        query: str,
        top_k: int = 5,
        enable_wormhole: bool = True,
        wormhole_hops: int = 2,
    ) -> List[Dict]:
        """
        被动联想：关键词触发 → 拉出相关记忆。
        流程：提取查询DNA → 磁吸匹配 → 虫洞展开(可选) → 返回top_k
        """
        self._recall_count += 1

        entities = self.pool.get_all()
        if not entities:
            return []

        entity_dicts = [e.to_dict() for e in entities]

        if self._idf_dirty:
            self._idf_weights = compute_idf(entity_dicts)
            self._idf_dirty = False

        matches = magnetic_resonance(
            query, entity_dicts,
            top_k=top_k * 2,
            idf_weights=self._idf_weights,
        )
        if not matches:
            return []

        # 虫洞展开
        if enable_wormhole and matches:
            seeds = matches[:3]
            expanded = game_wormhole_expand(
                seeds, entity_dicts, query,
                max_hops=wormhole_hops, max_expansions=top_k * 2,
            )
            seen_ids = {m["id"] for m in matches}
            for e in expanded:
                if e["id"] not in seen_ids:
                    e["_from_wormhole"] = True
                    matches.append(e)
                    seen_ids.add(e["id"])

        return matches[:top_k]

    # ── 衰减/清理 ──

    def decay(self, cycles: int = 1) -> Dict:
        """冷层能量衰减"""
        return self.pool.decay_cold(cycles)

    def cleanup(self) -> Dict:
        """清理过期记忆"""
        return {"pool_cleaned": 0}

    # ── 统计 ──

    def stats(self) -> Dict:
        """统计信息"""
        return {
            "pool": self.pool.layer_stats(),
            "pool_total": self.pool.count(),
            "recall_count": self._recall_count,
        }

    # ── 调试 ──

    def debug_recall(self, query: str) -> Dict:
        """调试模式：返回详细匹配信息"""
        entities = self.pool.get_all()
        entity_dicts = [e.to_dict() for e in entities]
        query_dna = extract_dna(query)
        matches = magnetic_resonance(query, entity_dicts, top_k=10)

        return {
            "query": query,
            "query_dna": query_dna,
            "game": identify_game(query),
            "system": identify_system(query),
            "matches": matches,
        }


# ════════════════════════════════════════════════════════════
# 快捷函数
# ════════════════════════════════════════════════════════════

_global_brain: Optional[Brain] = None


def get_brain(memory_dir: str = ".dna") -> Brain:
    """获取全局Brain实例"""
    global _global_brain
    if _global_brain is None:
        _global_brain = Brain(memory_dir)
        _global_brain.load()
    return _global_brain


def recall(query: str, top_k: int = 5) -> List[Dict]:
    """快捷联想"""
    return get_brain().recall(query, top_k)


def check(context: str) -> List:
    """快捷检查（已精简，返回空列表）"""
    return []


def add(eid: str, text: str, **kwargs) -> MemoryEntity:
    """快捷添加"""
    return get_brain().add(eid, text, **kwargs)


# ════════════════════════════════════════════════════════════
# 测试/调试
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    brain = Brain(memory_dir="test_brain")

    print("=== 添加记忆 ===")
    brain.add("bug-001", "贪吃蛇碰撞检测Bug：自碰判定有误", energy=0.6)
    brain.add("bug-002", "贪吃蛇食物生成位置异常", energy=0.5)
    brain.add("bug-003", "塔防炮塔碰撞范围错误", energy=0.4)
    brain.add("bug-004", "火柴人格斗hitbox偏移", energy=0.5)

    print("\n=== 被动联想 ===")
    results = brain.recall("碰撞检测", top_k=3)
    for r in results:
        print(f"  [{r.get('_score', 0):.4f}] {r['id']}: {r['text'][:50]}")

    print("\n=== 统计 ===")
    print(brain.stats())

    brain.save()
    import shutil
    if os.path.exists("test_brain"):
        shutil.rmtree("test_brain")
