"""
DNA Memory Engine — 主引擎

提供简洁的对外API，封装底层聚类/压缩/预加载逻辑。
"""

import os
import json
import time
import uuid
import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Memory:
    """记忆单元"""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    text: str = ""
    tags: list = field(default_factory=list)
    energy: float = 0.5
    created_at: float = field(default_factory=time.time)
    source_ids: list = field(default_factory=list)
    vector: Optional[np.ndarray] = None


class MemoryEngine:
    """
    可移植的智能体记忆优化引擎

    核心能力:
    1. 语义聚类分级加载（L0/L1/L2）
    2. 无损语义压缩（去重+分组+时间线合并）
    3. 命中学习智能预加载
    """

    def __init__(self, storage_dir: str = "./dna_memory"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)

        # 记忆池
        self.memories: dict[str, Memory] = {}

        # 聚类相关
        self.clusters: dict = {}
        self._cluster_dirty = True
        self._cluster_built = False

        # 压缩相关
        self.archive_dir = os.path.join(storage_dir, "archive")
        os.makedirs(self.archive_dir, exist_ok=True)

        # 命中图
        self.hit_graph: dict[tuple, int] = {}
        self._hit_count = 0
        self._preload_count = 0

        # 加载已有数据
        self._load()

    # ── 公开API ──

    def add(self, text: str, tags: list = None, energy: float = 0.5) -> str:
        """添加一条记忆，返回ID"""
        mem = Memory(text=text, tags=tags or [], energy=energy)
        mem.vector = self._encode(text)
        self.memories[mem.id] = mem
        self._cluster_dirty = True
        self.save()
        return mem.id

    def build_index(self):
        """构建聚类索引"""
        if len(self.memories) < 5:
            return
        self._build_clusters()
        self._cluster_dirty = False
        self._cluster_built = True
        self.save()

    def load_core(self) -> list[Memory]:
        """加载L0核心记忆（启动时调用）"""
        if not self._cluster_built:
            self.build_index()

        core_ids = set()
        for cid, meta in self.clusters.items():
            if meta.get("level") == "L0":
                core_ids.update(meta.get("members", []))

        return [self.memories[mid] for mid in core_ids if mid in self.memories]

    def load_topic(self, query: str) -> list[Memory]:
        """加载L1话题记忆（按需调用）"""
        if not self._cluster_built:
            self.build_index()

        # 找最匹配的簇
        query_vec = self._encode(query)
        best_cid = self._predict_cluster(query_vec)

        if best_cid is None:
            return []

        meta = self.clusters.get(best_cid, {})
        members = meta.get("members", [])

        # 记录命中
        self._record_hit(query, best_cid)

        return [self.memories[mid] for mid in members if mid in self.memories]

    def smart_preload(self, context: str) -> list[Memory]:
        """智能预加载（基于命中历史）"""
        # 提取话题
        topics = self._extract_topics(context)

        # 查命中图找高频簇
        cluster_scores: dict[int, int] = {}
        for topic in topics:
            for (t, cid), count in self.hit_graph.items():
                if t == topic:
                    cluster_scores[cid] = cluster_scores.get(cid, 0) + count

        # 按命中次数排序
        sorted_clusters = sorted(cluster_scores.items(), key=lambda x: -x[1])

        # 加载高频簇的记忆
        loaded = []
        loaded_ids = set()
        for cid, _ in sorted_clusters:
            meta = self.clusters.get(cid, {})
            for mid in meta.get("members", []):
                if mid not in loaded_ids and mid in self.memories:
                    loaded.append(self.memories[mid])
                    loaded_ids.add(mid)

        return loaded

    def compress(self) -> dict:
        """压缩记忆"""
        before_count = len(self.memories)
        archived_count = 0

        for cid, meta in self.clusters.items():
            members = [self.memories[mid] for mid in meta.get("members", [])
                       if mid in self.memories]

            if len(members) < 2:
                continue

            # 去重
            deduped = self._deduplicate(members)

            # 贪心分组
            groups = self._greedy_group(deduped)

            # 合并
            for group in groups:
                if len(group) > 1:
                    merged = self._merge_group(group)
                    # 归档原始
                    for m in group:
                        self._archive(m)
                        if m.id in self.memories:
                            del self.memories[m.id]
                        archived_count += 1
                    # 添加压缩后
                    self.memories[merged.id] = merged

        self._cluster_dirty = True
        self.save()

        return {
            "before": before_count,
            "after": len(self.memories),
            "archived": archived_count,
        }

    def restore(self, memory_id: str) -> bool:
        """从归档恢复记忆"""
        archive_path = os.path.join(self.archive_dir, f"{memory_id}.json")
        if not os.path.exists(archive_path):
            return False

        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            mem = Memory(
                id=data["id"],
                text=data["text"],
                tags=data.get("tags", []),
                energy=data.get("energy", 0.5),
                source_ids=data.get("source_ids", []),
            )
            mem.vector = self._encode(mem.text)
            self.memories[mem.id] = mem
            os.remove(archive_path)
            self.save()
            return True
        except:
            return False

    def stats(self) -> dict:
        """获取系统统计"""
        return {
            "active": len(self.memories),
            "archived": len([f for f in os.listdir(self.archive_dir)
                             if f.endswith(".json")]) if os.path.exists(self.archive_dir) else 0,
            "clusters": len(self.clusters),
            "hit_rate": self._hit_count / max(1, self._preload_count),
            "hit_graph_edges": len(self.hit_graph),
        }

    def save(self):
        """持久化"""
        # 保存记忆池
        pool_path = os.path.join(self.storage_dir, "pool.json")
        pool_data = {}
        for mid, mem in self.memories.items():
            pool_data[mid] = {
                "id": mem.id,
                "text": mem.text,
                "tags": mem.tags,
                "energy": mem.energy,
                "created_at": mem.created_at,
                "source_ids": mem.source_ids,
            }
        with open(pool_path, "w", encoding="utf-8") as f:
            json.dump(pool_data, f, ensure_ascii=False, indent=2)

        # 保存聚类索引
        index_path = os.path.join(self.storage_dir, "cluster_index.json")
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(self.clusters, f, ensure_ascii=False, indent=2)

        # 保存命中图
        hit_path = os.path.join(self.storage_dir, "hit_graph.json")
        hit_data = {
            "edges": {f"{t}|{cid}": count for (t, cid), count in self.hit_graph.items()},
            "hit_count": self._hit_count,
            "preload_count": self._preload_count,
        }
        with open(hit_path, "w", encoding="utf-8") as f:
            json.dump(hit_data, f, ensure_ascii=False, indent=2)

    # ── 内部方法 ──

    def _load(self):
        """加载已有数据"""
        # 加载记忆池
        pool_path = os.path.join(self.storage_dir, "pool.json")
        if os.path.exists(pool_path):
            with open(pool_path, "r", encoding="utf-8") as f:
                pool_data = json.load(f)
            for mid, data in pool_data.items():
                mem = Memory(
                    id=data["id"],
                    text=data["text"],
                    tags=data.get("tags", []),
                    energy=data.get("energy", 0.5),
                    created_at=data.get("created_at", 0),
                    source_ids=data.get("source_ids", []),
                )
                mem.vector = self._encode(mem.text)
                self.memories[mid] = mem

        # 加载聚类索引
        index_path = os.path.join(self.storage_dir, "cluster_index.json")
        if os.path.exists(index_path):
            with open(index_path, "r", encoding="utf-8") as f:
                self.clusters = json.load(f)
            self._cluster_built = bool(self.clusters)

        # 加载命中图
        hit_path = os.path.join(self.storage_dir, "hit_graph.json")
        if os.path.exists(hit_path):
            with open(hit_path, "r", encoding="utf-8") as f:
                hit_data = json.load(f)
            for key, count in hit_data.get("edges", {}).items():
                parts = key.split("|")
                if len(parts) == 2:
                    self.hit_graph[(parts[0], int(parts[1]))] = count
            self._hit_count = hit_data.get("hit_count", 0)
            self._preload_count = hit_data.get("preload_count", 0)

    def _encode(self, text: str) -> np.ndarray:
        """将文本编码为特征向量（简化版，128维）"""
        # 简化实现: 基于字符频率的hash向量
        vec = np.zeros(128, dtype=np.float32)
        for i, ch in enumerate(text[:256]):
            vec[ord(ch) % 128] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def _build_clusters(self):
        """构建K-Means聚类"""
        ids = list(self.memories.keys())
        if len(ids) < 5:
            return

        vectors = np.array([self.memories[mid].vector for mid in ids])
        n_clusters = min(12, len(ids) // 3)

        # K-Means++ 初始化
        centroids = self._kmeans_pp_init(vectors, n_clusters)

        # 迭代
        for _ in range(20):
            # 分配
            labels = self._assign_clusters(vectors, centroids)
            # 更新
            new_centroids = []
            for k in range(n_clusters):
                mask = labels == k
                if mask.any():
                    new_centroids.append(vectors[mask].mean(axis=0))
                else:
                    new_centroids.append(centroids[k])
            centroids = np.array(new_centroids)

        # 构建簇元数据
        self.clusters = {}
        labels = self._assign_clusters(vectors, centroids)
        for k in range(n_clusters):
            member_ids = [ids[i] for i in range(len(ids)) if labels[i] == k]
            if not member_ids:
                continue

            # 确定级别
            level = "L2"
            all_tags = set()
            for mid in member_ids:
                all_tags.update(self.memories[mid].tags)

            if any(t in all_tags for t in ["规则", "流程", "约束", "团队"]):
                level = "L0"
            elif len(member_ids) >= 3:
                level = "L0"
            elif len(member_ids) >= 2:
                level = "L1"

            self.clusters[k] = {
                "level": level,
                "members": member_ids,
                "size": len(member_ids),
                "tags": list(all_tags)[:5],
            }

    def _kmeans_pp_init(self, X: np.ndarray, k: int) -> np.ndarray:
        """K-Means++ 初始化"""
        n = X.shape[0]
        centroids = [X[np.random.randint(n)]]

        for _ in range(k - 1):
            dists = np.array([
                min(np.linalg.norm(x - c) ** 2 for c in centroids)
                for x in X
            ])
            probs = dists / dists.sum()
            idx = np.random.choice(n, p=probs)
            centroids.append(X[idx])

        return np.array(centroids)

    def _assign_clusters(self, X: np.ndarray, centroids: np.ndarray) -> np.ndarray:
        """分配样本到最近的簇"""
        # ||x - c||^2 = ||x||^2 + ||c||^2 - 2*x·c
        x_norms = (X ** 2).sum(axis=1, keepdims=True)
        c_norms = (centroids ** 2).sum(axis=1)
        dists = x_norms + c_norms - 2 * X @ centroids.T
        return dists.argmin(axis=1)

    def _predict_cluster(self, query_vec: np.ndarray) -> Optional[int]:
        """预测查询最匹配的簇"""
        if not self.clusters:
            return None

        best_cid = None
        best_sim = -1

        for cid, meta in self.clusters.items():
            members = meta.get("members", [])
            if not members:
                continue
            # 用成员向量均值作为簇中心
            member_vecs = [self.memories[mid].vector for mid in members
                           if mid in self.memories and self.memories[mid].vector is not None]
            if not member_vecs:
                continue
            centroid = np.mean(member_vecs, axis=0)
            sim = np.dot(query_vec, centroid) / (
                np.linalg.norm(query_vec) * np.linalg.norm(centroid) + 1e-10
            )
            if sim > best_sim:
                best_sim = sim
                best_cid = cid

        return best_cid

    def _record_hit(self, query: str, cluster_id: int):
        """记录命中"""
        topics = self._extract_topics(query)
        for topic in topics:
            key = (topic, cluster_id)
            self.hit_graph[key] = self.hit_graph.get(key, 0) + 1
        self._preload_count += 1
        self._hit_count += 1

    def _extract_topics(self, text: str) -> list[str]:
        """提取话题关键词（简化版）"""
        # 简单分词：按空格和标点分割，取长度>=2的词
        import re
        # 中文：取连续中文字符
        cn_words = re.findall(r'[一-鿿]{2,}', text)
        # 英文：取长度>=3的词
        en_words = [w for w in re.findall(r'[a-zA-Z]{3,}', text)
                    if len(w) >= 3]
        return cn_words + en_words

    def _deduplicate(self, memories: list[Memory]) -> list[Memory]:
        """去重（相似度>0.92）"""
        if len(memories) <= 1:
            return memories

        keep = []
        removed = set()

        for i, m1 in enumerate(memories):
            if m1.id in removed:
                continue
            for j in range(i + 1, len(memories)):
                m2 = memories[j]
                if m2.id in removed:
                    continue
                sim = self._cosine_sim(m1.vector, m2.vector)
                if sim > 0.92:
                    # 保留能量更高的
                    if m1.energy >= m2.energy:
                        removed.add(m2.id)
                    else:
                        removed.add(m1.id)
                        break

        return [m for m in memories if m.id not in removed]

    def _greedy_group(self, memories: list[Memory], threshold: float = 0.70) -> list[list[Memory]]:
        """贪心分组"""
        if len(memories) <= 1:
            return [[m] for m in memories]

        groups = []
        used = set()

        for m in memories:
            if m.id in used:
                continue
            group = [m]
            used.add(m.id)

            for other in memories:
                if other.id in used:
                    continue
                sim = self._cosine_sim(m.vector, other.vector)
                if sim >= threshold:
                    group.append(other)
                    used.add(other.id)

            groups.append(group)

        return groups

    def _merge_group(self, group: list[Memory]) -> Memory:
        """合并一组记忆"""
        # 合并文本
        texts = [m.text for m in group]
        merged_text = " | ".join(texts)
        if len(merged_text) > 500:
            merged_text = merged_text[:500] + "..."

        # 合并标签
        all_tags = set()
        for m in group:
            all_tags.update(m.tags)

        # 合并向量（均值）
        vectors = [m.vector for m in group if m.vector is not None]
        merged_vector = np.mean(vectors, axis=0) if vectors else None

        # 记录来源
        source_ids = [m.id for m in group]

        mem = Memory(
            text=merged_text,
            tags=list(all_tags),
            energy=max(m.energy for m in group),
            source_ids=source_ids,
        )
        mem.vector = merged_vector
        return mem

    def _archive(self, memory: Memory):
        """归档记忆"""
        path = os.path.join(self.archive_dir, f"{memory.id}.json")
        data = {
            "id": memory.id,
            "text": memory.text,
            "tags": memory.tags,
            "energy": memory.energy,
            "created_at": memory.created_at,
            "source_ids": memory.source_ids,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _cosine_sim(self, a: np.ndarray, b: np.ndarray) -> float:
        """余弦相似度"""
        if a is None or b is None:
            return 0.0
        dot = np.dot(a, b)
        na = np.linalg.norm(a)
        nb = np.linalg.norm(b)
        return dot / (na * nb + 1e-10)
