# Phase 4: 语义聚类 — 记忆按需加载

## 目标
将183条平铺记忆按语义自动分组，启动时只加载核心规则簇，其他簇按需唤醒。

## 当前问题
- 启动时全量加载183条记忆 → token消耗大
- 记忆平铺无结构 → 检索效率低
- 无关记忆占用上下文窗口

## 设计方案

### 1. 聚类引擎 (SemanticCluster)

基于现有 `VectorIndex` 的向量矩阵，使用 K-Means 聚类：

```python
class SemanticCluster:
    """语义聚类引擎"""

    def __init__(self, n_clusters=12):
        self.n_clusters = n_clusters
        self.clusters = {}          # cluster_id -> [dna_ids]
        self.centroids = {}         # cluster_id -> centroid_vector
        self.cluster_meta = {}      # cluster_id -> {label, keywords, size}

    def fit(self, dna_pool):
        """从DNA池构建聚类"""
        # 1. 提取所有记忆的特征向量
        # 2. K-Means聚类
        # 3. 为每个簇生成标签（从SmartTagger提取高频关键词）

    def predict(self, query_text):
        """查询应该加载哪个簇"""
        # 提取查询的特征向量
        # 找最近的簇中心
        # 返回cluster_id

    def get_cluster(self, cluster_id):
        """获取簇内所有记忆ID"""
        return self.clusters.get(cluster_id, [])
```

### 2. 三级加载策略

| 级别 | 内容 | 何时加载 | 条数 |
|------|------|----------|------|
| L0 核心 | 关键规则、团队流程 | 启动时必加载 | ~20条 |
| L1 话题 | 当前游戏相关记忆 | 用户提到游戏名时 | ~30-50条/簇 |
| L2 深层 | 具体Bug细节、历史决策 | 具体问题触发 | 按需 |

### 3. 簇标签生成

复用现有 `SmartTagger`，从簇内记忆提取高频标签：
- 游戏名标签：贪吃蛇、塔防、修仙...
- 技术标签：Bug修复、性能优化、UI/UX...
- 严重度标签：🔴严重、🟡中等、🟢轻微

### 4. 命中反馈记录

```python
class ClusterHitTracker:
    """簇命中追踪器"""

    def __init__(self):
        self.hit_log = []  # [{timestamp, cluster_id, context}]

    def record_hit(self, cluster_id, context):
        """记录一次命中"""
        self.hit_log.append({...})

    def get_hot_clusters(self, hours=24):
        """获取最近N小时高频命中簇"""
        # 用于Phase 6的预测预加载
```

### 5. 文件结构

```
dna_system/core/
├── semantic_cluster.py    # 新增：聚类引擎
├── cluster_loader.py      # 新增：三级加载器
├── cluster_tracker.py     # 新增：命中追踪
└── ...existing files
```

### 6. 集成点

- `DNASystem.__init__()` → 初始化聚类引擎
- `DNASystem.load()` → L0核心加载
- `Brain.recall()` → 根据查询加载相关簇
- `sync_dna_context.py` → 生成聚类索引

### 7. 预期效果

| 指标 | 当前 | Phase 4后 |
|------|------|-----------|
| 启动加载记忆数 | 183条 | ~20条(L0) |
| 启动token消耗 | 高 | 降低80%+ |
| 检索精度 | 平铺扫描 | 簇内精查 |
| 按需加载 | 无 | 有 |

### 8. 实现步骤

1. 创建 `semantic_cluster.py` — 聚类引擎核心
2. 创建 `cluster_loader.py` — 三级加载策略
3. 创建 `cluster_tracker.py` — 命中追踪
4. 修改 `DNASystem` — 集成聚类
5. 修改 `sync_dna_context.py` — 生成聚类索引
6. 测试 — 验证聚类质量和加载策略

## 依赖
- numpy (已有)
- VectorIndex (已有)
- SmartTagger (已有)
- BrainEncoder (已有)
