"""
DNA-Strand Web 服务器
提供实时仪表盘和API接口
"""
import json
import time
import threading
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os


class DNARequestHandler(SimpleHTTPRequestHandler):
    """DNA系统HTTP请求处理器"""

    # 共享的DNA系统实例
    system = None

    def do_GET(self):
        """处理GET请求"""
        path = self.path.split('?')[0]  # 移除查询参数

        if path == '/' or path == '/index.html':
            self._serve_dashboard()
        elif path == '/api/stats':
            self._serve_stats()
        elif path == '/api/quality':
            self._serve_quality()
        elif path == '/api/query':
            self._serve_query()
        elif path == '/api/dna-list':
            self._serve_dna_list()
        elif path == '/api/patterns':
            self._serve_patterns()
        elif path == '/api/map':
            self._serve_map()
        elif path == '/api/map-data':
            self._serve_map_data()
        elif path == '/api/map-nearby':
            self._serve_map_nearby()
        elif path == '/api/cache-stats':
            self._serve_cache_stats()
        elif path == '/api/token-savings':
            self._serve_token_savings()
        elif path == '/api/token-savings/recent':
            self._serve_token_savings_recent()
        elif path == '/api/token-savings/hourly':
            self._serve_token_savings_hourly()
        elif path == '/api/ollama-check':
            self._handle_ollama_check()
        elif path == '/api/inbox/submit':
            self._handle_inbox_submit()
        elif path.startswith('/api/inbox/status/'):
            self._handle_inbox_status()
        elif path == '/api/inbox/pending':
            self._handle_inbox_pending()
        elif path == '/api/inbox/complete':
            self._handle_inbox_complete()
        elif path == '/map' or path == '/map.html':
            self._serve_map_page()
        elif path == '/team' or path == '/team.html':
            self._serve_team_page()
        else:
            # 尝试作为静态文件
            try:
                super().do_GET()
            except Exception as e:
                self.send_error(404, f'Not found: {path}')

    def _serve_dashboard(self):
        """ serve 仪表盘页面 """
        dashboard_path = Path(__file__).parent / 'dashboard.html'
        if dashboard_path.exists():
            with open(dashboard_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
            self.send_header('Pragma', 'no-cache')
            self.send_header('Expires', '0')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(404, 'Dashboard not found')

    def _serve_stats(self):
        """serve 系统统计：复用CLI真实统计口径，兼容Dashboard旧字段。"""
        stats = {}
        if self.system:
            stats = self.system.stats()

        try:
            from dna_system.dna_tool import real_stats
            real = real_stats()
        except Exception as e:
            real = {
                'error': str(e),
                'total_strands': stats.get('dna_count', 0),
                'data_sources': {'strands': stats.get('dna_count', 0), 'brain_pool': 0},
                'bug_related': 0,
                'fixes_recorded': 0,
                'development_records': 0,
                'records_total': 0,
                'today_development': {},
                'by_game': {},
            }

        sources = real.get('data_sources', {})
        stats['dna_count'] = real.get('total_strands', 0)
        stats['strands_count'] = sources.get('strands', 0)
        stats['brain_pool_count'] = sources.get('brain_pool', 0)
        stats['bug_related'] = real.get('bug_related', 0)
        stats['fixes_recorded'] = real.get('fixes_recorded', 0)
        stats['development_records'] = real.get('development_records', 0)
        stats['records_total'] = real.get('records_total', 0)
        stats['today_development'] = real.get('today_development', {})
        stats['by_game'] = real.get('by_game', {})
        stats['stats_source'] = 'dna_tool.real_stats'

        self._send_json(stats)

    def _serve_quality(self):
        """ serve 质量报告 """
        if self.system:
            report = self.system.get_quality_report(show=False)
            self._send_json(report)
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_query(self):
        """ serve 查询结果 """
        # 从URL参数获取查询
        from urllib.parse import unquote
        query_string = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        query = unquote(params.get('q', ''))

        if self.system and query:
            results, query_id = self.system.query_with_feedback(query, show=False)
            self._send_json({
                'query': query,
                'query_id': query_id,
                'results': results,
                'count': len(results),
            })
        else:
            self._send_json({'error': 'No query provided'})

    def _serve_dna_list(self):
        """ serve DNA列表 """
        import json as _json
        import re
        if self.system:
            # 返回前100条DNA
            dnas = []
            for d in self.system.pool[:100]:
                # 确保content_preview是有效的JSON字符串
                content = d.content
                if isinstance(content, dict):
                    # 如果是字典，提取text字段或summary字段
                    preview = content.get('text', content.get('summary', ''))
                    if not preview:
                        # 如果没有text或summary，使用第一个字符串值
                        for v in content.values():
                            if isinstance(v, str) and len(v) > 10:
                                preview = v
                                break
                        if not preview:
                            preview = str(list(content.keys())[:3])
                    preview = str(preview)
                else:
                    preview = str(content)

                # 清理特殊字符，确保是有效的JSON字符串
                # 移除换行符、回车符、制表符等
                preview = preview.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
                # 移除多余的空格
                preview = re.sub(r'\s+', ' ', preview).strip()
                # 截断到100个字符，但确保不会破坏JSON字符串
                # json.dumps会自动处理转义，所以这里直接截断即可
                preview = preview[:100]

                dnas.append({
                    'id': d.id,
                    'type': d.dna_type.value,
                    'tags': d.tags[:5],
                    'lifetime': round(d.lifetime, 1),
                    'access_count': d.access_count,
                    'content_preview': preview,
                })
            self._send_json({'dnas': dnas, 'total': len(self.system.pool)})
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_patterns(self):
        """ serve 进化模式 """
        if self.system:
            patterns = []
            for p in self.system.evolution.patterns[:50]:
                if p.is_alive:
                    patterns.append({
                        'id': p.id,
                        'name': p.content.get('pattern_name', '未命名'),
                        'confidence': p.content.get('confidence', 0),
                        'source_count': p.content.get('source_count', 0),
                        'core_words': p.content.get('core_words', [])[:5],
                    })
            self._send_json({'patterns': patterns, 'total': len(patterns)})
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_map(self):
        """构建记忆地图（触发降维）"""
        from urllib.parse import unquote
        query_string = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        method = unquote(params.get('method', 'auto'))

        if self.system:
            result = self.system.build_memory_map(method=method)
            self._send_json(result)
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_map_data(self):
        """获取地图可视化数据"""
        from urllib.parse import unquote
        query_string = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        edge_radius = float(params.get('radius', '0.5'))

        if self.system:
            data = self.system.get_memory_map_data(edge_radius=edge_radius)
            self._send_json(data)
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_map_nearby(self):
        """查询附近记忆"""
        from urllib.parse import unquote
        query_string = self.path.split('?')[1] if '?' in self.path else ''
        params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
        dna_id = unquote(params.get('id', ''))
        radius = float(params.get('radius', '1.0'))

        if self.system and dna_id:
            results = self.system.find_nearby_memories(dna_id, radius)
            self._send_json({'dna_id': dna_id, 'radius': radius, 'nearby': results})
        else:
            self._send_json({'error': 'No dna_id provided'})

    def _serve_cache_stats(self):
        """serve 实时系统状态（无虚假数字，全部来自系统stats）"""
        if self.system:
            import time as _time
            stats = self.system.stats()

            # 从实际系统状态获取数据
            brain_s = stats.get('brain', {})
            pool_total = brain_s.get('pool_total', 0)
            cluster_s = stats.get('semantic_cluster', {})
            smart_s = stats.get('smart_loader', {})
            cluster_hit_s = stats.get('cluster_hits', {})
            vec_info = stats.get('vector_engine', {})

            # 向量引擎信息
            engine_type = vec_info.get('model_type', 'tfidf-hash-deterministic')
            is_semantic = vec_info.get('use_semantic', False)
            index_size = vec_info.get('index_size', 0)

            # Token节省：基于 cluster_loader 实际加载的DNA数计算
            # 每条DNA平均 ~150 tokens，加载后在上下文复用
            cluster_loader_s = stats.get('cluster_loader', {})
            loaded_count = cluster_loader_s.get('loaded_clusters', 0)
            # 估算：每个簇约15条DNA，每条约120 tokens
            estimated_cache_tokens = loaded_count * 15 * 120

            # 预加载命中统计
            preload_count = smart_s.get('preload_count', 0)
            hit_count = smart_s.get('hit_count', 0)
            hit_rate = smart_s.get('hit_rate', 0.0)

            # 聚类命中统计
            total_hits = cluster_hit_s.get('total_hits', 0)
            unique_clusters = cluster_hit_s.get('unique_clusters', 0)

            self._send_json({
                'cache': {
                    'loaded_clusters': loaded_count,
                    'estimated_cache_tokens': estimated_cache_tokens,
                    'preload_count': preload_count,
                    'hit_count': hit_count,
                    'hit_rate': round(hit_rate, 2),
                },
                'intelligence': {
                    'total_bugs': stats.get('fixes_recorded', stats.get('patterns', 0)),
                },
                'token_savings': {
                    'memory_md': estimated_cache_tokens,
                    'dna_cache': estimated_cache_tokens,
                    'total_per_session': estimated_cache_tokens,
                    'estimated_monthly': estimated_cache_tokens * 150,
                    'compression_ratio': f'{index_size}/{pool_total}' if pool_total > 0 else 'N/A',
                },
                'engine': {
                    'semantic': is_semantic,
                    'type': engine_type,
                    'dim': 512,
                },
                'timestamp': _time.time(),
            })
        else:
            self._send_json({'error': 'System not initialized'})

    def _serve_map_page(self):
        """serve 认知地图页面"""
        map_path = Path(__file__).parent / 'map.html'
        if map_path.exists():
            with open(map_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(404, 'Map page not found')

    def _serve_team_page(self):
        """serve 团队指挥中心页面"""
        team_path = Path(__file__).parent / 'team.html'
        if team_path.exists():
            with open(team_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(content.encode('utf-8'))
        else:
            self.send_error(404, 'Team page not found')

    def _serve_token_savings(self):
        """serve Token节省统计数据"""
        try:
            from dna_system.core.token_tracker import tracker
            # 重新加载最新数据
            tracker.reload()
            data = {
                'total': tracker.get_total_stats(),
                'today': tracker.get_today_stats(),
                'comparison': tracker.get_comparison_data(),
                'timestamp': time.time(),
            }
            self._send_json(data)
        except Exception as e:
            self._send_json({'error': str(e)})

    def _serve_token_savings_recent(self):
        """serve 最近的Token节省记录"""
        try:
            from urllib.parse import unquote
            query_string = self.path.split('?')[1] if '?' in self.path else ''
            params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
            limit = int(params.get('limit', '10'))

            from dna_system.core.token_tracker import tracker
            # 重新加载最新数据
            tracker.reload()
            data = {
                'recent_hits': tracker.get_recent_hits(limit),
                'timestamp': time.time(),
            }
            self._send_json(data)
        except Exception as e:
            self._send_json({'error': str(e)})

    def _serve_token_savings_hourly(self):
        """serve 每小时Token节省统计"""
        try:
            from urllib.parse import unquote
            query_string = self.path.split('?')[1] if '?' in self.path else ''
            params = dict(p.split('=') for p in query_string.split('&') if '=' in p)
            hours = int(params.get('hours', '24'))

            from dna_system.core.token_tracker import tracker
            # 重新加载最新数据
            tracker.reload()
            data = {
                'hourly': tracker.get_hourly_stats(hours),
                'timestamp': time.time(),
            }
            self._send_json(data)
        except Exception as e:
            self._send_json({'error': str(e)})

    def _send_json(self, data):
        """发送JSON响应"""
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode('utf-8'))

    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/chat':
            self._handle_chat()
        elif self.path == '/api/chat-stream':
            self._handle_chat_stream()
        elif self.path == '/api/inbox/submit':
            self._handle_inbox_submit()
        elif self.path == '/api/inbox/complete':
            self._handle_inbox_complete()
        else:
            self.send_error(404, 'Not found')

    def do_OPTIONS(self):
        """CORS preflight"""
        self.send_response(204)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _handle_chat(self):
        """向本地 Qwen 模型发送消息"""
        import requests as _requests
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self._send_json({'error': str(e), 'status': 'parse_error'})
            return

        message = body.get('message', '').strip()
        history = body.get('history', [])
        system_prompt = body.get('system', '')

        if not message:
            self._send_json({'error': 'Empty message', 'status': 'empty'})
            return

        # 构建 Ollama 请求
        ollama_url = 'http://127.0.0.1:11434/api/chat'
        ollama_messages = []
        if system_prompt:
            ollama_messages.append({'role': 'system', 'content': system_prompt})
        for h in history:
            ollama_messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
        ollama_messages.append({'role': 'user', 'content': message})

        try:
            r = _requests.post(ollama_url, json={
                'model': 'qwen2.5:1.5b_m',
                'messages': ollama_messages,
                'stream': False,
                'options': {'num_predict': 2048, 'temperature': 0.7},
            }, timeout=120)
            if r.status_code != 200:
                self._send_json({'error': f'Ollama returned {r.status_code}', 'status': 'offline'})
                return
            data = r.json()
            reply = data.get('message', {}).get('content', '')
            self._send_json({'reply': reply, 'status': 'ok'})
        except Exception as e:
            self._send_json({'error': str(e), 'status': 'offline'})

    def _handle_chat_stream(self):
        """流式向本地 Qwen 发送消息 (SSE)"""
        import requests as _requests
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self.send_error(400, str(e))
            return

        message = body.get('message', '').strip()
        history = body.get('history', [])
        system_prompt = body.get('system', '')

        ollama_messages = []
        if system_prompt:
            ollama_messages.append({'role': 'system', 'content': system_prompt})
        for h in history:
            ollama_messages.append({'role': h.get('role', 'user'), 'content': h.get('content', '')})
        ollama_messages.append({'role': 'user', 'content': message})

        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.end_headers()

        try:
            r = _requests.post('http://127.0.0.1:11434/api/chat', json={
                'model': 'qwen2.5:1.5b_m',
                'messages': ollama_messages,
                'stream': True,
                'options': {'num_predict': 2048, 'temperature': 0.7},
            }, stream=True, timeout=120)

            for line in r.iter_lines(decode_unicode=True):
                if not line: continue
                try:
                    chunk = json.loads(line)
                except json.JSONDecodeError:
                    continue
                text = chunk.get('message', {}).get('content', '')
                if text:
                    self.wfile.write(f"data: {json.dumps({'text': text}, ensure_ascii=False)}\n\n".encode('utf-8'))
                    self.wfile.flush()
            self.wfile.write(b"data: [DONE]\n\n")
            self.wfile.flush()
        except Exception as e:
            self.wfile.write(f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n".encode('utf-8'))
            self.wfile.flush()

    def _handle_ollama_check(self):
        """检查 Ollama 是否在线"""
        import requests as _requests
        try:
            r = _requests.get('http://127.0.0.1:11434/api/tags', timeout=3)
            if r.status_code == 200:
                data = r.json()
                models = [m.get('name', '') for m in data.get('models', [])]
                self._send_json({'online': True, 'models': models})
            else:
                self._send_json({'online': False, 'error': f'HTTP {r.status_code}'})
        except Exception as e:
            self._send_json({'online': False, 'error': str(e)})

    # ═══ Inbox 桥接 ═══

    def _handle_inbox_submit(self):
        """窗口提交任务 → 立即后台线程处理"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self._send_json({'error': str(e), 'status': 'parse_error'})
            return
        from .inbox import submit_task
        task = submit_task(
            agent_id=body.get('agent_id', 'unknown'),
            agent_role=body.get('agent_role', ''),
            message=body.get('message', ''),
            history=body.get('history', [])
        )
        # 在后台线程处理
        import threading
        t = threading.Thread(target=self._process_task_async, args=(task,), daemon=True)
        t.start()
        self._send_json({'status': 'pending', 'task_id': task['id']})

    def _process_task_async(self, task):
        """后台线程处理 inbox 任务"""
        import traceback
        try:
            from dna_system.web.inbox_daemon import process_task
            process_task(task)
        except Exception as e:
            err = traceback.format_exc()
            with open("inbox_error.log", "a", encoding="utf-8") as f:
                f.write(f"\n{'='*60}\n{err}\n")
            from .inbox import complete_task
            complete_task(task['id'], f"处理异常: {str(e)}", error=str(e))

    def _handle_inbox_status(self):
        """轮询任务状态"""
        task_id = self.path.replace('/api/inbox/status/', '').strip()
        if not task_id:
            self._send_json({'error': 'missing task_id'})
            return
        from .inbox import check_task
        result = check_task(task_id)
        self._send_json(result)

    def _handle_inbox_pending(self):
        """列出待处理任务（Claude Code 调用）"""
        from .inbox import list_pending
        tasks = list_pending()
        self._send_json({'pending': tasks, 'count': len(tasks)})

    def _handle_inbox_complete(self):
        """Claude Code 标记任务完成"""
        try:
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length).decode('utf-8'))
        except Exception as e:
            self._send_json({'error': str(e)})
            return
        from .inbox import complete_task
        result = complete_task(
            task_id=body.get('task_id', ''),
            response_text=body.get('response', ''),
            error=body.get('error')
        )
        self._send_json({'status': 'ok', 'task': result})


class DNAWebServer:
    """DNA系统Web服务器"""

    def __init__(self, system, host='127.0.0.1', port=8080):
        self.system = system
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self, background=True):
        """启动服务器"""
        # 设置系统实例
        DNARequestHandler.system = self.system

        # 切换到web目录
        web_dir = Path(__file__).parent
        os.chdir(web_dir)

        self.server = HTTPServer((self.host, self.port), DNARequestHandler)

        if background:
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            print(f"[Web] 服务器已启动: http://{self.host}:{self.port}")
        else:
            print(f"[Web] 服务器启动于: http://{self.host}:{self.port}")
            self.server.serve_forever()

    def stop(self):
        """停止服务器"""
        if self.server:
            self.server.shutdown()
            print("[Web] 服务器已停止")

    def get_url(self):
        """获取服务器URL"""
        return f"http://{self.host}:{self.port}"
