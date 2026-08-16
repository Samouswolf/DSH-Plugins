# Agent 农场 · 对话用法示例

Agent 农场帮你把多个本地 Agent 管起来：`探测` → `派活` → `模型校色`，还有一个浏览器看板。

## 1. 看有哪些 Agent 可用

**对话**：
> 我本机都有哪些 Agent 可用？

**内部**：`farm_status()` → 列出 Hermes/WorkBuddy/Claude/Codex/Agnes 的可用性、认证状态、模型。

## 2. 派活给某个 Agent

**对话**：
> 让 Hermes 分析这个项目的 README 结构。

**内部**：`farm_call(agent="hermes", task="分析这个项目的 README 结构")`

> 支持 `hermes` / `workbuddy` / `claude` / `codex`，每种走各自的 headless 驱动。

## 3. 指定模型 + 生图/生视频（需 Agnes Key）

**对话**：
> 用 Agnes 生成一张赛博朋克城市夜景图。

**内部**：`farm_call(agent="agnes", task="赛博朋克城市夜景，霓虹灯", model="agnes-image-2.1-flash")`

## 4. 切换当前会话默认模型

**对话**：
> 把当前会话切到 deepseek-v4-pro。

**内部**：`farm_set_model(provider="deepseek", model="deepseek-v4-pro")`

## 5. 浏览器看板

- 浏览器打开 `/api/farm` 路径：可视化状态卡片、任务输入框、模型校色、历史结果。
- 由 `agent-farm` 的 Host 半注册的 HTTP API 支撑。

---

## Key 依赖

| 能力 | 需要 | 缺失时 |
|------|------|--------|
| 探测本机 | 无 | — |
| 派活给 Hermes | Hermes 已装 | 对应 Agent 显示不可用 |
| Claude/Codex 走中转 | `OPENCODE_API_KEY` | 卡片无模型 |
| Agnes 生图/生视频 | `AGNES_API_KEY` | 生图报缺 key |
