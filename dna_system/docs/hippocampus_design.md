# DNA系统海马体进化设计文档

## 概述

将DNA记忆系统进化为类似人类海马体的功能，实现情景记忆、时间索引、睡眠巩固、模式补全和空间地图。

## 当前架构

```
DNA系统 v3.0
├── DNA单元 (dna.py) — 神经元
├── 磁吸引擎 (magnetic.py) — 突触连接
├── 生命周期 (lifecycle.py) — 记忆遗忘曲线
├── 进化引擎 (evolution.py) — 记忆巩固
├── 编译链 (compile.py) — 感觉输入
├── 智能标签 (smart_tagger.py) — 语义标记
├── 访问追踪 (access_tracker.py) — 记忆强化
└── 自动记录 (auto_recorder.py) — 感觉登记
```

## 目标架构

```
DNA系统 v4.0 (海马体进化)
├── 现有模块（保持兼容）
│   ├── DNA单元 (dna.py) — 扩展字段
│   ├── 磁吸引擎 (magnetic.py)
│   ├── 生命周期 (lifecycle.py)
│   ├── 进化引擎 (evolution.py)
│   ├── 编译链 (compile.py)
│   ├── 智能标签 (smart_tagger.py)
│   ├── 访问追踪 (access_tracker.py)
│   └── 自动记录 (auto_recorder.py)
│
└── 新增模块（海马体功能）
    ├── 时间索引 (temporal_index.py) — Phase 1
    ├── 情景记忆 (episodic.py) — Phase 2
    ├── 睡眠巩固 (consolidation.py) — Phase 3
    ├── 模式补全 (pattern_completion.py) — Phase 4
    └── 空间地图 (cognitive_map.py) — Phase 5
```

## Phase 1: 时间索引

### 目标
支持按时间范围查询记忆，解决"昨天做了什么"这类问题。

### 设计

#### 数据结构扩展
在DNA中增加时间相关字段（向后兼容）：

```python
# dna.py 扩展
@dataclass
class DNA:
    # 现有字段保持不变...
    
    # 新增时间字段（可选，默认None）
    temporal_tags: list[str] = field(default_factory=list)  # ["2026-06-03", "下午", "14:00"]
    episode_id: Optional[str] = None  # 所属情景ID
    sequence_index: Optional[int] = None  # 在情景中的顺序
```

#### 时间索引结构
```python
class TemporalIndex:
    """时间索引：按日期/小时分桶"""
    
    def __init__(self):
        self.by_date: dict[str, list[str]] = {}      # "2026-06-03" -> [dna_ids]
        self.by_hour: dict[str, list[str]] = {}       # "2026-06-03T14" -> [dna_ids]
        self.by_episode: dict[str, list[str]] = {}    # episode_id -> [dna_ids]
    
    def add(self, dna: DNA) -> None:
        """添加DNA到时间索引"""
        dt = datetime.fromtimestamp(dna.created_at)
        date_key = dt.strftime("%Y-%m-%d")
        hour_key = dt.strftime("%Y-%m-%dT%H")
        
        self.by_date.setdefault(date_key, []).append(dna.id)
        self.by_hour.setdefault(hour_key, []).append(dna.id)
        
        if dna.episode_id:
            self.by_episode.setdefault(dna.episode_id, []).append(dna.id)
    
    def query_by_date(self, date_str: str) -> list[str]:
        """查询某天的所有DNA ID"""
        return self.by_date.get(date_str, [])
    
    def query_by_range(self, start: datetime, end: datetime) -> list[str]:
        """查询时间范围内的DNA ID"""
        results = []
        current = start
        while current <= end:
            date_key = current.strftime("%Y-%m-%d")
            results.extend(self.by_date.get(date_key, []))
            current += timedelta(days=1)
        return list(set(results))
    
    def query_recent(self, hours: int = 24) -> list[str]:
        """查询最近N小时的DNA ID"""
        cutoff = time.time() - hours * 3600
        return [dna_id for dna_id, dna in self._dna_map.items() 
                if dna.created_at > cutoff]
```

### 实现步骤
1. 扩展DNA数据结构（向后兼容）
2. 实现TemporalIndex类
3. 在DNASystem中集成时间索引
4. 添加时间查询API

---

## Phase 2: 情景记忆

### 目标
记录完整的事件链："做了什么→结果如何"，解决"记不住发生了什么"的问题。

### 设计

#### 情景数据结构
```python
class Episode:
    """一次完整的事件记忆"""
    id: str
    timestamp: float
    trigger: str              # 什么触发了这个事件
    context: dict             # 当时的状态
    actions: list[str]        # 做了什么
    outcome: str              # 结果如何
    emotional_valence: float  # 情感权重 (-1到1)
    related_dna_ids: list[str]
    
    def to_dna(self) -> DNA:
        """转换为DNA存储"""
        return DNA(
            id=self.id,
            dna_type=DNAType.EPISODE,
            content={
                "trigger": self.trigger,
                "context": self.context,
                "actions": self.actions,
                "outcome": self.outcome,
                "emotional_valence": self.emotional_valence,
            },
            episode_id=self.id,
            temporal_tags=self._generate_temporal_tags(),
        )
```

#### 情景记忆引擎
```python
class EpisodicMemory:
    """情景记忆引擎"""
    
    def record_episode(self, trigger, actions, outcome, context=None):
        """记录一个情景"""
        episode = Episode(
            id=uuid.uuid4().hex[:12],
            timestamp=time.time(),
            trigger=trigger,
            context=context or {},
            actions=actions,
            outcome=outcome,
            emotional_valence=self._calculate_valence(outcome),
            related_dna_ids=[],
        )
        
        # 关联当前活跃的DNA
        episode.related_dna_ids = self._find_related_dnas(episode)
        
        # 存储
        self.store.save_episode(episode)
        
        # 强化关联DNA的生命周期
        self._reinforce_related_dnas(episode)
        
        return episode
    
    def recall_by_trigger(self, trigger: str) -> list[Episode]:
        """通过触发器回忆情景"""
        query_vec = self.magnetic.generate_vector(trigger)
        # 在情景DNA中搜索
        results = self.magnetic.attract(
            DNA(magnetic_vector=query_vec),
            self._get_episode_dnas()
        )
        return [self._dna_to_episode(dna) for dna, _ in results[:5]]
```

### 实现步骤
1. 定义Episode数据结构
2. 实现EpisodicMemory引擎
3. 扩展自动记录器，自动提取情景
4. 添加情景回忆API

---

## Phase 3: 睡眠巩固

### 目标
模拟睡眠巩固：重要记忆强化，不重要的遗忘。

### 设计

#### 巩固引擎
```python
class ConsolidationEngine:
    """睡眠巩固引擎"""
    
    def __init__(self, system):
        self.system = system
        self.consolidation_history = []
    
    def consolidate(self, recent_hours: int = 24) -> dict:
        """运行巩固周期（模拟睡眠）"""
        report = {
            "timestamp": time.time(),
            "episodes_processed": 0,
            "dnas_reinforced": 0,
            "dnas_weakened": 0,
            "patterns_extracted": 0,
        }
        
        # 1. 获取最近的情景
        recent_episodes = self._get_recent_episodes(recent_hours)
        report["episodes_processed"] = len(recent_episodes)
        
        # 2. 按情感权重排序
        episodes_by_importance = sorted(
            recent_episodes,
            key=lambda e: abs(e.emotional_valence),
            reverse=True
        )
        
        # 3. 强化重要记忆
        for episode in episodes_by_importance[:10]:  # 前10个最重要的
            if abs(episode.emotional_valence) > 0.3:
                self._reinforce_episode(episode)
                report["dnas_reinforced"] += len(episode.related_dna_ids)
        
        # 4. 弱化不重要的记忆
        for episode in episodes_by_importance[10:]:
            if abs(episode.emotional_valence) < 0.1:
                self._weaken_episode(episode)
                report["dnas_weakened"] += len(episode.related_dna_ids)
        
        # 5. 提取跨情景模式
        patterns = self._extract_patterns(recent_episodes)
        report["patterns_extracted"] = len(patterns)
        
        # 6. 记录巩固历史
        self.consolidation_history.append(report)
        
        return report
    
    def _reinforce_episode(self, episode: Episode):
        """强化一个情景及其关联DNA"""
        for dna_id in episode.related_dna_ids:
            dna = self.system.find_dna(dna_id)
            if dna:
                # 延长生命周期
                dna.lifetime = min(100, dna.lifetime + 20)
                # 增加访问计数
                dna.access_count += 1
                # 强化向量（向重要记忆靠拢）
                self._strengthen_vector(dna, episode)
    
    def _extract_patterns(self, episodes: list[Episode]) -> list[DNA]:
        """从多个情景中提取模式"""
        # 找出重复出现的触发器-结果对
        trigger_outcome_pairs = []
        for ep in episodes:
            trigger_outcome_pairs.append((ep.trigger, ep.outcome))
        
        # 聚类相似的触发器-结果对
        patterns = self._cluster_and_extract(trigger_outcome_pairs)
        
        return patterns
```

### 实现步骤
1. 实现ConsolidationEngine类
2. 添加巩固周期调度（每日首次启动时运行）
3. 实现情感权重计算
4. 实现跨情景模式提取

---

## Phase 4: 模式补全

### 目标
从部分线索重建完整记忆，增强现有碎片重构能力。

### 设计

#### 模式补全引擎
```python
class PatternCompletion:
    """模式补全引擎"""
    
    def complete(self, partial_cue: dict) -> Episode:
        """从部分线索重建完整记忆"""
        # 1. 用partial_cue匹配相关DNA
        query_text = json.dumps(partial_cue, ensure_ascii=False)
        query_vec = self.magnetic.generate_vector(query_text)
        
        # 2. 搜索相关DNA
        results = self.magnetic.attract(
            DNA(magnetic_vector=query_vec),
            self.system.pool
        )
        
        # 3. 找到这些DNA所属的Episode
        related_episodes = []
        for dna, score in results[:10]:
            if dna.episode_id:
                episode = self.system.find_episode(dna.episode_id)
                if episode:
                    related_episodes.append((episode, score))
        
        # 4. 选择最匹配的Episode
        if not related_episodes:
            return None
        
        # 按匹配度排序
        related_episodes.sort(key=lambda x: x[1], reverse=True)
        best_episode = related_episodes[0][0]
        
        # 5. 用Episode的context填充缺失部分
        completed = self._fill_missing(best_episode, partial_cue)
        
        return completed
    
    def _fill_missing(self, episode: Episode, partial_cue: dict) -> Episode:
        """填充缺失部分"""
        # 复制episode
        completed = Episode(
            id=episode.id,
            timestamp=episode.timestamp,
            trigger=partial_cue.get("trigger", episode.trigger),
            context={**episode.context, **partial_cue.get("context", {})},
            actions=partial_cue.get("actions", episode.actions),
            outcome=partial_cue.get("outcome", episode.outcome),
            emotional_valence=episode.emotional_valence,
            related_dna_ids=episode.related_dna_ids,
        )
        return completed
```

### 实现步骤
1. 实现PatternCompletion类
2. 增强现有碎片重构能力
3. 添加模式补全API

---

## Phase 5: 空间地图

### 目标
可视化记忆的空间组织，形成"记忆地形图"。

### 设计

#### 认知地图
```python
class CognitiveMap:
    """认知地图：记忆的空间组织"""
    
    def __init__(self, system):
        self.system = system
        self.coordinates = {}  # dna_id -> (x, y)
    
    def build_map(self, dnas: list[DNA] = None):
        """构建记忆地图"""
        if dnas is None:
            dnas = self.system.pool
        
        # 提取所有向量
        vectors = np.array([dna.magnetic_vector for dna in dnas])
        ids = [dna.id for dna in dnas]
        
        # 用UMAP降维到2D
        from umap import UMAP
        reducer = UMAP(n_components=2, random_state=42)
        coords_2d = reducer.fit_transform(vectors)
        
        # 存储坐标
        for i, dna_id in enumerate(ids):
            self.coordinates[dna_id] = (float(coords_2d[i, 0]), float(coords_2d[i, 1]))
        
        return self.coordinates
    
    def find_nearby(self, dna_id: str, radius: float = 1.0) -> list[str]:
        """找到附近的记忆"""
        if dna_id not in self.coordinates:
            return []
        
        center = self.coordinates[dna_id]
        nearby = []
        
        for other_id, coord in self.coordinates.items():
            if other_id == dna_id:
                continue
            distance = ((center[0] - coord[0])**2 + (center[1] - coord[1])**2)**0.5
            if distance <= radius:
                nearby.append((other_id, distance))
        
        nearby.sort(key=lambda x: x[1])
        return [id for id, _ in nearby]
    
    def find_cluster_center(self, topic: str) -> str:
        """找到某个主题的聚类中心"""
        # 找到所有相关DNA
        related_dnas = [dna for dna in self.system.pool if topic in dna.tags]
        if not related_dnas:
            return None
        
        # 计算中心点
        coords = [self.coordinates.get(dna.id, (0, 0)) for dna in related_dnas]
        center_x = sum(c[0] for c in coords) / len(coords)
        center_y = sum(c[1] for c in coords) / len(coords)
        
        # 找到最近的DNA
        min_dist = float('inf')
        center_dna_id = None
        
        for dna in related_dnas:
            coord = self.coordinates.get(dna.id, (0, 0))
            dist = ((center_x - coord[0])**2 + (center_y - coord[1])**2)**0.5
            if dist < min_dist:
                min_dist = dist
                center_dna_id = dna.id
        
        return center_dna_id
    
    def export_map_data(self) -> dict:
        """导出地图数据供可视化使用"""
        nodes = []
        for dna in self.system.pool:
            coord = self.coordinates.get(dna.id, (0, 0))
            nodes.append({
                "id": dna.id,
                "x": coord[0],
                "y": coord[1],
                "type": dna.dna_type.value,
                "tags": dna.tags[:3],
                "lifetime": dna.lifetime,
                "access_count": dna.access_count,
            })
        
        # 生成边（相似度高的连接）
        edges = []
        for dna in self.system.pool[:100]:  # 限制数量
            nearby = self.find_nearby(dna.id, radius=0.5)
            for other_id in nearby[:3]:  # 每个节点最多3条边
                edges.append({"source": dna.id, "target": other_id})
        
        return {"nodes": nodes, "edges": edges}
```

### 实现步骤
1. 安装UMAP依赖（可选，可降级到t-SNE）
2. 实现CognitiveMap类
3. 添加Web仪表盘页面
4. 实现交互式查询

---

## 向后兼容策略

1. **新字段全部可选**：DNA新增字段默认None，旧数据正常加载
2. **渐进式迁移**：不一次性改所有DNA，按需升级
3. **存储格式不变**：JSON格式保持，新字段追加
4. **API向后兼容**：现有接口不变，新功能通过新接口暴露

## 测试策略

1. **单元测试**：每个Phase的模块独立测试
2. **集成测试**：与现有系统集成后测试
3. **性能测试**：时间索引和模式补全需基准测试
4. **回归测试**：确保现有功能不受影响

## 风险控制

1. **备份先行**：开发前备份.dna/目录 ✅
2. **渐进式开发**：按Phase逐步实现
3. **向后兼容**：新字段可选，旧数据不迁移
4. **性能监控**：每个Phase后检查性能影响