"""
Token节省追踪器
实时记录每次DNA记忆命中节省的Token数量
"""
import json
import time
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict


class TokenSavingsTracker:
    """追踪Token节省的单例追踪器"""

    _instance = None
    _data_file = Path(__file__).parent.parent.parent / '.dna' / 'token_savings.json'

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._load()

    def _load(self):
        """从文件加载历史数据"""
        if self._data_file.exists():
            try:
                with open(self._data_file, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            except:
                self._init_data()
        else:
            self._init_data()

    def reload(self):
        """重新加载数据（用于API请求时获取最新数据）"""
        self._load()
        return self._data

    def _init_data(self):
        """初始化数据结构"""
        self._data = {
            'total_saved_tokens': 0,
            'total_queries': 0,
            'total_hits': 0,
            'sessions': {},
            'daily': {},
            'hourly': {},
            'recent_hits': [],  # 最近50次命中
        }

    def _save(self):
        """保存数据到文件"""
        try:
            self._data_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._data_file, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[TokenTracker] Save error: {e}")

    @staticmethod
    def _sanitize(s: str) -> str:
        """确保字符串是合法UTF-8（修复Windows GBK编码混入问题）"""
        if not isinstance(s, str):
            return str(s)
        try:
            s.encode('utf-8')
            return s
        except UnicodeEncodeError:
            return s.encode('utf-8', errors='replace').decode('utf-8')

    def record_hit(self, query: str, hit_count: int, hit_type: str = 'dna',
                   estimated_tokens_per_hit: int = 150):
        """
        记录一次DNA命中

        Args:
            query: 查询内容
            hit_count: 命中的DNA数量
            hit_type: 命中类型 (dna/brain/pattern)
            estimated_tokens_per_hit: 每次命中估算节省的Token数
        """
        now = datetime.now()
        saved_tokens = hit_count * estimated_tokens_per_hit

        # 消毒查询字符串（修复Windows编码问题）
        query = self._sanitize(query)

        # 更新总计
        self._data['total_saved_tokens'] += saved_tokens
        self._data['total_queries'] += 1
        self._data['total_hits'] += hit_count

        # 更新每日统计
        day_key = now.strftime('%Y-%m-%d')
        if day_key not in self._data['daily']:
            self._data['daily'][day_key] = {'tokens': 0, 'queries': 0, 'hits': 0}
        self._data['daily'][day_key]['tokens'] += saved_tokens
        self._data['daily'][day_key]['queries'] += 1
        self._data['daily'][day_key]['hits'] += hit_count

        # 更新每小时统计
        hour_key = now.strftime('%Y-%m-%d_%H')
        if hour_key not in self._data['hourly']:
            self._data['hourly'][hour_key] = {'tokens': 0, 'queries': 0, 'hits': 0}
        self._data['hourly'][hour_key]['tokens'] += saved_tokens
        self._data['hourly'][hour_key]['queries'] += 1
        self._data['hourly'][hour_key]['hits'] += hit_count

        # 记录最近命中（保留最近50条）
        hit_record = {
            'timestamp': now.isoformat(),
            'query': query[:100],
            'hit_count': hit_count,
            'saved_tokens': saved_tokens,
            'type': hit_type,
        }
        self._data['recent_hits'].insert(0, hit_record)
        self._data['recent_hits'] = self._data['recent_hits'][:50]

        # 保存
        self._save()

        return saved_tokens

    def record_session_start(self, session_id: str = None):
        """记录会话开始"""
        if session_id is None:
            session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self._data['sessions'][session_id] = {
            'start': datetime.now().isoformat(),
            'tokens': 0,
            'queries': 0,
            'hits': 0,
        }
        self._current_session = session_id
        self._save()
        return session_id

    def get_session_stats(self, session_id: str = None):
        """获取当前会话统计"""
        if session_id is None:
            session_id = getattr(self, '_current_session', None)
        if session_id and session_id in self._data['sessions']:
            return self._data['sessions'][session_id]
        return {'tokens': 0, 'queries': 0, 'hits': 0}

    def get_today_stats(self):
        """获取今日统计"""
        today = datetime.now().strftime('%Y-%m-%d')
        return self._data['daily'].get(today, {'tokens': 0, 'queries': 0, 'hits': 0})

    def get_hourly_stats(self, hours: int = 24):
        """获取最近N小时的统计"""
        now = datetime.now()
        result = []
        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour_key = hour.strftime('%Y-%m-%d_%H')
            stats = self._data['hourly'].get(hour_key, {'tokens': 0, 'queries': 0, 'hits': 0})
            result.append({
                'hour': hour.strftime('%H:00'),
                **stats
            })
        return list(reversed(result))

    def get_total_stats(self):
        """获取总统计"""
        return {
            'total_saved_tokens': self._data['total_saved_tokens'],
            'total_queries': self._data['total_queries'],
            'total_hits': self._data['total_hits'],
            'avg_tokens_per_query': (
                self._data['total_saved_tokens'] // self._data['total_queries']
                if self._data['total_queries'] > 0 else 0
            ),
            'hit_rate': (
                self._data['total_hits'] / self._data['total_queries']
                if self._data['total_queries'] > 0 else 0
            ),
        }

    def get_recent_hits(self, limit: int = 10):
        """获取最近的命中记录"""
        return self._data['recent_hits'][:limit]

    def get_comparison_data(self):
        """获取对比数据（今天 vs 昨天）"""
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        today_stats = self._data['daily'].get(today, {'tokens': 0, 'queries': 0, 'hits': 0})
        yesterday_stats = self._data['daily'].get(yesterday, {'tokens': 0, 'queries': 0, 'hits': 0})

        # 计算变化百分比
        def calc_change(current, previous):
            if previous == 0:
                return 100 if current > 0 else 0
            return ((current - previous) / previous) * 100

        return {
            'today': today_stats,
            'yesterday': yesterday_stats,
            'changes': {
                'tokens': calc_change(today_stats['tokens'], yesterday_stats['tokens']),
                'queries': calc_change(today_stats['queries'], yesterday_stats['queries']),
                'hits': calc_change(today_stats['hits'], yesterday_stats['hits']),
            }
        }


# 全局实例
tracker = TokenSavingsTracker()
