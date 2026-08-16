"""
DNA 生命周期管理
DNA 具备生命周期，结束后不会消亡，会坍缩变成小碎片。
碎片多次被指针吸引后，会重获新生（重构）。
就像记忆：被遗忘就碎片化，想起时便会被填充，想多了就细节化。

v2: 双链螺旋强化 —— 两条DNA形成闭环后，它们的关联网络整体强化
"""
import time
from .dna import DNA, DNAType
from .magnetic import MagneticEngine


class LifecycleManager:
    """生命周期管理器"""

    def __init__(self, magnetic: MagneticEngine):
        self.magnetic = magnetic
        self.fragments: list[DNA] = []  # 碎片池
        self._system = None  # 延迟绑定，用于模式补全

    def tick(self, dnas: list[DNA], hours_elapsed: float) -> list[DNA]:
        """
        时间推进，处理所有DNA的生命周期
        返回：存活的DNA + 被重构的DNA
        """
        alive = []
        for dna in dnas:
            dna.decay(hours_elapsed)

            if dna.is_alive and not dna.is_fragmented:
                alive.append(dna)
            elif dna.is_fragmented:
                # 坍缩为碎片
                frags = dna.fragment()
                self.fragments.extend(frags)
            # dna.lifetime <= 0 的直接丢弃

        # 清理过期的碎片
        self.fragments = [f for f in self.fragments if f.lifetime > 0]

        return alive

    def reinforce(self, dna: DNA) -> None:
        """强化：经常被访问的DNA，生命值恢复更多"""
        dna.access()
        # 额外强化：被访问次数越多，抗衰减越强
        bonus = min(20, dna.access_count * 0.5)
        dna.lifetime = min(100, dna.lifetime + bonus)

    def reconstruct(self, pointer_dna: DNA, min_fragments: int = 3) -> DNA | None:
        """
        重构：碎片被指针多次吸引后重获新生
        当有足够多的碎片指向同一parent时，尝试重组。

        增强（Phase 4）：碎片不足时尝试用模式补全引擎从情景记忆中补全。
        """
        parent_id = pointer_dna.parent_id
        if not parent_id:
            return None

        # 找到指向同一parent的所有碎片
        related = [f for f in self.fragments if f.parent_id == parent_id]

        # 碎片足够时走经典路径
        if len(related) >= min_fragments:
            return self._reconstruct_from_fragments(parent_id, related)

        # 碎片不足：尝试用模式补全
        return self._reconstruct_with_completion(parent_id, related)

    def _reconstruct_from_fragments(self, parent_id: str, related: list[DNA]) -> DNA | None:
        """从碎片重组DNA（经典路径）"""
        # 重组：合并碎片的内容
        merged_content = {}
        for frag in related:
            key = frag.content.get("key", "")
            val = frag.content.get("fragment", "")
            if key in merged_content:
                merged_content[key] = str(merged_content[key]) + " | " + str(val)
            else:
                merged_content[key] = val

        # 创建重构的DNA
        reconstructed = DNA(
            id=parent_id,  # 继承原始ID
            dna_type=DNAType.MEMORY,
            content=merged_content,
            magnetic_vector=related[0].magnetic_vector * 1.5,
            tags=related[0].tags,
            lifetime=50,  # 重构后生命值中等
            parent_id=None,
        )

        # 从碎片池移除已使用的碎片
        for frag in related:
            frag.lifetime = 0  # 标记为已使用
        self.fragments = [f for f in self.fragments if f.lifetime > 0]

        return reconstructed

    def _reconstruct_with_completion(self, parent_id: str, available_fragments: list[DNA]) -> DNA | None:
        """
        用模式补全辅助重构：当碎片不足时，从已有碎片提取线索，
        在情景记忆中搜索最匹配的完整记忆来填补缺失部分。

        仅在主系统已绑定且可用时生效。
        """
        if not self._system or not available_fragments:
            return None

        try:
            from .pattern_completion import PatternCompletion
        except ImportError:
            return None

        # 从已有碎片中提取线索文本
        cue_parts = []
        for frag in available_fragments:
            val = frag.content.get("fragment", "")
            if val:
                cue_parts.append(str(val))
            key = frag.content.get("key", "")
            if key:
                cue_parts.append(str(key))

        if not cue_parts:
            return None

        cue_text = " ".join(cue_parts)
        completer = PatternCompletion(self._system)
        best_episode, score = completer._find_best_match(cue_text)

        if not best_episode or score < 0.15:
            return None

        # 用情景的完整内容构建重构DNA
        episode_content = {
            "trigger": best_episode.trigger,
            "context": best_episode.context,
            "actions": best_episode.actions,
            "outcome": best_episode.outcome,
            "emotional_valence": best_episode.emotional_valence,
            "reconstructed_via": "pattern_completion",
            "match_score": round(score, 3),
        }

        reconstructed = DNA(
            id=parent_id,
            dna_type=DNAType.MEMORY,
            content=episode_content,
            magnetic_vector=available_fragments[0].magnetic_vector * 1.2,
            tags=available_fragments[0].tags + ["pattern_completed"],
            lifetime=40,
            parent_id=None,
        )

        # 清理已使用的碎片
        for frag in available_fragments:
            frag.lifetime = 0
        self.fragments = [f for f in self.fragments if f.lifetime > 0]

        return reconstructed

    def bind_system(self, system):
        """绑定主系统，用于模式补全等高级功能"""
        self._system = system

    def check_and_reconstruct(self, dnas: list[DNA]) -> list[DNA]:
        """检查碎片池，尝试重构所有可重构的DNA"""
        reconstructed = []
        for frag in list(self.fragments):
            result = self.reconstruct(frag)
            if result:
                reconstructed.append(result)
        return dnas + reconstructed

    def consolidate_reinforce(self, dna: DNA, importance: float = 0.5) -> None:
        """
        巩固强化：睡眠巩固阶段按重要性强化DNA

        Args:
            dna: 要强化的DNA
            importance: 重要性权重 (0~1)，影响强化幅度
        """
        # 重要性越高，恢复越多
        boost = 5 + importance * 20
        dna.lifetime = min(100, dna.lifetime + boost)
        dna.access_count += 1
        dna.last_accessed = time.time()

    def double_helix_reinforce(self, source_dna: DNA, target_dna: DNA) -> None:
        """
        双链螺旋强化：两条DNA形成闭环后，它们的关联网络整体强化
        - 找到两者之间的中间节点（碎片）
        - 共享标签的节点获得额外加成
        """
        # 找到两者相关的碎片
        source_links = [f for f in self.fragments if f.parent_id == source_dna.id]
        target_links = [f for f in self.fragments if f.parent_id == target_dna.id]

        # 共享标签的节点获得额外加成
        shared_tags = set(source_dna.tags) & set(target_dna.tags)

        # 强化source相关的碎片
        for s in source_links:
            if any(t in s.tags for t in shared_tags):
                s.lifetime = min(30, s.lifetime + 10)

        # 强化target相关的碎片
        for t in target_links:
            if any(tag in t.tags for tag in shared_tags):
                t.lifetime = min(30, t.lifetime + 10)

        # 双链强化完成（静默，避免Agent输出污染）

    def fragment_health(self, dnas: list[DNA]) -> dict:
        """
        记忆健康度分析：每条话题的存活DNA比例
        返回按话题标签分组的健康度统计
        """
        from collections import Counter, defaultdict

        # 按首标签分组
        topic_groups = defaultdict(list)
        for dna in dnas:
            if dna.tags:
                topic = dna.tags[0]  # 用第一个标签作为话题
            else:
                topic = "未分类"
            topic_groups[topic].append(dna)

        health = {}
        for topic, group in topic_groups.items():
            total = len(group)
            alive = sum(1 for d in group if d.lifetime > 20)
            fragmented = sum(1 for d in group if d.is_fragmented)
            dead = sum(1 for d in group if not d.is_alive)

            # 只有存活的可用于计算
            if total > 0:
                survival_rate = alive / total
                avg_lifetime = sum(d.lifetime for d in group) / total
                total_access = sum(d.access_count for d in group)
            else:
                survival_rate = 0
                avg_lifetime = 0
                total_access = 0

            health[topic] = {
                "total": total,
                "alive": alive,
                "fragmented": fragmented,
                "dead": dead,
                "survival_rate": round(survival_rate, 3),
                "avg_lifetime": round(avg_lifetime, 1),
                "total_access": total_access,
            }

        return health

    def stats(self) -> dict:
        return {
            "fragment_count": len(self.fragments),
            "fragment_total_lifetime": sum(f.lifetime for f in self.fragments),
        }
