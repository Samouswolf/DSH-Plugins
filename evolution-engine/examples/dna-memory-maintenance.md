---
name: dna-memory-maintenance
description: DNA 记忆库的维护与沉淀规范。涵盖记忆分层策略（hot/settle/protect/cold）、能量值设置、置顶铁律用途、自动注入机制、DSH 副本与主库双库同步。当用户想整理 DNA 记忆、决定一条经验该放哪一层/设多少能量、排查记忆不注入或不同步问题时使用。
version: 1.0.0
---

# DNA 记忆库维护规范

沉淀自 DNA 记忆系统的实践与 protect 层铁律。

## 何时使用
- 沉淀新经验到 DNA 记忆库
- 整理/分层既有记忆
- 排查记忆不注入系统提示词、或双库不同步
- 规划一条经验的能量值与层级

## 记忆结构
- 主库：`~/.hermes/`（Hermes 风格）；DSH 副本：`D:/DSH/.dna/brain_pool.json`
- 每条记忆含：`text` / `energy`(0~1) / `pinned` / `layer` / `dna(domain,intent)` / `access_count` 等
- 层级：`hot`(高频热度，当前无=0) / `settle`(沉淀经验) / `protect`(置顶铁律) / `cold`(冷记忆)

## 分层策略
- **protect**：置顶铁律、不可遗忘的重大结论、身份设定、关键机制真相。avg energy ~0.75+，`pinned: true`。数量应少（本库仅 24 条）。
- **settle**：解决过的经验、踩坑结论。avg energy ~0.7。这是技能打包的主要素材来源。
- **hot / cold**：冷记忆可批量沉淀但不溯及；hot 靠触发频率自动维持。

## 能量值设置
- 高频复用经验：0.7+
- 关键机制/铁律：0.8，且 pinned=true 升 protect
- 普通结论：0.5 默认
- 长期不用会衰减

## 自动注入
- dna-plugin 在会话启动时自动召回记忆并注入系统提示词（PromptSection）。
- 关键：注入的 section 必须**同步返回字符串**，未就绪返回 ''，不能返回占位符。

## 双库同步
- `dna_sync pull`：主库 → DSH 副本
- `dna_sync push`：DSH 副本 → 主库（主库被锁时导出）
- `dna_sync diff`：比对差异
- 主库被锁时走导出，避免冲突。

## 复盘 → 技能沉淀流程
1. `evolution_review`（或 `dna_board`/`dna_stats`）盘点：看 byLayer / avgEnergy / 高价值记忆
2. proted/settle 层的重复经验 → 固化为 `.skills/<name>/SKILL.md`
3. 落盘即被 skill-filesystem 发现，重启常驻
4. 回写一条记忆记录本次进化

## 检查清单
- [ ] 新经验按复用频率设 energy，重大结论置顶 pinned
- [ ] protect 层保持精简（稀缺）
- [ ] 定期 pull/push 同步双库
- [ ] 高价值重复经验及时固化为技能
