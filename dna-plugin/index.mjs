// dsh-dna plugin — DNA 记忆系统接入 DSH 的可复用 Cordis 插件（ESM）
// 被 agent preset 通过绝对路径引用。Host 半：DNA 工具 + 自动沉淀 + RPC。
// Client 半：Hermes 风格记忆面板。
//
// 双模式注册（2026-08-14 修复）：
//   - 动态插件沙箱（cordis_define 定义后运行）：harness 由沙箱注入，
//     走 harness.defineTool / harness.registerTool / harness.handle。
//   - 预设挂载的文件插件（file:/// 引用）：harness 不存在，走标准的
//     ctx.tools.register（与 dsh-tool-fs 等官方工具插件一致）。
// 两种环境都注册同一组 DNA 工具；RPC（记忆面板数据）只在动态环境注册，
// 文件模式下由面板插件自己的 Host 半提供，避免重复注册冲突。
//
// 注意：这是给 Cordis Loader 的插件模块，apply(ctx) 里使用 DSH 注入的
// harness/subprocess 等运行时能力。没有 import 任何 npm 包（保持零依赖）。

export const name = 'dsh-dna'
// 声明所需服务(与官方工具插件 dsh-tool-fs 同款):ctx.tools 是标准工具注册面,
// 未声明 inject 时在文件插件(预设挂载)环境下不可用,导致工具注册被静默跳过。
// (2026-08-14 修复:原版缺少 inject,ctx.tools 为 undefined → 走"无注册面"分支)
// (2026-08-16 修复:ctx.interval 定时刷新依赖 timer 服务,未注入时报
//  "cannot get property 'timer' without inject" 导致预设挂载失败)
export const inject = ['tools', 'subprocess', 'systemPrompt', 'timer']
export const apply = (ctx) => {
  const __dir = new URL('.', import.meta.url).pathname
  const BRIDGE = process.env.DNA_BRIDGE || __dir.replace(/\/$/, '') + '/../dna_bridge/bridge.py'
  const DEBATE = process.env.DNA_DEBATE || __dir.replace(/\/$/, '') + '/../dna_bridge/debate.py'
  const SYNC = process.env.DNA_SYNC || __dir.replace(/\/$/, '') + '/../dna_bridge/sync.py'
  const CODE_ROOT = process.env.DNA_CODE_ROOT || ''
  const MEMORY_DIR = process.env.DNA_MEMORY_DIR || (process.env.USERPROFILE || process.env.HOME || '') + '/.dna'
  // 身份记忆的判别关键词（可配置，默认空→不启用身份过滤）
  const IDENTITY_NAMES = (process.env.DNA_IDENTITY_NAMES || '').split(',').map((s) => s.trim()).filter(Boolean)
  let pythonPath = null

  async function resolvePython() {
    if (pythonPath) return pythonPath
    const sub = ctx.get('subprocess')
    if (!sub) throw new Error('subprocess 服务不可用')
    try { pythonPath = await sub.resolveExecutable('python') } catch (e) { pythonPath = 'python' }
    return pythonPath
  }

  async function runPy(script, argsList, signal, extraEnv) {
    const sub = ctx.get('subprocess')
    if (!sub) throw new Error('subprocess 服务不可用')
    const py = await resolvePython()
    const handle = sub.spawn({
      argv: [py, script, ...argsList],
      cwd: CODE_ROOT || __dir,
      stdio: {
        stdin: 'ignore',
        stdout: { maxBytes: 256 * 1024, spill: { maxBytes: 1024 * 1024 } },
        stderr: { maxBytes: 32 * 1024 },
      },
      graceMs: 5000,
      signal,
      env: Object.assign({ DNA_MEMORY_DIR: MEMORY_DIR, DNA_CODE_ROOT: CODE_ROOT || __dir }, extraEnv || {}),
    })
    const outcome = await handle.done
    const out = handle.collected.stdout ? handle.collected.stdout.readFrom(0) : null
    const err = handle.collected.stderr ? handle.collected.stderr.readFrom(0) : null
    const text = out ? out.text.trim() : ''
    const errText = err ? err.text.trim() : ''
    if (outcome.exitCode !== 0 || !text) {
      throw new Error(`DNA 脚本失败 (exit ${outcome.exitCode}): ${errText || text || '无输出'}`)
    }
    let parsed
    try { parsed = JSON.parse(text) } catch (e) { throw new Error(`DNA 输出非 JSON: ${text.slice(0, 300)}`) }
    if (!parsed.ok) throw new Error(parsed.error || 'DNA 脚本返回错误')
    return parsed
  }

  function textRender(args, value) {
    return [{ type: 'text', text: JSON.stringify(value, null, 2) }]
  }

  // ── 共享工具规格（harness 方言的 parameters：{type:'object', properties, required}）──
  const TOOL_SPECS = [
    {
      name: 'dna_recall',
      description: '从 DNA 记忆库召回相关记忆（零模型依赖的磁吸联想）。对话中遇到问题、任务、经验时先查记忆，避免重复踩坑；也可用于回忆之前沉淀的经验。',
      parameters: {
        type: 'object',
        properties: {
          query: { type: 'string', description: '要联想/检索的关键词或问题描述（中文即可）' },
          top: { type: 'number', description: '返回条数，默认 5，最大 10' },
        },
        required: ['query'],
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, count: { type: 'number' }, results: { type: 'array' } } },
      },
      timeoutMs: 30000,
      execute: async (args, exec) => {
        const top = Math.min(Math.max(Number(args.top) || 5, 1), 10)
        return runPy(BRIDGE, ['recall', String(args.query), '--top', String(top)], exec.signal)
      },
    },
    {
      name: 'dna_add',
      description: '向 DNA 记忆库写入一条记忆（零模型依赖的联想大脑，自动提取领域/意图标签）。在完成任务、解决问题、学到经验后调用，把关键结论沉淀为长期记忆。',
      parameters: {
        type: 'object',
        properties: {
          text: { type: 'string', description: '要沉淀的记忆内容（要点式、带结论）' },
          energy: { type: 'number', description: '初始能量 0~1，默认 0.5；重要经验可给 0.7+' },
          pinned: { type: 'boolean', description: '是否置顶保护（铁律/不可遗忘），默认 false' },
        },
        required: ['text'],
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, id: { type: 'string' }, text: { type: 'string' } } },
      },
      timeoutMs: 30000,
      execute: async (args, exec) => {
        const argv = ['add', String(args.text)]
        if (args.energy !== undefined) argv.push('--energy', String(args.energy))
        if (args.pinned) argv.push('--pinned')
        return runPy(BRIDGE, argv, exec.signal)
      },
    },
    {
      name: 'dna_stats',
      description: '查看 DNA 记忆库统计：总条数、各层（hot/cold/settle/protect）数量、平均能量、记忆库路径。',
      parameters: { type: 'object', properties: {} },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, pool_total: { type: 'number' } } },
      },
      timeoutMs: 30000,
      execute: async (args, exec) => runPy(BRIDGE, ['stats'], exec.signal),
    },
    {
      name: 'dna_debate',
      description: '运行 MOA 多模型辩证：保守派/激进派/综合者 三个角色围绕议题真实调用 LLM 辩证，输出最终决策。适合重大架构决策、方案评审、风险分析。key 自动从环境变量或 Hermes 配置 .env 读取。',
      parameters: {
        type: 'object',
        properties: {
          topic: { type: 'string', description: '议题 ID（topic_1~topic_5 或省略跑全部）；也可传自定义议题文本' },
        },
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, count: { type: 'number' }, decisions: { type: 'array' } } },
      },
      timeoutMs: 600000,
      execute: async (args, exec) => {
        const topic = args.topic ? String(args.topic) : undefined
        const argv = ['run']
        if (topic) argv.push('--topic', topic)
        return runPy(DEBATE, argv, exec.signal)
      },
    },
    {
      name: 'dna_sync',
      description: '同步 DNA 记忆库：pull=主库→DSH副本；push=DSH副本→主库（主库被锁时导出）；diff=对比两库差异。',
      parameters: {
        type: 'object',
        properties: {
          action: { type: 'string', description: 'pull / push / diff', enum: ['pull', 'push', 'diff'] },
          dryRun: { type: 'boolean', description: '仅预览不实际写入' },
        },
        required: ['action'],
      },
      output: {
        schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, action: { type: 'string' } } },
      },
      timeoutMs: 60000,
      execute: async (args, exec) => {
        const argv = [String(args.action)]
        if (args.dryRun) argv.push('--dry-run')
        return runPy(SYNC, argv, exec.signal)
      },
    },
  ]

  // ── 注册面判定(2026-08-14 修复)──
  // 宿主进程的 globalThis.harness 同样存在,不能再用它判定"动态沙箱":
  // 文件插件(预设挂载)环境下 ctx.tools 是标准注册面,应优先使用;
  // 动态插件沙箱的 ctx.tools.register 拒绝非 harness.defineTool 产物(会抛错),
  // 因此 try 失败后回退到 harness 注册。
  // 注意:宿主 tools.register 不编译 parameters,definition.parameters 必须
  // 直接是 JSON Schema({type:'object', properties, required})——spec.parameters
  // 本来就是该形态,原样传入即可(转 property-map 会把顶层 type 弄丢,
  // 上游 LLM 报 "schema must be a JSON Schema of type object, got type null")。
  const harness = ctx.get('harness') || globalThis.harness
  const dynamic = !!(harness && typeof harness.registerTool === 'function')
  const toolsReg = ctx.tools && typeof ctx.tools.register === 'function' ? ctx.tools : null

  let registered = false
  if (toolsReg) {
    try {
      for (const spec of TOOL_SPECS) {
        toolsReg.register({
          name: spec.name,
          description: spec.description,
          parameters: spec.parameters,
          output: { schema: spec.output.schema, render: textRender },
          timeoutMs: spec.timeoutMs,
          async execute(args, exec) {
            return spec.execute(args, exec)
          },
        })
      }
      registered = true
    } catch (e) {
      console.log(`[dna] ctx.tools 注册失败(${e.message}),回退 harness 注册`)
    }
  }
  if (!registered && dynamic) {
    for (const spec of TOOL_SPECS) {
      harness.registerTool(ctx, harness.defineTool({
        name: spec.name,
        description: spec.description,
        parameters: spec.parameters,
        output: { schema: spec.output.schema, render: textRender },
        timeoutMs: spec.timeoutMs,
        execute: spec.execute,
      }))
    }
    registered = true
  }
  if (!registered) {
    // 宿主未注入任何注册面时静默跳过(如 TUI 环境)
    console.log('[dna] 无工具注册面(harness/tools 均不可用),跳过工具注册')
    return
  }

  // RPC(记忆面板数据)—— 只在 harness 存在且 harness.handle 可用时注册,且容错:
  // 文件插件(预设挂载)环境里 ctx.get('harness') 与 globalThis.harness 均为 undefined,
  // 必须先判 harness 非空(否则读 undefined.handle 抛错);若与面板插件(动态)的
  // Host 半注册到同一 harness,重复注册会抛错,由面板插件提供;不同 harness 互不冲突。
  if (harness && typeof harness.handle === 'function') {
    try {
      harness.handle('dna-panel/stats', async (args) => {
        try {
          const s = await runPy(BRIDGE, ['stats'])
          return { ok: true, stats: s }
        } catch (e) {
          return { ok: false, error: e.message }
        }
      })
      harness.handle('dna-panel/recall', async (args) => {
        try {
          const q = String((args && args.query) || '')
          const top = Math.min(Math.max(Number((args && args.top) || 5), 1), 10)
          if (!q) return { ok: false, error: 'query 为空' }
          const r = await runPy(BRIDGE, ['recall', q, '--top', String(top)])
          return { ok: true, results: r.results || [] }
        } catch (e) {
          return { ok: false, error: e.message }
        }
      })
    } catch (e) {
      console.log(`[dna] RPC 注册跳过(可能已由面板插件提供): ${e.message}`)
    }
  }

  // ── 自动沉淀 ──
  function extractText(content) {
    if (!Array.isArray(content)) return ''
    const parts = []
    for (const block of content) {
      if (block && block.type === 'text' && typeof block.text === 'string') parts.push(block.text)
    }
    return parts.join('\n')
  }

  function isSedimentWorthy(text) {
    const t = text.trim()
    if (t.length < 60) return false
    if (/^(好的|ok|好的，|明白了|收到|嗯|可以|没问题|谢谢|知道了)/i.test(t) && t.length < 120) return false
    if (/^[-*•]\s*$/.test(t)) return false
    return true
  }

  const recentSediments = []
  function remember(text) {
    let h = 0
    for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0
    recentSediments.push(h)
    if (recentSediments.length > 50) recentSediments.shift()
    return h
  }
  function isRecent(text) {
    let h = 0
    for (let i = 0; i < text.length; i++) h = (h * 31 + text.charCodeAt(i)) | 0
    return recentSediments.includes(h)
  }

  const sediment = (text) => {
    const t = text.trim()
    if (!isSedimentWorthy(t) || isRecent(t)) return
    remember(t)
    const line = t.length > 600 ? t.slice(0, 600) + '…' : t
    runPy(BRIDGE, ['add', line, '--source', 'dsh-auto'], undefined).then(
      (r) => console.log(`[dna-auto] 已沉淀 ${r.id}`),
      (e) => console.log(`[dna-auto] 沉淀失败: ${e.message}`)
    )
  }

  ctx.on('session/event', (session, event) => {
    if (!event || event.type !== 'assistant/message') return
    try {
      const msg = event.data && event.data.message
      if (!msg) return
      const text = extractText(msg.content)
      if (text) sediment(text)
    } catch (e) {
      console.log(`[dna-auto] 解析失败: ${e.message}`)
    }
  })

  // ── 会话启动时自动注入 DNA 记忆到系统提示词 ──
  // 通过 systemPrompt.section() 注册一个动态 section，把召回的记忆注入系统提示词。
  //
  // 2026-08-15 重构（修复"自动挂载不生效"，两处硬伤）：
  //   ① PromptSection.text 必须【同步】返回（string | (ctx)=>string），不能是 Promise。
  //      旧版 async 召回未完成时返回 '[DNA memory is loading...]' 占位符，首个组装就把
  //      占位符写进 system prompt；LLM 请求缓存按渲染文本精确命中，占位符被冻结，
  //      看起来"没自动挂载"。现在【永不返回占位符】——没有就返回 ''，renderPrompt 丢弃。
  //   ② 旧版只召回一次永久缓存，且走磁吸打分，Top 全是带"身份…"字样的
  //      会话噪音/沉淀碎片，真正的身份记忆排不进 Top5。改用新增的 `identity` 命令
  //      【确定性】拉保护层(pinned)记忆，再按身份关键词过滤，只注入真实的身份/背景，
  //      不掺会话噪音；后台预热 + 短 TTL 周期刷新，每次组装都同步读到最新快照。
  const sysPrompt = ctx.get('systemPrompt')
  if (sysPrompt && typeof sysPrompt.section === 'function') {
    let snapshot = null          // { lines: string }
    let warming = false          // 防并发重复召回
    const TTL_MS = 60 * 1000     // 每 60s 后台刷新一次身份快照
    const MAX_LINES = 5
    // 身份记忆的判别基准：pinned 记忆的【标题】需以身份名开头，或正文以"身份名 是"开头。
    // 身份名来自环境变量 DNA_IDENTITY_NAMES（逗号分隔）；未配置则不启用身份过滤。
    // 技术归档（【DSH/DNA/Hermes…】）标题不含身份词，天然被排除 —— 用标题而非正文
    // 匹配，避免正文里出现的 "agent" 误判。
    function identityHeader(text) {
      const m = /^【([^】]+)】/.exec(text)
      return m ? m[1] : text.slice(0, 24)
    }
    function isIdentityLine(text) {
      if (IDENTITY_NAMES.length === 0) return true
      const head = identityHeader(text)
      return IDENTITY_NAMES.some((n) => head.startsWith(n) || text.trim().startsWith(n + ' 是'))
    }

    async function refreshSnapshot() {
      if (warming) return
      warming = true
      try {
        const r = await runPy(BRIDGE, ['identity'], undefined)
        const results = (r && r.results) || []
        const keep = results
          .filter((item) => item.text && isIdentityLine(item.text))
          .slice(0, MAX_LINES)
        if (keep.length > 0) {
          snapshot = { lines: keep.map((item) => `- ${item.text}`).join('\n'), ts: Date.now() }
          console.log(`[dna-mem] 身份快照就绪 ${keep.length} 条`)
        } else {
          snapshot = null
          console.log('[dna-mem] 未匹配到身份记忆（保持空注入）')
        }
      } catch (e) {
        console.log(`[dna-mem] 身份快照刷新失败，本次保留上一份: ${e.message}`)
        // 失败保留旧快照，保证注入不中断
      } finally {
        warming = false
      }
    }

    // 立即后台预热 + 周期刷新。ctx.interval() 返回的 disposer 归当前 fiber 所有，
    // 插件卸载自动回收，无需手动清理（Cordis fiber 生命周期保证）。
    refreshSnapshot()
    ctx.interval(() => refreshSnapshot(), TTL_MS)

    sysPrompt.section({
      name: 'dna-session-memory',
      // order 50：persona(0) 之后、工具说明(100~199) 之前，紧跟在身份后面。
      order: 50,
      text: () => {
        // 同步返回。无就绪副本则返回 ''（renderPrompt 会丢弃空 section）。
        return snapshot ? `## DNA Memory Context\nThe following memories were automatically recalled for this session:\n${snapshot.lines}` : ''
      },
    })
  } else {
    console.log('[dna-boot] systemPrompt 不可用，跳过自动记忆注入')
  }
}
