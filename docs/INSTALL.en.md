# Install & Configuration Guide

This repository is a collection of custom plugins for [DeepSeek Harness (DSH)](https://github.com/deepseek-ai/dsh). This guide walks you through installing, configuring, and running all three plugins from scratch.

---

## 0. Prerequisites

| Item | Requirement | Notes |
|------|-------------|-------|
| DeepSeek Harness | installed & runnable | plugins are mounted via `file:///` into an agent preset |
| Python | 3.8+ | used by the DNA bridge scripts |
| Node.js | 18+ | used by the Agent Farm bridge scripts |
| numpy | yes | required by the `dna_system` memory core (`pip install numpy`) |

> If you only use **Agent Farm** without DNA, you can skip the Python/numpy parts; conversely if you only use DNA you can skip Node.

---

## 1. General installation

### 1.1 Copy directories

Copy the plugin directories **as-is** into your DSH workspace, **keeping the same folder names** (the code locates sibling dirs/dependencies via relative paths):

```
<workspace>/
├── dna-plugin/       ← DNA memory system (DSH plugin entry)
├── dna_bridge/       ← DNA memory bridge (Python, called by dna-plugin)
├── dna_system/       ← DNA memory core (Python, the Brain)
├── agent-farm/       ← Agent Farm (DSH plugin entry)
└── evolution-engine/ ← Evolution Engine (DSH plugin entry)
```

### 1.2 Mount into an agent preset

In `agent.cordis.yml` (or the preset file you use):

```yaml
# ── DNA memory system ──
- id: dsh-dna
  name: 'file:///<workspace>/dna-plugin/index.mjs'

# ── Agent Farm ──
- id: agent-farm
  name: 'file:///<workspace>/agent-farm/index.mjs'

# ── Evolution Engine ──
- id: evolution-engine
  name: 'file:///<workspace>/evolution-engine/index.mjs'
```

### 1.3 Configure environment variables

Copy the root `config.example` and fill in your machine-specific paths / keys. **Every variable is documented in section 3.**

---

## 2. Per-plugin notes

### 2.1 DNA memory system

- **Entry**: `dna-plugin/index.mjs`
- **Dependencies**: `dna_bridge/` + `dna_system/`, placed side by side
- **Python**: `python` on PATH, with numpy installed
- **Capabilities**:
  - `dna_recall` / `dna_add` / `dna_stats`: recall, sediment, and stat memories in conversation
  - `dna_debate`: MOA multi-model debate (needs a DeepSeek key)
  - `dna_sync`: dual-base sync (pull/push/diff)
  - Auto-recall and inject identity memory into the system prompt on session start
- **Data location**: reads/writes `~/.dna` by default (override with `DNA_MEMORY_DIR`)

### 2.2 Agent Farm

- **Entry**: `agent-farm/index.mjs`
- **Dependencies**: Node.js; Hermes bridge additionally needs Hermes + Python
- **Capabilities**:
  - `farm_status`: probe local agents (Hermes/WorkBuddy/Claude/Codex/Agnes/Trae) for availability & credentials
  - `farm_call`: dispatch a task to a chosen local agent
  - `farm_set_model` / `farm_current_model`: switch/read the current session model
  - Browser dashboard: `/api/farm` (status, dispatch, model tuning)
- **Note**: probing only detects, it does **not** launch agent instances; `farm_call` actually drives them.

### 2.3 Evolution Engine

- **Entry**: `evolution-engine/index.mjs`
- **Capabilities**:
  - `evolution_review`: read-only review of the memory library + list existing skills for a decision
  - `evolution_engine`: persist an agent-produced skill as `SKILL.md` (write into the skills dir and register)
- **Outputs**: skills default to `<skills-dir>/<name>/SKILL.md` (configurable via `EVO_SKILLS_DIR`), auto-discovered by DSH's skill-filesystem, persistent across restarts.

---

## 3. Environment variable reference

### 3.1 DNA memory system

| Variable | Default | Purpose |
|---------|---------|---------|
| `DNA_MEMORY_DIR` | `~/.dna` | memory library dir (where brain_pool.json lives) |
| `DNA_CODE_ROOT` | current dir | `dna_system` code root; added to sys.path by `bridge.py` |
| `DNA_BRIDGE` | `<dna-plugin>/../dna_bridge/bridge.py` | bridge script path |
| `DNA_DEBATE` | `<dna-plugin>/../dna_bridge/debate.py` | MOA debate script path |
| `DNA_SYNC` | `<dna-plugin>/../dna_bridge/sync.py` | sync script path |
| `DNA_IDENTITY_NAMES` | empty | keywords for session "identity memory" injection (comma-separated); empty = disabled |
| `DEEPSEEK_API_KEY` | — | DeepSeek key for MOA debate |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | debate API endpoint |

> Dual-base sync also uses `DNA_DSH_DIR` / `DNA_MAIN_DIR` / `DNA_IMPORT_DIR` — see `dna_bridge/sync.py`.

### 3.2 Agent Farm

| Variable | Default | Purpose |
|---------|---------|---------|
| `AGNES_API_KEY` | — | Agnes cloud API (chat/image/video) |
| `AGNES_API_URL` | `https://apihub.agnes-ai.com/v1` | Agnes endpoint |
| `OPENCODE_API_KEY` | — | Opencode relay (default model route for Claude/Codex) |
| `CB_CLI` | common install path | WorkBuddy codebuddy CLI |
| `HERMES_VENV_PY` | common venv path | Hermes venv python |
| `HERMES_ENV` | `~/.hermes/.env` | Hermes .env (model route / credentials) |
| `HERMES_HOME` | `~/.hermes` | default Hermes HOME |
| `DSH_FARM_DIR` | plugin dir | base path for bridge scripts/assets |

> You can also override per-agent install paths with `CLAUDE_EXE` / `CODEX_JS` / `TRAE_CMD` / `AGNES_CORE` etc. (see the `PATHS` block at the top of `agent-farm/index.mjs`).

### 3.3 Evolution Engine

| Variable | Default | Purpose |
|---------|---------|---------|
| `EVO_SKILLS_DIR` | `<evolution-engine>/../.skills` | skills output dir (scanned by skill-filesystem) |
| `DNA_MEMORY_DIR` | `~/.dna` | memory library read during review |

---

## 4. Verify the install

In a DSH conversation, calling these tools should return a result:

```
# DNA responds (after at least one sedimented memory)
dna_stats

# farm probing
farm_status

# evolution review
evolution_review

# dynamic tools may only appear in the model tool list on the NEXT model step
```

## 5. Common config examples

**Minimal — DNA memory only, no debate:**

```bash
DNA_MEMORY_DIR=~/.dna
# leave DEEPSEEK_API_KEY empty; debate degrades gracefully
```

**Fully enable farm image generation:**

```bash
AGNES_API_KEY=your-agnes-key
OPENCODE_API_KEY=your-opencode-key
```
