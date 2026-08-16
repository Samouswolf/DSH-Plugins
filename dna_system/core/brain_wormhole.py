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


# ════════════════════════════════════════════════════════════
# 游戏工坊专用：跨游戏虫洞
# ════════════════════════════════════════════════════════════

from .brain_encoder import identify_game, identify_system


def game_wormhole_expand(
    seeds: List[Dict],
    all_entities: List[Dict],
    query_text: str = "",
    max_hops: int = 2,
    max_expansions: int = 10,
) -> List[Dict]:
    """
    游戏工坊专用虫洞展开。

    特点：
    1. 优先展开同游戏记忆
    2. 同系统记忆次优先
    3. 跨游戏记忆最后
    """
    if not seeds or not all_entities:
        return seeds

    target_game = identify_game(query_text)
    target_system = identify_system(query_text)

    # 分组实体
    same_game = []
    same_system = []
    other = []

    for e in all_entities:
        e_text = e.get("text", "")
        e_game = identify_game(e_text)
        e_system = identify_system(e_text)

        if e_game == target_game:
            same_game.append(e)
        elif e_system == target_system:
            same_system.append(e)
        else:
            other.append(e)

    # 按优先级展开
    seen_ids: Set[str] = {e.get("id") for e in seeds}
    all_candidates = list(seeds)

    # 1. 同游戏展开
    if same_game:
        game_expanded = wormhole_expand(
            seeds, same_game, query_text,
            max_hops=max_hops,
            max_expansions=max_expansions // 2,
        )
        for e in game_expanded:
            if e.get("id") not in seen_ids:
                e["_wormhole_type"] = "same_game"
                seen_ids.add(e.get("id"))
                all_candidates.append(e)

    # 2. 同系统展开
    if same_system:
        sys_expanded = wormhole_expand(
            seeds, same_system, query_text,
            max_hops=1,
            max_expansions=max_expansions // 3,
        )
        for e in sys_expanded:
            if e.get("id") not in seen_ids:
                e["_wormhole_type"] = "same_system"
                seen_ids.add(e.get("id"))
                all_candidates.append(e)

    # 3. 跨游戏展开
    if other:
        cross_expanded = wormhole_expand(
            seeds, other, query_text,
            max_hops=1,
            max_expansions=max_expansions // 4,
        )
        for e in cross_expanded:
            if e.get("id") not in seen_ids:
                e["_wormhole_type"] = "cross_game"
                seen_ids.add(e.get("id"))
                all_candidates.append(e)

    return all_candidates


# ════════════════════════════════════════════════════════════
# 测试/调试
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 测试实体
    test_entities = [
        {"id": "bug-001", "text": "贪吃蛇碰撞检测Bug：自碰判定有误", "energy": 0.6},
        {"id": "bug-002", "text": "贪吃蛇食物生成位置异常", "energy": 0.5},
        {"id": "bug-003", "text": "塔防炮塔碰撞范围错误", "energy": 0.4},
        {"id": "bug-004", "text": "火柴人格斗hitbox偏移", "energy": 0.3},
        {"id": "bug-005", "text": "苍穹射击子弹碰撞穿透", "energy": 0.2},
        {"id": "bug-006", "text": "贪吃蛇NPC AI路径规划", "energy": 0.5},
    ]

    # 种子匹配
    seeds = magnetic_resonance("碰撞检测", test_entities, top_k=2)
    print("=== 种子匹配 ===")
    for s in seeds:
        print(f"  [{s.get('_score', 0):.4f}] {s['id']}: {s['text']}")

    # 虫洞展开
    print("\n=== 虫洞展开 ===")
    expanded = wormhole_expand(seeds, test_entities, "碰撞检测", max_hops=2)
    for e in expanded:
        hop = e.get("wormhole_hop", 0)
        source = e.get("_source_id", "")
        tag = f" [hop={hop},from={source}]" if hop > 0 else " [种子]"
        print(f"  [{e.get('_score', 0):.4f}] {e['id']}: {e['text']}{tag}")

    # 游戏虫洞展开
    print("\n=== 游戏虫洞展开 ===")
    game_expanded = game_wormhole_expand(seeds, test_entities, "贪吃蛇碰撞", max_hops=2)
    for e in game_expanded:
        wtype = e.get("_wormhole_type", "seed")
        print(f"  [{wtype}] {e['id']}: {e['text']}")
