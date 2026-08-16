---
name: dsh-plugin-guardrails
description: DSH（DeepSeek Harness）Cordis 插件开发的避坑规范与铁律。涵盖：动态插件 vs 文件插件的生命周期差异、webServer 路由必须 declare inject、llm/stream 的 StreamChunk 驼峰字段解析、动态 Client 半的 timer/作用域陷阱、PromptSection 必须同步返回、模型工具注册面（harness vs ctx.tools）。当开发/修复/固化 DSH 自定义插件、排查插件不生效或重启丢失问题时使用。
version: 1.0.0
---

# DSH 插件开发避坑规范

沉淀自 DNA 记忆库 protect 层的大量踩坑铁律。开发或修复 DSH 自定义插件前先过一遍。

## 何时使用
- 开发/修改/固化 DSH 自定义 Cordis 插件（file:/// 引用的文件插件或动态插件）
- 排查插件"重启就丢""渲染报错""数据请求 404""工具不出现"
- 把动态插件固化为重启常驻的文件插件

## 铁律一：生命周期认知
- **动态插件**（create 后 run）：进程内临时，重启消失，需重装；适合临时实验、本次会话内生效。
- **文件插件**（file:///absolute/index.mjs 挂进 preset agent.cordis.yml）：重启常驻；UI/工具要长期使用必须固化为此形态。
- 固化流程：`<工作区>/<plugin>/index.mjs` 双半包（host+client），preset 里加一行 `file:///` 引用。

## 铁律二：工具注册面（关键）
- **动态插件**要用 `harness.registerTool(ctx, tool)` / `harness.defineTool` 注册模型工具，才能对当前 Agent 可见。
- **文件插件 / preset 挂载**用 `ctx.tools.register(tool)`（作用域是预设层）。
- 两者共用同一套 tool 结构（name/description/parameters/output/timeoutMs/execute）。
- 用 `ctx.tools.register` 在动态插件里注册 → 当前 Agent 看不到该工具（scope 不对），必须在模型工具列表用 `evolution_review` 验证。

## 铁律三：注入声明（declare inject）
- **webServer 路由**：Host 半若用 `ctx.get('webServer')` 且 inject 未声明 webServer，apply 可能早于 webServer 就绪 → 路由未注册 → /api 全部 404。对硬依赖必须 `inject: ['webServer', ...]`（文件插件的 inject 和 apply 用 Cordis 顶层 export）。
- **timer / tools / systemPrompt** 等也一样：用了 `ctx.xxx` 就必须在 inject 声明，否则报 "cannot get property without inject"。

## 铁律四：llm/stream 统计解析
- DSH 的 StreamChunk 是 union 类型。token 统计在专用 chunk：
  `{ type: 'usage', usage: { inputTokens, outputTokens, cacheReadTokens, cacheWriteTokens, reasoningTokens } }`（驼峰命名）。
- 只在 type==='usage' 时读 usage 字段，别在普通文本 chunk 里找 token → 否则统计恒为 0。

## 铁律五：动态 Client 半陷阱
- **禁用浏览器全局 timer**：setInterval/setTimeout 会崩 "setInterval is not available in a dynamic client half"。要用定时轮询，必须在插件对象 `inject: ['timer']` + React 组件内 `React.useEffect(() => ctx.interval(...), [])`。
- **组件作用域**：组件要用的 ctx（如 ctx.interval）必须把组件定义放进 `apply(ctx){}` 内部闭包，不能定义在 apply 外（会 "ctx is not defined"）。

## 铁律六：PromptSection 同步
- `PromptSection.text` 必须**同步**返回 string（契约 `string | (ctx)=>string`），绝不能异步。async 未就绪时返回 ''（rendered），不能返回占位符。

## 检查清单
- [ ] 生命周期：需要重启常驻？→ 用文件插件挂 preset；临时？→ 动态插件
- [ ] 工具：动态插件用 harness 注册；文件插件用 ctx.tools.register
- [ ] 所有用的 ctx.xxx 都已在 inject 声明（尤其 webServer/timer/tools/systemPrompt）
- [ ] llm/stream 只在 usage chunk 读 token
- [ ] Client 动态半用 ctx.interval 而非 setInterval
- [ ] PromptSection 同步返回字符串

## 相关记忆
- 见 `.dna/brain_pool.json` protect 层：webServer 404、StreamChunk 驼峰、动态插件固化、client timer 陷阱等条目。
