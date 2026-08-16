"""
智能标签系统 —— 从内容中自动提取有意义的标签
替代原来的 para_X 和文件名标签
"""
import re
from collections import Counter


# 游戏关键词映射
GAME_KEYWORDS = {
    "暗影幸存者": ["割草", "暗影幸存者", "survivor", "弹幕", "怪物", "波次", "经验", "升级", "素材工厂", "hero", "英雄"],
    "四川麻将": ["麻将", "mahjong", "血战", "川麻", "胡牌", "碰杠", "听牌", "番型", "换三张"],
    "贪吃蛇": ["贪吃蛇", "snake", "蛇", "NPC", "吞噬", "食物", "BattleSnake", "转弯帧"],
    "塔防保卫战": ["塔防", "td", "炮塔", "敌人", "波次", "路径", "水晶塔", "冰塔", "火塔", "td-v2"],
    "迷雾之塔": ["迷雾", "misty", "tower", "爬塔", "楼层", "roguelike", "房间", "魔塔"],
    "修仙": ["修仙", "xian", "练气", "筑基", "金丹", "渡劫", "功法"],
    "苍穹射击": ["苍穹", "射击", "shooter", "太空", "子弹"],
    "象棋翻翻乐": ["象棋", "翻翻乐", "chess", "flip", "暗棋"],
    "像素冒险": ["像素", "平台跳跃", "platformer", "跳跃"],
    "火柴人格斗": ["火柴人", "fighter", "格斗"],
}

# 技术关键词
TECH_KEYWORDS = {
    "Bug修复": ["fix", "bug", "修复", "崩溃", "报错", "错误", "异常", "死循环", "crash"],
    "性能优化": ["性能", "优化", "performance", "速度", "帧率", "FPS", "内存"],
    "架构设计": ["架构", "设计", "重构", "refactor", "模式", "系统", "模块"],
    "UI/UX": ["界面", "UI", "UX", "按钮", "菜单", "动画", "特效", "视觉"],
    "音频": ["音效", "音乐", "audio", "sound", "BGM"],
    "部署发布": ["部署", "deploy", "同步", "git", "发布", "上线"],
    "素材资源": ["素材", "sprite", "贴图", "图片", "资源", "1-bit-pack"],
    "数据结构": ["数组", "对象", "Map", "Set", "队列", "栈", "树"],
    "Canvas渲染": ["Canvas", "渲染", "draw", "paint", "像素", "ctx"],
    "游戏循环": ["游戏循环", "requestAnimationFrame", "update", "render", "tick"],
}

# 工作流关键词
WORKFLOW_KEYWORDS = {
    "需求分析": ["需求", "分析", "调研", "确认", "讨论"],
    "测试验证": ["测试", "验证", "test", "check", "确认"],
    "代码审查": ["审查", "review", "审计", "检查"],
    "文档记录": ["文档", "记录", "日志", "log", "README"],
    "经验教训": ["教训", "经验", "踩坑", "避坑", "总结"],
}


class SmartTagger:
    """智能标签提取器"""

    def __init__(self):
        self.all_keywords = {}
        # 合并所有关键词
        for category, keywords in {**GAME_KEYWORDS, **TECH_KEYWORDS, **WORKFLOW_KEYWORDS}.items():
            for kw in keywords:
                self.all_keywords[kw.lower()] = category

    def extract_tags(self, text: str, existing_tags: list[str] = None) -> list[str]:
        """
        从文本中提取有意义的标签
        返回: 去重后的标签列表（最多10个）
        """
        if not text:
            return []

        text_lower = text.lower()
        found_tags = set()

        # 1. 关键词匹配
        for keyword, category in self.all_keywords.items():
            if keyword.lower() in text_lower:
                found_tags.add(category)

        # 2. 提取文件名标签（如果有路径）
        file_match = re.search(r'[/\\]([^/\\]+\.(html|js|py|md|json))', text)
        if file_match:
            filename = file_match.group(1)
            # 移除扩展名作为标签
            name_without_ext = filename.rsplit('.', 1)[0]
            if len(name_without_ext) > 2:
                found_tags.add(name_without_ext)

        # 3. 提取中文短语（2-4字）
        cn_phrases = re.findall(r'[一-鿿]{2,4}', text)
        # 只保留出现频率高的短语
        phrase_counts = Counter(cn_phrases)
        for phrase, count in phrase_counts.most_common(5):
            if count >= 2 and len(phrase) >= 2:
                found_tags.add(phrase)

        # 4. 保留有意义的现有标签
        if existing_tags:
            for tag in existing_tags:
                # 过滤无意义标签
                if self._is_meaningful_tag(tag):
                    found_tags.add(tag)

        # 5. 限制标签数量
        tags_list = list(found_tags)[:10]

        return tags_list

    def _is_meaningful_tag(self, tag: str) -> bool:
        """判断标签是否有意义"""
        # 过滤无意义标签
        meaningless_patterns = [
            r'^para_\d+$',  # para_数字
            r'^ȫ.*$',      # 乱码
            r'^\d+$',       # 纯数字
            r'^.{1}$',      # 单字符
            r'^test',       # test开头
            r'^temp',       # temp开头
        ]
        for pattern in meaningless_patterns:
            if re.match(pattern, tag):
                return False
        return True

    def clean_existing_tags(self, tags: list[str]) -> list[str]:
        """清理现有标签列表"""
        return [t for t in tags if self._is_meaningful_tag(t)]


# 全局实例
tagger = SmartTagger()
