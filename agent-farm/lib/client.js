window.__ModuleLoader__.load({
	id: "dsh-agent-farm",
	factory: (require) => {
		var module = { exports: {} };
		var exports = module.exports;
		Object.defineProperty(exports, Symbol.toStringTag, { value: "Module" });
		let React = require("react");

		// ── Agent Farm 固化客户端：设置面板 + 聊天群 + AI Role 校色面板 ──
		// 数据通道：fetch('/api/farm/*')（Host 半 index.mjs 注册的 HTTP API）

		const API_BASE = "/api/farm";

		// BUG 修复 (2026-08-16)：原实现把参数名误作 HTTP method（method:"status"），
		// 导致所有请求以非法方法发出 → 后端统一 400/501 → 农场"全部失联 HTTP 400"。
		// host 端 farm 端点全部按 POST 解析，这里固定用 POST，参数名作路径段。
		function api(name, body) {
			const opts = { method: "POST", headers: { "content-type": "application/json" } };
			if (body !== undefined && body !== null) opts.body = JSON.stringify(body);
			return fetch(API_BASE + "/" + name, opts).then((r) => {
				if (!r.ok) return r.json().catch(() => ({ ok: false, error: "HTTP " + r.status })).then((j) => Promise.reject(new Error(j.error || "HTTP " + r.status)));
				return r.json();
			});
		}

		const CSS = `
      .afarm-wrap { padding: 4px 2px; }
      .afarm-head { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
      .afarm-title { font-weight: 600; font-size: 14px; }
      .afarm-refresh { cursor: pointer; border: 1px solid var(--color-border, #444); background: transparent; color: inherit; border-radius: 6px; padding: 4px 12px; font-size: 12px; }
      .afarm-refresh:disabled { opacity: .5; cursor: wait; }
      .afarm-note { font-size: 12px; opacity: .75; margin: 0 0 12px; }
      .afarm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; }
      .afarm-card { border: 1px solid var(--color-border, #444); border-radius: 10px; padding: 12px 14px; background: var(--color-surface, rgba(255,255,255,.03)); cursor: pointer; transition: border-color .15s; }
      .afarm-card:hover { border-color: var(--color-accent, #888); }
      .afarm-card-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
      .afarm-id { display: flex; align-items: center; gap: 8px; min-width: 0; }
      .afarm-avatar { width: 32px; height: 32px; border-radius: 8px; object-fit: contain; background: rgba(255,255,255,.06); flex-shrink: 0; }
      .afarm-avatar-fallback { display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 15px; color: #fff; }
      .afarm-name { font-weight: 600; font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .afarm-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }
      .afarm-badge { font-size: 11px; padding: 2px 8px; border-radius: 999px; }
      .afarm-badge.ok { background: rgba(46,160,67,.18); color: #3fb950; }
      .afarm-badge.bad { background: rgba(248,81,73,.18); color: #f85149; }
      .afarm-badge.warn { background: rgba(210,153,34,.18); color: #d29922; }
      .afarm-caret { font-size: 10px; opacity: .6; }
      .afarm-row { font-size: 12px; display: flex; justify-content: space-between; gap: 8px; padding: 3px 0; border-bottom: 1px dashed var(--color-border, rgba(255,255,255,.08)); }
      .afarm-row:last-child { border-bottom: none; }
      .afarm-row .k { opacity: .65; flex-shrink: 0; }
      .afarm-row .v { text-align: right; word-break: break-all; }
      .afarm-models { font-size: 11px; opacity: .75; margin-top: 6px; line-height: 1.5; }
      .afarm-detail { margin-top: 10px; padding-top: 8px; border-top: 1px solid var(--color-border, rgba(255,255,255,.1)); }
      .afarm-path { font-size: 11px; opacity: .8; padding: 3px 0; word-break: break-all; }
      .afarm-path .pk { opacity: .55; margin-right: 6px; }
      .afarm-path .pv { font-family: var(--font-mono, monospace); }
      .afarm-task { margin-top: 12px; padding-top: 10px; border-top: 1px solid var(--color-border, rgba(255,255,255,.1)); }
      .afarm-task-label { font-size: 11px; opacity: .65; margin-bottom: 6px; }
      .afarm-modes { display: flex; gap: 6px; margin-bottom: 6px; }
      .afarm-mode-btn { cursor: pointer; font-size: 11px; padding: 3px 10px; border-radius: 999px; border: 1px solid var(--color-border, #444); background: transparent; color: inherit; opacity: .7; }
      .afarm-mode-btn.on { opacity: 1; border-color: var(--color-accent, #888); background: rgba(255,255,255,.08); }
      .afarm-task-input { width: 100%; box-sizing: border-box; resize: vertical; min-height: 56px; font-size: 12px; font-family: inherit; color: inherit; background: rgba(255,255,255,.04); border: 1px solid var(--color-border, #444); border-radius: 6px; padding: 6px 8px; outline: none; }
      .afarm-task-input:focus { border-color: var(--color-accent, #888); }
      .afarm-task-bar { display: flex; align-items: center; gap: 6px; margin-top: 6px; }
      .afarm-task-model { flex: 1; min-width: 0; font-size: 11px; color: inherit; background: rgba(255,255,255,.04); border: 1px solid var(--color-border, #444); border-radius: 6px; padding: 4px 8px; outline: none; }
      .afarm-task-size { flex-shrink: 0; font-size: 11px; color: inherit; background: rgba(255,255,255,.04); border: 1px solid var(--color-border, #444); border-radius: 6px; padding: 4px 8px; outline: none; }
      .afarm-task-run { cursor: pointer; border: 1px solid var(--color-border, #444); background: transparent; color: inherit; border-radius: 6px; padding: 4px 12px; font-size: 12px; flex-shrink: 0; }
      .afarm-task-run:disabled { opacity: .5; cursor: not-allowed; }
      .afarm-task-run:not(:disabled):hover { border-color: var(--color-accent, #888); }
      .afarm-task-result { margin-top: 8px; border: 1px solid var(--color-border, #444); border-radius: 6px; padding: 6px 8px; font-size: 11px; max-height: 300px; overflow: auto; }
      .afarm-task-result.ok { border-color: rgba(46,160,67,.4); }
      .afarm-task-result.err { border-color: rgba(248,81,73,.4); }
      .afarm-task-result-head { opacity: .7; margin-bottom: 4px; }
      .afarm-task-result-body { margin: 0; white-space: pre-wrap; word-break: break-word; font-family: var(--font-mono, monospace); opacity: .9; }
      .afarm-task-img { max-width: 100%; max-height: 240px; border-radius: 6px; margin-top: 6px; display: block; }
      .afarm-task-link { display: inline-block; margin-top: 6px; font-size: 11px; color: var(--color-accent, #6cf); }
      .afarm-top-btn { cursor: pointer; border: 1px solid var(--color-border, #444); background: rgba(74,108,247,.16); color: inherit; border-radius: 8px; padding: 4px 10px; font-size: 12px; white-space: nowrap; }
      .afarm-top-btn:hover { background: rgba(74,108,247,.3); }
      .afarm-vision-btn { cursor: pointer; border: 1px solid var(--color-border, #444); background: rgba(63,185,80,.14); color: inherit; border-radius: 8px; padding: 4px 10px; font-size: 12px; white-space: nowrap; }
      .afarm-vision-btn:hover { background: rgba(63,185,80,.28); }
      .afarm-role-btn { cursor: pointer; border: 1px solid var(--color-border, #444); background: rgba(210,153,34,.14); color: inherit; border-radius: 8px; padding: 4px 10px; font-size: 12px; white-space: nowrap; }
      .afarm-role-btn:hover { background: rgba(210,153,34,.28); }
      .afarm-open-btn { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; border: none; background: transparent; color: inherit; font-size: 12px; padding: 8px 12px; border-radius: 8px; }
      .afarm-open-btn:hover { background: rgba(255,255,255,.06); }
      .afarm-open-icon { font-size: 16px; }
      .afarm-open-label { opacity: .85; }
      .afarm-chat-mask { position: fixed; inset: 0; z-index: 2147483000; background: rgba(0,0,0,.6); display: flex; align-items: center; justify-content: center; pointer-events: auto; }
      .afarm-chat-panel { width: min(960px, 94vw); height: min(720px, 90vh); background: #1b1e26; color: #e8e8e8; border: 1px solid #3a3f4b; border-radius: 14px; display: flex; overflow: hidden; box-shadow: 0 12px 48px rgba(0,0,0,.5); }
      .afarm-chat-side { width: 220px; border-right: 1px solid #3a3f4b; display: flex; flex-direction: column; background: #20242e; }
      .afarm-chat-side-head { padding: 14px 14px 8px; font-weight: 600; font-size: 13px; color: #e8e8e8; display: flex; justify-content: space-between; align-items: center; }
      .afarm-chat-close { cursor: pointer; border: none; background: transparent; color: #c8c8c8; font-size: 14px; }
      .afarm-chat-close:hover { color: #fff; }
      .afarm-chat-agents { flex: 1; overflow-y: auto; padding: 4px; }
      .afarm-chat-agent { display: flex; align-items: center; gap: 8px; width: 100%; cursor: pointer; border: none; background: transparent; color: #d8d8d8; padding: 8px 10px; border-radius: 8px; font-size: 12px; text-align: left; }
      .afarm-chat-agent:hover { background: rgba(255,255,255,.07); }
      .afarm-chat-agent.on { background: rgba(74,108,247,.22); color: #fff; }
      .afarm-chat-agent .afarm-avatar { width: 26px; height: 26px; border-radius: 7px; }
      .afarm-chat-agent .afarm-avatar-fallback { font-size: 12px; }
      .afarm-chat-agent-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
      .afarm-chat-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
      .afarm-chat-dot.ok { background: #3fb950; }
      .afarm-chat-dot.bad { background: #f85149; }
      .afarm-chat-dot.warn { background: #d29922; }
      .afarm-chat-main { flex: 1; display: flex; flex-direction: column; min-width: 0; background: #1b1e26; }
      .afarm-chat-head { padding: 12px 16px; border-bottom: 1px solid #3a3f4b; font-size: 13px; font-weight: 600; color: #e8e8e8; display: flex; align-items: center; gap: 8px; }
      .afarm-chat-head .afarm-avatar { width: 22px; height: 22px; border-radius: 6px; }
      .afarm-chat-msgs { flex: 1; overflow-y: auto; padding: 14px 16px; display: flex; flex-direction: column; gap: 10px; }
      .afarm-msg { display: flex; gap: 8px; max-width: 82%; }
      .afarm-msg.user { align-self: flex-end; flex-direction: row-reverse; }
      .afarm-msg-bubble { padding: 8px 12px; border-radius: 12px; font-size: 12.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; color: #e8e8e8; background: rgba(255,255,255,.08); }
      .afarm-msg.user .afarm-msg-bubble { background: rgba(74,108,247,.35); }
      .afarm-msg.err .afarm-msg-bubble { background: rgba(248,81,73,.18); color: #ff9d97; }
      .afarm-msg .afarm-avatar { width: 22px; height: 22px; border-radius: 6px; flex-shrink: 0; }
      .afarm-msg .afarm-avatar-fallback { font-size: 11px; }
      .afarm-msg-img { max-width: 100%; max-height: 280px; border-radius: 8px; margin-top: 6px; display: block; }
      .afarm-msg-meta { font-size: 10px; color: #8a8f9a; margin-top: 4px; }
      .afarm-chat-inputbar { padding: 10px 14px; border-top: 1px solid #3a3f4b; display: flex; gap: 8px; align-items: flex-end; }
      .afarm-chat-input { flex: 1; resize: none; min-height: 38px; max-height: 120px; font-size: 12.5px; font-family: inherit; color: #e8e8e8; background: #242833; border: 1px solid #3a3f4b; border-radius: 10px; padding: 8px 10px; outline: none; }
      .afarm-chat-input:focus { border-color: #5b6bff; }
      .afarm-chat-input::placeholder { color: #7a8090; }
      .afarm-chat-send { cursor: pointer; border: 1px solid #3a3f4b; background: rgba(74,108,247,.25); color: #e8e8e8; border-radius: 10px; padding: 8px 16px; font-size: 12.5px; flex-shrink: 0; }
      .afarm-chat-send:disabled { opacity: .5; cursor: not-allowed; }
      .afarm-chat-send:not(:disabled):hover { background: rgba(74,108,247,.4); }
      .afarm-chat-typing { font-size: 11px; color: #9aa0ad; padding: 0 16px 6px; }
      .afarm-chat-empty { flex: 1; display: flex; align-items: center; justify-content: center; font-size: 12.5px; color: #7a8090; }
      .afarm-role-panel { position: absolute; top: 56px; right: 14px; z-index: 100; width: 300px; background: #20242e; border: 1px solid #3a3f4b; border-radius: 12px; padding: 14px; box-shadow: 0 8px 32px rgba(0,0,0,.5); }
      .afarm-role-title { font-size: 13px; font-weight: 600; color: #e8e8e8; margin-bottom: 10px; }
      .afarm-role-item { display: flex; align-items: center; justify-content: space-between; gap: 8px; width: 100%; cursor: pointer; border: 1px solid #3a3f4b; background: transparent; color: #d8d8d8; border-radius: 8px; padding: 7px 10px; font-size: 12px; margin-bottom: 6px; text-align: left; }
      .afarm-role-item:hover { background: rgba(255,255,255,.06); }
      .afarm-role-item.on { border-color: #5b6bff; background: rgba(74,108,247,.2); color: #fff; }
      .afarm-role-tag { font-size: 10px; padding: 1px 7px; border-radius: 999px; background: rgba(255,255,255,.08); color: #9aa0ad; flex-shrink: 0; }
      .afarm-role-cur { font-size: 11px; color: #9aa0ad; margin-top: 8px; }
    `;

		// ── 聊天群开关 ──
		let chatOpen = false;
		const chatSubs = new Set();
		function setChatOpen(v) { chatOpen = !!v; for (const f of chatSubs) f(chatOpen); }
		function openChat() { setChatOpen(true); }

		const MODE_LABELS = { chat: "💬 对话", image: "🖼 生图", video: "🎬 生视频" };
		const GEN_AGENTS = { agnes: true, workbuddy: true, hermes: true };

		function ChatAvatar(props) {
			const a = props && props.agent;
			if (!a) return null;
			if (a.icon) return React.createElement("img", { className: "afarm-avatar", src: a.icon, alt: a.label, onError: (e) => { e.target.style.display = "none"; } });
			const letter = (a.label || "?").trim().charAt(0).toUpperCase();
			const from = a.accent || "#4a6cf7";
			const to = a.accent2 || "#7c3aed";
			return React.createElement("div", { className: "afarm-avatar afarm-avatar-fallback", style: { background: "linear-gradient(135deg, " + from + ", " + to + ")" } }, letter);
		}

		function RolePanel(props) {
			const [cur, setCur] = React.useState(null);
			const [busy, setBusy] = React.useState("");
			const [models, setModels] = React.useState([]);
			React.useEffect(() => {
				api("current-model").then((r) => { if (r && r.ok) setCur({ provider: r.provider, model: r.model }); }).catch(() => {});
				api("model-list").then((r) => { if (r && r.ok && Array.isArray(r.models)) setModels(r.models); }).catch(() => {});
			}, []);
			const pick = (m) => {
				setBusy(m.label);
				api("set-model", { provider: m.provider, model: m.model })
					.then((r) => { if (r && r.ok) setCur({ provider: m.provider, model: m.model }); setBusy(""); })
					.catch(() => setBusy(""));
			};
			const isCur = (m) => cur && cur.provider === m.provider && cur.model === m.model;
			const list = models.length ? models : [
				{ provider: "dashscope", model: "qwen-vl-max", label: "👁 眼睛 · Qwen VL Max", tag: "视觉 · 131K" },
				{ provider: "zhipu", model: "glm-4v-flash", label: "👁 眼睛 · GLM-4V Flash", tag: "免费视觉" },
				{ provider: "opencode-go", model: "deepseek-v4-flash", label: "⚡ 手 · DeepSeek V4 Flash", tag: "快速免费" },
				{ provider: "opencode-go", model: "deepseek-v4-pro", label: "🧠 大脑 · DeepSeek V4 Pro", tag: "强推理" },
			];
			return React.createElement("div", { className: "afarm-role-panel", onClick: (e) => e.stopPropagation() },
				React.createElement("div", { className: "afarm-role-title" }, "🎨 AI Role 校色面板（模型选择）"),
				list.map((m) => React.createElement("button", {
					key: m.provider + "/" + m.model,
					className: "afarm-role-item" + (isCur(m) ? " on" : ""),
					onClick: () => pick(m),
				},
					React.createElement("span", null, m.label),
					React.createElement("span", { className: "afarm-role-tag" }, m.tag),
				)),
				React.createElement("div", { className: "afarm-role-cur" },
					busy ? "切换中：" + busy : "当前：" + (cur ? cur.provider + " / " + cur.model : "未知（未连接）"),
				),
			);
		}

		function ChatPanel() {
			const [open, setOpen] = React.useState(chatOpen);
			const [agents, setAgents] = React.useState(null);
			const [loadErr, setLoadErr] = React.useState(null);
			const [active, setActive] = React.useState(null);
			const [sessions, setSessions] = React.useState({});
			const [sending, setSending] = React.useState(null);
			const [input, setInput] = React.useState("");
			const [mode, setMode] = React.useState("chat");
			const [size, setSize] = React.useState("square");
			const [roleOpen, setRoleOpen] = React.useState(false);
			// 慢 agent（如 Hermes 十几秒）的等待反馈：记录发送时刻 + 每秒耗时
			const [sendAt, setSendAt] = React.useState(0);
			const [elapsed, setElapsed] = React.useState(0);
			const msgsRef = React.useRef(null);

			React.useEffect(() => { chatSubs.add(setOpen); return () => chatSubs.delete(setOpen); }, []);

			React.useEffect(() => {
				if (!open) return;
				setLoadErr(null);
				api("status", { light: true })
					.then((res) => { setAgents(res && res.agents ? res.agents : null); setActive((cur) => cur || ((res && res.agents) ? Object.keys(res.agents)[0] : null)); })
					.catch((e) => { setAgents(null); setLoadErr(String(e && e.message ? e.message : e)); });
			}, [open]);

			React.useEffect(() => { const el = msgsRef.current; if (el) el.scrollTop = el.scrollHeight; }, [sessions, active, sending]);

			React.useEffect(() => {
				if (typeof window === "undefined") return;
				const onKey = (e) => { if (e && e.key === "Escape") setChatOpen(false); };
				window.addEventListener("keydown", onKey);
				return () => window.removeEventListener("keydown", onKey);
			}, []);

			// 发送中：每秒刷新"已等待时长"，让用户知道慢 agent（Hermes 十几秒）在干活
			const isSendingWait = sending !== null;
			React.useEffect(() => {
				if (!isSendingWait) { setElapsed(0); return; }
				setElapsed(Math.max(0, Math.round((Date.now() - sendAt) / 1000)));
				const t = window.setInterval(() => { setElapsed(Math.max(0, Math.round((Date.now() - sendAt) / 1000))); }, 1000);
				return () => { try { window.clearInterval(t); } catch (e) {} };
			}, [isSendingWait, sendAt]);

			if (!open) return null;

			const agentList = agents ? Object.keys(agents) : [];
			const cur = active && agents ? agents[active] || null : null;
			const canGen = !!active && GEN_AGENTS[active];
			const msgs = (active && sessions[active]) || [];
			const isSending = sending === active;

			const send = () => {
				const t = input.trim();
				if (!active || !t || isSending) return;
				const now = new Date().toLocaleTimeString();
				const payload = { agent: active, task: t, mode: mode };
				if (mode === "image") payload.size = size;
				setSessions((s) => Object.assign({}, s, { [active]: (s[active] || []).concat([{ role: "user", text: t, ts: now, mode: mode }]) }));
				setInput("");
				setSendAt(Date.now());
				setSending(active);
				api("call", payload)
					.then((r) => {
						const reply = r && r.ok
							? { role: "agent", text: r.text || "（空回复）", ts: new Date().toLocaleTimeString(), ok: true, mode: (r.mode || mode), dataUrl: r.dataUrl || "", url: r.url || "", localPath: r.localPath || "" }
							: { role: "agent", text: String((r && (r.error || r.text)) || "调用失败"), ts: new Date().toLocaleTimeString(), ok: false, mode: mode };
						setSessions((s) => Object.assign({}, s, { [active]: (s[active] || []).concat([reply]) }));
					})
					.catch((e) => { setSessions((s) => Object.assign({}, s, { [active]: (s[active] || []).concat([{ role: "agent", text: String(e && e.message ? e.message : e), ts: new Date().toLocaleTimeString(), ok: false, mode: mode }]) })); })
					.then(() => setSending(null));
			};

			return React.createElement("div", { className: "afarm-chat-mask", onClick: () => { setChatOpen(false); setRoleOpen(false); } },
				React.createElement("div", { className: "afarm-chat-panel", onClick: (e) => e.stopPropagation() },
					React.createElement("div", { className: "afarm-chat-side" },
						React.createElement("div", { className: "afarm-chat-side-head" }, "🤖 Agent 农场",
							React.createElement("button", { className: "afarm-chat-close", onClick: () => { setChatOpen(false); setRoleOpen(false); } }, "✕"),
						),
						React.createElement("div", { className: "afarm-chat-agents" },
							loadErr ? React.createElement("div", { className: "afarm-chat-empty", style: { color: "#ff9d97" } }, "加载失败: " + loadErr) : null,
							!agents && !loadErr ? React.createElement("div", { className: "afarm-chat-empty" }, "加载中…") : null,
							agentList.map((key) => {
								const a = agents[key];
								const dotCls = !a.available ? "bad" : (a.headless || a.apiReady ? "ok" : "warn");
								return React.createElement("button", { key: key, className: "afarm-chat-agent" + (active === key ? " on" : ""), onClick: () => setActive(key) },
									React.createElement(ChatAvatar, { agent: a }),
									React.createElement("span", { className: "afarm-chat-agent-name" }, a.label),
									React.createElement("span", { className: "afarm-chat-dot " + dotCls }),
								);
							}),
						),
					),
					React.createElement("div", { className: "afarm-chat-main", style: { position: "relative" } },
						React.createElement("div", { className: "afarm-chat-head" },
							cur ? React.createElement(ChatAvatar, { agent: cur }) : null,
							cur ? cur.label : "选择一个 Agent",
							React.createElement("button", { className: "afarm-role-btn", onClick: () => setRoleOpen((v) => !v) }, "🎨 AI Role"),
						),
						roleOpen ? React.createElement(RolePanel, {}) : null,
						React.createElement("div", { className: "afarm-chat-msgs", ref: msgsRef },
							msgs.length === 0 && !isSending ? React.createElement("div", { className: "afarm-chat-empty" },
								cur ? "开始和 " + cur.label + " 对话吧——发一段自然语言任务书" : "从左侧选择一个 Agent",
							) : null,
							msgs.map((m, i) => React.createElement("div", { key: i, className: "afarm-msg " + m.role + (m.ok === false ? " err" : "") },
								m.role === "agent" && cur ? React.createElement(ChatAvatar, { agent: cur }) : null,
								React.createElement("div", null,
									React.createElement("div", { className: "afarm-msg-bubble" }, m.text),
									m.dataUrl ? React.createElement("img", { className: "afarm-msg-img", src: m.dataUrl }) : null,
									m.url && m.mode === "video" ? React.createElement("a", { className: "afarm-task-link", href: m.url, target: "_blank", rel: "noreferrer" }, "🔗 打开视频链接") : null,
									m.localPath ? React.createElement("div", { className: "afarm-msg-meta" }, "📁 " + m.localPath) : null,
									m.ts ? React.createElement("div", { className: "afarm-msg-meta" }, m.ts) : null,
								),
							)),
							isSending ? React.createElement("div", { className: "afarm-msg" },
								cur ? React.createElement(ChatAvatar, { agent: cur }) : null,
								React.createElement("div", { className: "afarm-msg-bubble" },
									canGen && mode === "image" ? "🎨 正在生成图片…" : canGen && mode === "video" ? "🎬 正在生成视频（可数分钟）…" : "正在思考…",
									React.createElement("span", { style: { marginLeft: 6, opacity: .6, fontWeight: 400 } }, "（已 " + elapsed + "s）"),
								),
							) : null,
						),
						isSending && cur ? React.createElement("div", { className: "afarm-chat-typing" },
							"✍️ " + cur.label + " 正在工作… 已 " + elapsed + "s" + (elapsed >= 8 ? "（" + (cur.label || "").replace(/[（(].*?[）)]/g, "") + " 可能较慢，请稍候）" : ""),
						) : null,
						React.createElement("div", { className: "afarm-chat-inputbar" },
							React.createElement("div", { style: { display: "flex", flexDirection: "column", gap: 6, flex: 1, minWidth: 0 } },
								canGen ? React.createElement("div", { className: "afarm-modes", style: { marginBottom: 0 } },
									Object.keys(MODE_LABELS).map((md) => React.createElement("button", { key: md, className: "afarm-mode-btn" + (mode === md ? " on" : ""), onClick: () => setMode(md) }, MODE_LABELS[md])),
								) : null,
								React.createElement("div", { style: { display: "flex", gap: 8, alignItems: "flex-end" } },
									React.createElement("textarea", {
										className: "afarm-chat-input",
										placeholder: cur ? (canGen && mode === "image" ? "描述你想生成的图片…（如：赛博朋克城市夜景）" : canGen && mode === "video" ? "描述你想生成的视频…" : "给 " + cur.label + " 发任务（Enter 发送）") : "先选一个 Agent",
										value: input, disabled: !cur || isSending,
										onChange: (e) => setInput(e.target.value),
										onKeyDown: (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } },
									}),
									canGen && mode === "image" ? React.createElement("select", { className: "afarm-task-size", value: size, onChange: (e) => setSize(e.target.value) },
										React.createElement("option", { value: "square" }, "方图"), React.createElement("option", { value: "landscape" }, "横图"), React.createElement("option", { value: "portrait" }, "竖图"),
									) : null,
									React.createElement("button", { className: "afarm-chat-send", disabled: !cur || !input.trim() || isSending, onClick: send }, isSending ? "…" : "发送"),
								),
							),
						),
					),
				),
			);
		}

		function TaskBox(props) {
			const modes = props.modes || ["chat"];
			const [mode, setMode] = React.useState(modes[0]);
			const [text, setText] = React.useState("");
			const [model, setModel] = React.useState("");
			const [size, setSize] = React.useState("square");
			const [busy, setBusy] = React.useState(false);
			const [result, setResult] = React.useState(null);
			const run = () => {
				if (!text.trim() || busy) return;
				setBusy(true); setResult(null);
				const payload = { agent: props.agentKey, task: text, mode: mode };
				const m = model.trim();
				if (m) payload.model = m;
				if (mode === "image") payload.size = size;
				api("call", payload).then((r) => setResult(r)).catch((e) => setResult({ ok: false, error: String(e && e.message ? e.message : e) })).then(() => setBusy(false));
			};
			const resultBody = () => {
				if (!result) return null;
				const children = [];
				if (result.mode === "image") { const src = result.dataUrl || result.url; if (src) children.push(React.createElement("img", { key: "img", className: "afarm-task-img", src: src })); }
				if (result.url && result.mode === "video") children.push(React.createElement("a", { key: "a", className: "afarm-task-link", href: result.url, target: "_blank", rel: "noreferrer" }, "🔗 打开视频链接"));
				const bodyText = String(result.text || result.error || "");
				if (bodyText) children.push(React.createElement("pre", { key: "t", className: "afarm-task-result-body" }, bodyText.slice(0, 6000)));
				if (result.localPath) children.push(React.createElement("div", { key: "p", className: "afarm-task-result-body" }, "📁 " + result.localPath));
				return children;
			};
			return React.createElement("div", { className: "afarm-task", onClick: (e) => e.stopPropagation() },
				React.createElement("div", { className: "afarm-task-label" }, "📤 给 " + props.agentLabel + " 派任务（自然语言）"),
				modes.length > 1 ? React.createElement("div", { className: "afarm-modes" }, modes.map((md) => React.createElement("button", { key: md, className: "afarm-mode-btn" + (mode === md ? " on" : ""), onClick: () => setMode(md) }, MODE_LABELS[md] || md))) : null,
				React.createElement("textarea", { className: "afarm-task-input", placeholder: mode === "image" ? "描述你想生成的图片…（如：赛博朋克城市夜景，霓虹灯）" : mode === "video" ? "描述你想生成的视频…" : "例：帮我扫描项目目录下最近修改的 3 个文件并总结改动", value: text, onChange: (e) => setText(e.target.value) }),
				React.createElement("div", { className: "afarm-task-bar" },
					React.createElement("input", { className: "afarm-task-model", placeholder: props.modelHint ? "模型（默认 " + props.modelHint + "）" : "模型（可选）", value: model, onChange: (e) => setModel(e.target.value) }),
					mode === "image" ? React.createElement("select", { className: "afarm-task-size", value: size, onChange: (e) => setSize(e.target.value) }, React.createElement("option", { value: "square" }, "方图"), React.createElement("option", { value: "landscape" }, "横图"), React.createElement("option", { value: "portrait" }, "竖图")) : null,
					React.createElement("button", { className: "afarm-task-run", disabled: busy || !text.trim(), onClick: run }, busy ? (mode === "video" ? "生成中(可数分钟)…" : "执行中…") : "▶ 派活"),
				),
				result ? React.createElement("div", { className: "afarm-task-result " + (result.ok ? "ok" : "err") },
					React.createElement("div", { className: "afarm-task-result-head" }, (result.ok ? "✅ 完成" : "❌ 失败") + (result.agent ? " · " + result.agent : "") + (result.model ? " · " + result.model : "")),
					resultBody(),
				) : null,
			);
		}

		function FarmPanel() {
			const [data, setData] = React.useState(null);
			const [loading, setLoading] = React.useState(false);
			const [error, setError] = React.useState(null);
			const [expanded, setExpanded] = React.useState(null);
			const [fails, setFails] = React.useState({});
			const load = () => { setLoading(true); setError(null); api("status", {}).then((res) => setData(res)).catch((e) => setError(String(e && e.message ? e.message : e))).then(() => setLoading(false)); };
			React.useEffect(() => { load(); }, []);
			const badgeCls = (a) => { if (!a.available) return "bad"; return a.headless || a.apiReady ? "ok" : "warn"; };
			const badgeText = (a) => { if (!a.available) return "不可用"; return a.headless || a.apiReady ? "可用" : "仅探测"; };
			const modesFor = (key) => { if (key === "agnes" || key === "workbuddy" || key === "hermes") return ["chat", "image", "video"]; return ["chat"]; };
			const modelHintFor = (key) => { if (key === "workbuddy") return "hy3"; if (key === "hermes") return "deepseek-v4-flash"; if (key === "agnes") return "agnes-2.0-flash"; if (key === "claude" || key === "codex") return "deepseek-v4-flash"; return ""; };
			const rowsFor = (key, a) => {
				if (key === "workbuddy") { const models = Array.isArray(a.models) && a.models.length ? a.models.slice(0, 20).join(", ") : ""; return [["CLI 可执行", a.cliExists ? "✅ 存在" : "❌ 缺失"], ["models.json", a.modelsJsonExists ? "✅ 存在" : "❌ 缺失"], ["可用模型", models || "—"]]; }
				if (key === "hermes") { const cred = a.credentialOk === null ? "未知" : (a.credentialOk ? "✅ 就绪" : "❌ 未就绪"); const keys = [a.hasDeepseek ? "deepseek" : "", a.hasOpenai ? "openai" : ""].filter(Boolean).join(" + ") || "—"; return [["凭证", cred], ["默认模型", a.model || "—"], ["Provider", a.provider || "—"], ["密钥", keys]]; }
				if (key === "claude") return [["模型", "Opencode 免费 · " + (a.defaultModel || "deepseek-v4-flash")], ["settings.json", a.settingsExists ? "✅ 存在" : "❌ 缺失"], ["数据目录", a.dirExists ? "✅ ~/.claude" : "❌ 缺失"], ["费用", "免费中转，零官方消耗"]];
				if (key === "codex") return [["模型", "Opencode 免费 · " + (a.defaultModel || "deepseek-v4-flash")], ["认证", a.authOk ? "✅ OPENAI_API_KEY" : "❌ 未配置"], ["config.toml", a.configExists ? "✅ 存在" : "❌ 缺失"], ["费用", "免费中转，零官方消耗"]];
				if (key === "agnes") return [["云 API", a.apiUrl || "—"], ["凭据", a.apiReady ? "✅ 有效（Hermes 通道）" : "❌ 缺失"], ["对话", "agnes-2.0-flash"], ["生图", "agnes-image-2.0 / 2.1-flash"], ["生视频", "agnes-video-v2.0（当前被服务端屏蔽 403）"]];
				return [["trae-cn.cmd", a.cmdExists ? "✅" : "❌"], ["cli.js", a.cliJsExists ? "✅" : "❌"], ["主程序 exe", a.exeExists ? "✅" : "❌"]];
			};
			const avatar = (key, a) => {
				const src = a.icon;
				const label = a.label || "";
				if (!src || fails[key]) {
					const letter = label.trim().charAt(0).toUpperCase() || "?";
					const from = a.accent || "#4a6cf7";
					const to = a.accent2 || "#7c3aed";
					return React.createElement("div", { className: "afarm-avatar afarm-avatar-fallback", style: { background: "linear-gradient(135deg, " + from + ", " + to + ")" } }, letter);
				}
				return React.createElement("img", { className: "afarm-avatar", src: src, alt: label, onError: () => setFails((f) => Object.assign({}, f, { [key]: true })) });
			};
			const detailOf = (key, a) => {
				const blocks = [];
				const extra = a.detailNote || (a.note ? a.note : "");
				if (extra) blocks.push(React.createElement("div", { key: "note", className: "afarm-models" }, extra));
				return blocks;
			};
			return React.createElement("div", { className: "afarm-wrap" },
				React.createElement("div", { className: "afarm-head" },
					React.createElement("span", { className: "afarm-title" }, "本地 Agent 农场"),
					React.createElement("button", { className: "afarm-refresh", disabled: loading, onClick: load }, loading ? "探测中…" : "🔄 刷新"),
				),
				error ? React.createElement("div", { className: "afarm-note", style: { color: "#f85149" } }, "探测失败: " + error) : null,
				data && data.note ? React.createElement("div", { className: "afarm-note" }, data.note) : null,
				loading && !data ? React.createElement("div", { className: "afarm-note" }, "正在探测本地 Agent…") : null,
				data ? React.createElement("div", { className: "afarm-grid" }, Object.keys(data.agents || {}).map((key) => {
					const a = data.agents[key];
					const isOpen = expanded === key;
					return React.createElement("div", { key: key, className: "afarm-card", onClick: () => setExpanded((cur) => (cur === key ? null : key)) },
						React.createElement("div", { className: "afarm-card-head" },
							React.createElement("div", { className: "afarm-id" }, avatar(key, a), React.createElement("span", { className: "afarm-name" }, a.label)),
							React.createElement("div", { className: "afarm-right" }, React.createElement("span", { className: "afarm-badge " + badgeCls(a) }, badgeText(a)), React.createElement("span", { className: "afarm-caret" }, isOpen ? "▾" : "▸")),
						),
						rowsFor(key, a).map((r, i) => React.createElement("div", { key: i, className: "afarm-row" }, React.createElement("span", { className: "k" }, r[0]), React.createElement("span", { className: "v" }, r[1]))),
						isOpen ? React.createElement("div", { className: "afarm-detail" }, detailOf(key, a), (a.headless || a.apiReady) ? React.createElement(TaskBox, { key: "task", agentKey: key, agentLabel: a.label, modelHint: modelHintFor(key), modes: modesFor(key) }) : null) : null,
					);
				})) : null,
			);
		}

		const inject = ["slots"];

		function apply(ctx) {
			// CSS 注入
			if (typeof document !== "undefined" && document.querySelector("style[data-plugin-css=\"afarm\"]") === null) {
				const tag = document.createElement("style");
				tag.dataset.plugin = "dsh-agent-farm";
				tag.dataset.pluginCss = "afarm";
				tag.textContent = CSS;
				document.head.appendChild(tag);
			}

			ctx.slots.inject("conversation.session.header.actions", () => {
				return ctx.slots.register(
					{ name: "conversation.session.header.actions", id: "agent-farm-chat-open", order: 30, label: () => "Agent 农场" },
					() => React.createElement("div", { style: { display: "flex", gap: 6, alignItems: "center" } },
						React.createElement("button", { className: "afarm-top-btn", onClick: openChat, title: "打开 Agent 农场聊天群" }, "🤖 农场"),
						React.createElement("button", { className: "afarm-role-btn", onClick: openChat, title: "AI Role 校色面板（在农场聊天群里）" }, "🎨 AI Role"),
					),
				);
			});

			ctx.slots.inject("sidebar.footer.action", () => {
				return ctx.slots.register(
					{ name: "sidebar.footer.action", id: "agent-farm-open", order: 100, label: () => "Agent 农场" },
					(props) => React.createElement("button", { className: "afarm-open-btn", onClick: openChat, title: "Agent 农场（聊天群）" },
						React.createElement("span", { className: "afarm-open-icon" }, "🤖"),
						props && props.wide ? React.createElement("span", { className: "afarm-open-label" }, "Agent 农场") : null,
					),
				);
			});

			ctx.slots.inject("shell.overlay", () => {
				return ctx.slots.register(
					{ name: "shell.overlay", id: "agent-farm-chat", order: 100, label: () => "Agent 农场聊天群" },
					() => React.createElement(ChatPanel),
				);
			});

			ctx.slots.inject("settings.section", () => {
				return ctx.slots.register(
					{ name: "settings.section", id: "agent-farm", order: 26, label: () => "Agent Farm" },
					() => React.createElement(FarmPanel),
				);
			});
		}

		exports.apply = apply;
		exports.inject = inject;
		return module.exports;
	}
});
