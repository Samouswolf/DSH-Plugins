#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
dna_bridge.py — DNA 记忆系统的 JSON-RPC 桥接入口

给 DSH（Node 运行时）提供调用本地零模型依赖的 DNA "联想大脑"(Brain) 的
轻量接口。DSH 的 Host 工具通过 subprocess 调用本脚本，用命令行参数传命令，
用 stdout 输出一个 JSON 结果行，读写 DNA_MEMORY_DIR 下的记忆库。用命令行参数传命令，

用法:
    python bridge.py recall <query> [--top K]
    python bridge.py add <text> [--energy 0.5] [--pinned] [--source manual]
    python bridge.py stats

所有输出为一行 UTF-8 JSON: {"ok": true, ...} 或 {"ok": false, "error": "..."}
"""
import sys
import io
import os
import json
import argparse

# 强制 UTF-8 输出（Windows 控制台 GBK 会让中文变成乱码、且 JSON 解析失败）
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', newline='\n')
except Exception:
    pass

# 把 dna_system 代码根纳入 path（代码复制到工作区后设 DNA_CODE_ROOT）
_DNA_CODE_ROOT = os.environ.get('DNA_CODE_ROOT', os.path.abspath(os.path.dirname(__file__)))
if _DNA_CODE_ROOT not in sys.path:
    sys.path.insert(0, _DNA_CODE_ROOT)

# 记忆库位置：默认用户目录下的 .dna（可读写无锁）。主库被占用时可
# 设 DNA_MEMORY_DIR 指向另一个记忆库目录。
_def_mem = (os.environ.get('USERPROFILE') or os.environ.get('HOME') or '') + '/.dna'
_DNA_MEMORY_DIR = os.environ.get('DNA_MEMORY_DIR', _def_mem)


def _emit(payload):
    """输出一行 JSON 后退出。"""
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def _load_brain():
    from dna_system.core.brain import Brain
    b = Brain(memory_dir=_DNA_MEMORY_DIR)
    b.load()
    return b


def cmd_recall(args):
    if not args.query:
        _emit({'ok': False, 'error': 'recall 需要 query 参数'})
        return
    brain = _load_brain()
    results = brain.recall(args.query, top_k=args.top)
    # 只保留 JSON 安全的标量字段；避免把 DNA 里的非标量对象直接 dump
    clean = []
    for r in results:
        clean.append({
            'id': r.get('id'),
            'text': r.get('text'),
            'energy': r.get('energy'),
            'pinned': r.get('pinned'),
            'layer': r.get('layer'),
            'score': r.get('_score'),
            'from_wormhole': bool(r.get('_from_wormhole')),
        })
    _emit({'ok': True, 'count': len(clean), 'results': clean})


def cmd_add(args):
    # `add <文本>` 的文本落在第一个位置参数 args.query 上
    text = args.query or args.text
    if not text:
        _emit({'ok': False, 'error': 'add 需要 text 参数'})
        return
    brain = _load_brain()
    # 生成唯一 eid（重复 eid 会覆盖旧记忆；用时间戳+随机数保证不冲突）
    import time, random
    eid = f"dsh_{int(time.time())}_{random.randint(1000, 9999)}"
    entity = brain.add(eid=eid, text=text, energy=args.energy, pinned=args.pinned, source=args.source)
    brain.save()
    _emit({'ok': True, 'id': entity.id, 'text': entity.text, 'energy': entity.energy, 'pinned': entity.pinned})


def cmd_stats(_args):
    brain = _load_brain()
    _emit({'ok': True, **brain.stats(), 'memory_dir': _DNA_MEMORY_DIR})


def cmd_identity(_args):
    """返回保护层（pinned）的记忆——即稳定的身份/铁律块。

    与 recall 的磁吸打分不同，这里【确定性】返回 pinned 身份记忆，不掺入
    会话噪音/自动沉淀碎片，适合作为会话启动时注入系统提示词的稳定身份上下文。
    """
    brain = _load_brain()
    entities = brain.pool.get_by_layer('protect')
    clean = []
    for ent in entities:
        d = ent.to_dict()
        clean.append({
            'id': d.get('id'),
            'text': d.get('text'),
            'energy': d.get('energy'),
            'pinned': d.get('pinned', True),
            'layer': 'protect',
        })
    # 能量降序，身份/铁律优先在前
    clean.sort(key=lambda x: -(x.get('energy') or 0))
    _emit({'ok': True, 'count': len(clean), 'results': clean})


def main():
    parser = argparse.ArgumentParser(prog='dna_bridge', add_help=False)
    parser.add_argument('command', nargs='?', default='stats')
    parser.add_argument('query', nargs='?')
    parser.add_argument('text', nargs='?')
    parser.add_argument('--top', type=int, default=5)
    parser.add_argument('--energy', type=float, default=0.5)
    parser.add_argument('--pinned', action='store_true')
    parser.add_argument('--source', default='dsh')
    args = parser.parse_args()

    table = {
        'recall': cmd_recall,
        'add': cmd_add,
        'stats': cmd_stats,
        'identity': cmd_identity,
    }
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
