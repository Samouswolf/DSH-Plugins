# dsh-dna — DNA 记忆系统

零模型依赖的 DNA「联想大脑」接入 DSH 的插件。在对话中自动召回/沉淀记忆、MOA 多模型辩证、双库同步、会话启动自动注入身份记忆。文件插件双半包，重启常驻。

## 文件

| 目录 | 作用 |
|------|------|
| `dna-plugin/` | DSH 插件入口（工具 + 自动沉淀 + 提示词注入） |
| `dna_bridge/` | Python 桥接：`bridge.py`(召回/沉淀/统计) `debate.py`(MOA辩证) `sync.py`(双库同步) |

> 依赖：记忆核心 `dna_system/`（Brain 实现），需与本插件一起部署并指向其代码根。

## 安装

```yaml
- id: dsh-dna
  name: 'file:///<工作区>/dna-plugin/index.mjs'
```

并确保 Python 可用，`dna_bridge/` 与 `dna-plugin/` 同级。

## 配置（环境变量）

| 变量 | 说明 | 默认 |
|------|------|------|
| `DNA_BRIDGE` | bridge.py 路径 | `<插件>/../dna_bridge/bridge.py` |
| `DNA_DEBATE` | debate.py 路径 | `<插件>/../dna_bridge/debate.py` |
| `DNA_SYNC` | sync.py 路径 | `<插件>/../dna_bridge/sync.py` |
| `DNA_MEMORY_DIR` | 记忆库目录 | `~/.dna` |
| `DNA_CODE_ROOT` | dna_system 代码根 | 插件目录 |
| `DNA_IDENTITY_NAMES` | 自动注入的身份记忆关键词（逗号分隔） | 空（不启用身份过滤） |
| `DNA_DSH_DIR` / `DNA_MAIN_DIR` / `DNA_IMPORT_DIR` | 双库同步三路路径 | 见 `sync.py` |

MOA 辩证需要 DeepSeek API key：可设 `DEEPSEEK_API_KEY` / `DEEPSEEK_BASE_URL`，或写入 Hermes 生态的 `.env` 由脚本补全。

## 隐私

⚠️ 本仓库**不含任何记忆数据**（`.dna/` 目录被 gitignore 排除）。记忆发生在你本地的 `DNA_MEMORY_DIR`，只有你打算分享的技能产物（经 evolution-engine）才可能被导出。
