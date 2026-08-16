"""
磁吸匹配引擎
DNA 具备磁性（归一性），通过确定性TF-IDF哈希向量 + 余弦相似度实现匹配。
多个 DNA 节点周边的空节点因共振形成指向这些 DNA 的虫洞（交集）。

v4: 纯确定性引擎 — 零外部依赖，零网络请求，同输入永远同输出
"""
import re
import hashlib
import numpy as np
from typing import Optional
from .dna import DNA
from .vector_index import VectorIndex

# 模块级导入jieba，避免热路径中重复try/import
try:
    import jieba
    HAS_JIEBA = True
except ImportError:
    jieba = None
    HAS_JIEBA = False


class VectorEngine:
    """向量引擎：纯确定性TF-IDF加权hash，零外部依赖，零网络请求"""

    def __init__(self):
        self.use_semantic = False
        self._model_type = "tfidf-hash-deterministic"

    def generate_vector(self, text, dim=512):
        """生成确定性向量（TF-IDF hash，无ML依赖）"""
        return self._tfidf_hash(text, dim)

    def _tfidf_hash(self, text, dim=128):
        """增强版TF-IDF哈希 v2：jieba分词 + n-gram兜底"""
        text = str(text).lower()
        vec = np.zeros(dim, dtype=np.float32)
        if not text:
            return vec

        tokens = []  # [(token, weight), ...]

        # jieba分词（中文语义精度大幅提升，模块级导入避免重复try/import）
        if HAS_JIEBA:
            words = jieba.lcut(text)
            for w in words:
                w = w.strip()
                if not w:
                    continue
                # 停用词过滤
                if len(w) <= 1 and not ('一' <= w <= '鿿'):
                    continue
                # 词长加权：长词更语义化
                wlen = len(w)
                if wlen >= 3:
                    tokens.append((w, 3.0))  # 多字词高权重
                elif wlen == 2:
                    tokens.append((w, 2.0))  # 双字词中等权重
                else:
                    tokens.append((w, 1.0))  # 单字低权重

        # jieba失败或不可用时，用n-gram兜底
        if not tokens:
            chars = list(text)
            for ch in chars:
                tokens.append((ch, 1.0))
            for i in range(len(chars) - 1):
                bigram = chars[i] + chars[i + 1]
                if len(re.findall(r'[一-鿿]', bigram)) == 2:
                    tokens.append((bigram, 1.5))
                else:
                    tokens.append((bigram, 1.0))
            for i in range(len(chars) - 2):
                trigram = chars[i] + chars[i + 1] + chars[i + 2]
                if len(re.findall(r'[一-鿿]', trigram)) >= 2:
                    tokens.append((trigram, 2.0))
                else:
                    tokens.append((trigram, 1.0))

        # TF（词频）加权
        total_weight = sum(w for _, w in tokens) or 1
        tf_map = {}
        for gram, weight in tokens:
            tf_map[gram] = tf_map.get(gram, 0) + weight

        # IDF权重：罕见词（较长）权重更高
        for gram, count in tf_map.items():
            tf = count / total_weight
            h = hashlib.md5(gram.encode()).digest()
            idx = int.from_bytes(h[:4], 'little') % dim
            idf_sim = 1.0 + min(len(gram) / 10, 0.5)
            vec[idx] += tf * idf_sim

        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def get_info(self) -> dict:
        """返回当前引擎状态"""
        return {
            "use_semantic": self.use_semantic,
            "model_type": self._model_type,
        }


class MagneticEngine:
    """磁吸匹配引擎 (v5: deterministic, zero-dependency)"""

    def __init__(self, threshold: float = 0.3):
        self.threshold = threshold
        self.vector_engine = VectorEngine()
        self.index = VectorIndex(dim=512)

    def generate_vector(self, text: str, dim: int = 512) -> np.ndarray:
        """从文本生成磁吸向量"""
        return self.vector_engine.generate_vector(text, dim)

    def rebuild_index(self, dna_pool: list[DNA]) -> None:
        """从DNA池重建向量索引"""
        self.index.add_batch(dna_pool)
        self.index.rebuild(dna_pool)

    def attract(self, source: DNA, targets: list[DNA],
                use_index: bool = True) -> list[tuple[DNA, float]]:
        """
        计算 source 对 targets 中每个 DNA 的磁吸力
        use_index=True 时用向量索引加速（大池子推荐）
        """
        if not targets:
            return []

        id_to_dna = {d.id: d for d in targets}

        if use_index and len(targets) > 50:
            # 大池子: 用索引加速（索引已在 boot 时构建，直接用）
            if self.index.size == 0:
                self.rebuild_index(targets)
            raw_results = self.index.search_above_threshold(
                source.magnetic_vector, self.threshold, targets
            )
            # 加权调整
            max_len = max((len(str(d.content)) for d in targets), default=1)
            results = []
            for dna_id, sim in raw_results:
                target = id_to_dna.get(dna_id)
                if not target or target.id == source.id:
                    continue
                adjusted = self._adjust_score(source, target, sim, max_len)
                results.append((target, adjusted))
        else:
            # 小池子: 直接算
            src_vec = source.magnetic_vector
            max_len = max((len(str(t.content)) for t in targets), default=1)
            results = []
            for target in targets:
                if target.id == source.id:
                    continue
                sim = self._cosine_similarity(src_vec, target.magnetic_vector)
                if sim < self.threshold:
                    continue
                adjusted = self._adjust_score(source, target, sim, max_len)
                results.append((target, adjusted))

        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def _adjust_score(self, source: DNA, target: DNA,
                      base_sim: float, max_len: int) -> float:
        """计算加权调整后的相似度分数"""
        # 内容长度加权
        len_bonus = min(0.1, len(str(target.content)) / max(max_len, 1) * 0.1)

        # 汇总DNA额外加分
        content_str = str(target.content)
        is_summary = any(k in target.content
                         for k in ('image_text', 'audio_transcript', 'frame_text'))
        summary_bonus = 0.05 if is_summary else 0

        # 查询词直接命中加分
        query_text = str(source.content.get('command', str(source.content)))
        direct_hits = sum(1 for ch in query_text if ch in content_str)
        hit_bonus = min(0.1, direct_hits / max(len(query_text), 1) * 0.1)

        return base_sim + len_bonus + summary_bonus + hit_bonus

    def match_best(self, source: DNA, targets: list[DNA]) -> Optional[tuple[DNA, float]]:
        """返回最佳匹配"""
        results = self.attract(source, targets)
        return results[0] if results else None

    def find_wormhole(self, source: DNA, candidates: list[DNA]) -> list[DNA]:
        """寻找虫洞节点：与source最相似的top 5"""
        results = self.attract(source, candidates)
        return [t for t, _ in results[:5]]

    def cluster(self, dnas: list[DNA]) -> list[list[DNA]]:
        """
        养蛊聚合：相似 DNA 因磁性聚合到一起
        v3: 用 VectorIndex 的并查集聚类，O(N²) 矩阵乘法 + O(N) 并查集
        """
        if len(dnas) < 2:
            return [dnas]

        # 用索引做快速聚类
        if self.index.size == 0:
            self.rebuild_index(dnas)
        id_clusters = self.index.cluster_by_threshold(self.threshold, dnas)

        # 转回 DNA 对象
        id_to_dna = {d.id: d for d in dnas}
        clusters = []
        for id_group in id_clusters:
            cluster = [id_to_dna[did] for did in id_group if did in id_to_dna]
            if cluster:
                clusters.append(cluster)

        return clusters

    @staticmethod
    def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    def get_vector_info(self) -> dict:
        """返回向量引擎状态信息"""
        info = self.vector_engine.get_info()
        info["index_size"] = self.index.size
        return info
