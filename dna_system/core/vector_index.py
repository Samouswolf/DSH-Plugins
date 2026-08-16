"""
向量索引层 —— 批量相似度计算，替代 O(N²) 逐对比较
核心: 把所有向量堆成矩阵，一次矩阵乘法算完全部余弦相似度
"""
import numpy as np
from typing import Optional
from .dna import DNA


class VectorIndex:
    """
    向量索引: 维护一个 (N, dim) 的向量矩阵，支持:
    - 批量添加/删除
    - 快速 top-K 最近邻查询
    - 批量聚类（阈值截断）
    """

    def __init__(self, dim: int = 128):
        self.dim = dim
        self._ids: list[str] = []           # DNA id 列表，与矩阵行对齐
        self._matrix: Optional[np.ndarray] = None  # (N, dim) 向量矩阵
        self._norms: Optional[np.ndarray] = None   # (N,) 每行的L2范数
        self._dirty = True  # 矩阵是否需要重建

    def add(self, dna: DNA) -> None:
        """添加一条DNA的向量"""
        self._ids.append(dna.id)
        self._dirty = True

    def add_batch(self, dnas: list[DNA]) -> None:
        """批量添加"""
        for dna in dnas:
            self._ids.append(dna.id)
        self._dirty = True

    def remove(self, dna_id: str) -> None:
        """移除一条DNA"""
        if dna_id in self._ids:
            self._ids.remove(dna_id)
            self._dirty = True

    def rebuild(self, dna_pool: list[DNA]) -> None:
        """从DNA池重建索引矩阵"""
        id_to_dna = {d.id: d for d in dna_pool}
        valid_ids = [did for did in self._ids if did in id_to_dna]
        if not valid_ids:
            self._ids = []
            self._matrix = None
            self._norms = None
            self._dirty = False
            return

        self._ids = valid_ids
        vectors = []
        for did in valid_ids:
            vec = id_to_dna[did].magnetic_vector
            if len(vec) != self.dim:
                vec = np.zeros(self.dim, dtype=np.float32)
                vec[:min(len(id_to_dna[did].magnetic_vector), self.dim)] = \
                    id_to_dna[did].magnetic_vector[:self.dim]
            vectors.append(vec)

        self._matrix = np.array(vectors, dtype=np.float32)  # (N, dim)
        # 预计算范数
        self._norms = np.linalg.norm(self._matrix, axis=1, keepdims=True)  # (N, 1)
        self._norms[self._norms == 0] = 1e-10  # 防除零
        self._dirty = False

    def _ensure_built(self, dna_pool: list[DNA]) -> None:
        """确保索引已构建"""
        if self._dirty:
            self.rebuild(dna_pool)

    def search_top_k(self, query_vec: np.ndarray, k: int = 10,
                     dna_pool: list[DNA] = None) -> list[tuple[str, float]]:
        """
        top-K 最近邻查询
        返回: [(dna_id, similarity), ...] 按相似度降序
        """
        if dna_pool is not None:
            self._ensure_built(dna_pool)
        if self._matrix is None or len(self._ids) == 0:
            return []

        # 查询向量归一化
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []
        q_normalized = query_vec / q_norm

        # 矩阵乘法: (N, dim) @ (dim,) = (N,)
        similarities = self._matrix @ q_normalized

        # top-K（用 argpartition 比 argsort 快）
        k = min(k, len(self._ids))
        if k <= 0:
            return []
        top_indices = np.argpartition(similarities, -k)[-k:]
        top_indices = top_indices[np.argsort(similarities[top_indices])[::-1]]

        return [(self._ids[i], float(similarities[i])) for i in top_indices]

    def search_above_threshold(self, query_vec: np.ndarray, threshold: float,
                                dna_pool: list[DNA] = None) -> list[tuple[str, float]]:
        """阈值查询: 返回所有相似度 >= threshold 的"""
        if dna_pool is not None:
            self._ensure_built(dna_pool)
        if self._matrix is None or len(self._ids) == 0:
            return []

        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0:
            return []
        q_normalized = query_vec / q_norm

        similarities = self._matrix @ q_normalized
        mask = similarities >= threshold
        indices = np.where(mask)[0]
        # 按相似度降序
        indices = indices[np.argsort(similarities[indices])[::-1]]

        return [(self._ids[i], float(similarities[i])) for i in indices]

    def cluster_by_threshold(self, threshold: float,
                              dna_pool: list[DNA] = None) -> list[list[str]]:
        """
        快速聚类: 相似度 >= threshold 的归为一簇
        用并查集实现，比逐对比较快得多
        """
        if dna_pool is not None:
            self._ensure_built(dna_pool)
        if self._matrix is None or len(self._ids) == 0:
            return []

        n = len(self._ids)

        # 计算全部相似度矩阵 (一次矩阵乘法)
        norms = self._norms
        normalized = self._matrix / norms  # (N, dim)
        sim_matrix = normalized @ normalized.T  # (N, N)

        # 并查集
        parent = list(range(n))

        def find(x):
            while parent[x] != x:
                parent[x] = parent[parent[x]]  # 路径压缩
                x = parent[x]
            return x

        def union(x, y):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        # 只处理上三角（避免重复）
        rows, cols = np.where((sim_matrix >= threshold) & (np.triu(np.ones((n, n), dtype=bool), k=1)))
        for r, c in zip(rows, cols):
            union(r, c)

        # 收集聚类结果
        from collections import defaultdict
        clusters = defaultdict(list)
        for i in range(n):
            clusters[find(i)].append(self._ids[i])

        return [members for members in clusters.values() if len(members) >= 1]

    @property
    def size(self) -> int:
        return len(self._ids)
