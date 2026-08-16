#!/usr/bin/env node
// ============================================================
// farm-agnes.mjs — Agnes 云 API 桥接（对话 / 生图 / 生视频）
// 供 DSH 的 Agent Farm 面板调用。
//
// 用法：
//   node farm-agnes.mjs status
//   node farm-agnes.mjs chat "<prompt>" [model]
//   node farm-agnes.mjs image "<prompt>" [model] [square|landscape|portrait]
//   node farm-agnes.mjs video "<prompt>" [model]
//
// 凭据：环境变量 AGNES_API_KEY（必需）。
//       可选 AGNES_API_URL 覆盖默认端点。
// 输出：stdout 一行 JSON { ok, ... }
// ⚠️ 本文件不含任何密钥。
// ============================================================
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const BASE = process.env.AGNES_API_URL || 'https://apihub.agnes-ai.com/v1'
const OUT_ROOT = join(dirname(fileURLToPath(import.meta.url)), 'output')

const SIZES = { square: '1024x1024', landscape: '1792x1024', portrait: '1024x1792' }

function loadKey() {
  if (process.env.AGNES_API_KEY) return String(process.env.AGNES_API_KEY).trim()
  // 可选：指向一个含 AGNES_API_KEY= 的 env 文件，方便本地验证
  const envFile = process.env.AGNES_ENV_FILE
  if (envFile) {
    try {
      const text = readFileSync(envFile, 'utf8')
      for (const line of text.split(/\r?\n/)) {
        if (line.startsWith('AGNES_API_KEY=')) {
          return line.slice('AGNES_API_KEY='.length).trim().replace(/^["']|["']$/g, '')
        }
      }
    } catch {}
  }
  return null
}

function emit(payload) {
  process.stdout.write(JSON.stringify(payload) + '\n')
}

async function post(path, body, timeoutMs = 180000) {
  const key = loadKey()
  if (!key) return { ok: false, error: '未找到 AGNES_API_KEY（请设置环境变量 AGNES_API_KEY）' }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(BASE + path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key },
      body: JSON.stringify(body),
      signal: ctrl.signal,
    })
    const text = await res.text()
    if (!res.ok) {
      let msg = text.slice(0, 300)
      try { msg = (JSON.parse(text).error && JSON.parse(text).error.message) || msg } catch {}
      return { ok: false, error: 'HTTP ' + res.status + ': ' + msg }
    }
    let data
    try { data = JSON.parse(text) } catch { data = { raw: text } }
    return { ok: true, data }
  } catch (e) {
    return { ok: false, error: String(e && e.message ? e.message : e) }
  } finally {
    clearTimeout(timer)
  }
}

async function getJson(path, timeoutMs = 180000) {
  const key = loadKey()
  if (!key) return { ok: false, error: '未找到 AGNES_API_KEY（请设置环境变量 AGNES_API_KEY）' }
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(BASE + path, { headers: { Authorization: 'Bearer ' + key }, signal: ctrl.signal })
    const text = await res.text()
    if (!res.ok) return { ok: false, error: 'HTTP ' + res.status + ': ' + text.slice(0, 200) }
    return { ok: true, data: JSON.parse(text) }
  } catch (e) {
    return { ok: false, error: String(e && e.message ? e.message : e) }
  } finally {
    clearTimeout(timer)
  }
}

async function download(url, ext) {
  const res = await fetch(url, { signal: AbortSignal.timeout(120000) })
  if (!res.ok) throw new Error('下载失败 HTTP ' + res.status)
  const buf = Buffer.from(await res.arrayBuffer())
  mkdirSync(OUT_ROOT, { recursive: true })
  const name = 'agnes_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8) + '.' + ext
  const file = join(OUT_ROOT, name)
  writeFileSync(file, buf)
  return { file, buf }
}

// ── 命令实现 ──
async function cmdStatus() {
  const key = loadKey()
  const r = await getJson('/models', 30000)
  return emit({
    ok: r.ok,
    keyExists: !!key,
    apiUrl: BASE,
    models: r.ok && Array.isArray(r.data) ? r.data.map((m) => (m && m.id) || '').filter(Boolean).slice(0, 40) : [],
    note: r.ok ? '凭据有效，云 API 可访问' : (r.error || ''),
  })
}

async function cmdChat(prompt, model) {
  const r = await post('/chat/completions', {
    model: model || 'agnes-2.0-flash',
    messages: [{ role: 'user', content: prompt }],
    max_tokens: 4096,
  })
  if (!r.ok) return emit(r)
  const choice = r.data.choices && r.data.choices[0]
  const msg = choice && choice.message
  let text = (msg && msg.content) || ''
  if (!text && msg && msg.reasoning_content) text = '（推理过程）\n' + msg.reasoning_content
  return emit({ ok: true, model: r.data.model || model || 'agnes-2.0-flash', text: String(text).slice(0, 8000) })
}

async function cmdImage(prompt, model, size) {
  const r = await post('/images/generations', {
    model: model || 'agnes-image-2.1-flash',
    prompt: prompt,
    n: 1,
    size: SIZES[size] || SIZES.square,
  })
  if (!r.ok) return emit(r)
  const first = (r.data.data && r.data.data[0]) || {}
  let url = first.url || ''
  if (!url && first.b64_json) url = 'data:image/png;base64,' + first.b64_json
  if (!url) return emit({ ok: false, error: 'Agnes 未返回图片' })
  let localPath = ''
  let dataUrl = ''
  try {
    const ext = url.startsWith('data:') ? 'png' : (url.split('?')[0].split('.').pop() || 'png')
    const dl = await download(url, ext)
    localPath = dl.file
    dataUrl = 'data:image/' + ext.replace('jpg', 'jpeg') + ';base64,' + dl.buf.toString('base64')
  } catch (e) {
    localPath = '下载失败: ' + String(e && e.message ? e.message : e)
  }
  return emit({ ok: true, model: r.data.model || model || 'agnes-image-2.1-flash', url: url, localPath: localPath, dataUrl: dataUrl })
}

async function cmdVideo(prompt, model) {
  const r = await post('/video/generations', { model: model || 'agnes-video-v2.0', prompt: prompt, n: 1 })
  if (!r.ok) return emit(r)
  const d = r.data
  const taskId = d.task_id || d.id || (d.data && d.data[0] && (d.data[0].task_id || d.data[0].id))
  if (!taskId) {
    const url = d.url || (d.data && d.data[0] && d.data[0].url)
    if (url) {
      let localPath = ''
      try { localPath = await download(url, 'mp4') } catch (e) { localPath = '下载失败: ' + String(e && e.message ? e.message : e) }
      return emit({ ok: true, model: model || 'agnes-video-v2.0', url: url, localPath: localPath })
    }
    return emit({ ok: false, error: 'Agnes 视频响应缺少 task_id: ' + JSON.stringify(d).slice(0, 300) })
  }
  const deadline = Date.now() + 300000
  while (Date.now() < deadline) {
    await new Promise((res) => setTimeout(res, 6000))
    const p = await getJson('/video/generations/' + taskId, 30000)
    if (!p.ok) return emit({ ok: false, error: '轮询失败: ' + p.error })
    const pd = p.data
    const status = String(pd.status || (pd.data && pd.data[0] && pd.data[0].status) || '').toLowerCase()
    const url = pd.url || (pd.data && pd.data[0] && pd.data[0].url)
    if (url) {
      let localPath = ''
      try { localPath = await download(url, 'mp4') } catch (e) { localPath = '下载失败: ' + String(e && e.message ? e.message : e) }
      return emit({ ok: true, model: model || 'agnes-video-v2.0', url: url, localPath: localPath })
    }
    if (status === 'failed' || status === 'error') return emit({ ok: false, error: '视频生成失败: ' + JSON.stringify(pd).slice(0, 300) })
    if (status === 'processing' || status === 'pending' || status === '') continue
  }
  return emit({ ok: false, error: '视频生成超时（>300s）' })
}

// ── main ──
const [cmd, prompt, ...rest] = process.argv.slice(2)
function flag(name, def) {
  const i = rest.indexOf('--' + name)
  return i >= 0 && rest[i + 1] !== undefined ? rest[i + 1] : def
}
const model = flag('model', '')
const size = flag('size', 'square')
if (cmd === 'status') await cmdStatus()
else if (cmd === 'chat') await cmdChat(prompt || '', model)
else if (cmd === 'image') await cmdImage(prompt || '', model, size)
else if (cmd === 'video') await cmdVideo(prompt || '', model)
else emit({ ok: false, error: '未知命令: ' + String(cmd) + '（可选 status/chat/image/video）' })
