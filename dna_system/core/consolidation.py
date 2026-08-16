"""
睡眠巩固引擎 —— 模拟睡眠时的记忆巩固过程
Phase 3: 海马体进化

模拟人类睡眠中记忆巩固的机制：
- 重要记忆（高情感权重）被强化 → 更长的生命周期
- 不重要的记忆被弱化 → 加速遗忘
- 跨情景模式提取 → 归纳出PATTERN类型DNA
- 巩固历史记录 → 追踪每次巩固的效果
"""
import time
import uuid
import json
import numpy as np
from .dna import DNA, DNAType, StrandType


class MemoryConsolidation:
    """睡眠巩固引擎：强化重要记忆，弱化不重要记忆，提取跨情景模式"""

    def __init__(self, system):
        """
        Args:
            system: DNASystem 主系统实例
        """
        self.system = system
        self.consolidation_history: list[dict] = []  # 巩固历史记录

    # ===== 公开API =====

    def consolidate(self, recent_hours: float = 24) -> dict:
        """
        运行一个巩固周期（模拟睡眠过程）

        流程：
        1. 获取最近N小时的情景记忆
        2. 按情感权重排序
        3. 强化重要记忆（top 10，|valence| > 0.3）
        4. 弱化不重要记忆（|valence| < 0.1）
        5. 提取跨情景的模式

        Args:
            recent_hours: 回顾最近多少小时的情景，默认24

        Returns:
            巩固报告 dict:
            {
                "timestamp": 巩固时间,
                "episodes_processed": 处理的情景数,
                "dnas_reinforced": 强化的DNA数,
                "dnas_weakened": 弱化的DNA数,
                "patterns_extracted": 提取的模式数,
            }
        """
        report = {
            "timestamp": time.time(),
            "episodes_processed": 0,
            "dnas_reinforced": 0,
            "dnas_weakened": 0,
            "patterns_extracted": 0,
        }

        # 1. 获取最近的情景
        recent_episodes = self._get_recent_episodes(recent_hours)
        report["episodes_processed"] = len(recent_episodes)

        if not recent_episodes:
            self.consolidation_history.append(report)
            return report

        # 2. 按情感权重绝对值排序（最重要→最不重要）
        episodes_by_importance = sorted(
            recent_episodes,
            key=lambda e: abs(e.emotional_valence),
            reverse=True,
        )

        # 3. 强化重要记忆（前10个，情感权重>0.3）
        important = [
            ep for ep in episodes_by_importance[:10]
            if abs(ep.emotional_valence) > 0.3
        ]
        for episode in important:
            reinforced_count = self._reinforce_episode(episode)
            report["dnas_reinforced"] += reinforced_count

        # 4. 弱化不重要的记忆（情感权重<0.1）
        unimportant = [
            ep for ep in episodes_by_importance
            if abs(ep.emotional_valence) < 0.1
        ]
        for episode in unimportant:
            weakened_count = self._weaken_episode(episode)
            report["dnas_weakened"] += weakened_count

        # 5. 提取跨情景模式
        patterns = self._extract_patterns(recent_episodes)
        report["patterns_extracted"] = len(patterns)

        # 6. 记录巩固历史
        self.consolidation_history.append(report)
        # 限制历史记录数量
        if len(self.consolidation_history) > 50:
            self.consolidation_history = self.consolidation_history[-50:]

        return report

    # ===== 内部方法 =====

    def _get_recent_episodes(self, hours: float) -> list:
        """
        获取最近N小时的情景记忆

        优先从 episodic 引擎的缓存获取，fallback 到时间索引查询。
        """
        episodes = []

        # 方式1: 从 episodic 引擎获取
        if hasattr(self.system, 'episodic') and self.system.episodic:
            try:
                episodes = self.system.episodic.get_recent_episodes(hours)
            except Exception:
                pass

        # 方式2: 从DNA池直接筛选（fallback）
        if not episodes:
            cutoff = time.time() - hours * 3600
            for dna in self.system.pool:
                if dna.dna_type == DNAType.EPISODE and dna.created_at >= cutoff:
                    try:
                        from .episodic import Episode
                        ep = Episode.from_dna(dna)
                        episodes.append(ep)
                    except Exception:
                        pass

        return episodes

    def _reinforce_episode(self, episode) -> int:
        """
        强化一个情景及其关联DNA

        强化策略：
        - 延长DNA生命周期 +20
        - 增加访问计数 +1
        - 对关联DNA施加巩固强化（按情感权重缩放）

        Returns:
            被强化的DNA总数（情景本身 + 关联DNA）
        """
        reinforced_count = 0

        # 强化情景DNA本身
        dna = self.system._dna_by_id.get(episode.id)
        if dna and dna.is_alive:
            dna.lifetime = min(100, dna.lifetime + 20)
            dna.access_count += 1
            dna.last_accessed = time.time()
            reinforced_count += 1

        # 强化关联DNA
        if hasattr(self.system, 'lifecycle') and self.system.lifecycle:
            importance = min(0.9, abs(episode.emotional_valence) + 0.2)
            for related_id in episode.related_dna_ids:
                related_dna = self.system._dna_by_id.get(related_id)
                if related_dna and related_dna.is_alive:
                    self.system.lifecycle.consolidate_reinforce(
                        related_dna, importance
                    )
                    reinforced_count += 1

        return reinforced_count

    def _weaken_episode(self, episode) -> int:
        """
        弱化一个情景（加速遗忘不重要的记忆）

        弱化策略：
        - 减少DNA生命周期 -10
        - 不减少到0以下（让自然衰减完成遗忘）

        Returns:
            被弱化的DNA总数
        """
        weakened_count = 0

        # 弱化情景DNA本身
        dna = self.system._dna_by_id.get(episode.id)
        if dna and dna.is_alive and dna.lifetime > 10:
            dna.lifetime = max(5, dna.lifetime - 10)
            weakened_count += 1

        # 弱化关联DNA（幅度更小）
        for related_id in episode.related_dna_ids:
            related_dna = self.system._dna_by_id.get(related_id)
            if related_dna and related_dna.is_alive and related_dna.lifetime > 10:
                related_dna.lifetime = max(5, related_dna.lifetime - 5)
                weakened_count += 1

        return weakened_count

    def _extract_patterns(self, episodes: list) -> list[DNA]:
        """
        从多个情景中提取跨情景模式

        方法：
        1. 找出重复出现的 trigger-outcome 对
        2. 聚类相似的 trigger-outcome 对
        3. 为每个聚类生成 PATTERN 类型DNA

        仅从情感显著（|valence| > 0.2）的情景中提取，
        以防止噪音模式污染。

        Returns:
            新生成的 PATTERN 类型DNA列表
        """
        if len(episodes) < 2:
            return []

        # 只从情感显著的情景中提取
        significant = [e for e in episodes if abs(e.emotional_valence) > 0.2]
        if len(significant) < 2:
            return []

        # 构建 trigger-outcome 对，并按trigger相似度分组
        patterns = []

        # 用向量相似度聚类 trigger-outcome 对
        grouped = self._cluster_by_trigger(significant)

        for group in grouped:
            if len(group) < 2:
                continue

            # 提取共性
            common_trigger = self._extract_common_text([e.trigger for e in group])
            common_outcome = self._extract_common_text([e.outcome for e in group])
            avg_valence = sum(e.emotional_valence for e in group) / len(group)

            # 收集所有关联的DNA ID
            all_related = []
            for ep in group:
                all_related.extend(ep.related_dna_ids)
            all_related = list(set(all_related))[:20]

            # 生成模式名称
            pattern_name = f"{common_trigger} → {common_outcome}"

            # 创建PATTERN类型DNA
            pattern_content = {
                "pattern_name": pattern_name,
                "trigger_pattern": common_trigger,
                "outcome_pattern": common_outcome,
                "avg_emotional_valence": round(avg_valence, 3),
                "episode_count": len(group),
                "source_episode_ids": [e.id for e in group],
                "consolidation_timestamp": time.time(),
            }

            # 生成向量
            text = json.dumps(pattern_content, ensure_ascii=False)
            vector = self.system.magnetic.generate_vector(text)

            pattern_dna = DNA(
                id=uuid.uuid4().hex[:12],
                dna_type=DNAType.PATTERN,
                strand=StrandType.FORWARD,
                content=pattern_content,
                magnetic_vector=vector,
                created_at=time.time(),
                lifetime=80.0,  # 模式有较高的初始生命值
                tags=["pattern", "consolidated"] + self._tag_from_valence(avg_valence),
                child_ids=all_related,
            )

            # 加入系统池
            self.system.pool.append(pattern_dna)
            self.system._dna_by_id[pattern_dna.id] = pattern_dna

            # 更新时间索引
            if hasattr(self.system, 'temporal_index') and self.system.temporal_index:
                self.system.temporal_index.add(pattern_dna)

            # 持久化
            self.system.store.save(pattern_dna)

            patterns.append(pattern_dna)

        return patterns

    def _cluster_by_trigger(self, episodes: list) -> list[list]:
        """
        按trigger文本相似度聚类情景

        简单策略：用向量相似度做单链聚类
        阈值较低（0.3），确保不过度聚合。
        """
        if len(episodes) <= 1:
            return [[e] for e in episodes]

        # 为每个episode生成trigger向量
        vectors = []
        for ep in episodes:
            vec = self.system.magnetic.generate_vector(ep.trigger)
            vectors.append(vec)

        # 并查集聚类
        n = len(episodes)
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        # 两两比较相似度
        for i in range(n):
            for j in range(i + 1, n):
                sim = self._cosine_sim(vectors[i], vectors[j])
                if sim > 0.3:  # 低阈值，宽松聚类
                    union(i, j)

        # 按根节点分组
        groups = {}
        for i in range(n):
            root = find(i)
            if root not in groups:
                groups[root] = []
            groups[root].append(episodes[i])

        return list(groups.values())

    def _extract_common_text(self, texts: list[str]) -> str:
        """从多条文本中提取共性（简单实现：找最长公共子串）"""
        if not texts:
            return ""
        if len(texts) == 1:
            return texts[0]

        # 简化：取所有非空文本，找出现频率最高的词
        all_words = []
        for t in texts:
            # 简单分词
            words = t.replace("，", " ").replace(",", " ").split()
            all_words.extend(words)

        if not all_words:
            return texts[0]

        # 统计词频，取top3
        from collections import Counter
        word_counts = Counter(all_words)
        top_words = [w for w, _ in word_counts.most_common(3)]

        return " ".join(top_words) if top_words else texts[0]

    def _tag_from_valence(self, valence: float) -> list[str]:
        """根据情感权重生成标签"""
        if valence > 0.5:
            return ["positive_pattern"]
        elif valence < -0.3:
            return ["negative_pattern"]
        return ["neutral_pattern"]

    @staticmethod
    def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
        """余弦相似度（numpy实现）"""
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        if na == 0 or nb == 0:
            return 0.0
        return float(np.dot(a, b) / (na * nb))

    def stats(self) -> dict:
        """引擎统计信息"""
        episode_count = sum(
            1 for d in self.system.pool if d.dna_type == DNAType.EPISODE
        )
        pattern_count = sum(
            1 for d in self.system.pool if d.dna_type == DNAType.PATTERN
        )
        return {
            "consolidation_cycles": len(self.consolidation_history),
            "episodes_available": episode_count,
            "patterns_extracted": pattern_count,
            "last_consolidation": (
                self.consolidation_history[-1]["timestamp"]
                if self.consolidation_history else None
            ),
        }
