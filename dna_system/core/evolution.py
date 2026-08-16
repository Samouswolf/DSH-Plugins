"""
养蛊进化引擎
DNA 因为磁性会聚合 —— 吞噬、合并、进化。
相似的 DNA 碎片聚合后自动提炼出更高层的模式（洞察）。

v2: 多维度竞争力评分 + 语义模式识别
"""
import re
import time
from collections import Counter, defaultdict
from .dna import DNA, DNAType, StrandType
from .magnetic import MagneticEngine


class EvolutionEngine:
    """养蛊进化引擎"""

    # 进化阈值比查询阈值更高，避免过度合并
    EVOLUTION_THRESHOLD = 0.95  # 只有几乎相同的DNA才会被合并
    MIN_CLUSTER_SIZE = 3        # 至少3条DNA才会触发合并

    def __init__(self, magnetic: MagneticEngine):
        self.magnetic = magnetic
        self.patterns: list[DNA] = []  # 进化产物（洞察/模式）

    def devour(self, dnas: list[DNA]) -> list[DNA]:
        """
        吞噬合并：聚合相似的DNA，强者吞噬弱者（多维度竞争力）
        只有高度相似（>=0.6）且数量>=3的DNA才会被合并
        返回：吞噬后的存活DNA（强者更强）+ 新产生的模式DNA
        """
        # 用更高的阈值做聚类
        original_threshold = self.magnetic.threshold
        self.magnetic.threshold = self.EVOLUTION_THRESHOLD
        clusters = self.magnetic.cluster(dnas)
        self.magnetic.threshold = original_threshold

        survivors = []
        new_patterns = []
        merged_count = 0

        for cluster in clusters:
            # 小簇直接保留，不合并
            if len(cluster) < self.MIN_CLUSTER_SIZE:
                survivors.extend(cluster)
                continue

            # 多维度竞争力评分
            for d in cluster:
                content_len = len(str(d.content))
                len_weight = min(1.0, content_len / 500)
                d.fitness = d.access_count * 0.4 + d.lifetime * 0.3 + len_weight * 0.3

            # 按竞争力排序
            cluster.sort(key=lambda d: d.fitness, reverse=True)
            alpha = cluster[0]  # 最强DNA
            prey = cluster[1:]  # 被吞噬的

            for p in prey:
                # 按竞争力比例吸收（不是全部吞掉）
                ratio = p.fitness / (alpha.fitness + 0.001)
                # 吞噬内容和标签
                if hasattr(alpha, 'content') and hasattr(p, 'content'):
                    merged = dict(alpha.content)
                    merged.update(p.content)
                    alpha.content = merged
                alpha.tags = list(set(alpha.tags + p.tags))
                # 向量融合（按比例）
                alpha.magnetic_vector = (
                    alpha.magnetic_vector * (1 - ratio * 0.3) +
                    p.magnetic_vector * (ratio * 0.3)
                )
                p.lifetime = 0  # 被吞噬后消亡

            # 聚合后增强
            total_prey_fitness = sum(p.fitness for p in prey)
            alpha.lifetime = min(100, alpha.lifetime + len(prey) * 5)
            alpha.access_count += len(prey)
            alpha.fitness = min(100, alpha.fitness + total_prey_fitness * 0.1)
            survivors.append(alpha)
            merged_count += len(prey)

            # 聚合 >= 3 条且总体 fitness > 1.5 → 才产生洞察
            total_fitness = sum(d.fitness for d in cluster)
            if len(cluster) >= 3 and total_fitness > 1.5:
                pattern = self._evolve_pattern(cluster)
                new_patterns.append(pattern)

        self.patterns.extend(new_patterns)
        if merged_count > 0:
            print(f"  [吞噬] 合并 {merged_count} 条DNA → {len(survivors)} 条存活")
        return survivors + new_patterns

    def _evolve_pattern(self, cluster: list[DNA]) -> DNA:
        """真正的模式识别：语义聚类 + TF-IDF主题词 + 结构化洞察"""
        # 1. 计算簇内语义相似度均值（置信度）
        similarities = []
        for i in range(len(cluster)):
            for j in range(i + 1, len(cluster)):
                sim = self.magnetic._cosine_similarity(
                    cluster[i].magnetic_vector,
                    cluster[j].magnetic_vector
                )
                similarities.append(sim)
        avg_similarity = sum(similarities) / len(similarities) if similarities else 0.5
        confidence = min(1.0, avg_similarity * 1.5)

        # 2. 提取所有内容文本和标签
        all_texts = []
        all_tags = []
        all_files = set()
        for dna in cluster:
            content_str = str(dna.content)
            all_texts.append(content_str)
            all_tags.extend(dna.tags)
            src = dna.content.get('source_file', dna.content.get('source', dna.source))
            if src:
                all_files.add(str(src))

        # 3. 用TF-IDF找出核心主题词（排除通用词）
        combined_text = ' '.join(all_texts)
        cn_words = re.findall(r'[一-鿿]{2,}', combined_text)
        word_counter = Counter(cn_words)
        common_words = {'一个', '这个', '那个', '可以', '没有', '我们', '他们',
                        '进行', '通过', '使用', '什么', '如果', '因为', '所以',
                        '但是', '已经', '时候', '以后', '知道'}
        core_words = [w for w, c in word_counter.most_common(20)
                      if w not in common_words and c >= max(2, len(cluster) // 2)]

        # 4. 标签统计
        tag_counter = Counter(all_tags)
        top_tags = [t for t, c in tag_counter.most_common(5) if c > 1]

        # 5. 提取核心洞察（公共信息）
        common_keys = set(cluster[0].content.keys())
        for dna in cluster[1:]:
            common_keys &= set(dna.content.keys())

        core_insight_parts = []
        for key in list(common_keys)[:3]:
            values = [str(d.content[key])[:100] for d in cluster if key in d.content]
            if len(set(values)) <= 1 and values:
                core_insight_parts.append(f"{key}={values[0]}")

        # 6. 建议操作
        suggested_action = ""
        keywords_lower = combined_text.lower()
        if any(w in keywords_lower for w in ['todo', '待办', 'fix', '修复', 'bug']):
            suggested_action = "需要修复的问题检测到，建议分配工匠处理"
        elif any(w in keywords_lower for w in ['优化', 'improve', '重构', 'refactor']):
            suggested_action = "检测到优化/重构需求，建议安排迭代"
        elif any(w in keywords_lower for w in ['新增', 'add', 'feature', '功能']):
            suggested_action = "检测到新增功能需求，建议评估开发"

        # 7. 自动生成模式名称
        name_parts = core_words[:3] if core_words else top_tags[:3]
        pattern_name = f"模式: {'/'.join(name_parts)}" if name_parts else "未命名模式"

        # 8. 构建结构的模式内容
        pattern_content = {
            "pattern_name": pattern_name,
            "source_count": len(cluster),
            "key_tags": top_tags,
            "core_words": core_words[:10],
            "core_insight": '; '.join(core_insight_parts) if core_insight_parts else "无明确共同信息",
            "confidence": round(confidence, 3),
            "related_files": list(all_files)[:10],
            "suggested_action": suggested_action,
            "avg_similarity": round(avg_similarity, 3),
        }

        # 模式磁吸向量：聚合簇中所有DNA向量的加权平均
        pattern_vec = sum(d.magnetic_vector * d.lifetime for d in cluster)
        norm = __import__('numpy').linalg.norm(pattern_vec)
        if norm > 0:
            pattern_vec = pattern_vec / norm

        pattern = DNA(
            dna_type=DNAType.PATTERN,
            strand=StrandType.FORWARD,
            content=pattern_content,
            magnetic_vector=pattern_vec,
            tags=top_tags,
            lifetime=80,
            modality="pattern"
        )

        # 记录进化来源
        for dna in cluster:
            pattern.child_ids.append(dna.id)
            dna.parent_id = pattern.id

        return pattern

    def cross_breed(self, dnas: list[DNA]) -> list[DNA]:
        """
        异种杂交：扫描虫洞交叉点，识别跨类型DNA节点对进行重组试验
        原理：不同类型的DNA（如图片OCR文本 + 代码片段）在磁吸空间中
        距离接近时，杂交产生新的跨模态DNA
        """
        hybrids = []
        clusters = self.magnetic.cluster(dnas)

        for cluster in clusters:
            if len(cluster) < 2:
                continue
            # 找出簇中不同类型的DNA
            types_in_cluster = set(d.dna_type for d in cluster)
            if len(types_in_cluster) < 2:
                continue  # 只有同类型，无需杂交

            # 按类型分组
            by_type = defaultdict(list)
            for d in cluster:
                by_type[d.dna_type].append(d)

            # 跨类型配对杂交
            type_list = list(by_type.keys())
            for i in range(len(type_list)):
                for j in range(i + 1, len(type_list)):
                    for a in by_type[type_list[i]][:3]:
                        for b in by_type[type_list[j]][:3]:
                            hybrid = self._breed_pair(a, b)
                            if hybrid:
                                hybrids.append(hybrid)

        if hybrids:
            self.patterns.extend(hybrids)
            print(f"  [异种杂交] 产生 {len(hybrids)} 个跨模态节点")

        return hybrids

    def _breed_pair(self, a: DNA, b: DNA) -> DNA | None:
        """杂交两个不同类型DNA，产生跨模态后代"""
        # 合并内容：取两边的关键字段
        hybrid_content = {
            "breed_type": f"{a.dna_type.value}×{b.dna_type.value}",
            "parent_a_summary": str(a.content)[:150],
            "parent_b_summary": str(b.content)[:150],
            "common_tags": list(set(a.tags) & set(b.tags)),
            "modality_a": a.modality,
            "modality_b": b.modality,
        }

        # 如果有实际重叠的关键词，提取出来
        a_text = str(a.content)
        b_text = str(b.content)
        shared_keywords = []
        for tag in set(a.tags + b.tags):
            if tag in a_text and tag in b_text:
                shared_keywords.append(tag)
        if shared_keywords:
            hybrid_content["shared_keywords"] = shared_keywords[:10]

        # 杂交向量：两者的加权融合
        hybrid_vec = a.magnetic_vector * 0.5 + b.magnetic_vector * 0.5
        norm = __import__('numpy').linalg.norm(hybrid_vec)
        if norm > 0:
            hybrid_vec = hybrid_vec / norm

        hybrid = DNA(
            dna_type=DNAType.PATTERN,
            content=hybrid_content,
            magnetic_vector=hybrid_vec,
            tags=list(set(a.tags + b.tags)),
            lifetime=60,
            modality="cross_modal",
        )
        hybrid.child_ids.extend([a.id, b.id])
        return hybrid

    def get_patterns(self) -> list[DNA]:
        """获取所有进化出的模式"""
        return [p for p in self.patterns if p.is_alive]

    def query_by_pattern(self, query: str) -> list[DNA]:
        """根据查询找到相关模式"""
        query_vec = self.magnetic.generate_vector(query)
        results = self.magnetic.attract(
            DNA(magnetic_vector=query_vec),
            self.patterns
        )
        return [p for p, _ in results]

    def summarize_knowledge(self, dnas: list[DNA]) -> dict:
        """基于当前DNA池生成知识摘要"""
        # 统计内容类型分布
        type_dist = Counter(d.dna_type.value for d in dnas)
        modality_dist = Counter(d.modality for d in dnas)

        # 提取高频标签
        all_tags = []
        source_files = set()
        for d in dnas:
            all_tags.extend(d.tags[:5])
            src = d.content.get('source_image', d.content.get('source_file', d.source))
            if src:
                source_files.add(str(src)[:60])

        top_tags = [t for t, c in Counter(all_tags).most_common(20) if c > 1]

        # 汇总文本内容（取最长的几条）
        texts = []
        for d in dnas:
            text = str(d.content)
            if len(text) > 100:
                texts.append(text[:500])
        longest_texts = sorted(texts, key=len, reverse=True)[:5]

        return {
            "total_dnas": len(dnas),
            "type_distribution": dict(type_dist),
            "modality_distribution": dict(modality_dist),
            "source_files": list(source_files),
            "top_tags": top_tags,
            "pattern_count": len(self.get_patterns()),
            "sample_content": longest_texts,
        }
