# 注意事项 & 故障排查

使用本仓库插件前请先读这篇。关系到你的隐私、安全，以及"为什么我跑不起来"。

---

## 🔒 安全与隐私

### 绝对不要提交的内容
仓库的 `.gitignore` 已排除以下内容，但请**自己也不要 add**：

- `.env`、任何 `*sk-*` Key、`credentials*`、`*.pem`
- `.dna/`（你的记忆库，含个人/业务隐私）
- `*.log`、`memory_watcher*`、生成产物 `**/output/`
- Python 缓存 `__pycache__/`、`*.pyc`

### 记忆数据去哪了
- DNA 系统的记忆存在**你本地**的 `DNA_MEMORY_DIR`（默认 `~/.dna`）。
- 仓库里只有代码；你的记忆永远不会进 GitHub。
- `evolution-engine` 固化的技能默认写到 `<EVO_SKILLS_DIR>/<name>/SKILL.md`，**技能内容默认不进仓库**（除非你把 `.skills` 也纳入发布）。

### Key 怎么配
- 代码**不硬编码任何 Key**，全部读环境变量。
- 推荐：不要在 global shell profile 里长期 export，而是用 `.env` 文件 + 运行前 source，或在 DSH 的启动配置里注入。
- 一旦某个 Key 意外进了公开仓库，视为已泄露，请**及时轮换**。

### 路径与工作目录
- 代码使用相对路径找兄弟目录；把插件拷进工作区时**保持目录名一致**。
- 全部本机专属路径可通过环境变量覆盖（见 `docs/INSTALL.md` 第 3 节），不要改源码。

---

## ⚠️ 运行前置提醒

| 为什么装好没反应 | 排查 |
|------------------|------|
| 工具列表里看不到 `dna_*` | 确认 `dna-plugin/index.mjs` 已挂载；`python` 可用 |
| 看不到 `farm_*` | 确认 `agent-farm/index.mjs` 已挂载 |
| 看不到 `evolution_*` | 确认 `evolution-engine/index.mjs` 已挂载 |
| 工具注册了但要下一轮才出现 | 动态注册的工具要到**下一个模型步骤**才注入可见，属正常 |

### 工具注册面的区别（重要）
- **文件插件 / preset 挂载**：用 `ctx.tools.register` 注册工具。
- **动态创建插件（cordis_define）**：必须用 `harness.registerTool` 注册，用 `ctx.tools.register` 会在当前 Agent 不可见。
- 如果你把 `dna-plugin` 作为动态插件临时运行而非文件插件挂载，请走 harness 路径（代码已同时兼容两种）。

---

## 🐛 常见问题

### DNA 系统
- **`bridge.py` 报"找不到 Brain"**：确认 `DNA_CODE_ROOT` 指向 `dna_system` 父目录，且 `python` 能 `import dna_system`。
- **中文乱码**：脚本已强制 UTF-8 输出；若仍乱码，检查 Shell 代码页（Windows: `chcp 65001`）。
- **记忆不注入系统提示词**：确认 `systemPrompt` 可用（官方 preset 默认有）；注入的 section 必须**同步**返回字符串。
- **MOA 辩证一直失败**：需要 `DEEPSEEK_API_KEY`，且端点可访问。

### Agent 农场
- **探不到某 Agent**：多是路径没匹配到默认位置，用对应环境变量覆盖（如 `CB_CLI`、`HERMES_VENV_PY`、`CLAUDE_EXE`、`CODEX_JS`）。
- **Hermes 相关失败**：确认给 subprocess 的权限，以及 `HERMES_ENV` / `HERMES_HOME` 正确。
- **生图/生视频报 key 缺失**：设 `AGNES_API_KEY`。
- **Claude/Codex 卡片无模型**：设 `OPENCODE_API_KEY`（走 Opencode 免费中转）。

### 进化引擎
- **技能写到哪了**：`EVO_SKILLS_DIR`。若想让 DSH 自动发现，把它纳入 DSH 的 skill 扫描目录（`skill-filesystem` 的 `customSkillDirs`）。
- **evolution_review 为空**：`DNA_MEMORY_DIR` 下还没有 `brain_pool.json` 或该目录没有实体。

---

## 🧹 Git 使用建议

- 每次改完：`git add <具体文件>` → `git commit` → `git push origin main`。
- **不要 `git add -A` 一把梭**，尤其当工作区里混着 `.dna/`、`.env` 时。
- 提交前可以快扫一遍：`git ls-files | grep -E '\.dna|sk-|\.env$|brain_pool'`，应无结果。

---

## Q: 这个仓库和我本地有什么不同？

发布到 GitHub 的版本经过了**脱敏**：
- `dna_system` 是**通用记忆核心**，不含任何特定业务领域的逻辑、数据或工作规则。
- 所有本机路径、用户名、Key 均已移除/占位化。
- 本地原始工作区不会被推上去；GitHub 仓库只含干净的可公开内容。
