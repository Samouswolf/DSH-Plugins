# 贡献指南 / Contributing Guide

欢迎为 DSH Plugins 贡献！无论是修 Bug、加特性，还是完善文档，都很感谢。

> 中文优先，但英文 PR 也完全欢迎（仓库已提供双语文档）。

## 🧭 开发前须知

- 插件是 DSH（DeepSeek Harness）的自定义 Cordis 插件，纯 ESM + Python，无 npm 依赖。
- 目录职责：
  - `dna-plugin/` / `agent-farm/` / `evolution-engine/`：DSH 插件入口（`.mjs`）
  - `dna_bridge/` / `dna_system/`：Python 桥接与记忆核心
  - `docs/`：文档（中英各一份）
- 改动建议参考现有写法（见 `docs/CAVEATS.md` 的「工具注册面」等注意事项）。

## 🚫 绝不做的

- **不提交任何 key**：环境变量依赖见 `config.example`。
- **不提交 `.dna/`、`.env`、`.log`、生成产物 `**/output/`**。
- **不提交个人/业务路径**：一律用 `<工作区>` / `<workspace>` 占位。
- 若有此需求，请在 PR 说明里声明。

## 🌱 提交流程

1. **Fork** 本仓库，`git clone` 到本地。
2. 新建分支：`git checkout -b feat/your-feature` 或 `fix/your-fix`。
3. 修改代码 / 文档。
4. **本地验证**：
   - 语法：`python -c "import dna_system; from dna_system.core.brain import Brain; Brain()"`（DNA 相关）
   - 或加载插件，确认工具可注册、可调用。
   - 过一下安全扫描（无命中）：
     ```bash
     git ls-files | grep -E '\.dna|sk-[A-Za-z0-9]{8}|\.env$|brain_pool\.json'
     ```
5. 提交（写清改动说明），push 到你的 fork，发 PR。
6. PR 用仓库的 [PULL_REQUEST_TEMPLATE](.github/PULL_REQUEST_TEMPLATE.md)，勾选安全清单。

## ✅ 提交信息规范

建议用语义化前缀：
- `feat:` 新功能
- `fix:` 修 Bug
- `docs:` 文档
- `refactor:` 重构
- `chore:` 杂务

示例：`feat(agent-farm): 支持探测 Trae CN`

## 📦 环境变量改动

新增/修改环境变量时，请同步更新：
- 代码默认值（保持「能跑」）
- `config.example`
- `docs/INSTALL.md` 与 `docs/INSTALL.en.md` 的环境变量表
- 相关插件 `README.md`

## 🧪 测试

- 若改动涉及 Python 核心，尽量补一个可运行的验证（脚本或 `if __name__ == "__main__"` 冒烟测试）。
- 若涉及 DSH 工具，说明如何在对话中触发验证。

有疑问欢迎先开 [Issue](https://github.com/Samouswolf/DSH-Plugins/issues) 讨论再动手。
