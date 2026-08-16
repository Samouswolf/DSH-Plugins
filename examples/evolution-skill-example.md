# 进化引擎 · 记忆 → 技能 固化示例

进化引擎的闭环：**复盘记忆 → 挑选可复用经验 → 固化成语料技能 → 重启常驻**。

## 前置

- Agent 已挂载 `evolution-engine`。
- `DNA_MEMORY_DIR` 已指向一个有记忆的记忆库（里面有可复用经验）。

## 步骤 1：复盘

**对话**：
> 看看我的记忆库里有哪些值得固化成技能的经验？

**内部**：`evolution_review(top=8)` → 返回记忆分层统计 + 高价值记忆摘录 + 现有技能清单。

## 步骤 2：选定并固化

在你挑选出一条经验后，让 Agent 用 `evolution_engine` 落盘。**内部会做的**：

```
evolution_engine(
  name = "api-retry-policy",
  description = "后端接口超时重试与降级策略（当 QPS 超过 5 触发降级、退避重试的普适经验）",
  body = "## 用途\n...\n## 何时使用\n...\n## 操作步骤\n...\n## 检查清单\n..."
)
```

内部动作：
1. 写到 `<EVO_SKILLS_DIR>/api-retry-policy/SKILL.md`
2. 动态注册，本次会话立即可用
3. 重启后由 DSH 的 `skill-filesystem` 自动发现，**常驻**

## 产物形态

落盘后的 `SKILL.md` 大致是：

```markdown
---
name: api-retry-policy
description: 后端接口超时重试与降级策略（...）
version: 1.0.0
---

# API 重试与降级策略

## 用途
...

## 何时使用
...

## 操作步骤
1. ...

## 检查清单
- [ ] ...
```

## 验证

```
# 查看技能已注册
evolution_review
# 或直接给 Agent 一个匹配场景，看它是否自动使用该技能
```

> **注意**：固化出来的技能默认不会进入本仓库（除非你把 `.skills` 也纳入发布）。它是**你私有库的进化产物**，与开源仓库保持隔离。
