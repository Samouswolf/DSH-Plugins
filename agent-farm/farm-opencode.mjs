#!/usr/bin/env node
// ============================================================
// farm-opencode.mjs — Opencode 中转 API 桥接（对话）
// 供 DSH 的 Agent Farm 面板的 Claude Code / Codex 卡片使用：
// 用 opencode.ai 的 OpenAI 兼容端点调用模型。
//
// 用法：
//   node farm-opencode.mjs chat "<prompt>" [--model M]
//
// 凭据（按优先级）：
//   1. 环境变量 OPENCODE_BASE_URL / OPENCODE_API_KEY
//   2. 环境变量 HERMES_CONFIG 指向的 config.yaml 的 custom_providers
//   3. 默认端点 + 环境变量 OPENCODE_API_KEY
// ⚠️ 本文件不含任何密钥。key 一律来自环境 / 外部配置文件。
//
// 输出：stdout 一行 JSON { ok, model, text }
// ============================================================
import { readFileSync } from 'node:fs'

const DEFAULT_BASE = 'https://opencode.ai/zen/go/v1'
const DEFAULT_MODEL = 'deepseek-v4-flash'
// 可选：指向含 custom_providers 的 yaml；不设则跳过该来源
const HERMES_CONFIG = process.env.HERMES_CONFIG || ''
// 可选：优先使用这个 provider 名（yaml 内 custom_providers.<name>）
const PROVIDER_NAME = process.env.OPENCODE_PROVIDER || 'default'

function loadCreds() {
  // 1. 环境变量优先
  if (process.env.OPENCODE_BASE_URL && process.env.OPENCODE_API_KEY) {
    return { base: process.env.OPENCODE_BASE_URL.replace(/\/+$/, ''), key: process.env.OPENCODE_API_KEY }
  }
  if (process.env.OPENCODE_API_KEY) return { base: DEFAULT_BASE, key: process.env.OPENCODE_API_KEY }
  // 2. 外部 yaml 提供者
  if (HERMES_CONFIG) {
    try {
      const text = readFileSync(HERMES_CONFIG, 'utf8')
      const lines = text.split(/\r?\n/)
      let inProvider = false
      let base = ''
      let key = ''
      for (const raw of lines) {
        const line = raw.trim()
        if (line.startsWith('- name:')) inProvider = line.includes(PROVIDER_NAME)
        if (!inProvider) continue
        if (line.startsWith('base_url:')) base = line.slice('base_url:'.length).trim().replace(/["']/g, '')
        if (line.startsWith('api_key:')) key = line.slice('api_key:'.length).trim().replace(/["']/g, '')
      }
      if (base && key) return { base: base.replace(/\/+$/, ''), key }
    } catch (e) { /* 回退 */ }
  }
  return { base: DEFAULT_BASE, key: '' }
}

function emit(payload) {
  process.stdout.write(JSON.stringify(payload) + '\n')
}

async function cmdChat(prompt, model) {
  const { base, key } = loadCreds()
  if (!key) return emit({ ok: false, error: '未找到 Opencode API key（请设置 OPENCODE_API_KEY 或 HERMES_CONFIG）' })
  const ctrl = new AbortController()
  const timer = setTimeout(() => ctrl.abort(), 180000)
  try {
    const res = await fetch(base + '/chat/completions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + key },
      body: JSON.stringify({
        model: model || DEFAULT_MODEL,
        messages: [{ role: 'user', content: prompt }],
        max_tokens: 4096,
      }),
      signal: ctrl.signal,
    })
    const text = await res.text()
    if (!res.ok) {
      let msg = text.slice(0, 300)
      try { msg = (JSON.parse(text).error && JSON.parse(text).error.message) || msg } catch {}
      return emit({ ok: false, error: 'HTTP ' + res.status + ': ' + msg })
    }
    const data = JSON.parse(text)
    const choice = data.choices && data.choices[0]
    const content = choice && choice.message && choice.message.content
    return emit({ ok: true, model: data.model || model || DEFAULT_MODEL, text: String(content || '').slice(0, 8000) })
  } catch (e) {
    return emit({ ok: false, error: String(e && e.message ? e.message : e) })
  } finally {
    clearTimeout(timer)
  }
}

const [cmd, prompt, ...rest] = process.argv.slice(2)
function flag(name, def) {
  const i = rest.indexOf('--' + name)
  return i >= 0 && rest[i + 1] !== undefined ? rest[i + 1] : def
}
const model = flag('model', '')
if (cmd === 'chat') await cmdChat(prompt || '', model)
else emit({ ok: false, error: '未知命令: ' + String(cmd) + '（可选 chat）' })
