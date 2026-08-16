// ============================================================
// agent-farm — DSH 工具：本地 Agent 农场状态探测
// ============================================================
// 文件插件（file:/// 引用挂进 preset），重启常驻，纯 Host 半。
//
// 作用：探测本机已安装的三种 Agent 工具（WorkBuddy/cbc、Hermes、Trae CN）
//       的 CLI 可用性、版本、模型路由与认证状态，返回 JSON 给模型阅读。
//       —— 只读探测，绝不启动/干扰已运行的 Agent 实例。
//
// 用法（任何 agent 对话里）：
//   farm_status()                        → 探测全部三台 Agent 并返回状态
//
// 数据源（路径）：
//   WorkBuddy → codebuddy CLI + .workbuddy/models.json（走 cbc，headless 可用）
//   Hermes    → hermes-agent venv + cli.py + .hermes/.env（检测凭证；可 headless -q）
//   Trae CN   → bin/trae-cn.cmd + resources/app/out/cli.js（VS Code 系，headless 受限）
//
// 关键点（对齐 dsh-token-stats / dna-board / agent-team）：
//   - 只注册模型工具，不发布服务 → 无需 isolate realm。
//   - ctx.get('fs') 做只读路径探测；ctx.get('subprocess') 跑 Hermes 的 status.py。
//   - 探测失败不抛错，而是返回 { available:false, reason }，可观测不阻塞。
//   零 npm 依赖，纯 ESM。
// ============================================================

export const name = 'dsh-agent-farm'
// 必须注入 webServer：farm 的浏览器 UI 靠 /api/farm/* HTTP 通道取数据。
// 不在 inject 里声明时，apply 可能早于 webServer 就绪，ctx.get('webServer')
// 为 undefined → HTTP API 段被跳过，浏览器 UI 框架能显示但数据全 404（HTTP 40x）。
// 参考官方 dsh-client-connection / dsh-host-frontend-static 的 inject: ['webServer']。
export const inject = ['tools', 'webServer']

// 本机专属路径一律通过环境变量注入，默认走常见的 OS 安装位置；不写死个人主目录。
// 用法示例见 config.example.md，或以 DSH_ 开头的环境变量覆盖。
const HOME = process.env.USERPROFILE || (process.env.HOME || '')
const FARM_DIR = process.env.DSH_FARM_DIR || new URL('.', import.meta.url).pathname.replace(/\/$/, '')
const LOCALAPPDATA = process.env.LOCALAPPDATA || (HOME ? HOME + '/AppData/Local' : '')

const PATHS = {
  workbuddy: {
    label: 'WorkBuddy / CodeBuddy (cbc)',
    cli: process.env.CB_CLI || LOCALAPPDATA + '/Programs/WorkBuddy/resources/app.asar.unpacked/cli/bin/codebuddy',
    modelsJson: process.env.CB_MODELS || HOME + '/.workbuddy/models.json',
  },
  hermes: {
    label: 'Hermes Agent',
    venv: process.env.HERMES_VENV_PY || LOCALAPPDATA + '/hermes/hermes-agent/venv/Scripts/python.exe',
    cli: process.env.HERMES_CLI || LOCALAPPDATA + '/hermes/hermes-agent/cli.py',
    env: process.env.HERMES_ENV || HOME + '/.hermes/.env',
    statusScript: FARM_DIR + '/farm-hermes.py',
  },
  trae: {
    label: 'Trae CN',
    cmd: process.env.TRAE_CMD || LOCALAPPDATA + '/Programs/Trae CN/bin/trae-cn.cmd',
    cliJs: process.env.TRAE_CLI_JS || LOCALAPPDATA + '/Programs/Trae CN/resources/app/out/cli.js',
    exe: process.env.TRAE_EXE || LOCALAPPDATA + '/Programs/Trae CN/Trae CN.exe',
  },
  claude: {
    label: 'Claude Code',
    cli: process.env.CLAUDE_CLI || HOME + '/AppData/Roaming/npm/claude.cmd',
    exe: process.env.CLAUDE_EXE || HOME + '/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/bin/claude.exe',
    dir: process.env.CLAUDE_DIR || HOME + '/.claude',
  },
  codex: {
    label: 'Codex (OpenAI)',
    cli: process.env.CODEX_CLI || HOME + '/AppData/Roaming/npm/codex.cmd',
    js: process.env.CODEX_JS || HOME + '/AppData/Roaming/npm/node_modules/@openai/codex/bin/codex.js',
    dir: process.env.CODEX_DIR || HOME + '/.codex',
    auth: process.env.CODEX_AUTH || HOME + '/.codex/auth.json',
  },
  agnes: {
    label: 'Agnes (AgnesCode)',
    core: process.env.AGNES_CORE || LOCALAPPDATA + '/Programs/AgnesCode/resources/bin/agnesd.exe',
    dir: process.env.AGNES_DIR || LOCALAPPDATA + '/Agnes',
    bridge: FARM_DIR + '/farm-agnes.mjs',
    hermesEnv: process.env.AGNES_ENV || LOCALAPPDATA + '/hermes/.env',
  },
  assets: {
    workbuddy: FARM_DIR + '/assets/workbuddy.png',
    hermes: FARM_DIR + '/assets/hermes.png',
    trae: FARM_DIR + '/assets/trae.svg',
    claude: FARM_DIR + '/assets/claude.png',
    codex: FARM_DIR + '/assets/codex32.png',
    agnes: FARM_DIR + '/assets/agnes.png',
  },
}

// 用 fs 探测路径是否存在（只读 stat）
async function pathExists(ctx, path) {
  const fs = ctx.get('fs')
  if (!fs || typeof fs.resolve !== 'function') return null
  try {
    const t = await fs.resolve(path).catch(() => null)
    if (!t) return false
    const st = await fs.stat(t).catch(() => undefined)
    return !!st
  } catch (e) {
    return false
  }
}

async function runStatusScript(ctx, script, args) {
  const sub = ctx.get('subprocess')
  if (!sub || typeof sub.spawn !== 'function') return { err: 'subprocess 服务不可用' }
  // 用 Hermes 自己的 venv python 跑 hermes status 脚本
  const py = PATHS.hermes.venv
  if (!(await pathExists(ctx, py))) return { err: 'Hermes venv python 不存在' }
  try {
    const handle = sub.spawn({
      argv: [py, script, ...args],
      cwd: FARM_DIR,
      stdio: {
        stdin: 'ignore',
        stdout: { maxBytes: 32 * 1024 },
        stderr: { maxBytes: 8 * 1024 },
      },
      graceMs: 8000,
    })
    const outcome = await handle.done
    const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
    const text = out ? out.text.trim() : ''
    if (outcome.exitCode !== 0 || !text) {
      const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
      return { err: (err ? err.text.trim() : '') || 'status 脚本无输出' }
    }
    try {
      return { data: JSON.parse(text) }
    } catch (e) {
      return { err: 'status 输出非 JSON: ' + text.slice(0, 200) }
    }
  } catch (e) {
    return { err: String(e && e.message ? e.message : e) }
  }
}

// ── farm_call：实际派活给指定本地 Agent ──
async function callHermes(ctx, task, model, exec) {
  const sub = ctx.get('subprocess')
  if (!sub || typeof sub.spawn !== 'function') throw new Error('subprocess 服务不可用')
  const py = PATHS.hermes.venv
  const script = PATHS.hermes.statusScript
  const argv = [py, script, 'run', task]
  if (model) argv.push('--model', model)
  const handle = sub.spawn({
    argv,
    cwd: FARM_DIR,
    stdio: { stdin: 'ignore', stdout: { maxBytes: 256 * 1024, spill: { maxBytes: 1 * 1024 * 1024 } }, stderr: { maxBytes: 64 * 1024 } },
    graceMs: 5000,
    signal: exec && exec.signal,
  })
  const outcome = await handle.done
  const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
  const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
  const text = out ? out.text.trim() : ''
  const errText = err ? err.text.trim() : ''
  if (outcome.exitCode !== 0 || !text) throw new Error('Hermes 调用失败 (exit ' + outcome.exitCode + '): ' + (errText || '无输出'))
  let parsed
  try { parsed = JSON.parse(text) } catch (e) { throw new Error('Hermes 输出非 JSON: ' + text.slice(0, 200)) }
  if (!parsed.ok) throw new Error(parsed.error || 'Hermes 返回错误')
  return { ok: true, agent: 'hermes', model: parsed.model, elapsed_s: parsed.elapsed_s, text: parsed.text }
}

async function callWorkbuddy(ctx, task, model, exec) {
  const sub = ctx.get('subprocess')
  if (!sub) throw new Error('subprocess 服务不可用')
  let nodeExe = 'node'
  try { nodeExe = await sub.resolveExecutable('node') } catch (e) { /* node 默认 */ }
  const argv = [
    PATHS.workbuddy.cli,
    '-p', String(task),
    '--permission-mode', 'bypassPermissions',
    '--model', String(model || 'hy3'),
    '--output-format', 'json',
    '--no-session-persistence',
  ]
  const handle = sub.spawn({
    argv: [nodeExe, ...argv],
    cwd: FARM_DIR,
    stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024, spill: { maxBytes: 8 * 1024 * 1024 } }, stderr: { maxBytes: 256 * 1024 } },
    graceMs: 5000,
    signal: exec && exec.signal,
  })
  const outcome = await handle.done
  const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
  const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
  const text = out ? out.text : ''
  const errText = err ? err.text.trim() : ''
  if (outcome.exitCode !== 0) throw new Error('cbc 失败 (exit ' + outcome.exitCode + '): ' + (errText || '无输出'))
  // 提取 JSON 里的最终 result
  let resultText = text
  try {
    const nl = text.lastIndexOf('\n{')
    if (nl >= 0) {
      const lastJson = JSON.parse(text.slice(nl).trim())
      resultText = (lastJson.result && lastJson.result.text) || resultText
    }
  } catch (e) { /* 保留原文 */ }
  return { ok: true, agent: 'workbuddy', model: model || 'hy3', text: String(resultText).slice(0, 8000) }
}

async function callClaude(ctx, task, model, exec) {
  const sub = ctx.get('subprocess')
  if (!sub || typeof sub.spawn !== 'function') throw new Error('subprocess 服务不可用')
  const argv = [PATHS.claude.exe, '-p', String(task), '--output-format', 'json', '--permission-mode', 'bypassPermissions']
  if (model) argv.push('--model', model)
  const handle = sub.spawn({
    argv,
    cwd: FARM_DIR,
    stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024, spill: { maxBytes: 8 * 1024 * 1024 } }, stderr: { maxBytes: 256 * 1024 } },
    graceMs: 5000,
    signal: exec && exec.signal,
  })
  const outcome = await handle.done
  const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
  const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
  const text = out ? out.text : ''
  const errText = err ? err.text.trim() : ''
  if (outcome.exitCode !== 0) throw new Error('claude 调用失败 (exit ' + outcome.exitCode + '): ' + (errText || '无输出'))
  let resultText = text.trim()
  try {
    const nl = resultText.lastIndexOf('\n{')
    if (nl >= 0) {
      const parsed = JSON.parse(resultText.slice(nl).trim())
      if (parsed && typeof parsed.result === 'string') resultText = parsed.result
    }
  } catch (e) { /* 保留原文 */ }
  return { ok: true, agent: 'claude', model: model || 'default', text: String(resultText).slice(0, 8000) }
}

async function callCodex(ctx, task, model, exec) {
  const sub = ctx.get('subprocess')
  if (!sub || typeof sub.spawn !== 'function') throw new Error('subprocess 服务不可用')
  let nodeExe = 'node'
  try { nodeExe = await sub.resolveExecutable('node') } catch (e) { /* node 默认 */ }
  const argv = [PATHS.codex.js, 'exec', String(task), '--json', '--skip-git-repo-check']
  if (model) argv.push('--model', model)
  const handle = sub.spawn({
    argv: [nodeExe, ...argv],
    cwd: FARM_DIR,
    stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024, spill: { maxBytes: 8 * 1024 * 1024 } }, stderr: { maxBytes: 256 * 1024 } },
    graceMs: 5000,
    signal: exec && exec.signal,
  })
  const outcome = await handle.done
  const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
  const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
  const text = out ? out.text : ''
  const errText = err ? err.text.trim() : ''
  if (outcome.exitCode !== 0) throw new Error('codex 调用失败 (exit ' + outcome.exitCode + '): ' + (errText || '无输出'))
  let resultText = text.trim()
  try {
    const parsed = JSON.parse(resultText)
    if (parsed && Array.isArray(parsed.items)) {
      resultText = parsed.items.map((it) => it && typeof it.text === 'string' ? it.text : '').filter(Boolean).join('\n')
    } else if (parsed && typeof parsed.result === 'string') {
      resultText = parsed.result
    }
  } catch (e) { /* 保留原文 */ }
  return { ok: true, agent: 'codex', model: model || 'default', text: String(resultText).slice(0, 8000) }
}

export const apply = (ctx) => {
  ctx.tools.register({
    name: 'farm_status',
    description:
      '探测本机已安装的三台本地 Agent（WorkBuddy/CodeBuddy cbc、Hermes Agent、Trae CN）的 CLI 可用性、模型路由与认证状态。返回每台的可用能力 JSON。只读探测，不启动任何 Agent 实例。用于：确认哪个本地 Agent 当前能被 DSH 调用。',
    parameters: { type: 'object', properties: {}, additionalProperties: false },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
        properties: {
          ok: { type: 'boolean' },
          agents: { type: 'object', additionalProperties: true },
        },
      },
      render: (args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    async execute() {
      const result = { ok: true, agents: {}, note: '' }

      // ── WorkBuddy / cbc ──
      {
        const cli = await pathExists(ctx, PATHS.workbuddy.cli)
        const models = await pathExists(ctx, PATHS.workbuddy.modelsJson)
        result.agents.workbuddy = {
          label: PATHS.workbuddy.label,
          available: cli === true,
          headless: true,
          cliExists: cli === true,
          modelsJsonExists: models === true,
          note: cli === true
            ? 'codebuddy CLI 存在，headless 可用（node <cli> -p "<prompt>"）'
            : 'codebuddy CLI 不可访问',
        }
      }

      // ── Hermes，跑 status 脚本 ──
      {
        const venv = await pathExists(ctx, PATHS.hermes.venv)
        const cli = await pathExists(ctx, PATHS.hermes.cli)
        const env = await pathExists(ctx, PATHS.hermes.env)
        const hermes = {
          label: PATHS.hermes.label,
          available: venv === true && cli === true && env === true,
          headless: true,
          venvPython: venv === true,
          cli: cli === true,
          envFile: env === true,
        }
        if (venv === true && (await pathExists(ctx, PATHS.hermes.statusScript))) {
          const r = await runStatusScript(ctx, PATHS.hermes.statusScript, ['status'])
          if (r.data) {
            hermes.credentialOk = !!r.data.available
            hermes.model = r.data.model
            hermes.provider = r.data.provider
            hermes.hasDeepseek = !!r.data.has_deepseek
            hermes.hasOpenai = !!r.data.has_openai
            hermes.detailNote = r.data.note || ''
          } else {
            hermes.detailNote = r.err || 'status 脚本未能运行'
            hermes.credentialOk = null
          }
        } else {
          hermes.credentialOk = null
        }
        result.agents.hermes = hermes
      }

      // ── Trae CN ──
      {
        const cmd = await pathExists(ctx, PATHS.trae.cmd)
        const cliJs = await pathExists(ctx, PATHS.trae.cliJs)
        const exe = await pathExists(ctx, PATHS.trae.exe)
        result.agents.trae = {
          label: PATHS.trae.label,
          available: cmd === true && cliJs === true && exe === true,
          headless: false,
          cmdExists: cmd === true,
          cliJsExists: cliJs === true,
          exeExists: exe === true,
          note: 'Trae CN 的 CLI 是 VS Code 系，headless 派单次任务不可靠，仅作状态探测',
        }
      }

      // ── Claude Code ──
      {
        const exe = await pathExists(ctx, PATHS.claude.exe)
        const dir = await pathExists(ctx, PATHS.claude.dir)
        result.agents.claude = {
          label: PATHS.claude.label,
          available: exe === true && dir === true,
          headless: true,
          exeExists: exe === true,
          configDirExists: dir === true,
          note: exe === true ? 'claude.exe 存在，headless 可用（claude -p）' : 'claude CLI 不可访问',
        }
      }

      // ── Codex ──
      {
        const js = await pathExists(ctx, PATHS.codex.js)
        const dir = await pathExists(ctx, PATHS.codex.dir)
        let authOk = false
        const fs = ctx.get('fs')
        if (fs && typeof fs.readText === 'function') {
          try {
            const t = await fs.resolve(PATHS.codex.auth).catch(() => null)
            if (t) {
              const text = await fs.readText(t)
              authOk = text.indexOf('OPENAI_API_KEY') >= 0
            }
          } catch (e) {
            authOk = false
          }
        }
        result.agents.codex = {
          label: PATHS.codex.label,
          available: js === true && authOk === true,
          headless: true,
          cliExists: js === true,
          authOk: authOk,
          note: authOk ? 'codex.js 存在且已认证，headless 可用（codex exec）' : 'codex CLI 存在但未认证',
        }
      }

      const anyOk = Object.values(result.agents).some((a) => a.available)
      result.note = anyOk
        ? '本机 Agent 农场：WorkBuddy(cbc) / Hermes / Trae / Claude Code / Codex。其中 WorkBuddy、Hermes、Claude、Codex 支持 headless 调用；Trae 仅状态探测。'
        : '当前没有可被 DSH 调用的本地 Agent。'
      return result
    },
  })

  // ── farm_call：派活给指定本地 Agent ──
  ctx.tools.register({
    name: 'farm_call',
    description:
      '把任务派给本机指定的本地 Agent 执行并拿回结果。agent=hermes 用 Hermes Agent（deepseek-v4-flash，走官方 cli -q headless）；agent=workbuddy 用 WorkBuddy/CodeBuddy cbc（默认 hy3 免费模型）；agent=claude 用 Claude Code（claude -p）；agent=codex 用 Codex（codex exec）。均可传 model 覆盖。适合：把子任务拆出去交给独立本地 Agent 处理、并行分摊、或复用某台 Agent 的能力。返回该 Agent 的输出文本。委托前建议先 farm_status 确认可用。',
    parameters: {
      type: 'object',
      properties: {
        agent: { type: 'string', description: '目标本地 Agent：hermes / workbuddy / claude / codex', enum: ['hermes', 'workbuddy', 'claude', 'codex'] },
        task: { type: 'string', description: '要派给该 Agent 的完整任务指令' },
        model: { type: 'string', description: '可选模型覆盖（workbuddy 默认 hy3；hermes 默认 deepseek-v4-flash；claude/codex 默认各自配置）' },
      },
      required: ['agent', 'task'],
    },
    output: {
      schema: {
        type: 'object',
        additionalProperties: true,
        properties: {
          ok: { type: 'boolean' },
          agent: { type: 'string' },
          text: { type: 'string' },
        },
      },
      render: (args, value) => [{ type: 'text', text: value && value.text ? value.text : JSON.stringify(value) }],
    },
    timeoutMs: 300000,
    async execute(args, exec) {
      if (args.agent === 'hermes') return callHermes(ctx, args.task, args.model, exec)
      if (args.agent === 'workbuddy') return callWorkbuddy(ctx, args.task, args.model, exec)
      if (args.agent === 'claude') return callClaude(ctx, args.task, args.model, exec)
      if (args.agent === 'codex') return callCodex(ctx, args.task, args.model, exec)
      throw new Error('agent-farm: 未知 agent "' + args.agent + '"（可选 hermes/workbuddy/claude/codex）')
    },
  })

  // ── webServer HTTP API（浏览器端固化 UI 的数据通道）──
  // 文件插件环境没有 harness.handle，Client 半通过 HTTP 调这里。
  // inject: ['webServer'] 保证可用；与官方插件一致地用 ctx.webServer。
  const B64CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
  function bytesToBase64(bytes) {
    let out = ''
    const len = bytes.length
    for (let i = 0; i < len; i += 3) {
      const b0 = bytes[i]
      const b1 = i + 1 < len ? bytes[i + 1] : undefined
      const b2 = i + 2 < len ? bytes[i + 2] : undefined
      out += B64CHARS[b0 >> 2]
      out += B64CHARS[((b0 & 3) << 4) | (b1 === undefined ? 0 : b1 >> 4)]
      out += b1 === undefined ? '=' : B64CHARS[((b1 & 15) << 2) | (b2 === undefined ? 0 : b2 >> 6)]
      out += b2 === undefined ? '=' : B64CHARS[b2 & 63]
    }
    return out
  }

  async function readBytesOrNull(path) {
    const fs = ctx.get('fs')
    if (!fs || typeof fs.readBytes !== 'function') return null
    try {
      const t = await fs.resolve(path).catch(() => null)
      if (!t) return null
      const bytes = await fs.readBytes(t, undefined, 512 * 1024)
      if (!bytes || !bytes.length) return null
      return bytes
    } catch (e) { return null }
  }

  async function iconDataUrl(path, mime) {
    const bytes = await readBytesOrNull(path)
    if (!bytes) return null
    return 'data:' + mime + ';base64,' + bytesToBase64(bytes)
  }

  async function readTextOrNull(path) {
    const fs = ctx.get('fs')
    if (!fs || typeof fs.readText !== 'function') return null
    try {
      const t = await fs.resolve(path).catch(() => null)
      if (!t) return null
      return await fs.readText(t)
    } catch (e) { return null }
  }

  function extractResult(raw) {
    const text = String(raw || '').trim()
    if (!text) return ''
    try {
      const parsed = JSON.parse(text)
      if (Array.isArray(parsed)) {
        for (let i = parsed.length - 1; i >= 0; i--) {
          const it = parsed[i]
          if (!it || typeof it !== 'object') continue
          if (it.type === 'result' && typeof it.result === 'string' && it.result.trim()) return it.result
          if (it.type === 'message' && it.role === 'assistant' && Array.isArray(it.content)) {
            const t = it.content.map((c) => c && c.type === 'output_text' && typeof c.text === 'string' ? c.text : '').filter(Boolean).join('')
            if (t.trim()) return t
          }
        }
      }
      if (parsed && typeof parsed.result === 'string') return parsed.result
      if (parsed && parsed.result && typeof parsed.result.text === 'string') return parsed.result.text
      if (parsed && typeof parsed.output === 'string') return parsed.output
    } catch (e) { /* 继续 */ }
    try {
      const nl = text.lastIndexOf('\n{')
      if (nl >= 0) {
        const parsed = JSON.parse(text.slice(nl).trim())
        if (parsed && typeof parsed.result === 'string') return parsed.result
        if (parsed && parsed.result && typeof parsed.result.text === 'string') return parsed.result.text
      }
    } catch (e) { /* 保留原文 */ }
    return text
  }

  async function runBridge(bridge, mode, task, model, size) {
    const sub = ctx.get('subprocess')
    if (!sub || typeof sub.spawn !== 'function') return { ok: false, error: 'subprocess 服务不可用' }
    let nodeExe = 'node'
    try { nodeExe = await sub.resolveExecutable('node') } catch (e) { /* 默认 */ }
    const argv = [bridge, mode, String(task)]
    if (model) argv.push('--model', model)
    if (mode === 'image') argv.push('--size', size || 'square')
    const handle = sub.spawn({
      argv: [nodeExe].concat(argv),
      cwd: FARM_DIR,
      stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024, spill: { maxBytes: 8 * 1024 * 1024 } }, stderr: { maxBytes: 256 * 1024 } },
      graceMs: 5000,
    })
    const outcome = await handle.done
    const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
    const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
    const text = out ? out.text.trim() : ''
    const errText = err ? err.text.trim() : ''
    if (outcome.exitCode !== 0 || !text) return { ok: false, error: (errText || '桥接调用失败 exit ' + outcome.exitCode).slice(0, 2000) }
    let parsed
    try { parsed = JSON.parse(text) } catch (e) { return { ok: false, error: '桥接输出非 JSON: ' + text.slice(0, 300) } }
    if (!parsed.ok) return { ok: false, error: String(parsed.error || '桥接返回错误') }
    return parsed
  }

  async function runAgent(agent, task, model, mode, size) {
    try {
      if ((agent === 'agnes' || agent === 'workbuddy' || agent === 'hermes') && (mode === 'image' || mode === 'video')) {
        const parsed = await runBridge(PATHS.agnes.bridge, mode, task, model, size)
        if (!parsed.ok) return parsed
        return { ok: true, agent: agent, mode: mode, model: parsed.model || model || 'agnes-image-2.1-flash', text: parsed.text || '', url: parsed.url || '', localPath: parsed.localPath || '', dataUrl: parsed.dataUrl || '' }
      }
      if (agent === 'claude' || agent === 'codex') {
        const parsed = await runBridge(FARM_DIR + '/farm-opencode.mjs', 'chat', task, model || 'deepseek-v4-flash', size)
        if (!parsed.ok) return parsed
        return { ok: true, agent: agent, model: parsed.model || model || 'deepseek-v4-flash', text: parsed.text || '', mode: 'chat' }
      }
      if (agent === 'workbuddy') {
        const sub = ctx.get('subprocess')
        let nodeExe = 'node'
        try { nodeExe = await sub.resolveExecutable('node') } catch (e) { /* 默认 */ }
        const handle = sub.spawn({ argv: [nodeExe, PATHS.workbuddy.cli, '-p', String(task), '--permission-mode', 'bypassPermissions', '--model', String(model || 'hy3'), '--output-format', 'json', '--no-session-persistence'], cwd: FARM_DIR, stdio: { stdin: 'ignore', stdout: { maxBytes: 4 * 1024 * 1024, spill: { maxBytes: 8 * 1024 * 1024 } }, stderr: { maxBytes: 256 * 1024 } }, graceMs: 5000 })
        const outcome = await handle.done
        const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
        const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
        const text = out ? out.text : ''
        const errText = err ? err.text.trim() : ''
        if (outcome.exitCode !== 0) return { ok: false, error: (errText || 'cbc 失败 exit ' + outcome.exitCode).slice(0, 2000) }
        return { ok: true, agent: 'workbuddy', model: model || 'hy3', text: extractResult(text).slice(0, 8000), mode: 'chat' }
      }
      if (agent === 'hermes') {
        const sub = ctx.get('subprocess')
        const argv = [PATHS.hermes.venv, PATHS.hermes.statusScript, 'run', String(task)]
        if (model) argv.push('--model', model)
        const handle = sub.spawn({ argv: argv, cwd: FARM_DIR, stdio: { stdin: 'ignore', stdout: { maxBytes: 256 * 1024, spill: { maxBytes: 1 * 1024 * 1024 } }, stderr: { maxBytes: 64 * 1024 } }, graceMs: 5000 })
        const outcome = await handle.done
        const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
        const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
        const text = out ? out.text.trim() : ''
        const errText = err ? err.text.trim() : ''
        if (outcome.exitCode !== 0 || !text) return { ok: false, error: (errText || 'Hermes 调用失败 exit ' + outcome.exitCode).slice(0, 2000) }
        const parsed = JSON.parse(text)
        if (!parsed.ok) return { ok: false, error: String(parsed.error || 'Hermes 返回错误') }
        return { ok: true, agent: 'hermes', model: parsed.model || model || 'deepseek-v4-flash', text: String(parsed.text || '').slice(0, 8000), mode: 'chat' }
      }
      if (agent === 'agnes') {
        const parsed = await runBridge(PATHS.agnes.bridge, mode === 'image' || mode === 'video' ? mode : 'chat', task, model, size)
        if (!parsed.ok) return parsed
        return { ok: true, agent: 'agnes', mode: parsed.mode || (mode === 'image' || mode === 'video' ? mode : 'chat'), model: parsed.model || model || 'agnes-2.0-flash', text: parsed.text || '', url: parsed.url || '', localPath: parsed.localPath || '', dataUrl: parsed.dataUrl || '' }
      }
      return { ok: false, error: 'agent 不支持 headless 派单: ' + String(agent) }
    } catch (e) {
      return { ok: false, error: String(e && e.message ? e.message : e).slice(0, 2000) }
    }
  }

  async function probeVersion(argv0, extraArgs) {
    const sub = ctx.get('subprocess')
    if (!sub || typeof sub.spawn !== 'function') return ''
    try {
      const handle = sub.spawn({ argv: [argv0].concat(extraArgs || []), cwd: FARM_DIR, stdio: { stdin: 'ignore', stdout: { maxBytes: 8 * 1024 }, stderr: { maxBytes: 4 * 1024 } }, graceMs: 5000 })
      const outcome = await handle.done
      const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
      const text = out ? out.text.trim() : ''
      return text.split('\n')[0].slice(0, 60)
    } catch (e) { return '' }
  }

  async function readWorkbuddyModels() {
    try {
      const text = await readTextOrNull(PATHS.workbuddy.modelsJson)
      if (!text) return []
      const data = JSON.parse(text)
      const list = Array.isArray(data) ? data : (data.models || data.data || data.list || [])
      if (!Array.isArray(list)) return []
      const names = []
      for (const m of list) {
        if (typeof m === 'string') { names.push(m); continue }
        if (m && typeof m === 'object') {
          const n = m.id || m.name || m.model || m.slug
          if (typeof n === 'string' && n) names.push(n)
        }
      }
      return names.slice(0, 30)
    } catch (e) { return [] }
  }

  async function probeHermes() {
    const sub = ctx.get('subprocess')
    const py = PATHS.hermes.venv
    if (!sub || typeof sub.spawn !== 'function') return { err: 'subprocess 服务不可用' }
    const exists = await pathExists(ctx, py)
    if (exists !== true) return { err: 'Hermes venv python 不存在' }
    try {
      const handle = sub.spawn({ argv: [py, PATHS.hermes.statusScript, 'status'], cwd: FARM_DIR, stdio: { stdin: 'ignore', stdout: { maxBytes: 32 * 1024 }, stderr: { maxBytes: 8 * 1024 } }, graceMs: 8000 })
      const outcome = await handle.done
      const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
      const text = out ? out.text.trim() : ''
      if (outcome.exitCode !== 0 || !text) {
        const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
        return { err: (err ? err.text.trim() : '') || 'status 脚本无输出' }
      }
      return { data: JSON.parse(text) }
    } catch (e) { return { err: String(e && e.message ? e.message : e) } }
  }

  // ── 各 Agent 的可选模型清单（供看板下拉；cbc/Hermes 等以运行时可探测的实际值为准）──
  const AGENT_MODELS = {
    workbuddy: ['hy3', 'glm-5.2', 'glm-5.1', 'glm-5v-turbo', 'minimax-m3', 'kimi-k3-1', 'kimi-k2.7', 'kimi-k2.6', 'deepseek-v4-flash', 'deepseek-v4-pro'],
    hermes: ['deepseek-v4-flash', 'deepseek-v4-pro'],
    claude: ['deepseek-v4-flash', 'deepseek-v4-pro'],
    codex: ['deepseek-v4-flash', 'deepseek-v4-pro'],
    agnes: ['agnes-2.0-flash', 'agnes-2.5-flash', 'agnes-2.5-pro', 'agnes-image-2.0-flash', 'agnes-image-2.1-flash', 'agnes-video-v2.0'],
  }

  async function farmStatus(light) {
    const agents = {}
    {
      const cli = await pathExists(ctx, PATHS.workbuddy.cli)
      const models = await pathExists(ctx, PATHS.workbuddy.modelsJson)
      const modelList = light ? [] : await readWorkbuddyModels()
      agents.workbuddy = { label: PATHS.workbuddy.label, available: cli === true, headless: true, cliExists: cli === true, modelsJsonExists: models === true, models: modelList, modelOptions: Array.isArray(modelList) && modelList.length ? modelList : AGENT_MODELS.workbuddy, defaultModel: 'hy3', icon: light ? null : await iconDataUrl(PATHS.assets.workbuddy, 'image/png'), accent: '#2563eb', accent2: '#1d4ed8', note: cli === true ? 'codebuddy CLI 存在，headless 可用' : 'codebuddy CLI 不可访问' }
    }
    {
      const venv = await pathExists(ctx, PATHS.hermes.venv)
      const cli = await pathExists(ctx, PATHS.hermes.cli)
      const env = await pathExists(ctx, PATHS.hermes.env)
      const hermes = { label: PATHS.hermes.label, available: venv === true && cli === true && env === true, headless: true, venvPython: venv === true, cli: cli === true, envFile: env === true, modelOptions: AGENT_MODELS.hermes, defaultModel: 'deepseek-v4-flash', icon: light ? null : await iconDataUrl(PATHS.assets.hermes, 'image/png'), accent: '#8b5cf6', accent2: '#6d28d9' }
      if (!light && venv === true && (await pathExists(ctx, PATHS.hermes.statusScript))) {
        const r = await probeHermes()
        if (r.data) {
          hermes.credentialOk = !!r.data.available
          hermes.model = r.data.model || ''
          hermes.provider = r.data.provider || ''
          hermes.hasDeepseek = !!r.data.has_deepseek
          hermes.hasOpenai = !!r.data.has_openai
          hermes.detailNote = r.data.note || ''
        } else { hermes.detailNote = r.err || 'status 脚本未能运行'; hermes.credentialOk = null }
      } else { hermes.credentialOk = null; hermes.model = ''; hermes.provider = '' }
      agents.hermes = hermes
    }
    {
      const cmd = await pathExists(ctx, PATHS.trae.cmd)
      const cliJs = await pathExists(ctx, PATHS.trae.cliJs)
      const exe = await pathExists(ctx, PATHS.trae.exe)
      agents.trae = { label: PATHS.trae.label, available: cmd === true && cliJs === true && exe === true, headless: false, cmdExists: cmd === true, cliJsExists: cliJs === true, exeExists: exe === true, icon: light ? null : await iconDataUrl(PATHS.assets.trae, 'image/svg+xml'), accent: '#0f172a', accent2: '#334155', note: 'Trae CN 的 CLI 是 VS Code 系，headless 派单次任务不可靠，仅作状态探测' }
    }
    {
      const exe = await pathExists(ctx, PATHS.claude.exe)
      const dir = await pathExists(ctx, PATHS.claude.dir)
      const settings = await pathExists(ctx, PATHS.claude.settings)
      const version = light || exe !== true ? '' : await probeVersion(PATHS.claude.exe, ['--version'])
      agents.claude = { label: PATHS.claude.label, available: exe === true && dir === true, headless: true, version: version, cliExists: exe === true, dirExists: dir === true, settingsExists: settings === true, defaultModel: 'deepseek-v4-flash', modelOptions: AGENT_MODELS.claude, icon: light ? null : await iconDataUrl(PATHS.assets.claude, 'image/png'), accent: '#d97757', accent2: '#b45309', note: '模型走 Opencode 中转（免费 deepseek-v4-flash），不消耗官方配额' }
    }
    {
      const js = await pathExists(ctx, PATHS.codex.js)
      let authOk = false
      const authText = await readTextOrNull(PATHS.codex.auth)
      authOk = !!authText && authText.indexOf('OPENAI_API_KEY') >= 0
      const config = await pathExists(ctx, PATHS.codex.config)
      const version = light || js !== true ? '' : await probeVersion(PATHS.codex.js, ['--version'])
      agents.codex = { label: PATHS.codex.label, available: js === true && authOk === true, headless: true, version: version, cliExists: js === true, authOk: authOk, configExists: config === true, defaultModel: 'deepseek-v4-flash', modelOptions: AGENT_MODELS.codex, icon: light ? null : await iconDataUrl(PATHS.assets.codex, 'image/png'), accent: '#10a37f', accent2: '#0e7490', note: '模型走 Opencode 中转（免费 deepseek-v4-flash）' }
    }
    {
      const core = await pathExists(ctx, PATHS.agnes.core)
      const dir = await pathExists(ctx, PATHS.agnes.dir)
      const envText = await readTextOrNull(PATHS.agnes.hermesEnv)
      const keyOk = !!envText && envText.indexOf('AGNES_API_KEY=') >= 0
      const version = light || core !== true ? '' : await probeVersion(PATHS.agnes.core, ['--version'])
      agents.agnes = { label: PATHS.agnes.label, available: core === true && dir === true, headless: false, apiReady: keyOk === true, coreVersion: version, configDirExists: dir === true, apiUrl: 'https://apihub.agnes-ai.com/v1', modelOptions: AGENT_MODELS.agnes, defaultModel: 'agnes-2.0-flash', icon: light ? null : await iconDataUrl(PATHS.assets.agnes, 'image/png'), accent: '#f472b6', accent2: '#db2777', note: '云通道来自 Hermes 配置（apihub.agnes-ai.com，AGNES_API_KEY），支持对话/生图/生视频，免费限速 20/min' }
    }
    const anyOk = Object.values(agents).some((a) => a.available)
    return { ok: true, note: anyOk ? '本机 Agent 农场：WorkBuddy / Hermes / Trae / Claude Code / Codex / Agnes。' : '当前没有可被 DSH 调用的本地 Agent。', agents }
  }

  const ROLE_MODELS = [
    { provider: 'dashscope', model: 'qwen-vl-max', label: '👁 眼睛 · Qwen VL Max', tag: '视觉 · 131K', desc: '视觉+文本，能力全面' },
    { provider: 'dashscope', model: 'qvq-max', label: '🧠 推理 · QVQ Max', tag: '视觉推理', desc: '看图推理' },
    { provider: 'zhipu', model: 'glm-4v-flash', label: '👁 眼睛 · GLM-4V Flash', tag: '免费视觉', desc: '免费视觉，8K 上下文' },
    { provider: 'opencode-go', model: 'deepseek-v4-flash', label: '⚡ 手 · DeepSeek V4 Flash', tag: '快速免费', desc: '日常对话/执行' },
    { provider: 'opencode-go', model: 'deepseek-v4-pro', label: '🧠 大脑 · DeepSeek V4 Pro', tag: '强推理', desc: '复杂任务' },
  ]

  async function saveModel(provider, model) {
    const adm = ctx.get('agentDefaultModel')
    if (!adm || typeof adm.saveSelection !== 'function') return { ok: false, error: 'agentDefaultModel 服务不可用' }
    try {
      await adm.saveSelection({ provider: provider, model: model, reasoningEffort: 'max' })
      return { ok: true, provider: provider, model: model, note: '已切换为 ' + provider + '/' + model }
    } catch (e) {
      return { ok: false, error: String(e && e.message ? e.message : e).slice(0, 1000) }
    }
  }

  async function currentModel() {
    const adm = ctx.get('agentDefaultModel')
    if (!adm || typeof adm.currentSelection !== 'function') return { ok: false, error: 'agentDefaultModel 服务不可用' }
    try {
      const sel = adm.currentSelection()
      return { ok: true, provider: sel && sel.provider ? sel.provider : '', model: sel && sel.model ? sel.model : '', reasoningEffort: sel && sel.reasoningEffort ? sel.reasoningEffort : '' }
    } catch (e) {
      return { ok: false, error: String(e && e.message ? e.message : e).slice(0, 1000) }
    }
  }

  // HTTP 工具函数
  function sendJson(res, status, obj) {
    try {
      res.writeHead(status, { 'content-type': 'application/json; charset=utf-8', 'cache-control': 'no-cache' })
      res.end(JSON.stringify(obj))
    } catch (e) { /* 客户端已断开 */ }
  }

  function readJsonBody(req) {
    return new Promise((resolve) => {
      const chunks = []
      let size = 0
      req.on('data', (chunk) => {
        size += chunk.length
        if (size > 2 * 1024 * 1024) { resolve(null); req.destroy(); return }
        chunks.push(chunk)
      })
      req.on('end', () => {
        if (!chunks.length) { resolve({}); return }
        try { resolve(JSON.parse(Buffer.concat(chunks).toString('utf8'))) } catch (e) { resolve(null) }
      })
      req.on('error', () => resolve(null))
    })
  }

  const webServer = ctx.webServer
  try {
    ctx.effect(() => webServer.register({
      kind: 'prefix',
      path: '/api/farm',
      handler: async (req, res) => {
        try {
          const url = new URL(req.url || '/', 'http://x')
          const route = url.pathname.replace(/^\/api\/farm\/?/, '') || 'status'
          const method = (req.method || 'GET').toUpperCase()
          if (route === 'status' && method === 'POST') {
            const body = await readJsonBody(req)
            sendJson(res, 200, await farmStatus(!!(body && body.light)))
            return
          }
          if (route === 'call' && method === 'POST') {
            const body = await readJsonBody(req)
            if (!body || typeof body.task !== 'string' || !body.task.trim() || !body.agent) {
              sendJson(res, 400, { ok: false, error: 'agent/task 必填' }); return
            }
            sendJson(res, 200, await runAgent(body.agent, body.task, typeof body.model === 'string' ? body.model : '', typeof body.mode === 'string' ? body.mode : '', typeof body.size === 'string' ? body.size : ''))
            return
          }
          if (route === 'set-model' && method === 'POST') {
            const body = await readJsonBody(req)
            sendJson(res, 200, await saveModel(String((body && body.provider) || 'dashscope'), String((body && body.model) || 'qwen-vl-max')))
            return
          }
          if (route === 'current-model') {
            sendJson(res, 200, await currentModel())
            return
          }
          if (route === 'model-list') {
            sendJson(res, 200, { ok: true, models: ROLE_MODELS })
            return
          }
          sendJson(res, 404, { ok: false, error: '未知端点 /api/farm/' + route })
        } catch (e) {
          sendJson(res, 500, { ok: false, error: String(e && e.message ? e.message : e) })
        }
      },
    }), 'agent-farm: /api/farm 路由')
    console.log('[agent-farm] /api/farm HTTP API 已注册（status/call/set-model/current-model/model-list）')
  } catch (e) {
    console.log('[agent-farm] /api/farm 路由注册失败: ' + (e && e.message ? e.message : e))
  }

  // ── 模型校色工具（对话可直接调用）──
  ctx.tools.register({
    name: 'farm_set_model',
    description:
      '切换当前会话默认模型（AI Role 校色）：provider=模型服务商（dashscope=通义/qwen-vl 视觉、zhipu=智谱/glm-4v、opencode-go=免费中转/deepseek），model=模型名。适合需要看图（换 qwen-vl-max 或 glm-4v-flash）或需要更强推理（deepseek-v4-pro）时调用。',
    parameters: {
      type: 'object',
      properties: {
        provider: { type: 'string', description: '服务商：dashscope / zhipu / opencode-go' },
        model: { type: 'string', description: '模型名，如 qwen-vl-max / glm-4v-flash / deepseek-v4-flash / deepseek-v4-pro' },
      },
      required: ['provider', 'model'],
    },
    output: {
      schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, note: { type: 'string' } } },
      render: (args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    async execute(args) {
      return saveModel(String(args.provider), String(args.model))
    },
  })

  ctx.tools.register({
    name: 'farm_current_model',
    description: '查看当前会话默认模型（服务商 + 模型名）。',
    parameters: { type: 'object', properties: {}, additionalProperties: false },
    output: {
      schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, provider: { type: 'string' }, model: { type: 'string' } } },
      render: (args, value) => [{ type: 'text', text: JSON.stringify(value, null, 2) }],
    },
    async execute() {
      return currentModel()
    },
  })

  console.log('[agent-farm] farm_status + farm_call + farm_set_model + farm_current_model 工具已注册')
}
