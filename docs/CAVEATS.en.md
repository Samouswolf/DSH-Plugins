# Caveats & Troubleshooting

Please read this before using the plugins. It concerns your privacy, security, and "why isn't it working".

---

## 🔒 Security & Privacy

### What you must never commit
The repo `.gitignore` already excludes the following, but please **don't add them yourself**:

- `.env`, any `*sk-*` key, `credentials*`, `*.pem`
- `.dna/` (your memory library — contains personal/business privacy)
- `*.log`, `memory_watcher*`, generated outputs `**/output/`
- Python caches `__pycache__/`, `*.pyc`

### Where does memory data go?
- DNA memory is stored **locally** in `DNA_MEMORY_DIR` (default `~/.dna`).
- The repository contains only code; your memory never reaches GitHub.
- `evolution-engine` writes generated skills to `<EVO_SKILLS_DIR>/<name>/SKILL.md` by default; **skill content is not in the repo unless you also publish `.skills`**.

### How to configure keys
- Code **never hard-codes any key**; it reads environment variables only.
- Recommended: don't export long-lived keys in a global shell profile. Use a `.env` file and source it before running, or inject via DSH startup config.
- Once a key is accidentally pushed to a public repo, treat it as leaked and **rotate it immediately**.

### Paths & working directory
- Code uses relative paths to find sibling dirs; **keep folder names the same** when copying plugins into the workspace.
- All machine-specific paths are overridable via env vars (see `docs/INSTALL.en.md` section 3). Don't edit the source.

---

## ⚠️ Startup reminders

| "It's installed but nothing shows" | Check |
|-----------------------------------|-------|
| `dna_*` tools missing | `dna-plugin/index.mjs` mounted; `python` available |
| `farm_*` tools missing | `agent-farm/index.mjs` mounted |
| `evolution_*` tools missing | `evolution-engine/index.mjs` mounted |
| Tool registered but appears later | dynamically registered tools appear on the **next** model step — normal |

### Tool registration surfaces (important)
- **File plugin / preset mount**: registers tools via `ctx.tools.register`.
- **Dynamically created plugin (cordis_define)**: must use `harness.registerTool`; `ctx.tools.register` is not visible to the current agent.
- If you run `dna-plugin` as a temporary dynamic plugin rather than a mounted file plugin, it should use the harness path (the code supports both).

---

## 🐛 Common issues

### DNA system
- **`bridge.py` reports "Brain not found"**: make sure `DNA_CODE_ROOT` points to the `dna_system` parent, and `python` can `import dna_system`.
- **Chinese mojibake**: scripts force UTF-8 output; if still garbled, check the shell codepage (Windows: `chcp 65001`).
- **Memory not injected into system prompt**: confirm `systemPrompt` is available (present by default in the official preset); the injected section must return a **synchronous** string.
- **MOA debate keeps failing**: needs `DEEPSEEK_API_KEY` and a reachable endpoint.

### Agent Farm
- **Cannot detect an agent**: usually a path mismatch; override with the matching env var (e.g. `CB_CLI`, `HERMES_VENV_PY`, `CLAUDE_EXE`, `CODEX_JS`).
- **Hermes-related failures**: check subprocess permissions and that `HERMES_ENV` / `HERMES_HOME` are correct.
- **Image/video says missing key**: set `AGNES_API_KEY`.
- **Claude/Codex cards have no model**: set `OPENCODE_API_KEY` (Opencode free relay).

### Evolution Engine
- **Where do skills go**: `EVO_SKILLS_DIR`. To have DSH auto-discover them, include it in DSH's skill scan dirs (`skill-filesystem`'s `customSkillDirs`).
- **`evolution_review` is empty**: `DNA_MEMORY_DIR` has no `brain_pool.json` yet, or it has no entities.

---

## 🧹 Git usage advice

- After each change: `git add <specific files>` → `git commit` → `git push origin main`.
- **Do not `git add -A` blindly**, especially when the working dir contains `.dna/` or `.env`.
- A quick pre-commit scan: `git ls-files | grep -E '\.dna|sk-|\.env$|brain_pool'` should return nothing.

---

## Q: How does this repo differ from the author's local copy?

The version published to GitHub has been **sanitized**:
- `dna_system` is a **generic memory core** with no business/game-specific logic, data, or work rules.
- All local paths, usernames, and keys have been removed or replaced with placeholders.
- The local working directory is not pushed; the GitHub repo contains only clean, publishable content.
