"""
语义聚类引擎 -- 记忆按需加载的核心

Phase 4: 将平铺记忆按语义自动分组，启动时只加载核心规则簇，其他簇按需唤醒。
基于现有 VectorIndex 的向量矩阵做 K-Means 聚类，复用 SmartTagger 生成簇标签。
"""
import json
import math
import re
import time
import numpy as np
from pathlib import Path
from typing import Optional
from collections import Counter

from .smart_tagger import SmartTagger
from .brain_encoder import identify_game, extract_tokens, TFIDFEncoder


# K-Means 最大迭代次数
_MAX_ITER = 50
# 收敛阈值
_CONVERGE_THRESHOLD = 1e-4


class SemanticCluster:
    """语义聚类引擎"""

    def __init__(self, n_clusters: int = 12, seed: int = 42, tfidf_encoder: TFIDFEncoder = None):
        self.n_clusters = n_clusters
        self.seed = seed
        self.tfidf_encoder = tfidf_encoder
        self.clusters: dict[int, list[str]] = {}       # cluster_id -> [dna_ids]
        self.centroids: dict[int, np.ndarray] = {}      # cluster_id -> centroid_vector
        self.cluster_meta: dict[int, dict] = {}         # cluster_id -> {label, keywords, size, level}
        self._dna_to_cluster: dict[str, int] = {}       # dna_id -> cluster_id
        self._built = False

    def fit(self, dna_pool: list, tagger: Optional[SmartTagger] = None) -> dict:
        """
        从DNA池构建聚类

        优化版：
        - 自适应K值: K = min(12, max(3, n // 5))
        - TF-IDF向量编码（优先）或磁吸向量（降级）
        - 碎片合并: 成员<3的簇合并到最近的大簇
        - 标签去重: 同名簇合并

        Args:
            dna_pool: DNA对象列表
            tagger: 标签提取器（可选，默认创建新实例）

        Returns:
            聚类结果摘要
        """
        if not dna_pool:
            self._built = False
            return {"clusters": 0, "total_dnas": 0}

        if tagger is None:
            tagger = SmartTagger()

        # 0. 过滤超大记忆（代码文件等），不参与聚类
        _MAX_CLUSTER_CHARS = 4000
        dna_pool = [d for d in dna_pool if len(str(d.content or "")) <= _MAX_CLUSTER_CHARS]

        # 1. 提取ID
        ids = [d.id for d in dna_pool]
        n_samples = len(ids)

        # 2. 自适应K值: K = min(12, max(3, n // 5))
        actual_k = min(12, max(3, n_samples // 5))
        actual_k = min(actual_k, n_samples)

        if actual_k < 2:
            # 样本太少，全部归为一簇
            vec = self._get_vectors(dna_pool)
            self.clusters = {0: ids}
            self.centroids = {0: vec.mean(axis=0)}
            self._dna_to_cluster = {did: 0 for did in ids}
            self.cluster_meta = {0: {
                "label": "全部记忆",
                "keywords": [],
                "size": n_samples,
                "level": "L0",
                "score": 1.0,
                "games": {},
            }}
            self._built = True
            return {"clusters": 1, "total_dnas": n_samples}

        # 3. 生成向量（优先TF-IDF，降级磁吸向量）
        vectors = self._get_vectors(dna_pool)

        # 4. K-Means 聚类
        labels, centroids = self._kmeans(vectors, actual_k)

        # 5. 分配簇
        self.clusters = {}
        self.centroids = {}
        self._dna_to_cluster = {}
        for cid in range(actual_k):
            member_indices = np.where(labels == cid)[0]
            member_ids = [ids[i] for i in member_indices]
            self.clusters[cid] = member_ids
            self.centroids[cid] = centroids[cid]
            for did in member_ids:
                self._dna_to_cluster[did] = cid

        # 6. 碎片合并（成员<3的簇合并到最近的大簇）
        self._merge_fragments(vectors, ids)

        # 7. 为每个簇生成标签和级别（基于TF-IDF关键词 + 综合评分）
        self._generate_cluster_meta(dna_pool, tagger)

        # 8. 标签去重（同名簇合并）
        self._deduplicate_labels(dna_pool, vectors, ids)

        self._built = True
        return {
            "clusters": len(self.clusters),
            "total_dnas": n_samples,
            "cluster_sizes": {cid: len(members) for cid, members in self.clusters.items()},
        }

    def _get_vectors(self, dna_pool: list) -> np.ndarray:
        """生成向量矩阵（优先TF-IDF，降级磁吸向量）"""
        if self.tfidf_encoder and self.tfidf_encoder._built:
            return np.array(
                [self.tfidf_encoder.encode(self._extract_text(d)) for d in dna_pool],
                dtype=np.float32,
            )
        return np.array([d.magnetic_vector for d in dna_pool], dtype=np.float32)

    def _merge_fragments(self, vectors: np.ndarray, ids: list[str]):
        """
        碎片合并：成员<3的簇合并到最近的大簇

        - 找出所有碎片簇（成员<3）
        - 找出所有大簇（成员>=3）
        - 如果没有大簇，合并所有碎片到一个簇
        - 否则每个碎片合并到最近的大簇
        - 合并后更新大簇中心
        """
        MIN_CLUSTER_SIZE = 3
        id_to_idx = {did: i for i, did in enumerate(ids)}

        fragments = []
        large_clusters = []
        for cid in list(self.clusters.keys()):
            if len(self.clusters[cid]) < MIN_CLUSTER_SIZE:
                fragments.append(cid)
            else:
                large_clusters.append(cid)

        if not fragments:
            return

        # 如果没有大簇，合并所有碎片到第一个碎片簇
        if not large_clusters:
            keep_cid = fragments[0]
            for frag_cid in fragments[1:]:
                self.clusters[keep_cid].extend(self.clusters[frag_cid])
                for did in self.clusters[frag_cid]:
                    self._dna_to_cluster[did] = keep_cid
                del self.clusters[frag_cid]
                del self.centroids[frag_cid]
            # 重新计算中心
            keep_indices = [id_to_idx[did] for did in self.clusters[keep_cid] if did in id_to_idx]
            if keep_indices:
                self.centroids[keep_cid] = vectors[keep_indices].mean(axis=0)
            return

        # 有大簇时，每个碎片合并到最近的大簇
        for frag_cid in fragments:
            if frag_cid not in self.centroids:
                continue
            frag_centroid = self.centroids[frag_cid]

            best_cid = None
            best_dist = float('inf')
            for large_cid in large_clusters:
                if large_cid not in self.centroids:
                    continue
                dist = float(np.sum((frag_centroid - self.centroids[large_cid]) ** 2))
                if dist < best_dist:
                    best_dist = dist
                    best_cid = large_cid

            if best_cid is not None:
                self.clusters[best_cid].extend(self.clusters[frag_cid])
                for did in self.clusters[frag_cid]:
                    self._dna_to_cluster[did] = best_cid

                # 更新大簇中心
                best_indices = [id_to_idx[did] for did in self.clusters[best_cid] if did in id_to_idx]
                if best_indices:
                    self.centroids[best_cid] = vectors[best_indices].mean(axis=0)

                # 删除碎片簇
                del self.clusters[frag_cid]
                del self.centroids[frag_cid]

    def _deduplicate_labels(self, dna_pool: list, vectors: np.ndarray, ids: list[str]):
        """
        标签去重：如果两个簇标签相同，合并它们

        - 收集所有簇的标签
        - 找出重复标签的簇
        - 合并同名簇（保留第一个）
        - 合并后更新中心
        """
        label_to_cids: dict[str, list[int]] = {}
        for cid, meta in self.cluster_meta.items():
            label = meta.get("label", "")
            if label and label != f"簇{cid}":
                if label not in label_to_cids:
                    label_to_cids[label] = []
                label_to_cids[label].append(cid)

        id_to_idx = {did: i for i, did in enumerate(ids)}

        for label, cids in label_to_cids.items():
            if len(cids) <= 1:
                continue

            # 保留第一个，合并其他
            keep_cid = cids[0]
            for merge_cid in cids[1:]:
                if merge_cid not in self.clusters:
                    continue
                self.clusters[keep_cid].extend(self.clusters[merge_cid])
                for did in self.clusters[merge_cid]:
                    self._dna_to_cluster[did] = keep_cid
                del self.clusters[merge_cid]
                del self.centroids[merge_cid]
                if merge_cid in self.cluster_meta:
                    del self.cluster_meta[merge_cid]

            # 更新中心
            keep_indices = [id_to_idx[did] for did in self.clusters[keep_cid] if did in id_to_idx]
            if keep_indices:
                self.centroids[keep_cid] = vectors[keep_indices].mean(axis=0)

    def _kmeans(self, vectors: np.ndarray, k: int) -> tuple:
        """
        K-Means 聚类（纯numpy实现）

        Args:
            vectors: (N, dim) 向量矩阵
            k: 簇数

        Returns:
            (labels, centroids) — labels: (N,) 簇标签, centroids: (k, dim) 簇中心
        """
        rng = np.random.RandomState(self.seed)
        n, dim = vectors.shape

        # K-Means++ 初始化
        centroids = self._kmeans_pp_init(vectors, k, rng)

        labels = np.zeros(n, dtype=np.int32)
        for iteration in range(_MAX_ITER):
            # 分配：逐样本计算最近中心，避免 (N, k, dim) 临时数组
            # 使用 ||a-b||^2 = ||a||^2 + ||b||^2 - 2*a·b 展开
            # 空间从 O(N*k*dim) 降到 O(N*k)
            vec_sq = np.sum(vectors ** 2, axis=1)          # (N,)
            cen_sq = np.sum(centroids ** 2, axis=1)        # (k,)
            cross = vectors @ centroids.T                  # (N, k)
            dists_sq = vec_sq[:, np.newaxis] + cen_sq[np.newaxis, :] - 2 * cross  # (N, k)
            # 数值安全：截断负值
            np.maximum(dists_sq, 0, out=dists_sq)
            new_labels = np.argmin(dists_sq, axis=1)

            # 收敛检查
            if np.array_equal(new_labels, labels):
                break
            labels = new_labels

            # 更新中心
            for cid in range(k):
                members = vectors[labels == cid]
                if len(members) > 0:
                    centroids[cid] = members.mean(axis=0)
                else:
                    # 空簇：从距离当前中心最远的非空簇成员重新初始化
                    max_dist = -1.0
                    farthest_idx = -1
                    for other_cid in range(k):
                        if other_cid == cid:
                            continue
                        other_members = vectors[labels == other_cid]
                        if len(other_members) == 0:
                            continue
                        other_dists = np.sum((other_members - centroids[cid]) ** 2, axis=1)
                        local_max = other_dists.max()
                        if local_max > max_dist:
                            max_dist = local_max
                            farthest_idx = int(np.argmax(other_dists))
                            farthest_vec = other_members[farthest_idx]
                    if farthest_idx >= 0:
                        centroids[cid] = farthest_vec

        return labels, centroids

    def _kmeans_pp_init(self, vectors: np.ndarray, k: int, rng) -> np.ndarray:
        """K-Means++ 初始化（更优的初始中心选择）"""
        n = vectors.shape[0]
        centroids = np.empty((k, vectors.shape[1]), dtype=np.float32)

        # 第一个中心随机选
        idx = rng.randint(n)
        centroids[0] = vectors[idx]

        for i in range(1, k):
            # 计算每个点到最近已选中心的距离平方（同 _kmeans 的优化）
            vec_sq = np.sum(vectors ** 2, axis=1)
            cen_sq = np.sum(centroids[:i] ** 2, axis=1)
            cross = vectors @ centroids[:i].T
            dists_sq = vec_sq[:, np.newaxis] + cen_sq[np.newaxis, :] - 2 * cross
            np.maximum(dists_sq, 0, out=dists_sq)
            min_dists = dists_sq.min(axis=1)
            # 按距离平方成比例选择
            total = min_dists.sum()
            if total < 1e-10:
                # 所有点都重合，随机选
                idx = rng.randint(n)
            else:
                probs = min_dists / total
                idx = rng.choice(n, p=probs)
            centroids[i] = vectors[idx]

        return centroids

    def _generate_cluster_meta(self, dna_pool: list, tagger: SmartTagger):
        """
        为每个簇生成标签、关键词和加载级别

        优化版：
        - 用 TF-IDF 提取簇内关键词作为标签（降级: SmartTagger）
        - 过滤: 排除文件名、纯数字、停用词等无意义标签
        - 综合评分: 簇大小*0.4 + 访问频率*0.3 + 近期活跃*0.3
        - L0/L1/L2 基于评分排名分配
        """
        id_to_dna = {d.id: d for d in dna_pool}
        cluster_scores = {}

        # 停用词
        _stopwords = {
            "的", "了", "是", "在", "有", "和", "就", "不", "也", "都", "吗", "呢", "吧", "啊",
            "the", "a", "an", "is", "are", "was", "were", "how", "why", "what", "when", "where",
            "on", "in", "at", "to", "for", "of", "with", "by",
        }

        for cid, member_ids in self.clusters.items():
            all_tags = []
            all_text = []
            game_counter = Counter()

            for did in member_ids:
                dna = id_to_dna.get(did)
                if not dna:
                    continue
                if dna.tags:
                    all_tags.extend(dna.tags)
                text = self._extract_text(dna)
                if text:
                    all_text.append(text)
                    game = identify_game(text)
                    if game:
                        game_counter[game] += 1

            # --- 标签生成（TF-IDF关键词优先，降级SmartTagger） ---
            tfidf_keywords = self._extract_tfidf_keywords(member_ids, id_to_dna, n_keywords=8)
            tag_counts = Counter(all_tags)
            top_keywords = [t for t, _ in tag_counts.most_common(8)]

            # 过滤无意义标签
            def _is_good_label(t):
                if not t or len(t) <= 1:
                    return False
                if t in _stopwords:
                    return False
                if t.isdigit():
                    return False
                # 过滤文件名
                if '.' in t and any(t.endswith(ext) for ext in ['.html', '.js', '.py', '.md', '.json']):
                    return False
                # 过滤代码变量名（纯小写英文、长度<=4、常见代码模式）
                if re.match(r'^[a-z]{1,4}$', t):
                    return False
                # 过滤camelCase/snake_case代码标识符
                if re.match(r'^[a-z]+[A-Z]', t) or '_' in t:
                    return False
                # 过滤hex颜色/ID片段
                if re.match(r'^[0-9a-f]{6,}$', t):
                    return False
                return True

            # 确定标签：优先SmartTagger（词典匹配最准），降级高频标签，最后TF-IDF
            label = None

            # 优先: SmartTagger（基于词典的游戏名/技术词匹配）
            if len(all_text) > 20:
                import random as _rng
                sampled = _rng.sample(all_text, 20)
            else:
                sampled = all_text
            combined_text = " ".join(sampled)
            smart_tags = tagger.extract_tags(combined_text, all_tags)
            for st in smart_tags:
                if _is_good_label(st):
                    label = st
                    break

            # 降级: 高频标签（来自记忆自身的tags字段）
            if not label:
                for t in top_keywords:
                    if _is_good_label(t):
                        label = t
                        break

            # 最后: TF-IDF关键词（过滤掉纯ASCII短词，避免代码变量名）
            if not label:
                for kw in tfidf_keywords:
                    if _is_good_label(kw) and not re.match(r'^[a-z_]{1,8}$', kw):
                        label = kw
                        break

            if not label:
                label = f"簇{cid}"

            # 合并关键词列表（SmartTagger + 高频标签 + TF-IDF，去重）
            merged_keywords = []
            seen = set()
            # 先加SmartTagger的标签（最准）
            for st in smart_tags[:3]:
                if st not in seen and _is_good_label(st):
                    merged_keywords.append(st)
                    seen.add(st)
            # 再加高频标签（来自记忆自身的tags字段）
            for t in top_keywords[:3]:
                if t not in seen and _is_good_label(t):
                    merged_keywords.append(t)
                    seen.add(t)
            # 最后加TF-IDF关键词（过滤纯ASCII短词）
            for kw in tfidf_keywords[:3]:
                if kw not in seen and _is_good_label(kw) and not re.match(r'^[a-z_]{1,8}$', kw):
                    merged_keywords.append(kw)
                    seen.add(kw)

            # --- 综合评分 ---
            score = self._compute_cluster_score(dna_pool, member_ids)
            cluster_scores[cid] = score

            self.cluster_meta[cid] = {
                "label": label,
                "keywords": merged_keywords[:5],
                "size": len(member_ids),
                "score": score,
                "games": dict(game_counter.most_common(3)),
            }

        # --- 基于评分排名分配 L0/L1/L2 ---
        sorted_cids = sorted(cluster_scores.keys(), key=lambda c: cluster_scores[c], reverse=True)
        n = len(sorted_cids)
        for i, cid in enumerate(sorted_cids):
            if i < n * 0.5:
                self.cluster_meta[cid]["level"] = "L0"
            elif i < n * 0.8:
                self.cluster_meta[cid]["level"] = "L1"
            else:
                self.cluster_meta[cid]["level"] = "L2"

    def _compute_cluster_score(self, dna_pool: list, member_ids: list[str]) -> float:
        """
        综合评分: 簇大小*0.4 + 访问频率*0.3 + 近期活跃*0.3

        用于 L0/L1/L2 级别排名。
        """
        id_to_dna = {d.id: d for d in dna_pool}

        size = len(member_ids)
        access_counts = []
        last_accessed_list = []

        for did in member_ids:
            dna = id_to_dna.get(did)
            if not dna:
                continue
            access_counts.append(getattr(dna, 'access_count', 0))
            last_accessed_list.append(getattr(dna, 'last_accessed', 0))

        avg_access = sum(access_counts) / len(access_counts) if access_counts else 0
        avg_recency = sum(last_accessed_list) / len(last_accessed_list) if last_accessed_list else 0

        # 归一化（对数缩放，避免极端值主导）
        size_score = min(size / 20.0, 1.0)  # 20个成员即满分
        access_score = min(math.log(1 + avg_access) / math.log(100), 1.0)  # 100次访问即满分
        recency_score = min(avg_recency / (time.time() - 86400 * 30), 1.0) if avg_recency > 0 else 0  # 30天内活跃即满分

        return size_score * 0.4 + access_score * 0.3 + recency_score * 0.3

    def _extract_tfidf_keywords(self, member_ids: list[str], id_to_dna: dict, n_keywords: int = 5) -> list[str]:
        """
        用 TF-IDF 提取簇内关键词

        - 收集簇内所有 token
        - 计算 TF-IDF 分数（使用全局 IDF）
        - 过滤停用词、文件名、纯数字
        - 返回 top N 关键词
        """
        if not self.tfidf_encoder or not self.tfidf_encoder._built:
            return []

        token_counts: Counter = Counter()
        for did in member_ids:
            dna = id_to_dna.get(did)
            if not dna:
                continue
            text = self._extract_text(dna)
            if text:
                tokens = extract_tokens(text)
                token_counts.update(tokens)

        if not token_counts:
            return []

        total_tokens = sum(token_counts.values())
        _stopwords = {
            "的", "了", "是", "在", "有", "和", "就", "不", "也", "都", "吗", "呢", "吧", "啊",
            "the", "a", "an", "is", "are", "was", "were",
        }

        scores: dict[str, float] = {}
        for token, count in token_counts.items():
            if token in _stopwords or len(token) <= 1 or token.isdigit():
                continue
            if '.' in token and any(token.endswith(ext) for ext in ['.html', '.js', '.py', '.md', '.json']):
                continue
            tf = count / total_tokens
            idf = self.tfidf_encoder.idf.get(token, 1.0)
            scores[token] = tf * idf

        sorted_tokens = sorted(scores.keys(), key=lambda t: scores[t], reverse=True)
        return sorted_tokens[:n_keywords]

    def _extract_text(self, dna) -> str:
        """从DNA中提取文本"""
        content = dna.content
        if not content:
            return dna.source or ""
        for key in ("summary", "text", "full_text", "command", "pattern_name", "compressed_text"):
            if key in content and content[key]:
                return str(content[key])
        return ""

    def predict(self, query_text: str, brain_encoder=None) -> tuple[Optional[int], float]:
        """
        查询应该加载哪个簇

        优先使用 TF-IDF 编码（与聚类向量一致），降级使用磁吸引擎。

        Args:
            query_text: 查询文本
            brain_encoder: 磁吸引擎（降级用），需要有 generate_vector 方法

        Returns:
            (cluster_id, similarity) 或 (None, 0.0)
        """
        if not self._built or not self.centroids:
            return None, 0.0

        # 优先使用 TF-IDF 编码（与聚类维度一致）
        if self.tfidf_encoder and self.tfidf_encoder._built:
            query_vec = self.tfidf_encoder.encode(query_text)
        elif brain_encoder is not None:
            query_vec = brain_encoder.generate_vector(query_text, dim=512)
        else:
            return None, 0.0

        if query_vec is None or len(query_vec) == 0:
            return None, 0.0

        # 归一化
        q_norm = np.linalg.norm(query_vec)
        if q_norm < 1e-10:
            return None, 0.0
        q_normalized = query_vec / q_norm

        # 找最近的簇中心
        best_cid = None
        best_sim = -1.0
        for cid, centroid in self.centroids.items():
            c_norm = np.linalg.norm(centroid)
            if c_norm < 1e-10:
                continue
            sim = float(np.dot(q_normalized, centroid / c_norm))
            if sim > best_sim:
                best_sim = sim
                best_cid = cid

        return best_cid, best_sim

    def get_cluster(self, cluster_id: int) -> list[str]:
        """获取簇内所有记忆ID"""
        return self.clusters.get(cluster_id, [])

    def get_cluster_by_dna(self, dna_id: str) -> Optional[int]:
        """获取某个DNA所属的簇"""
        return self._dna_to_cluster.get(dna_id)

    def get_meta(self, cluster_id: int) -> Optional[dict]:
        """获取簇元信息"""
        return self.cluster_meta.get(cluster_id)

    def get_all_meta(self) -> dict:
        """获取所有簇的元信息"""
        return {
            cid: {
                "label": meta["label"],
                "keywords": meta["keywords"],
                "size": meta["size"],
                "level": meta["level"],
                "games": meta.get("games", {}),
            }
            for cid, meta in self.cluster_meta.items()
        }

    def get_level_clusters(self, level: str) -> dict[int, list[str]]:
        """获取指定级别的所有簇"""
        result = {}
        for cid, meta in self.cluster_meta.items():
            if meta.get("level") == level:
                result[cid] = self.clusters[cid]
        return result

    def save(self, path: str):
        """持久化聚类索引到JSON"""
        data = {
            "version": 1,
            "n_clusters": self.n_clusters,
            "built_at": time.time(),
            "clusters": {str(cid): members for cid, members in self.clusters.items()},
            "centroids": {str(cid): vec.tolist() for cid, vec in self.centroids.items()},
            "meta": {str(cid): meta for cid, meta in self.cluster_meta.items()},
            "dna_to_cluster": self._dna_to_cluster,
        }
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, path: str) -> bool:
        """从JSON加载聚类索引"""
        p = Path(path)
        if not p.exists():
            return False
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != 1:
                return False
            self.n_clusters = data.get("n_clusters", 12)
            self.clusters = {int(k): v for k, v in data.get("clusters", {}).items()}
            self.centroids = {int(k): np.array(v, dtype=np.float32) for k, v in data.get("centroids", {}).items()}
            self.cluster_meta = {int(k): v for k, v in data.get("meta", {}).items()}
            self._dna_to_cluster = data.get("dna_to_cluster", {})
            self._built = True
            return True
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            return False

    def stats(self) -> dict:
        """聚类统计"""
        level_counts = {}
        for meta in self.cluster_meta.values():
            lvl = meta.get("level", "unknown")
            level_counts[lvl] = level_counts.get(lvl, 0) + 1

        return {
            "built": self._built,
            "n_clusters": len(self.clusters),
            "total_dnas": sum(len(m) for m in self.clusters.values()),
            "level_distribution": level_counts,
        }
