# agent-farm — 本地 Agent 农场

探测本机多种本地 Agent（Hermes / WorkBuddy / Claude / Codex / Agnes / Trae），提供状态看板 + 一键调用。DSH 文件插件，纯 Host 半，重启常驻。

## 文件

| 文件 | 作用 |
|------|------|
| `index.mjs` | 插件入口：探测 + 工具 + /api/farm 路由 |
| `farm-hermes.py` | Hermes Agent headless 桥接 |
| `farm-opencode.mjs` | Opencode 中转 API 桥接（对话） |
| `farm-agnes.mjs` | Agnes 云 API 桥接（对话/生图/生视频） |

## 安装

把本目录放入工作区（如 `<工作区>/agent-farm`），在 agent preset（`agent.cordis.yml`）里挂载：

```yaml
- id: agent-farm
  name: 'file:///<工作区>/agent-farm/index.mjs'
```

## 配置（环境变量）

所有本机专属路径与凭据均通过环境变量注入，不写死在代码里。

| 变量 | 说明 | 默认 |
|------|------|------|
| `CB_CLI` | WorkBuddy codebuddy CLI 路径 | `$LOCALAPPDATA/Programs/WorkBuddy/.../codebuddy` |
| `HERMES_VENV_PY` | Hermes venv python | `$LOCALAPPDATA/hermes/hermes-agent/venv/.../python.exe` |
| `HERMES_ENV` | Hermes .env 路径 | `~/.hermes/.env` |
| `CLAUDE_EXE` / `CLAUDE_DIR` | Claude Code 路径 | npm 安装位置 / `~/.claude` |
| `CODEX_JS` / `CODEX_AUTH` | Codex 路径 | npm 位置 / `~/.codex/auth.json` |
| `AGNES_API_KEY` | Agnes 云 API 密钥（必须） | — |
| `OPENCODE_API_KEY` | Opencode 中转密钥（默认模型走此通道） | — |
| `DSH_FARM_DIR` | 插件目录（桥接脚本/资源路径） | 插件自身目录 |

> ⚠️ 本项目不包含任何密钥。`farm-opencode.mjs` / `farm-agnes.mjs` 只从环境变量或外部配置文件读取凭据。
> 若 Hermes 使用，`farm-hermes.py` 还会读取 `HERMES_ENV` 指向的 `.env` 获取模型路由。

## 🎚️ 模型选择

每个 agent 派活时**可以指定模型**，两种方式：

**方式一 · 看板下拉（推荐）**
打开浏览器里的 Agent 农场看板，选中某 agent 后，对话输入区会出现**模型下拉框**，直接点选要用的模型即可。

**方式二 · 对话里指定**
调用 `farm_call` 时传 `model` 参数：
```
farm_call(agent="agnes", task="...", model="agnes-image-2.1-flash")
```

**各 agent 的可选模型与默认：**

| Agent | 可选模型 | 默认 |
|-------|---------|------|
| **WorkBuddy** | hy3、glm-5.2、glm-5.1、glm-5v-turbo、minimax-m3、kimi-*、deepseek-v4-flash、deepseek-v4-pro | `hy3` |
| **Hermes** | deepseek-v4-flash、deepseek-v4-pro | `deepseek-v4-flash` |
| **Claude / Codex** | deepseek-v4-flash、deepseek-v4-pro（走 Opencode 中转） | `deepseek-v4-flash` |
| **Agnes** | agnes-2.0-flash、agnes-2.5-*、agnes-image-2.1-flash、agnes-video-v2.0 | `agnes-2.0-flash` |

> WorkBuddy 的下拉优先使用从 `models.json` 读到的**真实可用清单**；读取失败时才回退到上表默认值。
> 若你在看板里指定了模型，该 model 会随派活请求透传到底层桥接；不选就使用该 agent 的默认模型。

## 关联

- `smart-hub` / `agent-team` 与农场是同一生态的协作入口，可一并部署。
