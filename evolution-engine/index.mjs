// ============================================================
// evolution-engine — DSH 进化引擎
// ============================================================
// 复盘 DNA 记忆库与技能库，把 Agent 产出的经验持久化落盘为可复用技能，
// 形成「经验 → 记忆 → 技能 → 进化」闭环。
//
// 两个模型工具：
//   evolution_review  —— 只读盘点记忆库 + 现有技能，供复盘决策
//   evolution_engine  —— 把产物落盘为技能并注册，即时生效 / 重启常驻
//
// 路径全部可配置（环境变量）：
//   EVO_SKILLS_DIR    技能落盘目录（默认 <插件>/../.skills）
//   DNA_MEMORY_DIR    记忆库目录（默认 ~/.dna，读取其中的 brain_pool.json）
//
// ⚠️ 本文件不含任何密钥或本机私有路径。
// ============================================================

const LAYER_W = { hot: 3, settle: 2, protect: 4, cold: 1 }

// 技能落盘目录（默认取插件所在目录的上层 .skills）
const __dir = new URL('.', import.meta.url).pathname
const SKILLS_DIR = process.env.EVO_SKILLS_DIR || (__dir.replace(/\/$/, '') + '/../.skills')
const MEMORY_HOME = process.env.DNA_MEMORY_DIR || ((process.env.USERPROFILE || process.env.HOME || '') + '/.dna')
const POOL = SKILLS_DIR ? MEMORY_HOME + '/brain_pool.json' : ''

export const name = 'dsh-evolution-engine'
export const inject = ['fs', 'skills']
export const apply = (ctx) => {
  const fs = ctx.get('fs')
  const skills = ctx.get('skills')
  if (!fs || !skills) return

  const toolDefs = [
    {
      name: 'evolution_engine',
      description: '进化引擎·落盘注册。把一条已生成的技能产物持久化为 SKILL.md 并动态注册为可调用技能，重启后由 skill-filesystem 自动发现(常驻)。使用前应先调用 evolution_review 做复盘。',
      parameters: {
        type: 'object',
        properties: {
          name: { type: 'string', description: '技能名，kebab-case(小写字母数字连字符)' },
          description: { type: 'string', description: '技能描述(frontmatter description)' },
          body: { type: 'string', description: '技能正文(markdown)：可复用工作流' },
          overwrite: { type: 'boolean', description: '同名已存在时是否覆盖，默认 false' },
        },
        required: ['name', 'description', 'body'],
      },
      output: { schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, path: { type: 'string' }, registered: { type: 'boolean' }, message: { type: 'string' } } } },
      timeoutMs: 20000,
      async execute(args, exec) {
        const name = String(args.name || '').trim()
        if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(name)) return { ok: false, message: '技能名必须 kebab-case: ' + name }
        const description = String(args.description || '').trim()
        const body = String(args.body || '')
        if (!description || !body) return { ok: false, message: 'description 和 body 不能为空' }
        const file = await fs.resolve(SKILLS_DIR + '/' + name + '/SKILL.md')
        let existed = false
        try { existed = !!(await fs.stat(file, exec.signal)) } catch (e) { existed = false }
        if (existed && !args.overwrite) return { ok: false, message: '技能已存在(' + file + ')，覆盖请传 overwrite=true' }
        const frontmatter = '---\nname: ' + name + '\ndescription: ' + description.replace(/\n/g, ' ') + '\nversion: 1.0.0\n---\n\n' + body.trim() + '\n'
        try { await fs.writeText(file, frontmatter, undefined, exec.signal) }
        catch (e) { return { ok: false, message: '落盘失败: ' + (e && e.message ? e.message : String(e)) } }
        let registered = false, registeredMsg = ''
        try {
          const d = skills.register({ name, description, instructions: body })
          ctx.effect(() => d)
          registered = true
        } catch (e2) { registeredMsg = ' 动态注册失败: ' + (e2 && e2.message ? e2.message : String(e2)) }
        return { ok: true, path: file, registered, message: (existed ? '已覆盖' : '已创建') + ' ' + name + ' → ' + file + registeredMsg }
      },
    },
    {
      name: 'evolution_review',
      description: '进化引擎·复盘盘点。只读加载 DNA 记忆库 brain_pool.json(按 layer/energy 聚合)+ 列出技能目录，返回统计与高价值记忆摘录，供 Agent 判断哪些经验可固化为技能。不改文件。',
      parameters: {
        type: 'object',
        properties: {
          top: { type: 'number', description: '返回高价值记忆条数上限(默认 8)' },
          domain: { type: 'string', description: '可选：只统计某领域' },
        },
        required: [],
      },
      output: { schema: { type: 'object', additionalProperties: true, properties: { ok: { type: 'boolean' }, stats: { type: 'object' }, existingSkills: { type: 'array' }, highValueMemories: { type: 'array' } } } },
      timeoutMs: 20000,
      async execute(args, exec) {
        const top = Math.min(Math.max(Number(args.top) || 8, 1), 20)
        const domainFilter = args.domain ? String(args.domain).toLowerCase() : null
        let entities = []
        try {
          const t = await fs.resolve(POOL)
          const raw = await fs.readText(t, exec.signal)
          const p = JSON.parse(raw)
          if (Array.isArray(p.entities)) entities = p.entities
        } catch (e) {}
        const stats = { total: entities.length, byLayer: {}, byDomain: {}, avgEnergy: 0 }
        let energySum = 0
        const dc = {}
        for (const ent of entities) {
          const layer = ent.layer || 'cold'
          stats.byLayer[layer] = (stats.byLayer[layer] || 0) + 1
          energySum += typeof ent.energy === 'number' ? ent.energy : 0.5
          const ds = (ent.dna && Array.isArray(ent.dna.domain)) ? ent.dna.domain.join('/') : ''
          if (ds) { const d = (ds.split('/')[0] || '').replace(/[^\w\u4e00-\u9fa5]/g, ''); if (d) dc[d] = (dc[d] || 0) + 1 }
        }
        stats.avgEnergy = entities.length ? +(energySum / entities.length).toFixed(2) : 0
        stats.byDomain = Object.entries(dc).sort((a, b) => b[1] - a[1]).slice(0, 15)
        const highValue = entities
          .filter((e) => { if (!domainFilter) return true; const t = (e.text || '').toLowerCase(); const dd = (e.dna && (e.dna.domain || []).join(' ')).toLowerCase(); return t.indexOf(domainFilter) >= 0 || dd.indexOf(domainFilter) >= 0 })
          .map((e) => ({ id: e.id, layer: e.layer, energy: e.energy, pinned: !!e.pinned, text: String(e.text || '').slice(0, 400) }))
          .sort((a, b) => (LAYER_W[b.layer] || 1) - (LAYER_W[a.layer] || 1) || (b.energy || 0) - (a.energy || 0) || (b.pinned ? 1 : 0) - (a.pinned ? 1 : 0))
          .slice(0, top)
        let existingSkills = []
        try {
          const t = await fs.resolve(SKILLS_DIR)
          const entries = await fs.listDir(t, exec.signal)
          existingSkills = entries.map((e) => e.name || '').filter((n) => n && !n.startsWith('.')).map((n) => ({ name: n }))
        } catch (e) {}
        return { ok: true, stats, existingSkills, highValueMemories: highValue }
      },
    },
  ]

  const harness = ctx.get('harness') || globalThis.harness
  const dynamic = !!(harness && typeof harness.registerTool === 'function')
  const tools = ctx.get('tools')
  const registered = []
  for (const def of toolDefs) {
    const tool = { name: def.name, description: def.description, parameters: def.parameters, output: def.output, timeoutMs: def.timeoutMs, execute: def.execute }
    try {
      if (dynamic) { const d = harness.registerTool(ctx, tool); if (typeof d === 'function') ctx.effect(() => d); registered.push(def.name); continue }
    } catch (e) {}
    try { if (tools) ctx.effect(() => tools.register(tool)); registered.push(def.name) } catch (e) {}
  }

  let last = 0
  ctx.on('agent/turn-stopping', () => {
    const now = Date.now()
    if (now - last < 30 * 60 * 1000) return
    last = now
    console.log('[evolution-engine] turn 结束，可调 evolution_review 复盘')
  })

  console.log('[evolution-engine] 工具已注册: ' + registered.join(', '))
}
