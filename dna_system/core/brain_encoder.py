"""
🧠 联想大脑 — DNA信号提取器

核心思想：DNA是指纹，不是标签。
从文本固有结构提取信号，不依赖关键词表，确定性输出。

5链DNA：
  domain  — 领域信号（英文小写词、中文领域词）
  intent  — 意图信号（动作词、疑问词）
  entity  — 实体信号（中文块、英文专有名词）
  pattern — 模式信号（数字、标点、行数）
  context — 上下文信号（预留）

性能：0.02-0.06ms/次，零Token消耗
"""

from __future__ import annotations
import re
import math
import numpy as np
from typing import Dict, List, Set


# ════════════════════════════════════════════════════════════
# 词形归并（轻量级英文stemmer）
# ════════════════════════════════════════════════════════════

# 按后缀长度排序（长优先），避免部分匹配
_STEM_RULES = [
    ("ingly", 5),   # increasingly → increas
    ("iting", 5),   # exciting → excit
    ("ing", 3),     # running → runn
    ("ied", 3),     # applied → appl
    ("ed", 2),      # graduated → graduat
    ("ly", 2),      # carefully → careful
    ("es", 2),      # boxes → box
    ("er", 2),      # teacher → teach
    ("or", 2),      # actor → act
    ("s", 1),       # degrees → degree
]


def _stem(word: str) -> str:
    """轻量级英文词形归并"""
    if len(word) <= 3:
        return word
    for suffix, cut in _STEM_RULES:
        if len(word) > cut + 2 and word.endswith(suffix):
            return word[:-cut]
    return word


# ════════════════════════════════════════════════════════════
# Token提取（字符级扫描）
# ════════════════════════════════════════════════════════════

def extract_tokens(text: str) -> List[str]:
    """
    从文本中提取所有有意义信号。
    使用脚本隔离法逐字符扫描，不做分类，不丢弃。

    规则：
    - 连续中文字符 → 中文块
    - 连续英文字母 → 英文词（小写+词形归并）
    - 连续数字 → 数字串
    - 其他 → 单字符保留
    """
    if not text:
        return []

    tokens: List[str] = []
    i = 0
    while i < len(text):
        ch = text[i]
        # 跳过空白
        if ch.isspace():
            i += 1
            continue
        # 中文块
        if "一" <= ch <= "鿿":
            j = i
            while j < len(text) and "一" <= text[j] <= "鿿":
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        # 英文词
        if ch.isascii() and ch.isalpha():
            j = i
            while j < len(text) and text[j].isascii() and text[j].isalpha():
                j += 1
            tokens.append(_stem(text[i:j].lower()))
            i = j
            continue
        # 数字串
        if ch.isascii() and ch.isdigit():
            j = i
            while j < len(text) and text[j].isascii() and text[j].isdigit():
                j += 1
            tokens.append(text[i:j])
            i = j
            continue
        # 其他字符
        tokens.append(ch)
        i += 1
    return tokens


# ════════════════════════════════════════════════════════════
# DNA信号提取
# ════════════════════════════════════════════════════════════

# 意图信号词（辅助分类，不是关键词表）
_INTENT_HINTS = {
    # 中文动作词
    "查", "找", "看", "搜", "搜索", "查一下",
    "创", "写", "建", "改", "修", "删", "加", "添加",
    "部署", "安装", "配置", "设置",
    "控制", "管理", "优化", "调整",
    "解释", "说明", "告诉", "教", "推荐", "建议",
    # 英文动作词
    "fix", "build", "create", "deploy", "install", "config",
    "search", "find", "check", "query", "update", "delete",
}

# 虚词（过滤用）
_FUNC_WORDS = {
    "the", "a", "an", "is", "are", "was", "were",
    "how", "why", "what", "when", "where", "who",
    "on", "in", "at", "to", "for", "of", "with", "by",
    "的", "了", "是", "在", "有", "和", "就", "不", "也", "都",
    "吗", "呢", "吧", "啊", "哦", "嗯",
}


def extract_dna(text: str) -> Dict[str, List[str]]:
    """
    信号留存式DNA提取。
    不查表、不分类、不丢弃。提取所有信号，按启发式分链。

    返回：{"domain": [...], "intent": [...], "entity": [...], "pattern": [...], "context": [...]}
    """
    if not text:
        return {"domain": [], "intent": [], "entity": [], "pattern": [], "context": []}

    tokens = extract_tokens(text)
    if not tokens:
        return {"domain": [], "intent": [], "entity": [], "pattern": [], "context": []}

    # 分链收集
    domain_signals: Set[str] = set()
    intent_signals: Set[str] = set()
    entity_signals: Set[str] = set()
    pattern_signals: Set[str] = set()

    for token in tokens:
        tl = token.lower().strip()
        if not tl or tl in _FUNC_WORDS:
            continue

        # 英文词 → entity链（专有名词）或 domain链（普通词）
        if re.match(r'^[a-zA-Z]', tl):
            if len(tl) >= 3:
                # 大写开头 → entity（专有名词）
                if token[0].isupper():
                    entity_signals.add(tl)
                else:
                    domain_signals.add(tl)
            continue

        # 中文词 → 检查是否意图词
        is_intent = False
        for hint in _INTENT_HINTS:
            if hint in tl:
                intent_signals.add(tl)
                is_intent = True
                break

        # 非意图词 → domain链
        if not is_intent:
            domain_signals.add(tl)

    # 模式信号
    if "?" in text or "？" in text:
        pattern_signals.add("question")
    if "!" in text or "！" in text:
        pattern_signals.add("exclamation")
    if len(text) > 200:
        pattern_signals.add("long")
    if text.count("\n") > 3:
        pattern_signals.add("multi_line")

    # 数字提取
    for num in re.findall(r'\d+', text):
        pattern_signals.add(f"num:{num[:4]}")

    return {
        "domain": sorted(domain_signals),
        "intent": sorted(intent_signals),
        "entity": sorted(entity_signals),
        "pattern": sorted(pattern_signals),
        "context": [],  # 预留
    }


# ════════════════════════════════════════════════════════════
# 游戏工坊专用：游戏DNA编码
# ════════════════════════════════════════════════════════════

# 游戏名称映射
_GAME_ALIASES = {
    "暗影幸存者": ["割草", "survivor", "幸存者", "暗影"],
    "四川麻将": ["麻将", "mahjong", "血战", "川麻"],
    "迷雾之塔": ["迷雾之塔", "misty", "爬塔", "迷雾"],
    "塔防保卫战": ["塔防", "td", "塔防保卫战", "tower"],
    "贪吃蛇大作战": ["贪吃蛇", "snake", "蛇"],
    "修仙": ["修仙", "xian", "练气", "筑基"],
    "苍穹射击": ["苍穹射击", "shooter", "射击"],
    "象棋翻翻乐": ["象棋翻翻乐", "chess-flip", "翻翻乐"],
    "像素冒险": ["平台跳跃", "platformer", "像素冒险"],
    "火柴人格斗": ["火柴人格斗", "fighter", "格斗"],
}

# 系统关键词
_SYSTEM_KEYWORDS = {
    "渲染": ["渲染", "draw", "sprite", "图片", "显示", "画", "图层", "粒子", "particle"],
    "碰撞": ["碰撞", "collision", "判定", "hitbox", "hit", "穿透", "重叠"],
    "逻辑": ["逻辑", "计算", "规则", "算法", "判断", "条件", "状态机"],
    "UI": ["UI", "ui", "界面", "按钮", "弹窗", "菜单", "面板", "panel", "btn"],
    "音频": ["音频", "声音", "音效", "音乐", "sound", "audio", "sfx"],
    "物理": ["物理", "physics", "重力", "跳跃", "速度", "加速度"],
}


def identify_game(text: str) -> str:
    """从文本中识别游戏名称"""
    text_lower = text.lower()
    for game, aliases in _GAME_ALIASES.items():
        for alias in aliases:
            if alias.lower() in text_lower:
                return game
    return ""


def identify_system(text: str) -> str:
    """从文本中识别涉及的系统"""
    text_lower = text.lower()
    for system, keywords in _SYSTEM_KEYWORDS.items():
        for kw in keywords:
            if kw.lower() in text_lower:
                return system
    return ""


def encode_game_memory(text: str) -> Dict[str, List[str]]:
    """
    为游戏工坊记忆编码DNA。
    在标准DNA基础上，增加游戏和系统识别。
    """
    dna = extract_dna(text)

    # 识别游戏
    game = identify_game(text)
    if game:
        dna["entity"].append(f"game:{game}")

    # 识别系统
    system = identify_system(text)
    if system:
        dna["domain"].append(f"system:{system}")

    # 去重排序
    for key in dna:
        dna[key] = sorted(set(dna[key]))

    return dna


# ════════════════════════════════════════════════════════════
# TF-IDF 向量编码器（语义聚类专用）
# ════════════════════════════════════════════════════════════

class TFIDFEncoder:
    """
    TF-IDF 向量编码器

    基于 extract_tokens 分词器，使用 hashing trick 生成固定维度的 TF-IDF 向量。
    IDF 从记忆池语料库中一次性计算，后续复用。

    性能：编码 ~0.01ms/次，零Token消耗
    """

    def __init__(self, dim: int = 128):
        self.dim = dim
        self.idf: Dict[str, float] = {}
        self._built = False

    def build_idf(self, texts: List[str]):
        """
        从语料库计算 IDF 权重（启动时一次性计算）

        IDF(token) = log(N / (1 + df))
        其中 N = 文档总数，df = 包含该 token 的文档数

        Args:
            texts: 语料库文本列表（每条DNA的文本内容）
        """
        n_docs = len(texts)
        if n_docs == 0:
            return

        doc_freq: Dict[str, int] = {}
        for text in texts:
            tokens = set(extract_tokens(text))
            for token in tokens:
                doc_freq[token] = doc_freq.get(token, 0) + 1

        self.idf = {token: math.log(n_docs / (1 + df)) for token, df in doc_freq.items()}
        self._built = True

    def encode(self, text: str) -> np.ndarray:
        """
        将文本编码为 TF-IDF 向量（L2归一化）

        使用 hashing trick：将 token 哈希到 dim 个桶，累加 TF-IDF 权重。

        Args:
            text: 输入文本

        Returns:
            dim维 numpy 向量（L2归一化）
        """
        vec = np.zeros(self.dim, dtype=np.float32)
        if not text:
            return vec

        tokens = extract_tokens(text)
        if not tokens:
            return vec

        # TF
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        total = len(tokens)

        # Hashing trick: token -> bucket, 累加 TF-IDF 权重
        for token, count in tf.items():
            weight = (count / total) * self.idf.get(token, 1.0)
            bucket = hash(token) % self.dim
            vec[bucket] += weight

        # L2归一化
        norm = np.linalg.norm(vec)
        if norm > 1e-10:
            vec /= norm

        return vec

    def encode_tfidf(self, text: str, corpus: List[str] = None) -> np.ndarray:
        """
        便捷方法：编码文本（如果 corpus 不为空且 IDF 未构建则先构建）

        Args:
            text: 输入文本
            corpus: 语料库（可选，仅首次调用时需要）

        Returns:
            dim维 numpy 向量
        """
        if corpus and not self._built:
            self.build_idf(corpus)
        return self.encode(text)


# ════════════════════════════════════════════════════════════
# 测试/调试
# ════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 测试用例
    test_cases = [
        "帮我修复贪吃蛇碰撞检测",
        "塔防保卫战的炮塔升级逻辑有Bug",
        "deploy database timeout set 30 seconds",
        "修仙游戏的渡劫系统怎么实现？",
    ]

    for text in test_cases:
        print(f"\n输入: {text}")
        dna = extract_dna(text)
        print(f"DNA: {dna}")
        print(f"游戏: {identify_game(text)}")
        print(f"系统: {identify_system(text)}")
