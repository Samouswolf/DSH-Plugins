#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sync.py — DNA 双库同步

工作副本（DSH 记忆库）↔ 用户主库（Hermes 记忆库），两库路径均可通过环境变量
（DNA_DSH_DIR / DNA_MAIN_DIR / DNA_IMPORT_DIR）配置。

主库 brain_pool.json 可能被 Hermes 进程独占锁定（Windows 文件锁），
所以本工具设计为：
  - pull  : 主库 → 工作副本（读主库，只写副本，安全）
  - push  : 工作副本 → 主库（写主库；若被锁则导出到导入目录待导入）
  - diff  : 对比两库，列出差异

用法:
    python sync.py pull [--dry-run]
    python sync.py push [--dry-run]
    python sync.py diff

输出: 一行 UTF-8 JSON
"""
import sys
import io
import os
import json
import time
import argparse

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', newline='\n')
except Exception:
    pass

_def_home = (os.environ.get('USERPROFILE') or os.environ.get('HOME') or '')
_DSH_DIR = os.environ.get('DNA_DSH_DIR', _def_home + '/.dna')
_MAIN_DIR = os.environ.get('DNA_MAIN_DIR', _def_home + '/.hermes/dna')
_IMPORT_DIR = os.environ.get('DNA_IMPORT_DIR', _def_home + '/dna_import')


def _emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def _load_pool(path):
    """读取 brain_pool.json，返回 (entities_dict, version)"""
    p = os.path.join(path, 'brain_pool.json')
    if not os.path.exists(p):
        return {}, 0
    try:
        with open(p, 'r', encoding='utf-8') as f:
            data = json.load(f)
        ents = data.get('entities', {})
        # entities 可能是 dict 或 list
        if isinstance(ents, dict):
            return ents, data.get('version', 0)
        if isinstance(ents, list):
            return {e.get('id'): e for e in ents if isinstance(e, dict) and e.get('id')}, data.get('version', 0)
        return {}, data.get('version', 0)
    except PermissionError:
        raise RuntimeError(f'无法读取 {p}（可能被其它进程锁定）')
    except Exception:
        return {}, 0


def _save_pool(path, entities, version):
    """写 brain_pool.json（原子写）"""
    p = os.path.join(path, 'brain_pool.json')
    os.makedirs(path, exist_ok=True)
    data = {
        'version': version + 1,
        'pinned': [e['id'] for e in entities.values() if e.get('pinned')],
        'entities': list(entities.values()),
        'saved_at': time.time(),
    }
    tmp = p + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, p)


def cmd_diff(_args):
    dsh_ents, dsh_ver = _load_pool(_DSH_DIR)
    main_ents, main_ver = _load_pool(_MAIN_DIR)
    dsh_ids = set(dsh_ents.keys())
    main_ids = set(main_ents.keys())
    _emit({
        'ok': True,
        'dsh': {'count': len(dsh_ents), 'version': dsh_ver},
        'main': {'count': len(main_ents), 'version': main_ver},
        'only_in_dsh': sorted(dsh_ids - main_ids)[:20],
        'only_in_main': sorted(main_ids - dsh_ids)[:20],
        'dsh_only_count': len(dsh_ids - main_ids),
        'main_only_count': len(main_ids - dsh_ids),
    })


def cmd_pull(args):
    """主库 → DSH 副本（读主库写副本）"""
    dsh_ents, dsh_ver = _load_pool(_DSH_DIR)
    main_ents, _ = _load_pool(_MAIN_DIR)
    added = 0
    for mid, ent in main_ents.items():
        if mid not in dsh_ents:
            dsh_ents[mid] = ent
            added += 1
    if args.dry_run:
        _emit({'ok': True, 'dry_run': True, 'would_add': added})
        return
    _save_pool(_DSH_DIR, dsh_ents, dsh_ver)
    _emit({'ok': True, 'action': 'pull', 'added': added, 'dsh_total': len(dsh_ents)})


def cmd_push(args):
    """DSH 副本 → 主库；主库被锁则导出到导入目录"""
    dsh_ents, _ = _load_pool(_DSH_DIR)
    main_ents, main_ver = _load_pool(_MAIN_DIR)
    new_ents = {k: v for k, v in dsh_ents.items() if k not in main_ents}
    if not new_ents:
        _emit({'ok': True, 'action': 'push', 'added': 0, 'note': '无新记忆'})
        return
    if args.dry_run:
        _emit({'ok': True, 'dry_run': True, 'would_push': len(new_ents)})
        return
    # 尝试直接写主库
    try:
        merged = dict(main_ents)
        merged.update(new_ents)
        _save_pool(_MAIN_DIR, merged, main_ver)
        _emit({'ok': True, 'action': 'push', 'added': len(new_ents), 'target': 'main'})
    except (PermissionError, OSError):
        # 主库被锁 → 导出
        os.makedirs(_IMPORT_DIR, exist_ok=True)
        out = os.path.join(_IMPORT_DIR, f'dsh_export_{int(time.time())}.json')
        with open(out, 'w', encoding='utf-8') as f:
            json.dump({'exported_at': time.time(), 'source': 'DSH', 'entities': list(new_ents.values())},
                      f, ensure_ascii=False, indent=2)
        _emit({'ok': True, 'action': 'push', 'added': len(new_ents),
               'target': 'export', 'export_path': out,
               'note': '主库被锁定，已导出到导入目录，待 Hermes 空闲后手动导入'})


def main():
    parser = argparse.ArgumentParser(prog='sync', add_help=False)
    parser.add_argument('command', nargs='?', default='diff')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    table = {'diff': cmd_diff, 'pull': cmd_pull, 'push': cmd_push}
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
