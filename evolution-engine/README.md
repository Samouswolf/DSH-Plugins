# evolution-engine — DSH 进化引擎

复盘 DNA 记忆库与技能库，把 Agent 产出的经验持久化落盘为可复用技能，形成「经验 → 记忆 → 技能 → 进化」闭环。

## 工具

| 工具 | 作用 |
|------|------|
| `evolution_review` | 只读盘点记忆库（按 layer/energy 聚合）+ 列出技能目录，供复盘决策 |
| `evolution_engine` | 把产出的技能落盘为 `SKILL.md` 并注册，即时生效 / 重启常驻 |

## 安装

动态插件（本次会话临时）：

```js
// 通过 cordis_define + cordis_run 激活
```

文件插件（重启常驻）——把 `index.mjs` 放入工作区并挂载：

```yaml
- id: evolution-engine
  name: 'file:///<工作区>/evolution-engine/index.mjs'
```

## 配置（环境变量）

| 变量 | 说明 | 默认 |
|------|------|------|
| `EVO_SKILLS_DIR` | 技能落盘目录（会被 skill-filesystem 扫描） | `<插件>/../.skills` |
| `DNA_MEMORY_DIR` | 记忆库目录（读其中的 brain_pool.json） | `~/.dna` |

## 产物

`examples/` 下是可用的示例技能（进化引擎的第一轮产物）：
- `memo-to-skill.md` — 记忆 → 技能封装流程
- `dsh-plugin-guardrails.md` — DSH 插件开发避坑规范
- `dna-memory-maintenance.md` — DNA 记忆库运维规范

这些技能写入 `.skills/<name>/SKILL.md` 后会被 DSH 的 skill-filesystem 自动发现并成为可调用技能。
