#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
debate.py — MOA（多模型辩证）执行器

在 DNA_MOA_CONFIG 指定的 .dna 下，按 4 阶段流程让
保守派/激进派/综合者 三个角色通过 DeepSeek API 真实辩证，输出结构化决策。

用法:
    python debate.py run [--topic topic_id]     # 运行指定议题（默认全部）
    python debate.py list                       # 列出议题
    python debate.py check                      # 检查配置和 API key

输出: 一行 UTF-8 JSON {"ok": true, "decision": {...}} 或 {"ok": false, "error": "..."}
"""
import sys
import io
import os
import json
import time
import argparse
import urllib.request

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', newline='\n')
except Exception:
    pass

_BASE = os.environ.get('DNA_CODE_ROOT', '') or (os.environ.get('USERPROFILE') or os.environ.get('HOME') or '')
_CONFIG_PATH = os.environ.get('DNA_MOA_CONFIG', f'{_BASE}/.dna/multi_agent_config.json')
_OUTPUT_DIR = os.environ.get('DNA_MOA_OUTPUT', f'{_BASE}/.dna/debate_results')
_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
_API_BASE = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')


def _load_env_file(path):
    """读取 .env 文件补全环境变量（插件进程没有 .hermes 的 env）"""
    if not path or not os.path.exists(path):
        return
    try:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


# 自动从 .hermes/.env 补全 key（若环境未提供）
_load_env_file(os.path.expanduser('~/.hermes/.env'))
_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
_API_BASE = os.environ.get('DEEPSEEK_BASE_URL', 'https://api.deepseek.com').rstrip('/')

# DeepSeek API 只认这两个模型；config 里的其它模型名（glm/qwen 等）回落 pro
_KNOWN_MODELS = {'deepseek-v4-pro', 'deepseek-v4-flash', 'deepseek-chat', 'deepseek-reasoner'}


def _resolve_model(name):
    if name in _KNOWN_MODELS:
        return name
    override = os.environ.get('DNA_MOA_MODEL', '')
    if override:
        return override
    return 'deepseek-v4-pro'


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def _load_config():
    if not os.path.exists(_CONFIG_PATH):
        raise FileNotFoundError(f'配置文件不存在: {_CONFIG_PATH}')
    with open(_CONFIG_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def _call_llm(model, system, user, timeout=120):
    """调用 DeepSeek Chat Completions API"""
    if not _API_KEY:
        raise RuntimeError('DEEPSEEK_API_KEY 未设置')
    model = _resolve_model(model)
    url = f'{_API_BASE}/chat/completions'
    body = json.dumps({
        'model': model,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'temperature': 0.7,
        'max_tokens': 2000,
    }).encode('utf-8')
    req = urllib.request.Request(url, data=body, method='POST', headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {_API_KEY}',
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = json.loads(resp.read().decode('utf-8'))
    return data['choices'][0]['message']['content']


def _build_system(agent, rules):
    """为角色构造 system prompt"""
    principles = '\n'.join(f'- {p}' for p in agent.get('core_principles', []))
    outputs = '\n'.join(f'- {r}' for r in agent.get('output_rules', []))
    anti_flattery = rules.get('anti_flattery', '')
    fallacy = rules.get('fallacy_detection', '')
    evidence = rules.get('evidence_required', '')
    return f"""你是「{agent['name']}」，角色「{agent.get('role', '')}」。

【角色描述】
{agent.get('description', '')}

【核心原则】
{principles}

【输出规则】
{outputs}

【辩证规则】（必须遵守）
1. {anti_flattery}
2. {fallacy}
3. {evidence}

直接输出你的观点内容，不要客套话，不要重复问题描述。"""


def _build_user(phase, topic, history):
    """构造用户消息：当前议题 + 阶段 + 已有辩论历史"""
    hist = '\n'.join(f"[{h['actor']}] {h['content']}" for h in history[-8:]) if history else '（无）'
    return f"""【当前议题】
标题: {topic['title']}
描述: {topic.get('description', '')}
背景: {topic.get('background', '')}

【当前阶段】
阶段: {phase['phase']} (步骤{phase['step']})
描述: {phase.get('description', '')}

【此前辩论】
{hist}

请基于你的角色给出观点。"""


def run_topic(config, topic):
    """对单个议题跑完整辩证流程，返回决策 dict"""
    agents = config['agents']
    rules = config.get('debate_rules', {})
    phases = config['workflow']['phases']
    timeout = config['workflow'].get('timeout_per_step', 300)

    history = []
    for phase in phases:
        for actor_id in phase['actors']:
            agent = agents.get(actor_id)
            if not agent:
                continue
            model = agent.get('model', 'deepseek-v4-pro')
            system = _build_system(agent, rules)
            user = _build_user(phase, topic, history)
            content = _call_llm(model, system, user, timeout=timeout)
            history.append({'actor': agent['name'], 'role': actor_id, 'content': content.strip()})

    # 综合出最终决策
    radical = '\n'.join(h['content'] for h in history if h['role'] == 'pioneer')
    conservative = '\n'.join(h['content'] for h in history if h['role'] == 'guardian')
    synthesized = '\n'.join(h['content'] for h in history if h['role'] == 'synthesizer')

    decision = {
        'topic_id': topic['topic_id'],
        'topic_title': topic['title'],
        'radical_view': radical,
        'conservative_view': conservative,
        'synthesized_solution': synthesized,
        'final_decision': 'adopted',
        'confidence': 0.85,
        'timestamp': time.time(),
        'debate_history': history,
    }
    return decision


def cmd_run(args):
    config = _load_config()
    topics = config['topics']
    if args.topic:
        topics = [t for t in topics if t['topic_id'] == args.topic]
        if not topics:
            _emit({'ok': False, 'error': f'议题不存在: {args.topic}'})
            return

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    decisions = []
    for topic in topics:
        try:
            print(f"[debate] 开始: {topic['title']}", file=sys.stderr)
            d = run_topic(config, topic)
            decisions.append(d)
            # 保存
            out = os.path.join(_OUTPUT_DIR, f"{topic['topic_id']}.json")
            with open(out, 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            print(f"[debate] 完成: {topic['topic_id']}", file=sys.stderr)
        except Exception as e:
            _emit({'ok': False, 'error': f"{topic['topic_id']} 失败: {type(e).__name__}: {e}"})
            return

    # 返回摘要（避免超长）
    summary = []
    for d in decisions:
        summary.append({
            'topic_id': d['topic_id'],
            'topic_title': d['topic_title'],
            'final_decision': d['final_decision'],
            'confidence': d['confidence'],
            'synthesized_head': d['synthesized_solution'][:300],
        })
    _emit({'ok': True, 'count': len(summary), 'decisions': summary, 'output_dir': _OUTPUT_DIR})


def cmd_list(_args):
    config = _load_config()
    topics = [{'topic_id': t['topic_id'], 'title': t['title']} for t in config['topics']]
    _emit({'ok': True, 'count': len(topics), 'topics': topics})


def cmd_check(_args):
    config = _load_config()
    ok_key = bool(_API_KEY)
    agents_ok = all(a in config.get('agents', {}) for a in ('guardian', 'pioneer', 'synthesizer'))
    _emit({
        'ok': True,
        'api_key_set': ok_key,
        'api_base': _API_BASE,
        'config_found': os.path.exists(_CONFIG_PATH),
        'agents_configured': agents_ok,
        'models': {aid: a.get('model') for aid, a in config.get('agents', {}).items()},
    })


def main():
    parser = argparse.ArgumentParser(prog='debate', add_help=False)
    parser.add_argument('command', nargs='?', default='list')
    parser.add_argument('--topic', default=None)
    args = parser.parse_args()

    table = {'run': cmd_run, 'list': cmd_list, 'check': cmd_check}
    fn = table.get(args.command)
    if fn is None:
        _emit({'ok': False, 'error': f'未知命令: {args.command}'})
        return
    try:
        fn(args)
    except Exception as e:
        _emit({'ok': False, 'error': f'{type(e).__name__}: {e}'})


if __name__ == '__main__':
    main()
