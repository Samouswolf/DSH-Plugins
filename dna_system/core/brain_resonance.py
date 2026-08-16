"""
🧠 联想大脑 — 三级坐标共振匹配

核心思想：匹配是坐标共振，不是语义翻译。
字符级信号提取 + 三级共振打分 + TF-IDF增强。

三级共振：
  Layer 1 字符级 (x0.3) — 单字符重叠 Jaccard
  Layer 2 子串级 (x0.3) — 2字符bigram重叠
  Layer 3 精确级 (x0.4) — 完整token重叠（可IDF加权）

性能：0.08ms/10实体，零Token消耗
"""

from __future__ import annotations
import math
from typing import Dict, List, Optional, Tuple
from .brain_encoder import extract_dna, extract_tokens


# ════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════

def _flatten(dna: Dict[str, List[str]]) -> List[str]:
    """展平4链DNA为单层token列表"""
    result: List[str] = []
    for vals in dna.values():
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, str) and v:
                    result.append(v)
    return result


def _flatten_to_set(dna: Dict[str, List[str]]) -> Tuple[set, set, set]:
    """展平DNA为字符集、bigram集、token集"""
    all_tokens = _flatten(dna)

    # 字符集
    chars = set("".join(all_tokens))

    # Bigram集
    bigrams = set()
    for token in all_tokens:
        for i in range(len(token) - 1):
            bigrams.add(token[i:i + 2])

    # Token集
    token_set = set(all_tokens)

    return chars, bigrams, token_set


# ════════════════════════════════════════════════════════════
# TF-IDF计算
# ════════════════════════════════════════════════════════════

def compute_idf(entities: List[Dict]) -> Dict[str, float]:
    """
    计算实体池中所有token的IDF权重。

    IDF(t) = log(N / df(t)) + 1
    N = 总实体数, df(t) = 包含token t的实体数。

    出现在所有实体中的token权重=1.0（无增强）。
    出现在少数实体中的token权重>>1.0（强增强）。
    """
    N = len(entities)
    if N == 0:
        return {}

    # 文档频率
    df: Dict[str, int] = {}
    for ent in entities:
        text = ent.get("text", "")
        if not text:
            continue
        tokens = set(extract_tokens(text))
        for t in tokens:
            df[t] = df.get(t, 0) + 1

    # 计算IDF
    idf: Dict[str, float] = {}
    for token, doc_count in df.items():
        idf[token] = math.log(N / max(doc_count, 1)) + 1.0

    return idf


# ════════════════════════════════════════════════════════════
# 滑动窗口分片（长文本处理）
# ════════════════════════════════════════════════════════════

_CHUNK_SIZE = 200    # 每片最大字符数
_CHUNK_OVERLAP = 50  # 片间重叠字符数


def _chunk_text(text: str) -> List[str]:
    """
    长文本切分为重叠短片段。
    优先在 | 、换行、空格处分片，保持语义完整性。
    解决长文本中关键信息被无关内容稀释的问题。
    """
    if len(text) <= _CHUNK_SIZE:
        return [text]

    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(start + _CHUNK_SIZE, len(text))

        # 尽量在边界切
        if end < len(text):
            # 优先在 | 处切断
            sep_pos = text.rfind(" | ", start + _CHUNK_SIZE // 2, end)
            if sep_pos >= start + _CHUNK_SIZE // 2:
                end = sep_pos
            else:
                # 其次换行
                nl_pos = text.rfind("\n", start + _CHUNK_SIZE // 2, end)
                if nl_pos >= start + _CHUNK_SIZE // 2:
                    end = nl_pos

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # 确保总在前进
        next_start = end - _CHUNK_OVERLAP
        if next_start <= start:
            next_start = end
        start = next_start

        # 最后一段全部纳入
        if len(text) - start <= _CHUNK_SIZE and start < len(text):
            chunks.append(text[start:].strip())
            break

    return chunks


# ════════════════════════════════════════════════════════════
# 三级坐标共振打分
# ════════════════════════════════════════════════════════════

def coordinate_resonance(
    query_dna: Dict[str, List[str]],
    entity_dna: Dict[str, List[str]],
    idf_weights: Optional[Dict[str, float]] = None,
) -> float:
    """
    三级坐标共振打分。

    Layer 1 字符级 (x0.3) — 单字符重叠 Jaccard
    Layer 2 子串级 (x0.3) — 2字符bigram重叠
    Layer 3 精确级 (x0.4) — 完整token重叠（可IDF加权）

    Args:
        query_dna: 查询DNA信号
        entity_dna: 实体DNA信号
        idf_weights: 可选的IDF权重

    Returns:
        分数 0.0~1.0
    """
    score = 0.0

    # 展平DNA
    q_chars, q_bigrams, q_tokens = _flatten_to_set(query_dna)
    e_chars, e_bigrams, e_tokens = _flatten_to_set(entity_dna)

    if not q_chars or not e_chars:
        return 0.0

    # Layer 1: 字符级 (x0.3)
    common_chars = q_chars & e_chars
    union_chars = q_chars | e_chars
    if union_chars:
        score += len(common_chars) / len(union_chars) * 0.3

    # Layer 2: 子串级 (x0.3)
    if q_bigrams and e_bigrams:
        common_bigrams = q_bigrams & e_bigrams
        union_bigrams = q_bigrams | e_bigrams
        if union_bigrams:
            score += len(common_bigrams) / len(union_bigrams) * 0.3

    # Layer 3: 精确级 (x0.4)
    if q_tokens and e_tokens:
        common_tokens = q_tokens & e_tokens
        if idf_weights:
            # IDF加权：特异性词权重更高
            weighted_common = sum(idf_weights.get(t, 1.0) for t in common_tokens)
            weighted_union = sum(idf_weights.get(t, 1.0) for t in (q_tokens | e_tokens))
            if weighted_union > 0:
                score += (weighted_common / weighted_union) * 0.4
        else:
            # 普通Jaccard
            union_tokens = q_tokens | e_tokens
            if union_tokens:
                score += len(common_tokens) / len(union_tokens) * 0.4

    return round(score, 4)


# ════════════════════════════════════════════════════════════
# 磁吸匹配
# ════════════════════════════════════════════════════════════

def magnetic_resonance(
    query_text: str,
    entities: List[Dict],
    top_k: int = 5,
    idf_weights: Optional[Dict[str, float]] = None,
    enable_chunking: bool = True,
) -> List[Dict]:
    """
    磁吸匹配：基于坐标共振，非标签重叠。

    用查询原始信号 vs 实体DNA坐标计算共振度。
    不依赖关键词表，不依赖查询DNA分类。

    Args:
        query_text: 查询文本
        entities: 实体池
        top_k: 最大返回数
        idf_weights: 可选IDF权重
        enable_chunking: 启用长文本滑动窗口分片

    Returns:
        带 _score 的实体列表，按相关性排序
    """
    if not query_text or not entities:
        return []

    # 提取查询DNA
    query_dna = extract_dna(query_text)
    if not any(query_dna.values()):
        return []

    scored: List[Tuple[float, Dict]] = []

    for ent in entities:
        text = ent.get("text", "")
        if not text:
            continue

        # 长文本分片处理
        if enable_chunking and len(text) > _CHUNK_SIZE * 1.2:
            chunks = _chunk_text(text)
            best_score = 0.0
            for chunk in chunks:
                ent_dna = extract_dna(chunk)
                s = coordinate_resonance(query_dna, ent_dna, idf_weights)
                if s > best_score:
                    best_score = s
            if best_score > 0.01:
                scored.append((best_score, ent))
        else:
            # 短文本直接打分
            ent_dna = extract_dna(text)
            s = coordinate_resonance(query_dna, ent_dna, idf_weights)
            if s > 0.01:
                scored.append((s, ent))

    # 排序取top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    return [dict(e, _score=s) for s, e in scored[:top_k]]


# ════════════════════════════════════════════════════════════
# 文字回退（兜底匹配）
# ════════════════════════════════════════════════════════════

def text_fallback(
    query: str,
    entities: List[Dict],
    top_k: int = 3,
) -> List[Dict]:
    """
    文字回退：句级重叠兜底。
    当磁吸匹配无结果时使用。
    """
    if not entities:
        return []

    q_lower = query.lower().strip()
    if not q_lower:
        return []

    scored: List[Tuple[Dict, float]] = []
    for e in entities:
        t = e.get("text", "").lower()
        if not t:
            continue

        # 查询词长度覆盖度
        score = len([w for w in q_lower.split() if len(w) > 1 and w in t])

        # 中文子串
        if len(q_lower.split()) <= 1:
            if q_lower in t:
                score = len(q_lower) / max(len(t), 1) * 10
            for ch in q_lower:
                if ch in t and ch not in "的是的不啊了呢吗":
                    score += 0.5

        if score > 0:
            scored.append((e, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return [{**dict(e), "_score": s} for e, s in scored[:top_k]]

