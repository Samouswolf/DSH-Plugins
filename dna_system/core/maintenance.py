"""
定期维护模块 —— 清理低质量DNA、优化存储、重建索引
"""
import time
from collections import Counter
from .dna import DNA, DNAType
from .quality_filter import quality_filter
from .smart_tagger import tagger


class MaintenanceEngine:
    """维护引擎"""

    def __init__(self, system):
        self.system = system

    def run_full_maintenance(self) -> dict:
        """
        运行完整维护流程
        返回: 维护报告
        """
        report = {
            "timestamp": time.time(),
            "before": {
                "dna_count": len(self.system.pool),
                "storage": self.system.store.size(),
            },
            "actions": [],
        }

        # 1. 清理无意义标签
        tag_result = self._clean_tags()
        report["actions"].append(tag_result)

        # 2. 过滤低质量内容
        quality_result = self._filter_low_quality()
        report["actions"].append(quality_result)

        # 3. 合并重复内容
        dedup_result = self._deduplicate()
        report["actions"].append(dedup_result)

        # 4. 重新计算向量（如果需要）
        revector_result = self._check_vectors()
        report["actions"].append(revector_result)

        # 5. 重建索引
        self.system.magnetic.rebuild_index(self.system.pool)

        report["after"] = {
            "dna_count": len(self.system.pool),
            "storage": self.system.store.size(),
        }

        return report

    def _clean_tags(self) -> dict:
        """清理无意义标签"""
        cleaned_count = 0
        for dna in self.system.pool:
            original_tags = dna.tags
            cleaned_tags = tagger.clean_existing_tags(original_tags)

            # 如果标签被清理了，重新提取
            if len(cleaned_tags) < len(original_tags):
                # 从内容中提取新标签
                content_text = str(dna.content)
                new_tags = tagger.extract_tags(content_text, cleaned_tags)
                dna.tags = new_tags
                cleaned_count += 1

        return {
            "action": "clean_tags",
            "cleaned_count": cleaned_count,
        }

    def _filter_low_quality(self) -> dict:
        """过滤低质量内容"""
        removed_count = 0
        to_remove = []

        for dna in self.system.pool:
            content_text = str(dna.content)
            should_keep, score = quality_filter.should_ingest(content_text)

            if not should_keep:
                to_remove.append(dna)
                removed_count += 1

        # 移除低质量DNA
        for dna in to_remove:
            self.system.pool.remove(dna)
            self.system.store.remove(dna.id)

        return {
            "action": "filter_low_quality",
            "removed_count": removed_count,
        }

    def _deduplicate(self) -> dict:
        """合并重复内容"""
        # 按内容哈希分组
        content_hashes = {}
        for dna in self.system.pool:
            content_str = str(dna.content)
            content_hash = hash(content_str) % (2**32)

            if content_hash not in content_hashes:
                content_hashes[content_hash] = []
            content_hashes[content_hash].append(dna)

        # 找出重复的
        duplicates_removed = 0
        for content_hash, dnas in content_hashes.items():
            if len(dnas) > 1:
                # 保留第一个，移除其他
                for dna in dnas[1:]:
                    self.system.pool.remove(dna)
                    self.system.store.remove(dna.id)
                    duplicates_removed += 1

        return {
            "action": "deduplicate",
            "removed_count": duplicates_removed,
        }

    def _check_vectors(self) -> dict:
        """检查并重新生成向量"""
        revector_count = 0

        for dna in self.system.pool:
            # 检查向量是否有效
            norm = sum(v**2 for v in dna.magnetic_vector) ** 0.5
            if norm < 0.1 or norm > 2.0:
                # 重新生成向量
                content_text = str(dna.content)
                dna.magnetic_vector = self.system.magnetic.generate_vector(content_text)
                revector_count += 1

        return {
            "action": "revector",
            "revector_count": revector_count,
        }

    def get_quality_report(self) -> dict:
        """获取质量报告"""
        total = len(self.system.pool)

        # 标签质量
        all_tags = []
        for d in self.system.pool:
            all_tags.extend(d.tags)
        tag_counts = Counter(all_tags)
        meaningful_tags = sum(1 for t in tag_counts if tagger._is_meaningful_tag(t))

        # 内容质量
        short_content = sum(1 for d in self.system.pool if len(str(d.content)) < 50)
        long_content = sum(1 for d in self.system.pool if len(str(d.content)) > 500)

        # 访问频率
        never_accessed = sum(1 for d in self.system.pool if d.access_count == 0)

        return {
            "total_dna": total,
            "tag_quality": {
                "total_tags": len(tag_counts),
                "meaningful_tags": meaningful_tags,
                "meaningful_ratio": meaningful_tags / len(tag_counts) if tag_counts else 0,
            },
            "content_quality": {
                "short_content": short_content,
                "long_content": long_content,
                "short_ratio": short_content / total if total else 0,
            },
            "access_quality": {
                "never_accessed": never_accessed,
                "access_ratio": (total - never_accessed) / total if total else 0,
            },
        }


def run_maintenance(system) -> dict:
    """运行维护的便捷函数"""
    engine = MaintenanceEngine(system)
    return engine.run_full_maintenance()
