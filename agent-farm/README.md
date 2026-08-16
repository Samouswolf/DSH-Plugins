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

把本目录放入工作区（如 `D:/DSH/agent-farm`），在 agent preset（`agent.cordis.yml`）里挂载：

```yaml
- id: agent-farm
  name: 'file:///D:/DSH/agent-farm/index.mjs'
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

## 关联

- `smart-hub` / `agent-team` 与农场是同一生态的协作入口，可一并部署。
