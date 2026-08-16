# DSH Plugins

适用于 [DeepSeek Harness](https://github.com/deepseek-ai/dsh) 的自定义插件合集，把 Hermes 式的「DNA 记忆 + 多 Agent 农场 + 能力进化」能力带入 DSH。

> ⚠️ 安全声明：本仓库**不含任何个人记忆数据、API 密钥或本机私有路径**。所有凭据均通过环境变量 / 配置文件注入，请勿向本仓库提交 `.env`、key 或 `.dna/` 数据。

## 包含的插件

| 插件 | 目录 | 作用 |
|------|------|------|
| **DNA 记忆系统** | [`dna-plugin/`](dna-plugin/) + [`dna_bridge/`](dna_bridge/) | 会话内召回/沉淀记忆、MOA 多模型辩证、双库同步、自动注入身份记忆 |
| **Agent 农场** | [`agent-farm/`](agent-farm/) | 探测本机多种本地 Agent（Hermes/WorkBuddy/Claude/Codex/Agnes），状态看板 + 一键调用 |
| **进化引擎** | [`evolution-engine/`](evolution-engine/) | 复盘记忆库与技能库，把 Agent 产出的经验持久化落盘为可复用技能 |

## 快速开始

1. 把要用的插件目录拷入你的 DSH 工作区（如 `D:/DSH/<plugin>/`）。
2. 在 agent preset（如 `agent.cordis.yml`）里按需引用，例如：

   ```yaml
   - id: dsh-dna
     name: 'file:///D:/DSH/dna-plugin/index.mjs'
   ```

3. 根据需要创建本地配置，各插件读取的路径/凭据见其目录内 `config.example` 说明。

## 配置

所有本机专属路径与密钥都不写死在代码里。启动前按各插件要求设置环境变量（如 `DNA_MEMORY_DIR`、`AGNES_API_KEY`、`HERMES_HOME` 等），详见各插件目录的 `config.example.xxx`。

## License

[MIT](LICENSE) © 2026
