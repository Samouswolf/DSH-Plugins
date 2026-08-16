# DSH Plugins

适用于 [DeepSeek Harness](https://github.com/deepseek-ai/dsh) 的自定义插件合集，把 Hermes 式的「DNA 记忆 + 多 Agent 农场 + 能力进化」能力带入 DSH。

> ⚠️ **安全声明**：本仓库**不含任何个人记忆数据、API 密钥或本机私有路径**。所有凭据均通过环境变量 / 配置文件注入。请勿向本仓库提交 `.env`、任何 key 或 `.dna/` 数据。

---

## 📦 包含的插件

| 插件 | 目录 | 作用 |
|------|------|------|
| **DNA 记忆系统** | [`dna-plugin/`](dna-plugin/) + [`dna_bridge/`](dna_bridge/) + [`dna_system/`](dna_system/) | 零模型依赖的「联想大脑」：召回/沉淀记忆、MOA 多模型辩证、双库同步、会话自动注入身份记忆 |
| **Agent 农场** | [`agent-farm/`](agent-farm/) | 探测本机多种本地 Agent（Hermes/WorkBuddy/Claude/Codex/Agnes），状态看板 + 一键派活 |
| **进化引擎** | [`evolution-engine/`](evolution-engine/) | 复盘记忆库与技能库，把 Agent 产出的经验持久化固化为可复用技能 |

## 🚀 快速开始

```bash
# 1. 把插件目录拷入你的 DSH 工作区（保持目录名一致），例如：
#    <工作区>/dna-plugin、<工作区>/dna_bridge、<工作区>/dna_system、<工作区>/agent-farm ...
```

```yaml
# 2. 在 agent preset（agent.cordis.yml）里按需挂载
- id: dsh-dna
  name: 'file:///<工作区>/dna-plugin/index.mjs'

- id: agent-farm
  name: 'file:///<工作区>/agent-farm/index.mjs'

- id: evolution-engine
  name: 'file:///<工作区>/evolution-engine/index.mjs'
```

```bash
# 3. 配置运行所需的环境变量（key 由你自己填）
#    复制 config.example 并按需填写，每个变量的含义见 docs/INSTALL.md
```

## 📚 文档

| 文档 | 内容 |
|------|------|
| [**安装与配置**](docs/INSTALL.md) | 每个插件的前置条件、完整安装步骤、全部环境变量表 |
| [**注意事项**](docs/CAVEATS.md) | 安全边界、隐私保护、常见坑、故障排查 |

## 🔑 需要你自己准备的 Key

| 能力 | 需要的 Key |
|------|-----------|
| MOA 辩证 / DNA 系统 | DeepSeek API key（`DEEPSEEK_API_KEY`） |
| Agent 农场 · Agnes 生图/生视频 | Agnes API key（`AGNES_API_KEY`） |
| Agent 农场 · Claude/Codex 走中转 | Opencode 中转 key（`OPENCODE_API_KEY`） |

> 没有 key 时对应功能自动降级为「不可用 / 跳过」，不会阻止其他插件启动。

## Security / 隐私

- 本仓库**零敏感内容**：无个人记忆、无游戏业务数据、无本机路径、无硬编码 Key。
- 记忆数据写在你本地的 `DNA_MEMORY_DIR`（默认 `~/.dna`），不会进入仓库。
- 见 [注意事项](docs/CAVEATS.md) 了解更多安全边界。

## License

[MIT](LICENSE) © 2026
