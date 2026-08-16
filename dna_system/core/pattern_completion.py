"""
模式补全引擎 —— 从部分线索重建完整记忆
Phase 4: 海马体进化

模拟人类海马体的模式补全功能：
- 当只有部分线索时，自动匹配最相关的完整情景记忆
- 用已存储的完整情景来填充缺失信息
- 提供轻量级 hint 功能，返回相关记忆摘要
"""
import time
import json
import numpy as np
from .dna import DNA, DNAType


class PatternCompletion:
    """模式补全引擎：从部分线索重建完整记忆"""

    def __init__(self, system):
        """
        Args:
            system: DNASystem 主系统实例，提供 magnetic 和 pool 访问
        """
        self.system = system

    # ===== 公开API =====

    def complete(self, partial_cue: dict) -> object | None:
        """
        从部分线索重建完整记忆

        流程：
        1. 用 partial_cue 生成向量
        2. 磁吸搜索相关DNA
        3. 找到这些DNA所属的Episode
        4. 选择最佳匹配
        5. 用Episode的context填充缺失部分

        Args:
            partial_cue: 部分线索字典，可包含 trigger/context/actions/outcome 等字段。
                        例如: {"trigger": "修复碰撞检测", "outcome": "?"}

        Returns:
            补全后的 Episode 对象，如果没找到匹配则返回 None
        """
        if not partial_cue or not isinstance(partial_cue, dict):
            return None

        # 1. 从 partial_cue 生成查询文本和向量
        query_text = json.dumps(partial_cue, ensure_ascii=False)
        query_vec = self.system.magnetic.generate_vector(query_text)
        query_dna = DNA(magnetic_vector=query_vec)

        # 2. 搜索相关DNA
        try:
            results = self.system.magnetic.attract(
                query_dna, self.system.pool,
                use_index=(len(self.system.pool) > 50),
            )
        except Exception:
            return None

        if not results:
            return None

        # 3. 找到这些DNA所属的Episode
        episode_scores: dict[str, tuple[object, float]] = {}
        for dna, score in results[:20]:
            if score < 0.15:  # 低于阈值的不考虑
                continue
            # 如果DNA本身是EPISODE
            if dna.dna_type == DNAType.EPISODE:
                ep_id = dna.id
                if ep_id not in episode_scores or score > episode_scores[ep_id][1]:
                    try:
                        from .episodic import Episode
                        ep = Episode.from_dna(dna)
                        episode_scores[ep_id] = (ep, score)
                    except Exception:
                        pass
            # 如果DNA关联了某个episode
            elif dna.episode_id:
                ep_id = dna.episode_id
                if ep_id not in episode_scores or score > episode_scores[ep_id][1]:
                    ep_dna = self.system._dna_by_id.get(ep_id)
                    if ep_dna and ep_dna.dna_type == DNAType.EPISODE:
                        try:
                            from .episodic import Episode
                            ep = Episode.from_dna(ep_dna)
                            episode_scores[ep_id] = (ep, score)
                        except Exception:
                            pass

        if not episode_scores:
            return None

        # 4. 选择最佳匹配（按分数排序）
        sorted_eps = sorted(episode_scores.values(), key=lambda x: x[1], reverse=True)
        best_episode, best_score = sorted_eps[0]

        # 5. 用最佳匹配填充缺失部分
        completed = self._fill_missing(best_episode, partial_cue)
        return completed

    def hint(self, partial_text: str, top_k: int = 5) -> list[dict]:
        """
        轻量提示：返回相关DNA摘要，不重建完整Episode

        适用于快速搜索场景，不需要完整的模式补全。

        Args:
            partial_text: 部分文本/线索
            top_k: 返回前K个结果

        Returns:
            相关DNA摘要列表:
            [
                {
                    "dna_id": "...",
                    "dna_type": "episode" | "memory" | "pattern",
                    "summary": "摘要文本",
                    "score": 0.85,
                    "tags": [...],
                },
                ...
            ]
        """
        if not partial_text:
            return []

        query_vec = self.system.magnetic.generate_vector(partial_text)
        query_dna = DNA(magnetic_vector=query_vec)

        try:
            results = self.system.magnetic.attract(
                query_dna, self.system.pool,
                use_index=(len(self.system.pool) > 50),
            )
        except Exception:
            return []

        hints = []
        for dna, score in results[:top_k]:
            if score < 0.1:
                continue

            # 提取摘要
            summary = self._extract_summary(dna)

            hints.append({
                "dna_id": dna.id,
                "dna_type": dna.dna_type.value,
                "summary": summary,
                "score": round(score, 4),
                "tags": dna.tags[:5],
                "created_at": dna.created_at,
            })

        return hints

    # ===== 内部方法 =====

    def _fill_missing(self, episode, partial_cue: dict):
        """
        用完整Episode的内容填充partial_cue中缺失的字段

        策略：
        - 如果partial_cue中已提供有效值，保留用户输入
        - 如果partial_cue中该字段为空/不存在/占位符，用episode的值填充
        - 情感权重始终继承自episode（因为是同一个情景）
        """
        from .episodic import Episode

        def _is_valid(value) -> bool:
            """判断值是否为有效内容（非空，非占位符）"""
            if value is None:
                return False
            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    return False
                # 占位符
                if stripped in ("?", "??", "???", "unknown", "未知", "..."):
                    return False
                return True
            if isinstance(value, (list, dict)):
                return len(value) > 0
            return True

        trigger = partial_cue.get("trigger")
        actions = partial_cue.get("actions")
        outcome = partial_cue.get("outcome")

        completed = Episode(
            id=episode.id,  # 继承原始Episode ID
            timestamp=episode.timestamp,
            trigger=trigger if _is_valid(trigger) else episode.trigger,
            context=_merge_context(episode.context, partial_cue.get("context", {})),
            actions=actions if _is_valid(actions) else episode.actions,
            outcome=outcome if _is_valid(outcome) else episode.outcome,
            emotional_valence=episode.emotional_valence,
            related_dna_ids=episode.related_dna_ids,
        )

        return completed

    def _find_best_match(self, query_text: str) -> tuple[object | None, float]:
        """
        找到最佳匹配的情景（供 lifecycle.py 的模式补全重构使用）

        Args:
            query_text: 查询文本

        Returns:
            (Episode | None, score)
        """
        partial_cue = {"query": query_text}
        result = self.complete(partial_cue)
        if result is None:
            return None, 0.0

        # 用query_text重新计算匹配分数
        query_vec = self.system.magnetic.generate_vector(query_text)
        query_dna = DNA(magnetic_vector=query_vec)
        target_dna = self.system._dna_by_id.get(result.id)
        if target_dna:
            sim = float(np.dot(query_vec, target_dna.magnetic_vector) / (
                max(np.linalg.norm(query_vec), 1e-8) *
                max(np.linalg.norm(target_dna.magnetic_vector), 1e-8)
            ))
            return result, sim
        return result, 0.0

    def _extract_summary(self, dna: DNA) -> str:
        """从DNA中提取可读摘要"""
        content = dna.content

        # EPISODE类型
        if dna.dna_type == DNAType.EPISODE:
            trigger = content.get("trigger", "")
            outcome = content.get("outcome", "")
            actions = content.get("actions", [])
            action_str = " → ".join(actions) if actions else ""
            parts = [p for p in [trigger, action_str, outcome] if p]
            return " | ".join(parts)[:120]

        # PATTERN类型
        if dna.dna_type == DNAType.PATTERN:
            return content.get("pattern_name", "")[:120] or str(content)[:120]

        # 通用
        for key in ("summary", "text", "command", "pattern_name"):
            if key in content and content[key]:
                return str(content[key])[:120]

        return str(content)[:120]

    def stats(self) -> dict:
        """引擎统计信息"""
        episode_count = sum(
            1 for d in self.system.pool if d.dna_type == DNAType.EPISODE
        )
        return {
            "episodes_searchable": episode_count,
            "total_pool_size": len(self.system.pool),
        }


def _merge_context(base: dict, override: dict) -> dict:
    """合并上下文：override中的值覆盖base，但保留base中override没有的键"""
    if not override:
        return dict(base)
    merged = dict(base)
    merged.update(override)
    return merged
