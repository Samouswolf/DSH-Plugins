"""
情景记忆引擎 —— 记录完整事件链，支持按触发器回忆
Phase 2: 海马体进化

模拟人类海马体的情景记忆功能：
- 记录"做了什么→结果如何"的完整事件链
- 通过磁吸匹配按触发器回忆相关情景
- 自动计算情感权重，强化关联记忆
"""
import time
import uuid
import json
import numpy as np
from .dna import DNA, DNAType, StrandType


class Episode:
    """一次完整的事件记忆（情景）"""

    def __init__(self, id=None, timestamp=None, trigger="", context=None,
                 actions=None, outcome="", emotional_valence=0.0,
                 related_dna_ids=None):
        self.id = id or uuid.uuid4().hex[:12]
        self.timestamp = timestamp or time.time()
        self.trigger = trigger              # 什么触发了这个事件
        self.context = context or {}        # 当时的状态/环境
        self.actions = actions or []        # 做了什么（步骤列表）
        self.outcome = outcome              # 结果如何
        self.emotional_valence = emotional_valence  # 情感权重 (-1到1)
        self.related_dna_ids = related_dna_ids or []  # 关联的DNA ID列表

    def to_dna(self, magnetic=None) -> DNA:
        """转换为EPISODE类型DNA，用于持久化存储"""
        content = {
            "trigger": self.trigger,
            "context": self.context,
            "actions": self.actions,
            "outcome": self.outcome,
            "emotional_valence": self.emotional_valence,
        }
        # 用内容文本生成磁吸向量
        text = json.dumps(content, ensure_ascii=False)
        if magnetic is not None:
            vector = magnetic.generate_vector(text)
        else:
            vector = np.zeros(512, dtype=np.float32)

        # 生成时间标签
        import datetime
        dt = datetime.datetime.fromtimestamp(self.timestamp)
        temporal_tags = [
            dt.strftime("%Y-%m-%d"),
            "下午" if dt.hour >= 12 else "上午",
            dt.strftime("%H:%M"),
        ]

        return DNA(
            id=self.id,
            dna_type=DNAType.EPISODE,
            strand=StrandType.FORWARD,
            content=content,
            magnetic_vector=vector,
            created_at=self.timestamp,
            lifetime=100.0,
            episode_id=self.id,           # 情景DNA自身也是episode
            sequence_index=0,
            tags=self._generate_tags(),
            temporal_tags=temporal_tags,
            child_ids=self.related_dna_ids,
        )

    @staticmethod
    def from_dna(dna: DNA) -> 'Episode':
        """从DNA恢复Episode对象"""
        return Episode(
            id=dna.id,
            timestamp=dna.created_at,
            trigger=dna.content.get("trigger", ""),
            context=dna.content.get("context", {}),
            actions=dna.content.get("actions", []),
            outcome=dna.content.get("outcome", ""),
            emotional_valence=dna.content.get("emotional_valence", 0.0),
            related_dna_ids=dna.child_ids if dna.child_ids else [],
        )

    def _generate_tags(self) -> list[str]:
        """根据情感极性生成标签"""
        tags = ["episode"]
        if self.emotional_valence > 0.5:
            tags.append("positive")
        elif self.emotional_valence < -0.3:
            tags.append("negative")
        else:
            tags.append("neutral")
        return tags

    def to_dict(self) -> dict:
        """导出为字典（用于序列化）"""
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "trigger": self.trigger,
            "context": self.context,
            "actions": self.actions,
            "outcome": self.outcome,
            "emotional_valence": self.emotional_valence,
            "related_dna_ids": self.related_dna_ids,
        }


class EpisodicMemory:
    """情景记忆引擎：记录、回忆、关联情景记忆"""

    def __init__(self, system):
        """
        Args:
            system: DNASystem 主系统实例，提供 magnetic/lifecycle/temporal_index/store 等服务
        """
        self.system = system
        self._recent_episodes: list[Episode] = []  # 内存中的最近情景缓存

    # ===== 公开API =====

    def record_episode(self, trigger: str, actions, outcome: str,
                       context: dict = None) -> Episode:
        """
        记录一个情景事件

        Args:
            trigger: 触发器描述（什么触发了这个事件）
            actions: 执行的动作（字符串或字符串列表）
            outcome: 结果描述
            context: 额外上下文信息

        Returns:
            创建的Episode对象
        """
        if isinstance(actions, str):
            actions = [actions]

        episode = Episode(
            trigger=trigger,
            context=context or {},
            actions=actions,
            outcome=outcome,
            emotional_valence=self._calculate_valence(outcome),
        )

        # 关联当前系统中活跃的DNA（磁吸搜索相关记忆）
        episode.related_dna_ids = self._find_related_dnas(episode)

        # 转换为DNA并加入系统池
        dna = episode.to_dna(self.system.magnetic)
        self.system.pool.append(dna)

        # 维护O(1)查找索引（海马体优化）
        self.system._dna_by_id[dna.id] = dna
        self.system._episode_ids.add(dna.id)

        # 更新时间索引
        if hasattr(self.system, 'temporal_index') and self.system.temporal_index:
            self.system.temporal_index.add(dna)

        # 增量更新向量索引
        self.system.magnetic.index.add(dna)

        # 持久化到磁盘
        self.system.store.save(dna)

        # 强化关联DNA的生命周期（相关记忆被"想起"）
        self._reinforce_related_dnas(episode)

        # 缓存最近情景
        self._recent_episodes.append(episode)
        if len(self._recent_episodes) > 100:
            self._recent_episodes = self._recent_episodes[-100:]

        return episode

    def recall_by_trigger(self, trigger: str, top_k: int = 5) -> list[tuple[Episode, float]]:
        """
        通过触发器回忆相关情景

        Args:
            trigger: 触发器文本
            top_k: 返回最匹配的前K个

        Returns:
            [(Episode, 匹配分数), ...] 按分数降序排列
        """
        # 构建查询DNA
        query_vec = self.system.magnetic.generate_vector(trigger)
        query_dna = DNA(
            content={"trigger": trigger},
            magnetic_vector=query_vec,
        )

        # 获取所有EPISODE类型的DNA
        episode_dnas = [d for d in self.system.pool if d.dna_type == DNAType.EPISODE]
        if not episode_dnas:
            return []

        # 磁吸匹配
        results = self.system.magnetic.attract(query_dna, episode_dnas)

        # 转换为Episode对象
        episodes = []
        for dna, score in results[:top_k]:
            ep = Episode.from_dna(dna)
            episodes.append((ep, round(score, 4)))

        return episodes

    def get_recent_episodes(self, hours: float = 24) -> list[Episode]:
        """获取最近N小时的情景（结合时间索引）"""
        cutoff = time.time() - hours * 3600
        recent = []
        for ep in self._recent_episodes:
            if ep.timestamp >= cutoff:
                recent.append(ep)

        # 也从DNA池中恢复（缓存可能不完整）
        if hasattr(self.system, 'temporal_index') and self.system.temporal_index:
            recent_ids = self.system.temporal_index.query_recent(int(hours))
            for dna_id in recent_ids:
                dna = self.system._dna_by_id.get(dna_id)
                if dna and dna.dna_type == DNAType.EPISODE:
                    ep = Episode.from_dna(dna)
                    # 去重
                    if not any(e.id == ep.id for e in recent):
                        recent.append(ep)

        return recent

    # ===== 内部方法 =====

    def _calculate_valence(self, outcome: str) -> float:
        """
        计算情感权重 (-1.0 到 1.0)

        基于关键词匹配的简单情感分析：
        - 正向词加分
        - 负向词减分
        """
        if not outcome:
            return 0.0

        positive_words = [
            "成功", "完成", "修复", "解决", "通过", "正确",
            "好", "优秀", "完美", "顺利", "正常", "✅",
            "success", "ok", "pass", "fixed", "solved",
        ]
        negative_words = [
            "失败", "错误", "崩溃", "bug", "问题", "异常",
            "坏", "差", "损坏", "❌", "无法", "不能",
            "fail", "error", "crash", "broken",
        ]

        outcome_lower = str(outcome).lower()
        score = 0.0

        for w in positive_words:
            if w.lower() in outcome_lower:
                score += 0.15

        for w in negative_words:
            if w.lower() in outcome_lower:
                score -= 0.15

        # 限制在 [-1, 1] 范围内
        return max(-1.0, min(1.0, score))

    def _find_related_dnas(self, episode: Episode, max_related: int = 10) -> list[str]:
        """
        找到与当前情景相关的DNA（磁吸搜索）

        组合trigger和outcome作为查询文本，搜索整个DNA池，
        找出语义相关的DNA。
        """
        query_text = f"{episode.trigger} {episode.outcome} {' '.join(episode.actions)}"

        try:
            query_vec = self.system.magnetic.generate_vector(query_text)
            query_dna = DNA(magnetic_vector=query_vec)

            # 用较小池子搜索（不使用索引，避免阈值过滤太激进）
            results = self.system.magnetic.attract(
                query_dna, self.system.pool,
                use_index=False,
            )
        except Exception:
            return []

        related = []
        for dna, score in results[:max_related]:
            if score > 0.15 and dna.id != episode.id:
                # 排除自己
                if dna.dna_type != DNAType.EPISODE:
                    related.append(dna.id)

        return related

    def _reinforce_related_dnas(self, episode: Episode) -> None:
        """
        强化关联DNA的生命周期

        当记录新情景时，相关的DNA被"想起"，获得生命值恢复。
        情感权重越高，强化幅度越大。
        """
        if not hasattr(self.system, 'lifecycle') or not self.system.lifecycle:
            return

        boost_scale = 1.0 + abs(episode.emotional_valence)  # 情感越强，强化越多

        for dna_id in episode.related_dna_ids:
            dna = self.system._dna_by_id.get(dna_id)
            if dna and dna.is_alive:
                # 使用生命周期管理器的巩固强化方法
                importance = min(0.8, abs(episode.emotional_valence))
                self.system.lifecycle.consolidate_reinforce(dna, importance * boost_scale)

    def stats(self) -> dict:
        """引擎统计信息"""
        episode_count = sum(
            1 for d in self.system.pool if d.dna_type == DNAType.EPISODE
        )
        return {
            "total_episodes": episode_count,
            "cached_recent": len(self._recent_episodes),
        }
