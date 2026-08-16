<div align="center">

# 🧠 DSH Plugins

**把 Hermes 式的「DNA 记忆 + 多 Agent 农场 + 能力进化」带入 [DeepSeek Harness](https://github.com/deepseek-ai/dsh)**

![License-MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Language-JavaScript/Python](https://img.shields.io/badge/Language-JS%2FPython-blue.svg)
![Zero-Sensitive](https://img.shields.io/badge/Privacy-Zero%20Sensitive-brightgreen.svg)
![DSH-Ready](https://img.shields.io/badge/DeepSeek%20Harness-Ready-8b5cf6.svg)

**中文** · [English](README.en.md)

</div>

> ⚠️ **安全声明**：本仓库**不含任何个人记忆数据、API 密钥或本机私有路径**。所有凭据均通过环境变量 / 配置文件注入。请勿提交 `.env`、任何 key 或 `.dna/` 数据。详见 [SECURITY.md](SECURITY.md)。

---

## 📦 包含的插件

| 插件 | 入口目录 | 作用 |
|------|----------|------|
| **DNA 记忆系统** | [`dna-plugin/`](dna-plugin/) · [`dna_bridge/`](dna_bridge/) · [`dna_system/`](dna_system/) | 零模型依赖的「联想大脑」：召回/沉淀记忆、MOA 多模型辩证、双库同步、会话自动注入身份记忆 |
| **Agent 农场** | [`agent-farm/`](agent-farm/) | 探测本机多种本地 Agent（Hermes/WorkBuddy/Claude/Codex/Agnes），状态看板 + 一键派活 |
| **进化引擎** | [`evolution-engine/`](evolution-engine/) | 复盘记忆库与技能库，把 Agent 产出的经验持久化固化为可复用技能 |

## 📁 仓库结构

```
DSH-Plugins/
├── dna-plugin/        # DNA 记忆 DSH 插件入口 (.mjs)
├── dna_bridge/        # DNA 记忆 Python 桥接 (bridge/debate/sync)
├── dna_system/        # DNA 记忆核心 (Brain: 四层记忆池 + 坐标共振 + 虫洞)
├── agent-farm/        # Agent 农场 (Host 插件 + 桥接 + 前端看板)
├── evolution-engine/  # 进化引擎 (复盘 + 技能固化)
├── docs/              # 安装/注意事项 (中英双语)
├── .github/           # Issue / PR 模板
├── config.example     # 环境变量模板 (复制即用)
└── LICENSE            # MIT
```

## 🚀 快速开始

```bash
# 1. 把插件目录拷入你的 DSH 工作区（保持目录名一致）
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
# 3. 配置环境变量（key 由你自己填）
#    复制 config.example 并填写，每个变量的含义见 docs/INSTALL.md
```

完整步骤见 **[安装与配置](docs/INSTALL.md)**。

## 🔑 需要你自己准备的 Key

| 能力 | 需要的 Key |
|------|-----------|
| MOA 辩证 / DNA 系统 | DeepSeek API key（`DEEPSEEK_API_KEY`） |
| Agent 农场 · Agnes 生图/生视频 | Agnes API key（`AGNES_API_KEY`） |
| Agent 农场 · Claude/Codex 走中转 | Opencode 中转 key（`OPENCODE_API_KEY`） |

> 没有 key 时对应功能自动降级为「不可用 / 跳过」，不会阻止其他插件启动。

## 📚 文档

| 文档 | 内容 |
|------|------|
| [安装与配置](docs/INSTALL.md) | 前置条件、分插件安装、环境变量全表、验证方法 |
| [注意事项](docs/CAVEATS.md) | 安全边界、隐私、常见坑、故障排查 |
| [安全问题报告](SECURITY.md) | 报告漏洞 / key 泄露的处理方式 |

## 🤝 贡献

欢迎提交 [Bug 报告](.github/ISSUE_TEMPLATE/bug_report.md) 与 [功能建议](.github/ISSUE_TEMPLATE/feature_request.md)，也欢迎 PR。请先阅读 [贡献指南](CONTRIBUTING.md)。

## 🛡️ 隐私 / Security

- 本仓库**零敏感内容**：无个人记忆、无业务数据、无本机路径、无硬编码 Key。
- 记忆数据写在你本地的 `DNA_MEMORY_DIR`（默认 `~/.dna`），不会进入仓库。
- 查阅 [SECURITY.md](SECURITY.md) 与 [注意事项](docs/CAVEATS.md)。

## License

[MIT](LICENSE) © 2026 · 作者保留署名权
