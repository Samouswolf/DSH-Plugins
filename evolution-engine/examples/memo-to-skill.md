---
name: memo-to-skill
description: 把 DNA 记忆库里的高价值经验封装成可复用技能。从 evolution_review 复盘结果中挑出值得固化的条目，写出 SKILL.md（frontmatter: name+description; 正文: 用途/何时用/步骤/清单），落盘到 .skills/<name>/并注册。当用户要"把学到的东西变成技能""进化沉淀"时使用。
version: 1.0.0
---

# 记忆 → 技能封装

## 用途
把散落在 DNA 记忆库里的高价值经验（energy 高 / protect·hot 层 / 反复出现的 fix 经验），固化为可复用的 Skill，形成"经验→记忆→技能→进化"闭环。

## 何时使用
- 用户在对话中沉淀了一批经验，想固化技能
- 用户说"把 XX 变成技能""自动打包技能""进化升级"
- 定期复盘 DNA 记忆库时发现可复用经验

## 操作步骤
1. 调 `evolution_review` 盘点记忆库：看 byLayer / byDomain、高价值记忆摘录、现有技能缺口。
2. 挑 1 条最值得固化的经验（重复次数多、可复用、有明确操作步骤）。
3. 写 SKILL.md：
   - frontmatter：`name`（kebab-case）+ `description`（做什么、何时用）+ `version`
   - 正文：`## 用途` / `## 何时使用` / `## 操作步骤` / `## 检查清单`
4. 落盘到 `<技能目录>/<name>/SKILL.md`。
5. 若在对话框执行：用 `evolution_engine` 工具落盘并动态注册（即时生效）。

## 检查清单
- [ ] name 是 kebab-case（小写+连字符）
- [ ] description 一句说明做什么、何时用
- [ ] 正文含可执行步骤而非空泛描述
- [ ] 文件在 .skills/<name>/SKILL.md
