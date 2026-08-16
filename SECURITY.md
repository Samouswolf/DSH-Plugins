# 安全策略 / Security Policy

## 支持的版本 / Supported Versions

本仓库持续迭代，建议始终使用最新 `main` 分支版本。

## 🔑 密钥处理 / Key handling

### 仓库内不会有 Key
- 代码**绝不硬编码任何 API key、token 或密钥**，全部通过环境变量读取。
- 缺失 key 时对应功能**自动降级**（不可用/跳过），不会崩溃或伪造。

### 你自己也别提交 Key
- 仓库 `.gitignore` 已排除 `.env`、`*sk-*`、`credentials*`、`*.pem` 等。
- 请在 issue / PR / 评论中**不要粘贴任何 key**。

### Key 泄露了怎么办
一旦某个 key 意外进入公开仓库，**视为已泄露**：
1. **立即轮换**该 key（在对应服务商控制台撤销并重新生成）。
2. 在仓库 [Issues](https://github.com/Samouswolf/DSH-Plugins/issues) 报告（**不要**在报告里贴 key）。
3. 若泄露的是你组织的生产凭据，按贵组织的应急流程处理。

## 🧠 个人数据 / Personal data

- 本仓库只含代码，**不含任何记忆数据、业务数据或工作规则**。
- 记忆数据永不进 GitHub；它存在于使用者的本地 `DNA_MEMORY_DIR`（默认 `~/.dna`）。
- 若你发现仓库中出现了个人/敏感内容，立即按下方联系方式报告。

## 🐛 报告漏洞 / Reporting a vulnerability

如有安全漏洞或敏感内容，请优先**私信 / 邮件**而非公开 issue，以留出修复时间：

- 通过 GitHub Issue 时，选择 **bug_report** 模板并在标题加 `[SECURITY]`
- 内容**不要包含**任何 key / 私有路径 / 记忆数据

处理承诺：
- 我们会尽快评估、修复并同步。
- 若问题涉及已公开数据（如误提交 key），会第一时间提醒相关后果。
