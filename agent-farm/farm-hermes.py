#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
farm-hermes.py — Hermes Agent headless 桥接（供 DSH 的 agent-farm 插件调用）

作用：以一次性 headless 方式驱动 Hermes 的 AIAgent 跑一个任务并返回结果。
      DSH 侧（agent-farm/index.mjs）通过 subprocess 调本脚本，脚本把结果
      以一行 UTF-8 JSON 输出到 stdout。

用法:
    python farm-hermes.py status                    # 探测可用性（不跑任务）
    python farm-hermes.py run "<prompt>" [--model M] [--timeout S]

数据源（路径均可通过环境变量覆盖：HERMES_ROOT / HERMES_VENV_PY / HERMES_ENV）：
    - 模型路由/凭证：`$HERMES_ENV` 或 `~/.hermes/.env`（HERMES_MODEL / DEEPSEEK_* 等）
    - hermes-agent 代码根：`$HERMES_ROOT` 或本地安装位置

依赖 hermes-agent 的 venv python。stdout 一行 JSON，含 ok / error / text。
"""
import sys, io, os, json, argparse, time

try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')
except Exception:
    pass

def _home():
    return os.environ.get('USERPROFILE') or os.environ.get('HOME') or ''

def _localappdata():
    return os.environ.get('LOCALAPPDATA') or (_home() + '/AppData/Local')

HERMES_ROOT = os.environ.get('HERMES_ROOT') or (_localappdata() + '/hermes/hermes-agent')
VENV_PY = os.environ.get('HERMES_VENV_PY') or (HERMES_ROOT + '/venv/Scripts/python.exe')
ENV_FILE = os.environ.get('HERMES_ENV') or (_home() + '/.hermes/.env')


def load_env():
    env = {}
    try:
        with open(ENV_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                env[k.strip()] = v.strip().strip('"').strip("'")
    except Exception as e:
        return None, f'读取 .env 失败: {e}'
    return env, None


def emit(payload):
    sys.stdout.write(json.dumps(payload, ensure_ascii=False) + '\n')
    sys.stdout.flush()


def find_loop(env):
    """根据 .env 推断 provider/base_url/model。Hermes 支持多 provider，
    这里只做最稳的：优先 DEEPSEEK_*（base_url+key），其次 OPENAI_*。"""
    model = env.get('HERMES_MODEL', '')
    if env.get('DEEPSEEK_BASE_URL') and env.get('DEEPSEEK_API_KEY'):
        return {
            'provider': 'deepseek',
            'base_url': env['DEEPSEEK_BASE_URL'],
            'api_key': env['DEEPSEEK_API_KEY'],
            'model': model or 'deepseek-chat',
        }
    if env.get('OPENAI_BASE_URL') and env.get('OPENAI_API_KEY'):
        return {
            'provider': 'openai',
            'base_url': env['OPENAI_BASE_URL'],
            'api_key': env['OPENAI_API_KEY'],
            'model': model or 'gpt-4o-mini',
        }
    return None


def cmd_status():
    env, err = load_env()
    if err:
        import shutil
        return emit({'ok': False, 'available': False, 'error': err,
                     'venv_py': os.path.exists(VENV_PY),
                     'hermes_root': os.path.exists(HERMES_ROOT)})
    loop = find_loop(env)
    return emit({
        'ok': True,
        'available': loop is not None,
        'hermes_root': os.path.exists(HERMES_ROOT),
        'venv_py': os.path.exists(VENV_PY),
        'model': (loop or {}).get('model'),
        'provider': (loop or {}).get('provider'),
        'has_deepseek': bool(env.get('DEEPSEEK_BASE_URL')),
        'has_openai': bool(env.get('OPENAI_BASE_URL')),
        'note': '凭证已就绪，可 headless 调用' if loop else '未找到可直接用的模型路由',
    })


def cmd_run(prompt, model_opt, timeout_s):
    env, err = load_env()
    if err:
        return emit({'ok': False, 'error': err})
    # 首选自定义 provider（config.yaml 里定义，走 DeepSeek）；回退自动推理
    loop = find_loop(env)
    if loop is None:
        return emit({'ok': False, 'error': '未找到可用的模型凭证（.env 缺 DEEPSEEK/OPENAI）'})
    if model_opt:
        loop['model'] = model_opt

    # 正确驱动方式：python cli.py -q "<prompt>"（官方 headless 单次模式）
    # 用默认 HERMES_HOME=~/.hermes（含自定义 custom_providers 定义）。
    # 需要完整权限访问用户目录；由 DSH 侧为这个 subprocess 放行。
    import subprocess as sp
    cli = os.path.join(HERMES_ROOT, 'cli.py')
    py = VENV_PY
    if not os.path.exists(py):
        return emit({'ok': False, 'error': f'venv python 不存在: {py}'})
    if not os.path.exists(cli):
        return emit({'ok': False, 'error': f'cli.py 不存在: {cli}'})

    cmd = [py, cli, '-q', prompt, '--quiet', '--reasoning', 'none']
    if loop.get('provider'): cmd += ['--provider', loop['provider']]
    cmd += ['--model', loop['model']]
    cmd_env = dict(os.environ)
    cmd_env['HERMES_HOME'] = os.path.expanduser('~/.hermes')
    if os.name == 'nt':
        cmd_env['LOCALAPPDATA'] = os.environ.get('LOCALAPPDATA', _localappdata())

    start = time.time()
    try:
        proc = sp.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace',
                      timeout=timeout_s, env=cmd_env, cwd=HERMES_ROOT)
        elapsed = round(time.time() - start, 2)
        out = (proc.stdout or '') + '\n' + proc.stderr if proc.stderr else (proc.stdout or '')
    except sp.TimeoutExpired:
        return emit({'ok': False, 'error': f'Hermes 运行超时(>{timeout_s}s)'})
    except Exception as e:
        return emit({'ok': False, 'error': f'Hermes 启动失败: {type(e).__name__}: {e}'})

    # 提取最终回答：通常紧随 "session_id:" 前，或最后一段非诊断文本
    tail = out.strip()
    # 去掉 session_id 尾行和 reasoning 框
    lines = [ln for ln in tail.splitlines() if ln.strip()]
    # 找 session_id 前的文本
    result_text = ''
    for i, ln in enumerate(lines):
        if ln.strip().startswith('session_id:'):
            result_text = '\n'.join(lines[:i]).strip()
            break
    if not result_text:
        # 回退：取最后若干行"
        result_text = lines[-5:].join('\n') if lines else ''
    # 进一步清理 reasoning 框
    if 'Reasoning' in result_text:
        seg = result_text.split('└', 1)
        result_text = seg[-1] if len(seg) > 1 else result_text
    return emit({'ok': proc.returncode == 0, 'exit': proc.returncode,
                 'elapsed_s': elapsed, 'model': loop['model'],
                 'text': result_text.strip()[:4000] if result_text else (out.strip()[:2000] or '（无输出）')})


def main():
    p = argparse.ArgumentParser(prog='farm-hermes')
    p.add_argument('command', nargs='?', default='status')
    p.add_argument('prompt', nargs='?')
    p.add_argument('--model', default=None)
    p.add_argument('--timeout', type=float, default=300)
    a = p.parse_args()
    if a.command == 'status':
        cmd_status()
    elif a.command == 'run':
        if not a.prompt:
            emit({'ok': False, 'error': 'run 需要 prompt'})
            return
        cmd_run(a.prompt, a.model, a.timeout)
    else:
        emit({'ok': False, 'error': f'未知命令: {a.command}'})


if __name__ == '__main__':
    main()
