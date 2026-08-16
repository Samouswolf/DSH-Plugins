"""
认知地图 —— 记忆的空间组织，形成"记忆地形图"
Phase 5: 海马体进化

模拟人类海马体的空间认知功能：
- 用PCA将高维磁吸向量降维到2D空间
- 支持按距离查找附近记忆
- 支持找主题聚类中心
- 导出地图数据供可视化
"""
import time
import numpy as np
from .dna import DNA


class CognitiveMap:
    """
    认知地图：将记忆组织为2D空间中的点

    使用Numpy SVD实现简单PCA降维（零外部依赖，只需numpy）。
    """

    def __init__(self, system):
        """
        Args:
            system: DNASystem 主系统实例
        """
        self.system = system
        self.coordinates: dict[str, tuple[float, float]] = {}  # dna_id -> (x, y)
        self._map_built: bool = False
        self._map_method: str = ""

    # ===== 公开API =====

    def build_map(self, dnas: list[DNA] = None, method: str = "pca") -> dict[str, tuple[float, float]]:
        """
        构建记忆地图：将DNA向量降维到2D

        Args:
            dnas: 要映射的DNA列表，默认使用系统池中的所有DNA
            method: 降维方法，目前仅支持 "pca"

        Returns:
            {dna_id: (x, y), ...} 坐标字典
        """
        if dnas is None:
            dnas = self.system.pool

        if not dnas:
            self.coordinates = {}
            self._map_built = False
            return {}

        # 提取所有向量
        vectors = []
        ids = []
        for dna in dnas:
            vec = dna.magnetic_vector
            if vec is not None and len(vec) > 0:
                vectors.append(vec)
                ids.append(dna.id)

        if len(vectors) < 2:
            # 只有1个点，放在原点
            if ids:
                self.coordinates = {ids[0]: (0.0, 0.0)}
            self._map_built = True
            self._map_method = method
            return dict(self.coordinates)

        # 堆成矩阵
        matrix = np.array(vectors, dtype=np.float64)  # (N, D)

        if method == "pca":
            coords_2d = self._pca_reduce(matrix, n_components=2)
        else:
            # 不支持的method，回退到pca
            coords_2d = self._pca_reduce(matrix, n_components=2)

        # 存储坐标
        self.coordinates = {}
        for i, dna_id in enumerate(ids):
            self.coordinates[dna_id] = (
                float(coords_2d[i, 0]),
                float(coords_2d[i, 1]),
            )

        self._map_built = True
        self._map_method = method
        return dict(self.coordinates)

    def find_nearby(self, dna_id: str, radius: float = 1.0) -> list[str]:
        """
        找到某个记忆附近的其它记忆（欧氏距离）

        Args:
            dna_id: 目标DNA的ID
            radius: 搜索半径（在2D PCA空间中的欧氏距离）

        Returns:
            按距离升序排列的附近DNA ID列表
        """
        if not self._map_built:
            self.build_map()

        if dna_id not in self.coordinates:
            return []

        cx, cy = self.coordinates[dna_id]
        nearby = []

        for other_id, (ox, oy) in self.coordinates.items():
            if other_id == dna_id:
                continue
            dist = ((cx - ox) ** 2 + (cy - oy) ** 2) ** 0.5
            if dist <= radius:
                nearby.append((other_id, dist))

        # 按距离升序排列
        nearby.sort(key=lambda x: x[1])
        return [nid for nid, _ in nearby]

    def find_cluster_center(self, topic: str) -> str | None:
        """
        找到某个主题在认知地图中的聚类中心DNA ID

        找到所有标签包含 topic 的DNA，计算它们在2D空间中的质心，
        然后返回离质心最近的DNA的ID。

        Args:
            topic: 主题标签（如 "贪吃蛇", "碰撞检测"）

        Returns:
            聚类中心DNA ID，如果没有找到则返回 None
        """
        if not self._map_built:
            self.build_map()

        # 找到所有相关DNA（标签包含topic）
        related = []
        for dna in self.system.pool:
            if dna.id in self.coordinates:
                if topic in dna.tags or topic in str(dna.content):
                    related.append(dna)

        if not related:
            return None

        # 计算质心
        coords_list = [self.coordinates[d.id] for d in related]
        center_x = sum(c[0] for c in coords_list) / len(coords_list)
        center_y = sum(c[1] for c in coords_list) / len(coords_list)

        # 找到离质心最近的DNA
        min_dist = float('inf')
        center_dna_id = None
        for dna in related:
            cx, cy = self.coordinates[dna.id]
            dist = ((center_x - cx) ** 2 + (center_y - cy) ** 2) ** 0.5
            if dist < min_dist:
                min_dist = dist
                center_dna_id = dna.id

        return center_dna_id

    def export_map_data(self, edge_radius: float = 0.5, max_edges_per_node: int = 3) -> dict:
        """
        导出地图数据供可视化使用

        Args:
            edge_radius: 边连接的半径阈值
            max_edges_per_node: 每个节点最多连接的边数

        Returns:
            {
                "nodes": [
                    {
                        "id": dna_id,
                        "x": float, "y": float,
                        "type": "episode" | "memory" | "pattern" | ...,
                        "tags": [...],
                        "lifetime": float,
                        "access_count": int,
                    },
                    ...
                ],
                "edges": [
                    {"source": dna_id, "target": dna_id},
                    ...
                ],
            }
        """
        if not self._map_built:
            self.build_map()

        nodes = []
        for dna in self.system.pool:
            coord = self.coordinates.get(dna.id)
            if coord is None:
                continue  # 跳过未能映射的DNA

            nodes.append({
                "id": dna.id,
                "x": round(coord[0], 4),
                "y": round(coord[1], 4),
                "type": dna.dna_type.value,
                "tags": dna.tags[:5],
                "lifetime": round(dna.lifetime, 1),
                "access_count": dna.access_count,
            })

        # 生成边：在2D空间中距离近的连接
        edges = []
        # 用KD树思想简化：对每个节点找附近节点
        for dna in self.system.pool:
            if dna.id not in self.coordinates:
                continue
            nearby = self.find_nearby(dna.id, radius=edge_radius)
            for other_id in nearby[:max_edges_per_node]:
                # 避免重复边（按ID排序确保唯一性）
                edge_key = tuple(sorted([dna.id, other_id]))
                if edge_key not in {(e["source"], e["target"]) for e in edges}:
                    edges.append({"source": dna.id, "target": other_id})

        # 限制总边数（避免过多）
        if len(edges) > 500:
            edges = edges[:500]

        return {"nodes": nodes, "edges": edges}

    # ===== 内部方法 =====

    def _pca_reduce(self, matrix: np.ndarray, n_components: int = 2) -> np.ndarray:
        """
        用Numpy SVD实现简单PCA降维

        步骤：
        1. 中心化（减去均值）
        2. SVD分解
        3. 取前 n_components 个主成分投影

        Args:
            matrix: (N, D) 数据矩阵
            n_components: 目标维度

        Returns:
            (N, n_components) 降维后的坐标
        """
        N, D = matrix.shape

        # 1. 中心化
        mean = np.mean(matrix, axis=0, keepdims=True)
        centered = matrix - mean

        # 2. SVD分解（full_matrices=False 节省内存）
        # U: (N, N) 或 (N, min(N,D)), S: (min(N,D),), Vt: (min(N,D), D)
        try:
            U, S, Vt = np.linalg.svd(centered, full_matrices=False)
        except np.linalg.LinAlgError:
            # SVD失败时返回随机坐标作为fallback
            np.random.seed(42)
            return np.random.randn(N, n_components).astype(np.float64) * 0.1

        # 3. 取前 n_components 个奇异向量投影
        k = min(n_components, len(S))
        # 投影: X_centered @ Vt[:k].T = U[:, :k] @ diag(S[:k])
        reduced = U[:, :k] * S[:k]

        # 如果k < n_components，用0填充
        if k < n_components:
            padding = np.zeros((N, n_components - k), dtype=np.float64)
            reduced = np.hstack([reduced, padding])

        return reduced

    def stats(self) -> dict:
        """引擎统计信息"""
        return {
            "map_built": self._map_built,
            "map_method": self._map_method,
            "mapped_dnas": len(self.coordinates),
            "total_pool": len(self.system.pool),
        }
