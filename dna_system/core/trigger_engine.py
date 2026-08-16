"""
DNA系统条件触发引擎
实现"条件触发 + 渐进增强"方案中的触发逻辑
增强版：添加高频Bug类型自动提示
"""
import re
import json
import time
from datetime import datetime, timedelta
from pathlib import Path


class TriggerEngine:
    """条件触发引擎"""
    
    def __init__(self, config_file=None):
        self.config_file = config_file or Path(__file__).parent / "trigger_rules.json"
        self.load_config()
        self.last_trigger_time = {}
        self.trigger_count = {}
        self.critical_rules = self._load_critical_rules()
    
    def _load_critical_rules(self):
        """加载关键规则"""
        rules_file = Path(__file__).parent.parent.parent / ".dna" / "critical_rules.json"
        if rules_file.exists():
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def load_config(self):
        """加载触发规则配置"""
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = self._default_config()
    
    def _default_config(self):
        """默认配置"""
        return {
            "trigger_keywords": {
                "碰撞": ["碰撞", "collision", "hitbox", "判定", "穿透", "hitThisFrame"],
                "渲染": ["渲染", "draw", "canvas", "显示", "画面", "闪烁"],
                "UI": ["UI", "按钮", "界面", "点击", "菜单", "弹窗"],
                "逻辑": ["逻辑", "计算", "数值", "分数", "计数"],
                "Bug": ["bug", "Bug", "修复", "错误", "问题"],
                "定时器": ["定时器", "timer", "setTimeout", "setInterval", "倒计时"],
                "状态机": ["状态", "state", "状态机", "切换", "transition"],
            },
            "action_keywords": ["改", "修", "优化", "调整", "重构", "新增"],
            "trigger_phrases": ["检索DNA", "查历史", "历史经验", "之前做过", "之前的Bug", "以前的Bug", "之前的问题"],
            "frequency_limit": 300,
            "cooldown_period": 1800,
            "similarity_threshold_high": 0.5,
            "similarity_threshold_low": 0.3,
            "game_names": [
                "贪吃蛇", "割草", "麻将", "塔防", "射击", "象棋", "赛车",
                "弹球", "方块", "捕鱼", "地牢", "超级玛丽", "跳一跳",
            ],
            "bug_pattern_hints": {
                "碰撞": {
                    "query": "碰撞检测 hitThisFrame 双重判定 穿透",
                    "advice": "注意：历史上碰撞Bug主要是hitThisFrame未重置导致双重判定，建议先检查相关记忆",
                },
                "渲染": {
                    "query": "渲染异常 canvas globalAlpha 状态重置",
                    "advice": "注意：历史上渲染Bug主要是Canvas状态(globalAlpha/compositeOperation)未重置，建议先检查相关记忆",
                },
                "定时器": {
                    "query": "定时器 setTimeout setInterval 泄漏 清理",
                    "advice": "注意：历史上定时器Bug主要是清理不及时导致泄漏，建议先检查相关记忆",
                },
                "状态机": {
                    "query": "状态机 state 重置 非法状态 切换",
                    "advice": "注意：历史上状态机Bug主要是状态未重置或非法状态，建议先检查相关记忆",
                },
            },
        }
    
    def detect_game_name(self, text):
        """从文本中检测游戏名"""
        text_lower = text.lower()
        for game in self.config["game_names"]:
            if game in text or game.lower() in text_lower:
                return game
        return None
    
    def detect_keywords(self, text):
        """检测触发关键词"""
        text_lower = text.lower()
        detected = []
        
        for category, keywords in self.config["trigger_keywords"].items():
            for kw in keywords:
                if kw in text or kw.lower() in text_lower:
                    detected.append(category)
                    break
        
        for action in self.config["action_keywords"]:
            if action in text:
                detected.append("action")
        
        for phrase in self.config["trigger_phrases"]:
            if phrase in text:
                detected.append("explicit")
        
        return list(set(detected))
    
    def should_trigger(self, text, context=None):
        """判断是否应该触发检索"""
        game_name = self.detect_game_name(text)
        keywords = self.detect_keywords(text)
        
        if "explicit" in keywords:
            hints = self._get_auto_hints(keywords)
            return True, {
                "game_name": game_name,
                "keywords": keywords,
                "cache_key": "explicit_trigger",
                "hints": hints,
            }
        
        if not game_name:
            return False, {"reason": "未检测到游戏名"}
        
        if not keywords:
            return False, {"reason": "未检测到触发关键词"}
        
        now = time.time()
        cache_key = f"{game_name}_{'_'.join(sorted(keywords))}"
        
        if cache_key in self.last_trigger_time:
            if now - self.last_trigger_time[cache_key] < self.config["frequency_limit"]:
                return False, {"reason": "触发频率限制中"}
        
        hints = self._get_auto_hints(keywords)
        return True, {
            "game_name": game_name,
            "keywords": keywords,
            "cache_key": cache_key,
            "hints": hints,
        }
    
    def _get_auto_hints(self, keywords):
        """根据关键词生成自动提示"""
        hints = []
        bug_patterns = self.config.get("bug_pattern_hints", {})
        
        for kw in keywords:
            if kw in bug_patterns:
                hints.append(bug_patterns[kw])
        
        return hints
    
    def get_auto_retrieval_query(self, text):
        """根据文本内容生成自动检索查询词"""
        keywords = self.detect_keywords(text)
        game_name = self.detect_game_name(text)
        
        bug_patterns = self.config.get("bug_pattern_hints", {})
        queries = []
        
        for kw in keywords:
            if kw in bug_patterns:
                queries.append(bug_patterns[kw]["query"])
        
        if game_name:
            queries = [f"{game_name} {q}" for q in queries]
        
        return queries
    
    def record_trigger(self, cache_key):
        """记录触发时间"""
        self.last_trigger_time[cache_key] = time.time()
        self.trigger_count[cache_key] = self.trigger_count.get(cache_key, 0) + 1
    
    def get_stats(self):
        """获取触发统计"""
        return {
            "total_triggers": sum(self.trigger_count.values()),
            "trigger_count": self.trigger_count,
            "active_cache_keys": len(self.last_trigger_time),
        }
    
    def clear_cache(self):
        """清除缓存"""
        self.last_trigger_time.clear()
        self.trigger_count.clear()


def test_trigger_engine():
    """测试触发引擎"""
    engine = TriggerEngine()
    
    test_cases = [
        ("修复贪吃蛇碰撞检测", True),
        ("优化塔防渲染性能", True),
        ("查一下之前的Bug", True),
        ("帮我做个小游戏", False),
        ("检索DNA", True),
        ("修改象棋界面", True),
        ("hello world", False),
        ("修复定时器泄漏问题", True),
        ("修改状态机切换逻辑", True),
    ]
    
    print("=== 触发引擎测试 ===")
    for text, expected in test_cases:
        result, info = engine.should_trigger(text)
        status = "✅" if result == expected else "❌"
        print(f"{status} '{text}' -> {result} ({info.get('reason', '')})")
        if result:
            engine.record_trigger(info["cache_key"])
            hints = info.get("hints", [])
            if hints:
                for hint in hints:
                    print(f"   💡 自动提示: {hint['advice']}")
                auto_queries = engine.get_auto_retrieval_query(text)
                if auto_queries:
                    print(f"   🔍 自动检索词: {', '.join(auto_queries)}")
    
    print(f"\n统计: {engine.get_stats()}")


if __name__ == "__main__":
    test_trigger_engine()