"""
内容质量过滤器 —— 入库时过滤低质量内容
"""
import re


class QualityFilter:
    """内容质量过滤器"""

    # 最小内容长度
    MIN_CONTENT_LENGTH = 30

    # 噪音模式（匹配到的内容不入库）
    NOISE_PATTERNS = [
        r'^\s*$',                          # 空白
        r'^[{}\[\](),;:]+$',              # 纯符号
        r'^\d+$',                          # 纯数字
        r'^[a-zA-Z]{1,3}$',              # 太短的英文
        r'console\.log',                   # 调试日志
        r'//.*TODO',                       # TODO注释
        r'/\*.*?\*/',                      # 块注释
        r'^\s*//\s*$',                     # 空注释行
    ]

    # 高价值内容模式（匹配到的内容优先保留）
    HIGH_VALUE_PATTERNS = [
        r'(设计|架构|决策|方案)',          # 设计决策
        r'(bug|fix|修复|问题)',            # Bug修复
        r'(优化|改进|重构)',               # 优化改进
        r'(教训|经验|总结|避坑)',          # 经验教训
        r'(需求|功能|特性)',               # 需求功能
        r'(测试|验证|确认)',               # 测试验证
    ]

    def should_ingest(self, content: str, content_type: str = "text") -> tuple[bool, float]:
        """
        判断内容是否应该入库
        返回: (是否入库, 质量分数 0-1)
        """
        if not content or not content.strip():
            return False, 0.0

        content = content.strip()

        # 1. 长度检查
        if len(content) < self.MIN_CONTENT_LENGTH:
            return False, 0.0

        # 2. 噪音检查
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, content, re.DOTALL):
                return False, 0.0

        # 3. 计算质量分数
        score = self._calculate_score(content, content_type)

        # 4. 阈值判断
        if score < 0.2:
            return False, score

        return True, score

    def _calculate_score(self, content: str, content_type: str) -> float:
        """计算内容质量分数"""
        score = 0.0

        # 1. 长度分数（越长越好，但有上限）
        length_score = min(1.0, len(content) / 500)
        score += length_score * 0.3

        # 2. 信息密度（中文字符比例）
        cn_chars = len(re.findall(r'[一-鿿]', content))
        total_chars = len(content)
        if total_chars > 0:
            density = cn_chars / total_chars
            score += density * 0.2

        # 3. 高价值内容加分
        for pattern in self.HIGH_VALUE_PATTERNS:
            if re.search(pattern, content, re.IGNORECASE):
                score += 0.2
                break

        # 4. 结构化内容加分
        if re.search(r'[-*]\s+', content):  # 列表
            score += 0.1
        if re.search(r'```', content):      # 代码块
            score += 0.1
        if re.search(r'#{1,3}\s+', content): # 标题
            score += 0.1

        return min(1.0, score)

    def filter_batch(self, contents: list[str], content_type: str = "text") -> list[tuple[str, float]]:
        """
        批量过滤内容
        返回: [(内容, 质量分数), ...] 只包含应该入库的
        """
        results = []
        for content in contents:
            should_ingest, score = self.should_ingest(content, content_type)
            if should_ingest:
                results.append((content, score))
        return results


# 全局实例
quality_filter = QualityFilter()
