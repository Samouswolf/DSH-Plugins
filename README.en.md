# DSH Plugins

<div align="center">
  
![License-MIT](https://img.shields.io/badge/License-MIT-green.svg)
![Language-JavaScript/Python](https://img.shields.io/badge/Language-JS%2FPython-blue.svg)
![Zero-Sensitive](https://img.shields.io/badge/Privacy-Zero%20Sensitive-brightgreen.svg)
![DSH-Ready](https://img.shields.io/badge/DeepSeek%20Harness-Ready-8b5cf6.svg)

**中文**: [中文版](README.md)
  
</div>

Custom plugins for [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/dsh) that bring Hermes-style DNA memory, a multi-agent farm, and capability evolution into DSH.

> ⚠️ **Security statement**: this repository contains **no personal memory data, no API keys, and no machine-specific paths**. All credentials are injected via environment variables / config files. Do not commit `.env`, any key, or `.dna/` data here.

---

## 📦 What's included

| Plugin | Directory | Purpose |
|--------|-----------|---------|
| **DNA Memory System** | [`dna-plugin/`](dna-plugin/) + [`dna_bridge/`](dna_bridge/) + [`dna_system/`](dna_system/) | Model-free "associative brain": recall/sediment memories, MOA multi-model debate, dual-base sync, auto-inject identity memory on session start |
| **Agent Farm** | [`agent-farm/`](agent-farm/) | Probe local agents (Hermes/WorkBuddy/Claude/Codex/Agnes), status dashboard + one-click dispatch |
| **Evolution Engine** | [`evolution-engine/`](evolution-engine/) | Review the memory & skills library, persist agent-generated experience as reusable SKILLs |

## 🚀 Quick start

```bash
# 1. Copy the plugin directories into your DSH workspace (keep the same folder names).
#    e.g. <workspace>/dna-plugin, <workspace>/dna_bridge, <workspace>/dna_system, <workspace>/agent-farm ...
```

```yaml
# 2. Mount them in your agent preset (agent.cordis.yml)
- id: dsh-dna
  name: 'file:///<workspace>/dna-plugin/index.mjs'

- id: agent-farm
  name: 'file:///<workspace>/agent-farm/index.mjs'

- id: evolution-engine
  name: 'file:///<workspace>/evolution-engine/index.mjs'
```

```bash
# 3. Configure the environment variables (fill in your own keys)
#    Copy config.example and fill as needed. See docs/INSTALL.en.md for every variable.
```

## 📚 Documentation

| Doc | Contents |
|-----|----------|
| [**Install & Config**](docs/INSTALL.en.md) | Prerequisites, per-plugin install steps, full env-var tables, verification |
| [**Caveats**](docs/CAVEATS.en.md) | Security boundaries, privacy, common pitfalls, troubleshooting |
| [Security](SECURITY.md) | reporting vulnerabilities / key-leak handling |
| [Contributing](CONTRIBUTING.md) | how to contribute |
| [Code of Conduct](CODE_OF_CONDUCT.md) | community guidelines |

Chinese docs: [`docs/INSTALL.md`](docs/INSTALL.md) · [`docs/CAVEATS.md`](docs/CAVEATS.md)

## 🔑 Keys you must supply yourself

| Capability | Required Key |
|-----------|--------------|
| MOA debate / DNA system | DeepSeek API key (`DEEPSEEK_API_KEY`) |
| Agent Farm · Agnes image/video | Agnes API key (`AGNES_API_KEY`) |
| Agent Farm · Claude/Codex via relay | Opencode relay key (`OPENCODE_API_KEY`) |

> Without a key the corresponding feature degrades to "unavailable / skipped" and does not block the other plugins from starting.

## 🎯 Examples

Quickest way to see how it works:

| Example | Contents |
|---------|----------|
| [`agent-preset-snippet.yml`](examples/agent-preset-snippet.yml) | Minimal mount snippet (copy & paste) |
| [`dna-quick-usage.md`](examples/dna-quick-usage.md) | DNA memory tool usage in conversation |
| [`agent-farm-usage.md`](examples/agent-farm-usage.md) | Agent Farm usage + key dependencies |
| [`evolution-skill-example.md`](examples/evolution-skill-example.md) | memory → skill persistence walkthrough |

## Security / Privacy

- This repository has **zero sensitive content**: no personal memory, no business data, no local paths, no hard-coded keys.
- Memory data lives in your local `DNA_MEMORY_DIR` (default `~/.dna`) and never enters the repository.
- See [Caveats](docs/CAVEATS.en.md) for more security boundaries.

## License

[MIT](LICENSE) © 2026
