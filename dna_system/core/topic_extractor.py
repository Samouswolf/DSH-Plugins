"""
话题提取器 -- 从文本中提取话题信号

Phase 6 辅助模块：从对话上下文中提取话题信号，
复用 SmartTagger 的 GAME_KEYWORDS 和 TECH_KEYWORDS。

话题类型：
- 游戏名：贪吃蛇、塔防、修仙...
- 技术词：碰撞、渲染、部署...
- Bug关键词：崩溃、报错、修复...
"""
import re
from .smart_tagger import GAME_KEYWORDS, TECH_KEYWORDS


class TopicExtractor:
    """话题提取器 -- 从文本中提取有意义的话题信号"""

    def __init__(self):
        # 构建话题关键词表：keyword -> topic_name
        self._keyword_map: dict[str, str] = {}

        # 游戏关键词
        for game_name, keywords in GAME_KEYWORDS.items():
            for kw in keywords:
                self._keyword_map[kw.lower()] = game_name

        # 技术关键词（用类别名作为话题）
        for category, keywords in TECH_KEYWORDS.items():
            for kw in keywords:
                self._keyword_map[kw.lower()] = category

        # W5: 预编译短英文关键词的正则（纯ASCII且长度<=3的用 word boundary 匹配）
        # 中文关键词不做 word boundary 匹配（中文字符本身不会产生子串误报）
        self._short_kw_patterns: dict[str, tuple[re.Pattern, str]] = {}
        for keyword, topic in self._keyword_map.items():
            if len(keyword) <= 3 and all(ord(c) < 128 for c in keyword):
                # 纯英文短关键词：用 \\b 避免子串误报（如 "fix" 匹配 "prefix"）
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                self._short_kw_patterns[keyword] = (pattern, topic)

        # 停用词集合（过滤无意义匹配）
        self._stopwords: set[str] = {
            "的", "了", "是", "在", "有", "和", "就", "不", "也", "都",
            "吗", "呢", "吧", "啊", "哦", "嗯", "这", "那", "个", "我",
            "你", "他", "她", "它", "们", "很", "会", "能", "要", "让",
        }

    def _get_topic_weight(self, topic: str) -> float:
        """
        获取话题权重

        权重体系：游戏名(3.0) > 技术词(2.0) > 工作流词(1.0)
        """
        if topic in GAME_KEYWORDS:
            return 3.0
        if topic in TECH_KEYWORDS:
            return 2.0
        return 1.0

    def extract_topics(self, text: str) -> list[str]:
        """
        从文本中提取话题列表（带权重排序）

        优化版：
        - 停用词过滤：排除"的了是在不"等无意义匹配
        - 权重体系：游戏名(3.0) > 技术词(2.0) > 通用词(1.0)
        - 按相关度排序：权重高的话题排在前面

        Args:
            text: 输入文本

        Returns:
            按相关度排序的话题列表
        """
        if not text:
            return []

        text_lower = text.lower()
        topic_scores: dict[str, float] = {}

        for keyword, topic in self._keyword_map.items():
            # 停用词过滤
            if keyword in self._stopwords:
                continue

            matched = False
            if keyword in self._short_kw_patterns:
                # W5: 短关键词用正则匹配
                pattern, topic_name = self._short_kw_patterns[keyword]
                if pattern.search(text_lower):
                    matched = True
            else:
                # 长关键词直接子串匹配
                if keyword in text_lower:
                    matched = True

            if matched:
                weight = self._get_topic_weight(topic)
                if topic not in topic_scores:
                    topic_scores[topic] = 0.0
                topic_scores[topic] += weight

        # 按分数降序排序
        sorted_topics = sorted(topic_scores.keys(), key=lambda t: topic_scores[t], reverse=True)
        return sorted_topics

    def extract_game_topics(self, text: str) -> list[str]:
        """
        只提取游戏相关话题

        Args:
            text: 输入文本

        Returns:
            游戏话题列表
        """
        if not text:
            return []

        text_lower = text.lower()
        found_games: set[str] = set()

        for game_name, keywords in GAME_KEYWORDS.items():
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in self._short_kw_patterns:
                    pattern, _ = self._short_kw_patterns[kw_lower]
                    if pattern.search(text_lower):
                        found_games.add(game_name)
                        break
                else:
                    if kw_lower in text_lower:
                        found_games.add(game_name)
                        break

        return sorted(found_games)

    def extract_tech_topics(self, text: str) -> list[str]:
        """
        只提取技术相关话题

        Args:
            text: 输入文本

        Returns:
            技术话题列表
        """
        if not text:
            return []

        text_lower = text.lower()
        found_techs: set[str] = set()

        for category, keywords in TECH_KEYWORDS.items():
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower in self._short_kw_patterns:
                    pattern, _ = self._short_kw_patterns[kw_lower]
                    if pattern.search(text_lower):
                        found_techs.add(category)
                        break
                else:
                    if kw_lower in text_lower:
                        found_techs.add(category)
                        break

        return sorted(found_techs)

    def get_all_topics(self) -> dict[str, list[str]]:
        """获取所有已注册的话题及其关键词"""
        topic_keywords: dict[str, list[str]] = {}
        for kw, topic in self._keyword_map.items():
            if topic not in topic_keywords:
                topic_keywords[topic] = []
            topic_keywords[topic].append(kw)
        return topic_keywords


# 全局实例
_extractor = TopicExtractor()


def extract_topics(text: str) -> list[str]:
    """便捷函数：提取话题"""
    return _extractor.extract_topics(text)
