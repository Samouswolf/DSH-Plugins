# 安装与配置指南

本仓库是 [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/dsh) 的自定义插件合集。本文档从零说明如何把三个插件装好、配好、跑起来。

---

## 0. 前置条件

| 项目 | 要求 | 说明 |
|------|------|------|
| DeepSeek Harness | 已安装可运行 | 插件以 `file:///` 挂载到 agent preset |
| Python | 3.8+ | DNA 系统桥接脚本用 |
| Node.js | 18+ | Agent 农场桥接脚本用 |
| numpy | 有 | `dna_system` 的记忆核心依赖（`pip install numpy`） |

> 若你只用 **Agent 农场** 且不连 DNA，可跳过 Python/numpy 部分；反之只用 DNA 可跳过 Node。

---

## 1. 整体安装

### 1.1 拷贝目录

把需要的插件目录**原样**拷入你的 DSH 工作区，**保持目录名一致**（代码内部用相对路径找兄弟目录 / 依赖）：

```
<工作区>/
├── dna-plugin/      ← DNA 记忆系统（DSH 插件入口）
├── dna_bridge/      ← DNA 记忆桥接（Python，供 dna-plugin 调用）
├── dna_system/      ← DNA 记忆核心（Python，含 Brain 实现）
├── agent-farm/      ← Agent 农场（DSH 插件入口）
└── evolution-engine/← 进化引擎（DSH 插件入口）
```

### 1.2 挂载到 agent preset

在 `agent.cordis.yml`（或你用的 preset 文件）里加：

```yaml
# ── DNA 记忆系统 ──
- id: dsh-dna
  name: 'file:///<工作区>/dna-plugin/index.mjs'

# ── Agent 农场 ──
- id: agent-farm
  name: 'file:///<工作区>/agent-farm/index.mjs'

# ── 进化引擎 ──
- id: evolution-engine
  name: 'file:///<工作区>/evolution-engine/index.mjs'
```

### 1.3 配置环境变量

复制根目录的 `config.example`，按章节填入你本机的路径 / Key。**具体每个变量的含义见第 3 节。**

---

## 2. 各插件独立说明

### 2.1 DNA 记忆系统

- **入口**：`dna-plugin/index.mjs`（DSH 插件）
- **依赖**：`dna_bridge/` + `dna_system/`，三者需同级放置
- **Python**：需要 `python` 在 PATH，且已装 numpy
- **能力**：
  - `dna_recall` / `dna_add` / `dna_stats`：对话中召回、沉淀、统计记忆
  - `dna_debate`：MOA 多模型辩证（需要 DeepSeek key）
  - `dna_sync`：记忆库双库同步（pull/push/diff）
  - 会话启动自动召回身份记忆并注入系统提示词
- **数据位置**：默认读/写 `~/.dna`（可用 `DNA_MEMORY_DIR` 改），**绝不含个人隐私以外的共享内容**

### 2.2 Agent 农场

- **入口**：`agent-farm/index.mjs`
- **依赖**：Node.js；如需 Hermes 桥接还需 Hermes 安装、Python
- **能力**：
  - `farm_status`：探测本机各 Agent 可用性（Hermes/WorkBuddy/Claude/Codex/Agnes/Trae）与认证状态
  - `farm_call`：派任务给指定本地 Agent
  - `farm_set_model` / `farm_current_model`：切换/查看当前会话模型
  - 浏览器看板：`/api/farm`（状态、派活、模型校色）
- **注意**：这里只做**探测**，不主动启动 Agent 实例；`farm_call` 才真正驱动。

### 2.3 进化引擎

- **入口**：`evolution-engine/index.mjs`
- **能力**：
  - `evolution_review`：只读盘点记忆库 + 列出现有技能，做复盘决策
  - `evolution_engine`：把 Agent 产出的技能固化为 `SKILL.md`（写入技能目录并注册）
- **产物**：技能默认落到 `<技能目录>/<name>/SKILL.md`（用 `EVO_SKILLS_DIR` 配置），会被 DSH 的 skill-filesystem 自动发现，重启常驻。

---

## 3. 环境变量总表

### 3.1 DNA 记忆系统

| 变量 | 默认 | 说明 |
|------|------|------|
| `DNA_MEMORY_DIR` | `~/.dna` | 记忆库目录（brain_pool.json 所在） |
| `DNA_CODE_ROOT` | 当前目录 | `dna_system` 代码根；`bridge.py` 用它加入 sys.path |
| `DNA_BRIDGE` | `<dna-plugin>/../dna_bridge/bridge.py` | 桥接脚本路径 |
| `DNA_DEBATE` | `<dna-plugin>/../dna_bridge/debate.py` | MOA 辩证脚本路径 |
| `DNA_SYNC` | `<dna-plugin>/../dna_bridge/sync.py` | 同步脚本路径 |
| `DNA_IDENTITY_NAMES` | 空 | 会话注入「身份记忆」的关键词（逗号分隔）；空=不启用身份过滤 |
| `DEEPSEEK_API_KEY` | — | MOA 辩证的 DeepSeek key |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | 辩证 API 端点 |

> 双库同步另有 `DNA_DSH_DIR` / `DNA_MAIN_DIR` / `DNA_IMPORT_DIR`，见 `dna_bridge/sync.py`。

### 3.2 Agent 农场

| 变量 | 默认 | 说明 |
|------|------|------|
| `AGNES_API_KEY` | — | Agnes 云 API（对话/生图/生视频） |
| `AGNES_API_URL` | `https://apihub.agnes-ai.com/v1` | Agnes 端点 |
| `OPENCODE_API_KEY` | — | Opencode 中转（Claude/Codex 默认模型通道） |
| `CB_CLI` | 常见安装位 | WorkBuddy codebuddy CLI 路径 |
| `HERMES_VENV_PY` | 常见 venv 位 | Hermes venv python |
| `HERMES_ENV` | `~/.hermes/.env` | Hermes .env（模型路由/凭证） |
| `HERMES_HOME` | `~/.hermes` | 默认 Hermes HOME |
| `DSH_FARM_DIR` | 插件目录 | 桥接脚本/资源基础路径 |

> 你也可用 `CLAUDE_EXE` / `CODEX_JS` / `TRAE_CMD` / `AGNES_CORE` 等覆盖具体 Agent 安装路径（见 `agent-farm/index.mjs` 顶部的 `PATHS`）。

### 3.3 进化引擎

| 变量 | 默认 | 说明 |
|------|------|------|
| `EVO_SKILLS_DIR` | `<evolution-engine>/../.skills` | 技能落盘目录（会被 skill-filesystem 扫描） |
| `DNA_MEMORY_DIR` | `~/.dna` | 复盘读取的记忆库目录 |

---

## 4. 验证是否装好

启动 DSH 会话后，在对话里调用对应工具应能看到结果：

```
# 看 DNA 是否有响应（需先沉淀过记忆）
dna_stats

# 看农场探测
farm_status

# 看进化引擎复盘
evolution_review

# 看工具是否出现在模型工具列表
# （动态注册的工具可能要到下一个模型步骤才可见）
```

## 5. 常见配置示例

**只想用 DNA 记忆 + 不需要辩证**（最简）：

```bash
DNA_MEMORY_DIR=~/.dna
# DEEPSEEK_API_KEY 留空即可，辩证功能自动降级
```

**完整启用农场生图**：

```bash
AGNES_API_KEY=你的-agnes-key
OPENCODE_API_KEY=你的-opencode-key
```
