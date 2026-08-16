"""
DNA 智能层 v1.0 — 游戏工坊 AI 副驾驶
======================================

不做通用记忆系统，专为记忆工作区的创作/开发场景设计。

四个核心能力：
1. BugClassifier     — 按类型/严重度/游戏自动分类Bug，跨游戏匹配相似模式
2. ImpactPredictor   — 改代码前预测影响范围，基于历史踩坑记录
3. DecisionMemory    — 不只记"做了什么"，更记"为什么选方案A不选B"
4. SmartContext      — 按当前任务智能过滤，不塞垃圾上下文

设计原则：
- 每个分析结果 ≤ 3行输出，不废话
- 只输出可执行的建议，不输出"可能"、"建议关注"之类的废话
- 对游戏开发者有用，不是对AI研究者有用
"""

import json
import re
import os
from datetime import datetime
from collections import Counter, defaultdict
from typing import Optional

from .dna import DNA, DNAType


# ===== 游戏/系统识别 =====

GAME_PATTERNS = {
    "暗影幸存者": {
        "files": ["割草.html", "game.html", "survivor"],
        "systems": {
            "渲染": ["drawSprite", "drawPlayer", "sprIdx", "sprite", "canvas", "ctx.draw", "粒子", "particle"],
            "碰撞": ["collision", "碰撞", "hitbox", "overlap", "distance", "radius"],
            "升级": ["levelUp", "upgrade", "升级", "exp", "经验", "技能树"],
            "装备": ["equip", "装备", "loot", "掉落", "rarity", "品质"],
            "怪物": ["monster", "怪物", "spawn", "波次", "wave", "boss"],
        },
    },
    "四川麻将": {
        "files": ["麻将.html", "mahjong.html"],
        "systems": {
            "渲染": ["drawTile", "sprite", "牌面", "canvas", "ctx.draw", "纹理"],
            "逻辑": ["胡牌", "碰", "杠", "吃", "听牌", "番型", "计分", "血战"],
            "UI": ["按钮", "panel", "btn", "overlay", "界面", "弹窗"],
            "音频": ["sound", "sfx", "音频", "配音", "语音", "voice"],
        },
    },
    "迷雾之塔": {
        "files": ["迷雾之塔.html", "misty-tower.html"],
        "systems": {
            "渲染": ["drawTile", "floor", "房间", "canvas", "迷雾", "fog"],
            "逻辑": ["楼层", "探索", "钥匙", "门", "怪物", "战斗", "道具"],
            "地图": ["FLOORS", "makeFloor", "地图数据", "格子"],
        },
    },
    "塔防保卫战": {
        "files": ["塔防保卫战.html", "td.html", "塔防保卫战-v2.html", "td-v2.html"],
        "systems": {
            "渲染": ["drawSprite", "canvas", "炮弹", "bullet", "特效"],
            "逻辑": ["炮塔", "tower", "路径", "path", "波次", "wave", "敌人", "enemy"],
            "UI": ["panel", "btn", "升级", "upgrade", "出售"],
        },
    },
    "贪吃蛇大作战": {
        "files": ["贪吃蛇大作战.html", "snake.html"],
        "systems": {
            "渲染": ["drawSnake", "drawFood", "canvas", "grid", "格子"],
            "碰撞": ["collision", "碰撞", "边界", "boundary", "自碰", "撞墙"],
            "逻辑": ["食物", "food", "成长", "grow", "速度", "speed", "AI"],
        },
    },
    "修仙": {
        "files": ["修仙.html", "xian.html"],
        "systems": {
            "逻辑": ["练气", "筑基", "金丹", "元婴", "渡劫", "功法", "修炼"],
        },
    },
    "苍穹射击": {
        "files": ["苍穹射击.html", "shooter.html"],
        "systems": {
            "渲染": ["bullet", "射击", "粒子", "explosion"],
            "逻辑": ["敌机", "enemy", "升级", "powerup"],
        },
    },
    "象棋翻翻乐": {
        "files": ["象棋翻翻乐.html", "chess-flip.html"],
        "systems": {
            "逻辑": ["棋子", "翻牌", "chess", "翻转"],
        },
    },
    "像素冒险": {
        "files": ["平台跳跃.html", "platformer.html"],
        "systems": {
            "逻辑": ["跳跃", "平台", "物理", "physics", "重力"],
        },
    },
    "火柴人格斗": {
        "files": ["火柴人格斗.html", "fighter.html"],
        "systems": {
            "逻辑": ["格斗", "fighter", "连招", "combo", "打击"],
        },
    },
}


# ===== Bug分类关键词 =====

BUG_CATEGORIES = {
    "渲染异常": {
        "keywords": ["不显示", "显示异常", "花屏", "闪烁", "透明", "图层", "绘制", "渲染",
                    "draw", "sprite", "图片不", "消失", "黑色", "白屏", "canvas"],
        "severity_boost": 0,
    },
    "碰撞/判定": {
        "keywords": ["碰撞", "collision", "穿透", "重叠", "判定", "hitbox", "穿墙",
                    "打不中", "打不到", "miss", "偏移"],
        "severity_boost": 1,  # 核心玩法Bug，更严重
    },
    "逻辑错误": {
        "keywords": ["逻辑", "计算错误", "数值不对", "分数", "金币", "计数", "回合",
                    "条件判断", "状态机", "死循环", "卡死"],
        "severity_boost": 1,
    },
    "UI/交互": {
        "keywords": ["按钮", "点击", "界面", "UI", "弹窗", "菜单", "面板", "panel",
                    "btn", "overlay", "无法操作", "点不了", "进不去"],
        "severity_boost": 0,
    },
    "音频": {
        "keywords": ["声音", "音频", "音效", "音乐", "sound", "audio", "sfx", "voice",
                    "没声音", "杂音", "延迟"],
        "severity_boost": -1,  # 不影响可玩性
    },
    "性能/卡顿": {
        "keywords": ["卡顿", "掉帧", "性能", "内存", "泄漏", "lag", "fps", "慢",
                    "优化", "performance"],
        "severity_boost": 0,
    },
    "兼容性": {
        "keywords": ["浏览器", "手机", "移动端", "safari", "chrome", "firefox",
                    "屏幕", "分辨率", "缩放", "响应式"],
        "severity_boost": 0,
    },
}


class BugClassifier:
    """Bug分类器：按类型/严重度/游戏分类，支持跨游戏匹配"""

    def __init__(self, system=None):
        self.system = system

    def set_system(self, system):
        self.system = system

    def classify(self, text: str) -> dict:
        """对一段文本进行Bug分类"""
        text_lower = text.lower()
        categories = []
        for cat_name, config in BUG_CATEGORIES.items():
            score = sum(1 for kw in config["keywords"] if kw.lower() in text_lower)
            if score > 0:
                categories.append({
                    "category": cat_name,
                    "score": score + config["severity_boost"],
                })
        categories.sort(key=lambda x: x["score"], reverse=True)
        return {
            "primary": categories[0]["category"] if categories else "未分类",
            "all": [c["category"] for c in categories],
            "severity": self._assess_severity(text_lower, categories),
        }

    def _assess_severity(self, text: str, categories: list) -> str:
        """评估严重度: critical / high / medium / low"""
        critical_words = ["崩溃", "闪退", "白屏", "进不去", "致命", "数据丢失", "死循环"]
        high_words = ["不显示", "无法操作", "点不了", "卡死", "打不中", "穿透"]

        if any(w in text for w in critical_words):
            return "critical"
        if any(w in text for w in high_words):
            return "high"
        total_score = sum(c["score"] for c in categories)
        if total_score >= 3:
            return "medium"
        return "low"

    def classify_dnas(self, dnas: list[DNA] = None) -> list[dict]:
        """批量分类DNA条目，只处理Bug相关的"""
        if dnas is None and self.system:
            dnas = self.system.pool
        elif dnas is None:
            return []

        bug_entries = []
        for dna in dnas:
            text = self._extract_text(dna)
            if not self._is_bug_related(text):
                continue
            classification = self.classify(text)
            game = self._identify_game(text)
            bug_entries.append({
                "dna_id": dna.id,
                "game": game,
                "category": classification["primary"],
                "severity": classification["severity"],
                "preview": text[:100],
                "created_at": dna.created_at,
            })
        return bug_entries

    def cross_game_match(self, bug_text: str, dnas: list[DNA] = None) -> list[dict]:
        """
        跨游戏Bug匹配：给定一个Bug描述，在所有游戏中找类似模式
        """
        if dnas is None and self.system:
            dnas = self.system.pool
        elif dnas is None:
            return []

        classification = self.classify(bug_text)
        target_game = self._identify_game(bug_text)

        matches = []
        for dna in dnas:
            text = self._extract_text(dna)
            if not self._is_bug_related(text):
                continue
            dna_game = self._identify_game(text)
            # 跨游戏：不同游戏，同类Bug
            if dna_game and dna_game != target_game:
                dna_class = self.classify(text)
                if dna_class["primary"] == classification["primary"]:
                    matches.append({
                        "dna_id": dna.id,
                        "game": dna_game,
                        "preview": text[:100],
                        "severity": dna_class["severity"],
                    })
        return matches[:5]

    def _is_bug_related(self, text: str) -> bool:
        text_lower = text.lower()
        bug_signals = ["bug", "修复", "fix", "异常", "报错", "崩溃", "问题", "不显示",
                       "error", "fail", "失败", "闪退", "卡死"]
        return any(s in text_lower for s in bug_signals)

    def _identify_game(self, text: str) -> Optional[str]:
        text_lower = text.lower()
        for game, config in GAME_PATTERNS.items():
            for f in config["files"]:
                if f.lower() in text_lower:
                    return game
        # 关键词匹配
        game_keywords = {
            "暗影幸存者": ["割草", "survivor", "素材工厂"],
            "四川麻将": ["麻将", "mahjong", "血战", "川麻"],
            "迷雾之塔": ["迷雾之塔", "misty-tower", "爬塔"],
            "塔防保卫战": ["塔防", "td-v2", "td"],
            "贪吃蛇大作战": ["贪吃蛇", "snake"],
            "修仙": ["修仙", "xian", "练气"],
            "苍穹射击": ["苍穹射击", "shooter"],
            "象棋翻翻乐": ["象棋翻翻乐", "chess-flip"],
            "像素冒险": ["平台跳跃", "platformer"],
            "火柴人格斗": ["火柴人格斗", "fighter"],
        }
        for game, kws in game_keywords.items():
            if any(kw in text_lower for kw in kws):
                return game
        return None

    def _extract_text(self, dna: DNA) -> str:
        """提取DNA中的可读文本"""
        content = dna.content
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("text", "full_text", "summary", "description", "decision",
                       "reason", "trigger", "outcome", "pattern_name"):
                val = content.get(key)
                if val and isinstance(val, str) and len(val) > 3:
                    return val
            parts = [str(v) for v in content.values() if isinstance(v, str) and len(v) > 2]
            if parts:
                return " | ".join(parts[:3])
            return str(content)[:200]
        return str(content)


class ImpactPredictor:
    """
    改动影响预测：改代码前基于历史踩坑记录预测风险

    核心逻辑：找历史上"改了XX → 导致YY出问题"的模式，
    当用户又要改XX时，提醒上次导致了什么后果。
    """

    def __init__(self, system=None):
        self.system = system

    def set_system(self, system):
        self.system = system

    def predict(self, target_game: str, target_system: str = None) -> dict:
        """
        预测改动影响

        Args:
            target_game: 目标游戏名
            target_system: 目标系统（碰撞/渲染/UI等），可选

        Returns:
            影响预测报告
        """
        if not self.system:
            return {"risks": [], "related_changes": []}

        risks = []
        related = []

        # 找到该游戏/系统的历史Bug
        classifier = BugClassifier(self.system)
        bug_entries = classifier.classify_dnas(self.system.pool)

        game_bugs = [b for b in bug_entries if b["game"] == target_game]
        if target_system:
            game_bugs = [b for b in game_bugs
                        if target_system in self._get_system_for_text(b["preview"])]

        # 统计高频Bug类型
        cat_counter = Counter(b["category"] for b in game_bugs)
        for cat, count in cat_counter.most_common(3):
            severity = max((b["severity"] for b in game_bugs if b["category"] == cat),
                          key=lambda s: {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0))
            risks.append({
                "category": cat,
                "count": count,
                "severity": severity,
                "warning": f"{target_game}历史上{cat}类Bug出现{count}次，最近一次严重度:{severity}",
            })

        # 跨游戏关联：同一系统在其他游戏中出过问题
        if target_system:
            for game, config in GAME_PATTERNS.items():
                if game == target_game:
                    continue
                sys_kws = config["systems"].get(target_system, [])
                if not sys_kws:
                    continue
                game_bugs_other = [b for b in bug_entries
                                  if b["game"] == game
                                  and any(kw in b["preview"].lower() for kw in sys_kws)]
                if game_bugs_other:
                    related.append({
                        "game": game,
                        "system": target_system,
                        "bug_count": len(game_bugs_other),
                        "note": f"{game}的{target_system}系统也有{len(game_bugs_other)}个Bug，可能共享代码",
                    })

        return {
            "target": target_game,
            "system": target_system,
            "risks": risks[:5],
            "related_changes": related[:3],
        }

    def _get_system_for_text(self, text: str) -> str:
        """从文本中识别涉及的系统"""
        text_lower = text.lower()
        all_systems = set()
        for game, config in GAME_PATTERNS.items():
            for sys_name, kws in config["systems"].items():
                if any(kw.lower() in text_lower for kw in kws):
                    all_systems.add(sys_name)
        return ",".join(all_systems) if all_systems else ""


class DecisionMemory:
    """
    决策记忆：不只记"做了什么"，更记"为什么"

    格式: {game, decision, reason, alternatives, outcome, timestamp}
    """

    def __init__(self, system=None):
        self.system = system
        self._decisions: list[dict] = []

    def set_system(self, system):
        self.system = system

    def record(self, game: str, decision: str, reason: str,
               alternatives: list[str] = None, tags: list[str] = None) -> dict:
        """记录一个决策"""
        entry = {
            "game": game,
            "decision": decision,
            "reason": reason,
            "alternatives": alternatives or [],
            "outcome": None,  # 待后续更新
            "timestamp": __import__('time').time(),
            "tags": tags or [],
        }
        self._decisions.append(entry)

        # 同时存入DNA系统
        if self.system:
            dna = DNA(
                dna_type=DNAType.MEMORY,
                content={
                    "type": "decision",
                    "game": game,
                    "decision": decision,
                    "reason": reason,
                    "alternatives": alternatives or [],
                },
                tags=["decision", game] + (tags or []),
                lifetime=90,
            )
            self.system.pool.append(dna)
            if hasattr(self.system, '_dna_by_id'):
                self.system._dna_by_id[dna.id] = dna
            self.system.store.save(dna)

        return entry

    def recall(self, game: str = None, limit: int = 5) -> list[dict]:
        """回忆相关决策"""
        if self.system:
            # 从DNA池中检索决策记忆
            decisions = []
            for dna in self.system.pool:
                content = dna.content
                if isinstance(content, dict) and content.get("type") == "decision":
                    if game and content.get("game") != game:
                        continue
                    decisions.append({
                        "game": content.get("game", ""),
                        "decision": content.get("decision", ""),
                        "reason": content.get("reason", ""),
                        "alternatives": content.get("alternatives", []),
                        "timestamp": dna.created_at,
                    })
            decisions.sort(key=lambda d: d["timestamp"], reverse=True)
            return decisions[:limit]
        return sorted(self._decisions, key=lambda d: d["timestamp"], reverse=True)[:limit]

    def update_outcome(self, decision_text: str, outcome: str):
        """更新决策结果（成功了还是踩坑了）"""
        for entry in self._decisions:
            if entry["decision"] == decision_text:
                entry["outcome"] = outcome
                break


class SmartContext:
    """
    智能上下文：按当前任务智能过滤记忆，不塞垃圾

    输入："改贪吃蛇碰撞" → 只返回贪吃蛇+碰撞相关的记忆
    而非全部1400条
    """

    def __init__(self, system=None):
        self.system = system

    def set_system(self, system):
        self.system = system

    def filter(self, task_description: str, dnas: list[DNA] = None,
               max_results: int = 20) -> list[dict]:
        """
        按任务描述智能过滤DNA

        Args:
            task_description: "改贪吃蛇碰撞" / "麻将UI优化" 等
            dnas: DNA列表，默认系统全池
            max_results: 最多返回条数

        Returns:
            过滤后的相关DNA
        """
        if dnas is None and self.system:
            dnas = self.system.pool
        elif dnas is None:
            return []

        task_lower = task_description.lower()

        # 提取任务中的关键维度
        target_game = self._extract_game(task_lower)
        target_system = self._extract_system(task_lower)

        scored = []
        for dna in dnas:
            text = self._extract_text(dna).lower()
            if not text:
                continue

            score = 0

            # 游戏匹配 (+50)
            if target_game:
                game_config = GAME_PATTERNS.get(target_game, {})
                for f in game_config.get("files", []):
                    if f.lower() in text:
                        score += 50
                        break
                # 关键词兜底
                game_keywords = {
                    "暗影幸存者": ["割草", "survivor"],
                    "四川麻将": ["麻将", "mahjong"],
                    "迷雾之塔": ["迷雾之塔", "misty"],
                    "塔防保卫战": ["塔防", "td"],
                    "贪吃蛇大作战": ["贪吃蛇", "snake"],
                    "修仙": ["修仙", "xian"],
                }
                for kw in game_keywords.get(target_game, []):
                    if kw in text:
                        score += 30
                        break

            # 系统匹配 (+40)
            if target_system and target_game:
                sys_kws = GAME_PATTERNS.get(target_game, {}).get("systems", {}).get(target_system, [])
                for kw in sys_kws:
                    if kw.lower() in text:
                        score += 40
                        break

            # 决策记忆加权 (+20) — 决策比纯记录更有价值
            if isinstance(dna.content, dict) and dna.content.get("type") == "decision":
                score += 20

            # Bug相关加权 (+15) — Bug经验很重要
            if any(w in text for w in ["bug", "修复", "fix", "异常", "报错", "崩溃"]):
                score += 15

            # 近期记忆加权 (+10) — 最近改的更相关
            hours_ago = (__import__('time').time() - dna.created_at) / 3600
            if hours_ago < 24:
                score += 10
            elif hours_ago < 72:
                score += 5

            if score > 0:
                scored.append((dna, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        results = []
        for dna, score in scored[:max_results]:
            results.append({
                "dna_id": dna.id,
                "score": score,
                "preview": self._extract_text(dna)[:150],
                "is_decision": isinstance(dna.content, dict) and dna.content.get("type") == "decision",
                "is_bug": any(w in self._extract_text(dna).lower()
                             for w in ["bug", "修复", "fix", "异常", "报错"]),
                "created_at": dna.created_at,
            })
        return results

    def _extract_game(self, task: str) -> Optional[str]:
        game_keywords = {
            "暗影幸存者": ["割草", "暗影幸存者", "survivor", "幸存者"],
            "四川麻将": ["麻将", "mahjong", "血战"],
            "迷雾之塔": ["迷雾之塔", "misty", "迷雾", "爬塔"],
            "塔防保卫战": ["塔防", "td", "塔防保卫战"],
            "贪吃蛇大作战": ["贪吃蛇", "snake", "蛇"],
            "修仙": ["修仙", "xian"],
            "苍穹射击": ["苍穹射击", "shooter", "射击"],
            "象棋翻翻乐": ["象棋翻翻乐", "chess-flip", "翻翻乐"],
            "像素冒险": ["平台跳跃", "platformer", "像素冒险"],
            "火柴人格斗": ["火柴人格斗", "fighter", "格斗"],
        }
        for game, kws in game_keywords.items():
            if any(kw in task for kw in kws):
                return game
        return None

    def _extract_system(self, task: str) -> Optional[str]:
        system_keywords = {
            "渲染": ["渲染", "draw", "sprite", "图片", "显示", "画", "图层", "粒子"],
            "碰撞": ["碰撞", "collision", "判定", "hitbox", "hit"],
            "逻辑": ["逻辑", "计算", "规则", "算法", "判断"],
            "UI": ["UI", "ui", "界面", "按钮", "弹窗", "菜单", "面板"],
            "音频": ["音频", "声音", "音效", "音乐", "sound", "audio"],
            "物理": ["物理", "physics", "重力", "跳跃"],
        }
        for sys_name, kws in system_keywords.items():
            if any(kw in task for kw in kws):
                return sys_name
        return None

    def _extract_text(self, dna: DNA) -> str:
        """提取DNA中的可读文本"""
        content = dna.content
        if isinstance(content, str):
            return content
        if isinstance(content, dict):
            for key in ("text", "full_text", "summary", "description", "decision",
                       "reason", "trigger", "outcome", "pattern_name"):
                val = content.get(key)
                if val and isinstance(val, str) and len(val) > 3:
                    return val
            parts = [str(v) for v in content.values() if isinstance(v, str) and len(v) > 2]
            if parts:
                return " | ".join(parts[:3])
            return str(content)[:200]
        return str(content)


class IntelligenceEngine:
    """
    智能引擎 — 统一入口

    整合四个子模块 + 联想大脑，提供一键分析接口。
    """

    def __init__(self, system=None):
        self.bug_classifier = BugClassifier(system)
        self.impact_predictor = ImpactPredictor(system)
        self.decision_memory = DecisionMemory(system)
        self.smart_context = SmartContext(system)
        self._system = system
        self._brain = None  # 延迟加载

    def set_system(self, system):
        self._system = system
        self.bug_classifier.set_system(system)
        self.impact_predictor.set_system(system)
        self.decision_memory.set_system(system)
        self.smart_context.set_system(system)

    def _get_brain(self):
        """获取联想大脑实例（延迟加载）"""
        if self._brain is None and self._system and hasattr(self._system, 'brain'):
            self._brain = self._system.brain
        return self._brain

    def analyze(self, task: str) -> dict:
        """
        一键分析：给定当前任务，返回完整的智能简报

        Args:
            task: 任务描述，如 "改贪吃蛇碰撞检测"

        Returns:
            完整分析报告
        """
        target_game = self.smart_context._extract_game(task)
        target_system = self.smart_context._extract_system(task)

        report = {
            "task": task,
            "game": target_game,
            "system": target_system,
            "timestamp": __import__('time').time(),
        }

        # 1. 影响预测
        if target_game:
            report["impact"] = self.impact_predictor.predict(target_game, target_system)

        # 2. 联想大脑（替代旧的SmartContext）
        brain = self._get_brain()
        if brain:
            # 被动联想
            brain_results = brain.recall(task, top_k=10, enable_wormhole=True)
            report["relevant_memories"] = brain_results

            # 主动监控
            alerts = brain.check(task)
            report["alerts"] = [a.to_dict() for a in alerts]
        else:
            # 降级到旧的SmartContext
            report["relevant_memories"] = self.smart_context.filter(task, max_results=10)
            report["alerts"] = []

        # 3. 跨游戏Bug匹配
        if task:
            # 用任务描述当Bug文本来做跨游戏匹配
            report["cross_game_bugs"] = self.bug_classifier.cross_game_match(task)

        # 4. 相关决策
        report["related_decisions"] = self.decision_memory.recall(game=target_game, limit=3)

        # 5. 游戏Bug概况
        if target_game:
            all_bugs = self.bug_classifier.classify_dnas()
            game_bugs = [b for b in all_bugs if b["game"] == target_game]
            cat_counts = Counter(b["category"] for b in game_bugs)
            report["game_bug_summary"] = {
                "total": len(game_bugs),
                "by_category": dict(cat_counts.most_common(5)),
            }

        return report

    def brief(self, task: str) -> str:
        """生成人类可读的简报"""
        report = self.analyze(task)
        lines = []

        game = report.get("game") or "??"
        system = report.get("system") or ""

        lines.append(f"[{game}]" + (f" {system}" if system else ""))

        # 🧠 联想大脑提醒
        alerts = report.get("alerts", [])
        if alerts:
            for alert in alerts[:2]:  # 最多显示2条
                alert_type = alert.get("type", "")
                msg = alert.get("message", "")
                if alert_type == "bug_history":
                    lines.append(f"⚠️ {msg}")
                elif alert_type == "cross_game":
                    lines.append(f"🔗 {msg}")
                elif alert_type == "decision":
                    lines.append(f"💡 {msg}")

        # 风险提示
        impact = report.get("impact", {})
        risks = impact.get("risks", [])
        if risks:
            top_risk = risks[0]
            lines.append(f"WARN: {top_risk['category']}Bug x{top_risk['count']} (severity:{top_risk['severity']})")

        # 跨游戏匹配
        cross = report.get("cross_game_bugs", [])
        if cross:
            games = list(set(c["game"] for c in cross[:3]))
            lines.append(f"LINK: same bug also in: {', '.join(games)}")

        # 相关决策
        decisions = report.get("related_decisions", [])
        if decisions:
            lines.append(f"DECISION: {decisions[0]['decision'][:60]}")

        # Bug概况
        bug_sum = report.get("game_bug_summary", {})
        if bug_sum.get("total", 0) > 0:
            cats = ', '.join(f'{k}x{v}' for k, v in bug_sum.get('by_category', {}).items())
            lines.append(f"BUGS: {bug_sum['total']} total ({cats})")

        # 联想大脑统计
        brain = self._get_brain()
        if brain:
            brain_stats = brain.stats()
            lines.append(f"BRAIN: {brain_stats['pool_total']} memories, {brain_stats['recall_count']} recalls")

        return "\n".join(lines)
