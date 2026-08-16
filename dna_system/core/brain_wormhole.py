"""
🧠 联想大脑 — 虫洞展开

核心思想：匹配到的实体继续向外扩散，找到关联记忆。
从种子实体出发，用实体DNA作为查询信号，匹配池中其他实体。

机制：
  1. 种子匹配 → 找到直接相关记忆
  2. 种子DNA → 二次磁吸 → 找到关联记忆
  3. 关联记忆DNA → 三次磁吸 → 找到更远关联
  4. 能量衰减：replica_energy = energy * 0.7
  5. 最多4跳，能量阈值0.03

效果：一个关键词触发 → 拉出一串相关记忆网络
"""

from __future__ import annotations
from typing import Dict, List, Optional, Set
from .brain_encoder import extract_dna
from .brain_resonance import coordinate_resonance, magnetic_resonance


# ════════════════════════════════════════════════════════════
# 虫洞展开
# ════════════════════════════════════════════════════════════

def wormhole_expand(
    seeds: List[Dict],
    all_entities: List[Dict],
    query_text: str = "",
    max_hops: int = 4,
    energy_decay: float = 0.7,
    energy_threshold: float = 0.03,
    max_expansions: int = 20,
) -> List[Dict]:
    """
    虫洞展开：从种子实体出发，找到关联记忆网络。

    流程：
      1. 种子实体作为起点
      2. 用种子实体的text作为查询信号
      3. 在所有实体中做磁吸匹配
      4. 匹配到的实体加入候选，继续扩散
      5. 能量衰减，直到低于阈值或达到最大跳数

    Args:
        seeds: 种子实体列表（直接匹配到的）
        all_entities: 所有实体池
        query_text: 原始查询文本（用于避免重复）
        max_hops: 最大跳数（默认4）
        energy_decay: 每跳能量衰减系数（默认0.7）
        energy_threshold: 能量阈值（默认0.03）
        max_expansions: 最大展开数（默认20）

    Returns:
        所有候选实体（包含种子+展开的）
    """
    if not seeds or not all_entities:
        return seeds

    # 已访问集合
    seen_ids: Set[str] = {e.get("id") for e in seeds}
    all_candidates = list(seeds)
    current = seeds[:]
    hop = 0

    while hop < max_hops and len(all_candidates) < max_expansions:
        next_replicas: List[Dict] = []

        for e in current:
            # 计算当前实体的能量
            replica_energy = e.get("energy", 0.5) * energy_decay
            if replica_energy < energy_threshold:
                continue

            # 用实体text作为查询信号
            e_text = e.get("text", "")
            if not e_text:
                continue

            # 在所有实体中做磁吸匹配
            for nb in all_entities:
                nb_id = nb.get("id")
                if nb_id in seen_ids:
                    continue

                # 计算共振
                nb_text = nb.get("text", "")
                if not nb_text:
                    continue

                nb_dna = extract_dna(nb_text)
                e_dna = extract_dna(e_text)
                score = coordinate_resonance(e_dna, nb_dna)

                if score > 0.05:
                    probe = dict(nb)
                    probe["energy"] = replica_energy
                    probe["wormhole_hop"] = hop + 1
                    probe["_score"] = score
                    probe["_source_id"] = e.get("id")
                    seen_ids.add(nb_id)
                    next_replicas.append(probe)

        if not next_replicas:
            break

        all_candidates.extend(next_replicas)
        current = next_replicas
        hop += 1

    return all_candidates


# ════════════════════════════════════════════════════════════
# 智能虫洞展开（带反链免疫）
# ════════════════════════════════════════════════════════════

def smart_wormhole_expand(
    seeds: List[Dict],
    all_entities: List[Dict],
    query_text: str = "",
    anti_chain=None,
    max_hops: int = 3,
    energy_decay: float = 0.7,
    energy_threshold: float = 0.05,
    max_expansions: int = 15,
) -> List[Dict]:
    """
    智能虫洞展开：带反链免疫的虫洞展开。

    在标准虫洞展开基础上：
    1. 反链命中时跳过该实体
    2. 记录展开路径，避免循环
    3. 优先展开高能量实体

    Args:
        seeds: 种子实体列表
        all_entities: 所有实体池
        query_text: 原始查询文本
        anti_chain: 反链免疫系统（可选）
        max_hops: 最大跳数
        energy_decay: 能量衰减系数
        energy_threshold: 能量阈值
        max_expansions: 最大展开数

    Returns:
        所有候选实体
    """
    if not seeds or not all_entities:
        return seeds

    seen_ids: Set[str] = {e.get("id") for e in seeds}
    all_candidates = list(seeds)

    # 按能量排序种子
    current = sorted(seeds, key=lambda x: x.get("energy", 0), reverse=True)
    hop = 0

    while hop < max_hops and len(all_candidates) < max_expansions:
        next_replicas: List[Dict] = []

        for e in current:
            replica_energy = e.get("energy", 0.5) * energy_decay
            if replica_energy < energy_threshold:
                continue

            e_text = e.get("text", "")
            if not e_text:
                continue

            # 获取当前实体的反链词
            anti_words = set()
            if anti_chain:
                anti_words = anti_chain.get_words(e.get("id", ""))

            # 磁吸匹配
            candidates = magnetic_resonance(
                e_text, all_entities, top_k=5
            )

            for nb in candidates:
                nb_id = nb.get("id")
                if nb_id in seen_ids:
                    continue

                # 反链检查
                if anti_chain and anti_chain.has(nb_id, e_text[:10]):
                    continue

                probe = dict(nb)
                probe["energy"] = replica_energy
                probe["wormhole_hop"] = hop + 1
                probe["_source_id"] = e.get("id")
                seen_ids.add(nb_id)
                next_replicas.append(probe)

        if not next_replicas:
            break

        # 按分数排序，取top
        next_replicas.sort(key=lambda x: x.get("_score", 0), reverse=True)
        all_candidates.extend(next_replicas)
        current = next_replicas
        hop += 1

    return all_candidates
