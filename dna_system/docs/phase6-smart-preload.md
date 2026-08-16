# Phase 6: 智能按需加载 — 命中学习

## 目标
基于历史命中数据，智能预测需要加载哪些记忆簇，实现"用到再加载，加载后记住关联"。

## 当前问题
- Phase 4 实现了按需加载（L0/L1/L2），但L1/L2的触发依赖用户显式提到游戏名
- 没有学习机制——不知道哪些簇经常一起被使用
- 预加载如果盲目，命中率低反而浪费token

## 设计方案

### 核心思路：延迟预加载 + 命中反馈

不是"预测要什么"，而是"用到了再加载，加载后记住关联"：

| 阶段 | 行为 | Token消耗 |
|------|------|-----------|
| 初始 | 只加载L0核心（~30条） | 低 |
| 对话中 | 用户提到话题 → 按需加载相关簇 | 精准 |
| 学习 | 记录"话题→簇"命中关联 | 0（后台） |
| 下次 | 启动时自动加载高频关联簇 | 命中率高 |

### 1. 命中关联图 (HitGraph)

```python
class HitGraph:
    """命中关联图 — 记录话题与簇的关联"""

    def __init__(self):
        self.edges = {}  # {(topic, cluster_id): hit_count}

    def record(self, topic, cluster_id):
        """记录一次命中"""
        key = (topic, cluster_id)
        self.edges[key] = self.edges.get(key, 0) + 1

    def get_preload_clusters(self, topics, threshold=0.5):
        """根据话题列表，获取应该预加载的簇"""
        # 统计每个簇的命中次数
        # 返回命中率 > 阈值的簇列表
```

### 2. 话题提取器 (TopicExtractor)

从对话上下文中提取话题信号：
- 游戏名：贪吃蛇、塔防、修仙...
- 技术词：碰撞、渲染、部署...
- Bug关键词：崩溃、报错、修复...

复用现有 SmartTagger 的 GAME_KEYWORDS 和 TECH_KEYWORDS。

### 3. 智能加载器 (SmartLoader)

```python
class SmartLoader:
    """智能加载器 — 基于命中图预加载"""

    def __init__(self, hit_graph, cluster_loader):
        self.hit_graph = hit_graph
        self.cluster_loader = cluster_loader

    def preload_for_context(self, context_text):
        """根据上下文预加载相关簇"""
        # 1. 提取话题
        # 2. 查命中图，获取高频关联簇
        # 3. 按需加载（跳过已加载的）

    def learn(self, context_text, used_cluster_ids):
        """学习：记录这次的命中关联"""
        topics = self.extract_topics(context_text)
        for topic in topics:
            for cid in used_cluster_ids:
                self.hit_graph.record(topic, cid)
```

### 4. 启动优化

```
启动流程（Phase 6后）:
1. 加载L0核心簇（~30条）— 固定
2. 读取命中图，获取高频关联簇
3. 预加载高频簇（命中率>50%的）
4. 对话中按需加载其他簇
5. 每次加载后学习，更新命中图
```

### 5. 命中率保障

```
命中率 = 实际使用的记忆 / 预加载的记忆

阈值设定：
- >70% → 保持预加载
- 50-70% → 缩减预加载范围
- <50% → 关闭该组合的预加载
```

自动调节，不会出现"越预加载越亏"。

## 预期效果

| 指标 | Phase 5后 | Phase 6后 |
|------|-----------|-----------|
| 启动加载 | 30条(L0) | 30条(L0) + 高频簇 |
| 命中率 | 被动加载 | 70%+ 主动命中 |
| Token效率 | 基准 | 再提升20-30% |

## 实现步骤

1. 创建 `dna_system/core/hit_graph.py` — 命中关联图
2. 创建 `dna_system/core/topic_extractor.py` — 话题提取器
3. 创建 `dna_system/core/smart_loader.py` — 智能加载器
4. 修改 `dna_system/system.py` — 集成智能加载

## 依赖
- semantic_cluster.py (Phase 4)
- cluster_loader.py (Phase 4)
- cluster_tracker.py (Phase 4)
- smart_tagger.py (已有)
