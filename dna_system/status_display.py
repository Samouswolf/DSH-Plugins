"""
DNA-Strand 状态显示窗口
系统启动时显示当前状态概览
"""
import os
import sys
import time
from datetime import datetime


class StatusDisplay:
    """状态显示窗口"""

    # ANSI颜色代码
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'dim': '\033[2m',
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'bg_blue': '\033[44m',
        'bg_green': '\033[42m',
    }

    def __init__(self, use_color: bool = True):
        self.use_color = use_color and self._supports_color()
        self.start_time = time.time()

    def _supports_color(self) -> bool:
        """检查终端是否支持颜色"""
        # Windows 10+ 支持 ANSI
        if os.name == 'nt':
            return os.environ.get('TERM_PROGRAM') != '' or 'ANSICON' in os.environ
        return hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()

    def _c(self, color: str, text: str) -> str:
        """着色文本"""
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def _bar(self, value: float, max_value: float, width: int = 20, fill_char: str = '#', empty_char: str = '-') -> str:
        """生成进度条"""
        if max_value == 0:
            return empty_char * width
        ratio = min(1.0, value / max_value)
        filled = int(ratio * width)
        return fill_char * filled + empty_char * (width - filled)

    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        else:
            return f"{size_bytes / (1024 * 1024):.1f} MB"

    def _format_duration(self, seconds: float) -> str:
        """格式化时长"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds / 60:.1f}min"
        else:
            return f"{seconds / 3600:.1f}h"

    def show_boot_status(self, system_stats: dict):
        """
        显示启动状态
        system_stats: {
            'dna_count': int,
            'patterns': int,
            'storage': str,
            'fragments': int,
            'vector_engine': dict,
            'boot_time': float,
        }
        """
        dna_count = system_stats.get('dna_count', 0)
        patterns = system_stats.get('patterns', 0)
        storage = system_stats.get('storage', '0 B')
        fragments = system_stats.get('fragments', 0)
        vector_info = system_stats.get('vector_engine', {})
        boot_time = system_stats.get('boot_time', 0)

        # 计算健康度
        health_score = self._calculate_health(dna_count, patterns, fragments)
        health_bar = self._bar(health_score, 100, 20)
        health_color = 'green' if health_score > 70 else 'yellow' if health_score > 40 else 'red'

        # 向量引擎状态
        vec_type = '语义' if vector_info.get('use_semantic') else 'TF-IDF'
        vec_model = vector_info.get('model_type') or 'hash'
        index_size = vector_info.get('index_size', 0)

        # 输出状态框
        print()
        print(self._c('bold', '+' + '=' * 58 + '+'))
        print(self._c('bold', '|') + self._c('cyan', '   [DNA] DNA-Strand 记忆系统 v3.0                         ') + self._c('bold', '|'))
        print(self._c('bold', '+' + '=' * 58 + '+'))

        # 核心指标
        print(self._c('bold', '|') + f'   DNA 数量:    {self._c("green", str(dna_count)):20s}  洞察: {self._c("yellow", str(patterns)):10s}  ' + self._c('bold', '|'))
        print(self._c('bold', '|') + f'   存储大小:    {self._c("blue", storage):20s}  碎片: {self._c("dim", str(fragments)):10s}  ' + self._c('bold', '|'))
        print(self._c('bold', '|') + f'   向量引擎:    {self._c("magenta", f"{vec_type} ({vec_model})"):20s}  索引: {self._c("cyan", str(index_size)):10s}  ' + self._c('bold', '|'))

        # 健康度
        print(self._c('bold', '|') + f'   健康度:      [{self._c(health_color, health_bar)}] {health_score:.0f}%'.ljust(58) + self._c('bold', '|'))

        # 启动时间
        print(self._c('bold', '|') + f'   启动耗时:    {self._c("dim", self._format_duration(boot_time))}'.ljust(58) + self._c('bold', '|'))

        print(self._c('bold', '+' + '=' * 58 + '+'))

        # 快捷命令提示
        print(self._c('bold', '|') + self._c('dim', '   命令: query | evolve | stats | maintenance | status  ') + self._c('bold', '|'))
        print(self._c('bold', '+' + '=' * 58 + '+'))
        print()

    def show_query_result(self, query: str, results: list, query_time: float):
        """显示查询结果"""
        print()
        print(self._c('bold', f'+- [QRY] {self._c("cyan", query)} -----------------------------+'))
        print(self._c('bold', f'│  结果: {len(results)} 条  耗时: {self._c("dim", f"{query_time*1000:.1f}ms")}                          │'))
        print(self._c('bold', '+---------------------------------------------------------+'))

        for i, r in enumerate(results[:5]):
            content = r.get('content', {})
            if isinstance(content, dict):
                name = content.get('pattern_name', content.get('text', str(content)))[:40]
            else:
                name = str(content)[:40]
            print(self._c('bold', f'│  {i+1}. {self._c("green", name):40s}              │'))

        if len(results) > 5:
            print(self._c('bold', f'│  ... 还有 {len(results) - 5} 条结果                              │'))

        print(self._c('bold', '+---------------------------------------------------------+'))
        print()

    def show_maintenance_report(self, report: dict):
        """显示维护报告"""
        before = report.get('before', {})
        after = report.get('after', {})
        actions = report.get('actions', [])

        print()
        print(self._c('bold', '+' + '=' * 50 + '+'))
        print(self._c('bold', '|') + self._c('cyan', '   [MAINT] 维护报告                                   ') + self._c('bold', '|'))
        print(self._c('bold', '+' + '=' * 50 + '+'))

        # 概览
        dna_before = before.get('dna_count', 0)
        dna_after = after.get('dna_count', 0)
        removed = dna_before - dna_after
        print(self._c('bold', '|') + f'   DNA: {dna_before} → {self._c("green", str(dna_after))} (清理 {self._c("red", str(removed))} 条)'.ljust(50) + self._c('bold', '|'))

        # 各项操作
        for action in actions:
            action_name = action.get('action', 'unknown')
            if action_name == 'clean_tags':
                count = action.get('cleaned_count', 0)
                print(self._c('bold', '|') + f'   [TAG] 标签清理: {self._c("yellow", str(count))} 条'.ljust(50) + self._c('bold', '|'))
            elif action_name == 'filter_low_quality':
                count = action.get('removed_count', 0)
                print(self._c('bold', '|') + f'   [QTY] 质量过滤: {self._c("red", str(count))} 条'.ljust(50) + self._c('bold', '|'))
            elif action_name == 'deduplicate':
                count = action.get('removed_count', 0)
                print(self._c('bold', '|') + f'   [DUP] 去重: {self._c("yellow", str(count))} 条'.ljust(50) + self._c('bold', '|'))

        print(self._c('bold', '+' + '=' * 50 + '+'))
        print()

    def show_quality_report(self, report: dict):
        """显示质量报告"""
        total = report.get('total_dna', 0)
        tag_quality = report.get('tag_quality', {})
        content_quality = report.get('content_quality', {})
        access_quality = report.get('access_quality', {})

        print()
        print(self._c('bold', '+' + '=' * 50 + '+'))
        print(self._c('bold', '|') + self._c('cyan', '   [QRY] 质量报告                                     ') + self._c('bold', '|'))
        print(self._c('bold', '+' + '=' * 50 + '+'))

        # 标签质量
        meaningful_ratio = tag_quality.get('meaningful_ratio', 0) * 100
        tag_bar = self._bar(meaningful_ratio, 100, 15)
        tag_color = 'green' if meaningful_ratio > 50 else 'yellow' if meaningful_ratio > 20 else 'red'
        print(self._c('bold', '|') + f'   标签质量:    [{self._c(tag_color, tag_bar)}] {meaningful_ratio:.0f}%'.ljust(50) + self._c('bold', '|'))

        # 内容质量
        short_ratio = content_quality.get('short_ratio', 0) * 100
        content_score = 100 - short_ratio
        content_bar = self._bar(content_score, 100, 15)
        content_color = 'green' if content_score > 80 else 'yellow' if content_score > 60 else 'red'
        print(self._c('bold', '|') + f'   内容质量:    [{self._c(content_color, content_bar)}] {content_score:.0f}%'.ljust(50) + self._c('bold', '|'))

        # 访问质量
        access_ratio = access_quality.get('access_ratio', 0) * 100
        access_bar = self._bar(access_ratio, 100, 15)
        access_color = 'green' if access_ratio > 30 else 'yellow' if access_ratio > 10 else 'red'
        print(self._c('bold', '|') + f'   访问活跃度:  [{self._c(access_color, access_bar)}] {access_ratio:.0f}%'.ljust(50) + self._c('bold', '|'))

        print(self._c('bold', '+' + '=' * 50 + '+'))
        print()

    def _calculate_health(self, dna_count: int, patterns: int, fragments: int) -> float:
        """计算系统健康度分数"""
        score = 0.0

        # DNA数量分数 (0-40分)
        if dna_count > 1000:
            score += 40
        elif dna_count > 100:
            score += 30
        elif dna_count > 10:
            score += 20
        else:
            score += 10

        # 洞察数量分数 (0-30分)
        if patterns > 50:
            score += 30
        elif patterns > 10:
            score += 20
        elif patterns > 0:
            score += 10

        # 碎片比例分数 (0-30分)
        if dna_count > 0:
            fragment_ratio = fragments / dna_count
            if fragment_ratio < 0.1:
                score += 30
            elif fragment_ratio < 0.3:
                score += 20
            else:
                score += 10

        return score

    def show_evolution_result(self, before: int, after: int, patterns: int):
        """显示进化结果"""
        print()
        print(self._c('bold', '+- [EVO] 进化完成 -----------------------------+'))
        print(self._c('bold', f'│  DNA: {before} -> {self._c("green", str(after))}  洞察: {self._c("yellow", str(patterns))}'.ljust(50) + self._c('bold', '│')))
        print(self._c('bold', '+------------------------------------------------+'))
        print()

    def show_session_summary(self, summary: str):
        """显示会话摘要"""
        print()
        print(self._c('bold', '+- [SES] 会话摘要 -----------------------------+'))
        # 截断长摘要
        if len(summary) > 100:
            summary = summary[:100] + '...'
        print(self._c('bold', f'│  {summary}'.ljust(50) + self._c('bold', '│')))
        print(self._c('bold', '+------------------------------------------------+'))
        print()


# 全局实例
_display = None

def get_display(use_color: bool = True) -> StatusDisplay:
    """获取全局状态显示实例"""
    global _display
    if _display is None:
        _display = StatusDisplay(use_color)
    return _display
