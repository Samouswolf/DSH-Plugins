# DNA Memory Engine — 可移植版

独立的智能体记忆优化引擎，可嵌入任何Python项目。

## 安装

```bash
# 方式1: 直接复制
cp -r dna_memory_engine/ your_project/

# 方式2: pip安装（如果有setup.py）
pip install -e .
```

## 快速开始

```python
from dna_memory_engine import MemoryEngine

# 1. 初始化引擎
engine = MemoryEngine(storage_dir="./my_memory")

# 2. 添加记忆
engine.add("贪吃蛇碰撞Bug修复", tags=["贪吃蛇", "Bug"])
engine.add("塔防v2素材切换完成", tags=["塔防", "部署"])
engine.add("修仙功法平衡调整", tags=["修仙", "数值"])

# 3. 构建聚类索引（首次或记忆变化后）
engine.build_index()

# 4. 启动时加载核心记忆（L0）
core = engine.load_core()
print(f"核心记忆: {len(core)} 条")

# 5. 按需加载话题记忆（L1）
topic_memories = engine.load_topic("贪吃蛇")
print(f"贪吃蛇相关: {len(topic_memories)} 条")

# 6. 智能预加载（基于历史命中）
preloaded = engine.smart_preload("碰撞Bug怎么修")
print(f"预加载: {len(preloaded)} 条")

# 7. 压缩记忆
result = engine.compress()
print(f"压缩: {result['before']} → {result['after']} 条")

# 8. 查询统计
stats = engine.stats()
print(f"活跃: {stats['active']}, 归档: {stats['archived']}")
```

## API参考

### MemoryEngine

| 方法 | 说明 | 返回 |
|------|------|------|
| `add(text, tags=[])` | 添加一条记忆 | memory_id |
| `build_index()` | 构建聚类索引 | None |
| `load_core()` | 加载L0核心记忆 | list[Memory] |
| `load_topic(query)` | 加载L1话题记忆 | list[Memory] |
| `smart_preload(context)` | 智能预加载 | list[Memory] |
| `compress()` | 压缩记忆 | dict |
| `restore(memory_id)` | 从归档恢复 | bool |
| `stats()` | 系统统计 | dict |
| `save()` | 持久化 | None |

### Memory对象

```python
@dataclass
class Memory:
    id: str           # 唯一ID
    text: str         # 记忆文本
    tags: list        # 标签列表
    energy: float     # 能量值 (0-1)
    created_at: float # 创建时间
    source_ids: list  # 压缩来源ID（可追溯）
```

## 移植到其他项目

### 方式1: 独立包（推荐）

```bash
# 复制整个目录
cp -r dna_memory_engine/ /path/to/your/project/

# 在你的项目中使用
from dna_memory_engine import MemoryEngine
```

### 方式2: 嵌入现有智能体

```python
# 在你的Agent类中集成
class YourAgent:
    def __init__(self):
        self.memory = MemoryEngine(storage_dir="./agent_memory")

    def on_message(self, message):
        # 对话时自动记忆
        self.memory.add(message, tags=self.extract_tags(message))

        # 智能加载相关记忆
        relevant = self.memory.smart_preload(message)

        # 用记忆增强回复
        response = self.llm.generate(
            message=message,
            context=relevant,
        )
        return response

    def on_startup(self):
        # 启动时只加载核心记忆
        core = self.memory.load_core()
        self.llm.set_system_context(core)
```

### 方式3: 替换LangChain Memory

```python
from langchain.memory import BaseMemory
from dna_memory_engine import MemoryEngine

class DNAMemory(BaseMemory):
    """替代LangChain的ConversationBufferMemory"""

    def __init__(self):
        self.engine = MemoryEngine()

    def load_memory_variables(self, inputs):
        context = inputs.get("input", "")
        memories = self.engine.smart_preload(context)
        return {"history": "\n".join(m.text for m in memories)}

    def save_context(self, inputs, outputs):
        self.engine.add(
            f"用户: {inputs['input']}\nAI: {outputs['output']}"
        )
```

## 性能基准

| 指标 | 全量加载 | L0核心加载 | 提升 |
|------|----------|-----------|------|
| 启动Token | 104,018 | 14,340 | **86.2%↓** |
| 检索范围 | 73条 | 8-20条 | **87.7%↓** |
| 记忆压缩 | 980条 | 73条 | **92.6%↓** |
| 启动时间 | - | 463ms | - |

## 目录结构

```
dna_memory_engine/
├── __init__.py          # 入口
├── engine.py            # 主引擎（对外API）
├── core/
│   ├── semantic_cluster.py   # 语义聚类
│   ├── cluster_loader.py     # 三级加载
│   ├── memory_compressor.py  # 记忆压缩
│   ├── hit_graph.py          # 命中关联图
│   ├── topic_extractor.py    # 话题提取
│   └── smart_loader.py       # 智能预加载
├── storage/
│   └── store.py              # 存储层
└── README.md
```

## 依赖

- Python 3.10+
- numpy（唯一外部依赖）

## 协议

MIT License
