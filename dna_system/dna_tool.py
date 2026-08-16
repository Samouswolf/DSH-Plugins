#!/usr/bin/env python3
"""
DNA工作流工具 v2.0 — 从"被动工具"到"主动大脑"
==============================================

五大脑区：
  海马体 — consolidate  记忆巩固（合并冗余、生成洞察、遗忘旧数据）
  前额叶 — brief        主动开工简报（历史坑+模式匹配+风险预测）
  杏仁核 — risk         风险预警（检测高风险操作，给出历史参考）
  小脑   — insight      模式识别（从修复历史提炼知识洞察）
  联想大脑 — recall/check  被动联想 + 主动监控

基础命令：
  python dna_system/dna_tool.py lookup <游戏名>     # 查Bug历史
  python dna_system/dna_tool.py classify <描述文本>  # 分类Bug
  python dna_system/dna_tool.py patterns             # 跨游戏Bug模式
  python dna_system/dna_tool.py stats                # 真实统计
  python dna_system/dna_tool.py record <游戏> <描述> # 记录修复

主动命令：
  python dna_system/dna_tool.py brief <游戏名> [任务描述]
  python dna_system/dna_tool.py consolidate
  python dna_system/dna_tool.py risk <代码改动描述>
  python dna_system/dna_tool.py insight <游戏名>

🧠 联想大脑命令：
  python dna_system/dna_tool.py recall <查询文本>    # 被动联想
  python dna_system/dna_tool.py check <任务上下文>   # 主动监控
  python dna_system/dna_tool.py brain-stats          # 大脑统计
  python dna_system/dna_tool.py brain-add <ID> <文本> [能量]  # 添加记忆

🤖 Agent专用命令（简洁输出，便于解析）：
  python dna_system/dna_tool.py agent-context <任务描述> [top_k] # Token预算入口：少量摘要+风险
  python dna_system/dna_tool.py brain-recall <查询文本> [top_k]  # 被动联想（含智能预加载）
  python dna_system/dna_tool.py brain-check <任务上下文>         # 主动监控
  python dna_system/dna_tool.py brain-brief <游戏名> [任务描述]  # 开工简报

🧠 智能回忆命令（串联完整记忆管线）：
  python dna_system/dna_tool.py smart-recall <查询文本> [top_k] # 智能回忆（预加载+聚类+Brain）
  python dna_system/dna_tool.py preload <上下文文本>            # 预加载相关记忆簇

🔄 同步命令：
  python dna_system/dna_tool.py sync-games                     # 同步deploy目录游戏列表到DNA
"""
import sys
import os
import json
import glob
import re
from datetime import datetime, timedelta
import time
from pathlib import Path
from collections import Counter, defaultdict

# 强制UTF-8 I/O（修复Windows bash GBK编码导致的乱码）
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stdin, 'reconfigure'):
    sys.stdin.reconfigure(encoding='utf-8', errors='replace')

# 自动修复 sys.argv 编码（Windows bash可能用GBK传递参数）
# 检测策略：如果argv中的中文字符无法正确编码为UTF-8，尝试从GBK恢复
if sys.platform == 'win32':
    _fixed_argv = []
    for _a in sys.argv:
        try:
            _a.encode('utf-8')
            _fixed_argv.append(_a)
        except UnicodeEncodeError:
            # 尝试从latin-1恢复（GBK→latin-1→UTF-8管线）
            try:
                _fixed_argv.append(_a.encode('latin-1').decode('gbk'))
            except Exception:
                _fixed_argv.append(_a)
    sys.argv = _fixed_argv

ROOT = Path(__file__).parent.parent
STRANDS = ROOT / ".dna" / "strands"
FIX_LOG = ROOT / ".dna" / "fix_log.json"
INSIGHTS_FILE = ROOT / ".dna" / "insights.json"

# 安全模块
try:
    from .core.security import (
        add_security_fields,
        verify_signature,
        verify_and_fix_record,
        record_operation,
        get_audit_log,
        generate_security_report,
        soft_delete,
    )
    SECURITY_ENABLED = True
except ImportError:
    SECURITY_ENABLED = False

# ===== 游戏名映射（别名 → 标准名）=====
GAME_ALIASES = {
    "贪吃蛇": "贪吃蛇大作战", "snake": "贪吃蛇大作战",
    "割草": "暗影幸存者", "survivor": "暗影幸存者", "shadow": "暗影幸存者",
    "麻将": "四川麻将", "mahjong": "四川麻将",
    "塔防": "塔防保卫战", "td": "塔防保卫战", "tower": "塔防保卫战",
    "迷雾": "迷雾之塔", "misty": "迷雾之塔", "tower-defense": "迷雾之塔",
    "修仙": "修仙", "xian": "修仙", "cultivation": "修仙",
    "射击": "苍穹射击", "shooter": "苍穹射击",
    "象棋": "象棋翻翻乐", "chess": "象棋翻翻乐",
    "像素冒险": "像素冒险", "platformer": "像素冒险",
    "火柴人": "火柴人格斗", "fighter": "火柴人格斗",
    "寿司": "寿司店大亨", "sushi": "寿司店大亨",
    "弹球": "弹球大作战", "pinball": "弹球大作战",
    "方块": "方块消消乐", "block": "方块消消乐",
    "细胞": "细胞吞噬", "cell": "细胞吞噬",
    "节奏": "节奏大师", "rhythm": "节奏大师",
    "地牢": "地牢卡牌", "dungeon": "地牢卡牌",
    "勇者": "勇者冒险", "hero": "勇者冒险",
    "像素赛车": "像素赛车", "racing": "像素赛车",
    "东方": "东方幻想", "touhou": "东方幻想",
    "塔防v2": "塔防保卫战v2", "td-v2": "塔防保卫战v2",
}

# deploy英文文件名 → 中文游戏名映射（15组英文/中文双版本）
_DEPLOY_NAME_MAP = {
    "game": "暗影幸存者", "mahjong": "川麻血战到底", "snake": "贪吃蛇大作战",
    "misty-tower": "迷雾之塔", "td": "塔防保卫战", "td-v2": "塔防保卫战v2",
    "shooter": "苍穹射击", "chess-flip": "象棋翻翻乐", "platformer": "像素冒险",
    "fighter": "火柴人格斗", "pixel-racer": "像素赛车", "xian": "文字修仙",
    "tetris": "俄罗斯方块", "2048": "2048数字", "bubble-shooter": "泡泡龙",
    "gomoku": "五子棋", "rhythm": "节奏大师", "pacman": "吃豆人大作战",
    "ninja-runner": "忍者跑酷", "whack-mole": "打地鼠", "link-match": "连连看",
}

# fix_log旧名 → deploy标准名映射（历史兼容）
_FIX_LOG_ALIASES = {
    "四川麻将": "川麻血战到底",
    "修仙": "文字修仙",
    "吃豆人": "吃豆人大作战",
    "贪吃蛇": "贪吃蛇大作战",
}

def _get_html_title(filepath):
    """从HTML文件提取<title>标签内容"""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            head = f.read(2048)  # 只读前2KB够了
        import re
        m = re.search(r'<title>(.*?)</title>', head)
        return m.group(1).strip() if m else ''
    except Exception:
        return ''

def _discover_games():
    """从deploy目录按title去重发现所有游戏（88款唯一游戏）"""
    deploy_dir = ROOT / "deploy"
    if not deploy_dir.exists():
        return []
    seen_titles = {}  # title → 标准名
    for f in sorted(deploy_dir.glob("*.html")):
        if f.name in ("index.html", "精灵选择器.html"):
            continue
        title = _get_html_title(f)
        if not title:
            title = f.stem
        # 去掉副标题（" - xxx"部分）用于去重
        base_title = title.split(" - ")[0].strip()
        if base_title not in seen_titles:
            # 优先用中文文件名作为标准名
            stem = f.stem
            if stem.isascii() and stem in _DEPLOY_NAME_MAP:
                seen_titles[base_title] = _DEPLOY_NAME_MAP[stem]
            elif not stem.isascii():
                seen_titles[base_title] = stem
            else:
                seen_titles[base_title] = stem
    # 补充fix_log中有记录但deploy没有的游戏（模糊匹配避免重复）
    try:
        if FIX_LOG.exists():
            with open(FIX_LOG, 'r', encoding='utf-8') as f:
                fixes = json.load(f).get("fixes", [])
            existing = set(seen_titles.values())
            for fix in fixes:
                game = fix.get("game", "")
                if not game or game == "unknown":
                    continue
                # 旧名→标准名映射
                game = _FIX_LOG_ALIASES.get(game, game)
                # 精确匹配跳过
                if game in existing:
                    continue
                # 模糊匹配：game是某个已有名字的子串，或反过来
                matched = False
                for eg in existing:
                    if game in eg or eg in game:
                        matched = True
                        break
                if not matched:
                    seen_titles[game] = game
    except Exception:
        pass
    return sorted(set(seen_titles.values()))


ALL_GAMES = _discover_games()


def normalize_game(name):
    """游戏名标准化"""
    if not name:
        return name
    # 精确匹配
    if name in ALL_GAMES:
        return name
    # 别名匹配
    lower = name.lower()
    for alias, std in GAME_ALIASES.items():
        if alias in lower or lower in alias:
            return std
    # 子串匹配
    for g in ALL_GAMES:
        if name in g or g in name:
            return g
    return name


# ===== 数据加载 =====

def load_strands():
    """加载所有DNA strands"""
    strands = []
    for f in STRANDS.glob("*.json"):
        try:
            with open(f, 'r', encoding='utf-8') as fh:
                data = json.load(fh)
                data['_file'] = f.name
                strands.append(data)
        except:
            pass
    return strands


def load_fix_log():
    """加载修复记录"""
    if FIX_LOG.exists():
        with open(FIX_LOG, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"fixes": [], "patterns": {}}


def save_fix_log(log, record_info=None):
    """保存修复记录（带安全字段）"""
    FIX_LOG.parent.mkdir(parents=True, exist_ok=True)
    
    # 添加安全字段
    if SECURITY_ENABLED and record_info:
        log = add_security_fields(log, is_new=True)
        # 记录审计日志
        record_operation(
            operation="save",
            target_id="fix_log",
            target_type="fix_log",
            details=record_info,
            success=True
        )
    
    with open(FIX_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def load_insights():
    """加载洞察库"""
    if INSIGHTS_FILE.exists():
        with open(INSIGHTS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"insights": [], "last_consolidated": None}


def save_insights(data):
    """保存洞察库"""
    INSIGHTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(INSIGHTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _content_text(s):
    """从strand提取文本内容"""
    c = s.get("content", {})
    if isinstance(c, dict):
        return str(c)
    elif isinstance(c, str):
        return c
    d = s.get("data", {})
    if isinstance(d, dict):
        return str(d)
    return ""


def _extract_game(s):
    """从strand识别游戏名"""
    tags = s.get("tags", [])
    tag_str = " ".join(str(t) for t in tags)
    content_preview = _content_text(s)[:200]
    combined = tag_str + " " + content_preview
    for g in ALL_GAMES:
        if g in combined:
            return g
    return None


# ============================================================
# 1. 前额叶 — 主动开工简报 (brief)
# ============================================================

def brief(game, task=""):
    """
    主动开工简报 — DNA大脑的核心功能

    不等用户查，主动搜索相关记忆，输出可执行建议。
    """
    game = normalize_game(game)
    fix_log = load_fix_log()
    fixes = fix_log.get("fixes", [])
    insights = load_insights()

    # 按游戏筛选修复记录
    game_fixes = [f for f in fixes if f.get("game") == game]

    # 分析任务类型
    task_type = classify_task_type(task) if task else None

    report = []
    report.append(f"{'='*50}")
    report.append(f"[BRIEF] {game} 开工简报")
    if task:
        report.append(f"  任务: {task}")
    report.append(f"{'='*50}")

    # === 1. 历史坑（最近修复）===
    if game_fixes:
        # 按严重度排序：critical > high > medium > low
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recent = sorted(game_fixes, key=lambda f: sev_order.get(f.get("severity", "low"), 9))

        report.append(f"\n[历史坑] {game} 共{len(game_fixes)}条修复记录:")
        for f in recent[:5]:
            sev = f.get("severity", "?")
            icon = {"critical": "!!!", "high": "!!", "medium": "!", "low": "."}.get(sev, "?")
            report.append(f"  [{icon}] [{sev}] {f.get('description', '?')[:60]}")
    else:
        report.append(f"\n[历史坑] {game} 暂无修复记录")

    # === 2. 模式匹配（跨游戏同类型）===
    if task_type:
        same_type = [f for f in fixes if f.get("category") == task_type and f.get("game") != game]
        if same_type:
            games_involved = list(set(f.get("game", "?") for f in same_type))
            report.append(f"\n[模式匹配] {task_type}类Bug在其他游戏也出现过{len(same_type)}次:")
            report.append(f"  涉及: {', '.join(games_involved[:5])}")
            # 取最近2条作为参考
            for f in same_type[-2:]:
                report.append(f"  -> [{f.get('game','?')}] {f.get('description','?')[:50]}")

    # === 3. 风险预测 ===
    if task:
        risk = _assess_risk(task, game_fixes)
        if risk["level"] == "high":
            report.append(f"\n!!! [高风险] {risk['reason']}")
            if risk.get("advice"):
                report.append(f"  建议: {risk['advice']}")
        elif risk["level"] == "medium":
            report.append(f"\n! [中风险] {risk['reason']}")

    # === 4. 相关洞察 ===
    game_insights = [i for i in insights.get("insights", [])
                     if game in i.get("games", [])]
    if game_insights:
        report.append(f"\n[洞察] 从历史中提炼的模式:")
        for i in game_insights[:2]:
            report.append(f"  * {i.get('pattern', '?')}: {i.get('root_cause', '?')[:60]}")

    report.append(f"\n{'='*50}")
    return "\n".join(report)


def classify_task_type(task):
    """从任务描述推断Bug类型"""
    t = task.lower()
    type_keywords = {
        "渲染异常": ["渲染", "显示", "draw", "sprite", "canvas", "画面", "绘制", "闪烁", "花屏", "消失"],
        "碰撞/判定": ["碰撞", "collision", "hitbox", "判定", "穿透", "穿墙", "重叠"],
        "逻辑错误": ["逻辑", "计算", "数值", "分数", "金币", "计数", "死循环", "卡死"],
        "UI/交互": ["UI", "按钮", "点击", "界面", "菜单", "弹窗", "面板", "触屏", "触摸"],
        "音频": ["声音", "音频", "音效", "音乐", "sound", "audio"],
        "性能": ["卡顿", "掉帧", "性能", "内存", "泄漏", "lag", "fps", "优化"],
        "道具系统": ["道具", "powerup", "buff", "效果"],
        "碰撞检测": ["碰撞检测", "hitbox", "hitThisFrame", "CCD"],
    }
    for cat, kws in type_keywords.items():
        if any(kw in t for kw in kws):
            return cat
    return None


def _assess_risk(task, game_fixes):
    """评估任务风险"""
    t = task.lower()

    # 高风险关键词
    high_risk_kws = ["核心逻辑", "渲染系统", "碰撞检测", "碰撞系统", "游戏循环",
                     "gameLoop", "requestAnimationFrame", "全量重构", "重写"]
    # 中风险关键词
    mid_risk_kws = ["升级系统", "道具", "计分", "波次", "关卡", "存档", "动画"]

    # 检查高风险
    for kw in high_risk_kws:
        if kw in t:
            # 查找历史上同类改动出过的问题
            related = [f for f in game_fixes if any(
                rk in f.get("description", "").lower()
                for rk in ["逻辑", "渲染", "碰撞", "循环"]
            )]
            if related:
                return {
                    "level": "high",
                    "reason": f"历史上{len(related)}次相关修复，这类改动容易出问题",
                    "advice": f"最近一次: {related[-1].get('description', '?')[:40]}。建议先通读相关代码再动手。"
                }
            return {
                "level": "high",
                "reason": f"涉及'{kw}'，属于高风险区域",
                "advice": "小步修改，每步验证，不留未测试的改动。"
            }

    # 检查中风险
    for kw in mid_risk_kws:
        if kw in t:
            related_count = sum(1 for f in game_fixes if kw in f.get("description", ""))
            if related_count >= 2:
                return {
                    "level": "medium",
                    "reason": f"'{kw}'相关历史Bug{related_count}次，注意边界条件"
                }

    return {"level": "low", "reason": "低风险改动"}


# ============================================================
# 2. 海马体 — 记忆巩固 (consolidate)
# ============================================================

def consolidate():
    """
    记忆巩固 — 海马体的核心功能

    1. 扫描所有修复记录
    2. 按模式分组，3次以上生成洞察
    3. 合并冗余记忆
    4. 遗忘超期未引用的旧数据
    """
    fix_log = load_fix_log()
    fixes = fix_log.get("fixes", [])
    insights_data = load_insights()

    if not fixes:
        return {"message": "无修复记录，跳过巩固", "insights_generated": 0}

    report = []
    report.append(f"[CONSOLIDATE] 记忆巩固")
    report.append(f"  修复记录总数: {len(fixes)}")

    # === 1. 按模式分组 ===
    groups = defaultdict(list)
    for fix in fixes:
        key = fix.get("category", "未分类")
        groups[key].append(fix)

    # === 2. 对每组生成洞察（3次以上才形成模式）===
    new_insights = []
    for pattern, group in groups.items():
        if len(group) < 3:
            continue

        # 分析根因
        root_causes = _analyze_root_causes(group)
        games_involved = list(set(f.get("game", "?") for f in group))

        insight = {
            "pattern": pattern,
            "count": len(group),
            "games": games_involved,
            "root_cause": root_causes,
            "prevention": _generate_prevention(pattern, root_causes),
            "created": datetime.now().isoformat(),
            "last_referenced": datetime.now().isoformat(),
        }
        new_insights.append(insight)

    # === 3. 跨游戏模式分析（同类型跨游戏 = 系统性问题）===
    cross_patterns = _find_cross_game_patterns(fixes)
    for cp in cross_patterns:
        if cp["game_count"] >= 3:
            new_insights.append({
                "pattern": f"跨游戏-{cp['category']}",
                "count": cp["total"],
                "games": cp["games"],
                "root_cause": cp["root_cause"],
                "prevention": cp["prevention"],
                "created": datetime.now().isoformat(),
                "last_referenced": datetime.now().isoformat(),
            })

    # === 4. 合并冗余洞察 ===
    merged = _merge_insights(insights_data.get("insights", []), new_insights)
    insights_data["insights"] = merged
    insights_data["last_consolidated"] = datetime.now().isoformat()

    # === 5. 遗忘机制 ===
    forgotten = _forget_old_memories(insights_data, days=30)

    save_insights(insights_data)

    report.append(f"  新生成洞察: {len(new_insights)}")
    report.append(f"  合并后总洞察: {len(merged)}")
    report.append(f"  遗忘条目: {forgotten}")
    report.append(f"\n[洞察摘要]")
    for i in merged[:10]:
        report.append(f"  * [{i['pattern']}] {i['count']}次, 涉及{len(i.get('games',[]))}款游戏")
        report.append(f"    根因: {i.get('root_cause', '?')[:60]}")

    return {
        "total_fixes": len(fixes),
        "insights_generated": len(new_insights),
        "insights_total": len(merged),
        "forgotten": forgotten,
        "report": "\n".join(report),
    }


def _analyze_root_causes(group):
    """分析一组同类Bug的根因"""
    descriptions = [f.get("description", "") for f in group]

    # 关键词共现分析
    cause_keywords = {
        "计时器/定时器问题": ["计时", "定时", "setTimeout", "setInterval", "timer", "倒计时"],
        "状态未重置": ["重置", "reset", "状态", "残留", "遗留"],
        "边界条件遗漏": ["边界", "边界条件", "空", "null", "undefined", "溢出"],
        "公式/计算错误": ["公式", "计算", "数值", "公式错误", "倍率"],
        "事件处理竞态": ["事件", "回调", "异步", "竞态", "race"],
        "条件分支短路": ["短路", "else", "条件", "分支", "漏判"],
        "双重执行/重复": ["双重", "重复", "两次", "叠加", "double"],
        "可见性/渲染层": ["不显示", "不可见", "透明", "层级", "z-index", "覆盖"],
        "坐标/偏移错误": ["偏移", "错位", "坐标", "位置", "offset"],
    }

    causes = []
    all_text = " ".join(descriptions).lower()
    for cause, kws in cause_keywords.items():
        match_count = sum(1 for kw in kws if kw in all_text)
        if match_count >= 1:
            causes.append(cause)

    if not causes:
        # 回退：根据描述中的动词模式推断
        if any("不" in d and ("生效" in d or "工作" in d) for d in descriptions):
            causes.append("功能未生效/未接入")
        elif any("重复" in d or "两次" in d for d in descriptions):
            causes.append("双重执行/重复")
        else:
            causes.append("需人工分析")

    return "; ".join(causes[:3])


def _generate_prevention(pattern, root_causes):
    """根据模式和根因生成预防建议"""
    prevention_map = {
        "渲染异常": "渲染改动后截图对比，检查canvas状态（globalAlpha, globalCompositeOperation）",
        "碰撞/判定": "碰撞改动后用边界值测试（零距离、重叠50%、高速穿越），考虑hitThisFrame标志",
        "逻辑错误": "逻辑改动后单步走读关键路径，检查边界条件和状态重置",
        "UI/交互": "UI改动后在移动端和桌面端分别测试触摸/点击区域",
        "性能": "性能改动前后对比FPS，检查是否有O(n^2)循环或每帧重建对象",
        "道具系统": "道具改动后验证：生成→拾取→效果→过期→重新生成 全链路",
    }
    return prevention_map.get(pattern, "改动后自测关键路径，检查边界条件")


def _find_cross_game_patterns(fixes):
    """找出跨3款以上游戏的同类Bug模式"""
    by_category = defaultdict(list)
    for f in fixes:
        by_category[f.get("category", "未分类")].append(f)

    patterns = []
    for cat, group in by_category.items():
        games = list(set(f.get("game", "?") for f in group))
        if len(games) >= 3:
            patterns.append({
                "category": cat,
                "total": len(group),
                "games": games,
                "game_count": len(games),
                "root_cause": _analyze_root_causes(group),
                "prevention": _generate_prevention(cat, ""),
            })
    return patterns


def _merge_insights(existing, new):
    """合并新旧洞察，去重"""
    merged = list(existing)

    for ni in new:
        # 检查是否已有同模式洞察
        found = False
        for ei in merged:
            if ei.get("pattern") == ni.get("pattern"):
                # 合并：更新计数和游戏列表
                ei["count"] = max(ei.get("count", 0), ni.get("count", 0))
                existing_games = set(ei.get("games", []))
                existing_games.update(ni.get("games", []))
                ei["games"] = list(existing_games)
                ei["last_referenced"] = datetime.now().isoformat()
                if ni.get("root_cause") and ni["root_cause"] != "需人工分析":
                    ei["root_cause"] = ni["root_cause"]
                if ni.get("prevention"):
                    ei["prevention"] = ni["prevention"]
                found = True
                break
        if not found:
            merged.append(ni)

    return merged


def _forget_old_memories(insights_data, days=30):
    """遗忘机制：超过N天未被引用的洞察降权或移除"""
    cutoff = datetime.now() - timedelta(days=days)
    original_count = len(insights_data.get("insights", []))

    kept = []
    for i in insights_data.get("insights", []):
        last_ref = i.get("last_referenced")
        if last_ref:
            try:
                ref_time = datetime.fromisoformat(last_ref)
                if ref_time > cutoff:
                    kept.append(i)
                # else: 遗忘
            except:
                kept.append(i)  # 解析失败则保留
        else:
            kept.append(i)  # 无时间戳则保留

    insights_data["insights"] = kept
    return original_count - len(kept)


# ============================================================
# 3. 杏仁核 — 风险预警 (risk)
# ============================================================

def risk(description):
    """
    风险预警 — 检测高风险操作

    当检测到高风险操作时：
    - 不是阻止，是提醒
    - 给出历史上类似改动出过的问题
    - 给出具体建议
    """
    fix_log = load_fix_log()
    fixes = fix_log.get("fixes", [])
    insights = load_insights()

    d = description.lower()

    # === 风险等级判定 ===
    critical_patterns = {
        "游戏主循环": {
            "keywords": ["gameLoop", "requestAnimationFrame", "主循环", "游戏循环", "update函数"],
            "history_tag": "逻辑错误",
            "advice": "改主循环前：1)确认帧率不受影响 2)检查所有依赖帧率的定时器 3)改完跑5分钟不崩溃",
        },
        "渲染系统": {
            "keywords": ["渲染", "draw", "render", "canvas", "ctx.", "globalCompositeOperation"],
            "history_tag": "渲染异常",
            "advice": "改渲染前：1)截图留档 2)改完对比 3)检查透明度/混合模式状态",
        },
        "碰撞系统": {
            "keywords": ["碰撞", "collision", "hitbox", "判定", "穿透", "hitThisFrame"],
            "history_tag": "碰撞/判定",
            "advice": "改碰撞前：1)列出所有碰撞对 2)用极端位置测试 3)高速物体考虑CCD",
        },
        "状态机": {
            "keywords": ["状态", "state", "状态机", "切换", "transition", "mode"],
            "history_tag": "逻辑错误",
            "advice": "改状态机前：1)画状态转移图 2)检查每个转移的前置条件 3)防止非法状态",
        },
        "计时器系统": {
            "keywords": ["计时", "定时", "setTimeout", "setInterval", "timer", "倒计时", "暂停"],
            "history_tag": "逻辑错误",
            "advice": "改计时器前：1)暂停时是否暂停 2)游戏结束是否清理 3)数值单位（秒vs毫秒vs帧）",
        },
        "存档系统": {
            "keywords": ["存档", "save", "load", "持久化", "localStorage"],
            "history_tag": "逻辑错误",
            "advice": "改存档前：1)新旧格式兼容 2)读取失败的fallback 3)版本号字段",
        },
    }

    matched_risks = []
    for risk_name, cfg in critical_patterns.items():
        if any(kw in d for kw in cfg["keywords"]):
            matched_risks.append((risk_name, cfg))

    if not matched_risks:
        return {
            "level": "low",
            "message": f"[RISK] 低风险: '{description[:50]}'",
            "detail": "未匹配到已知高风险模式，但仍建议自测。",
        }

    # 取最高匹配的风险
    risk_name, cfg = matched_risks[0]

    # 查找历史相关Bug
    tag = cfg["history_tag"]
    related = [f for f in fixes if f.get("category") == tag]

    # 构建报告
    report = []
    level = "high" if len(related) >= 5 else "medium"
    icon = "!!!" if level == "high" else "!"

    report.append(f"[RISK] {icon} {level.upper()} RISK: {risk_name}")
    report.append(f"  描述: {description[:60]}")
    report.append(f"  历史同类Bug: {len(related)}次")

    if related:
        # 列出最近3条
        games_hit = list(set(f.get("game", "?") for f in related))
        report.append(f"  涉及游戏: {', '.join(games_hit[:5])}")
        for f in related[-3:]:
            report.append(f"    -> [{f.get('game','?')}] {f.get('description','?')[:50]}")

    report.append(f"  建议: {cfg['advice']}")

    # 检查相关洞察
    game_insights = [i for i in insights.get("insights", [])
                     if tag in i.get("pattern", "")]
    if game_insights:
        report.append(f"  洞察: {game_insights[0].get('prevention', '?')[:60]}")

    return {
        "level": level,
        "risk_type": risk_name,
        "related_bugs": len(related),
        "message": "\n".join(report),
    }


# ============================================================
# 4. 小脑 — 洞察生成 (insight)
# ============================================================

def insight(game):
    """
    洞察生成 — 从修复历史中提炼知识

    不是统计"碰撞Bug出现3次"，
    而是提炼"碰撞Bug的根因是高速物体用离散碰撞检测"
    """
    game = normalize_game(game)
    fix_log = load_fix_log()
    fixes = fix_log.get("fixes", [])
    insights_data = load_insights()

    game_fixes = [f for f in fixes if f.get("game") == game]

    if not game_fixes:
        return {
            "game": game,
            "message": f"[INSIGHT] {game} 暂无修复记录，无法生成洞察",
            "insights": [],
        }

    report = []
    report.append(f"{'='*50}")
    report.append(f"[INSIGHT] {game} 知识洞察")
    report.append(f"  修复记录: {len(game_fixes)}条")
    report.append(f"{'='*50}")

    game_insights = []

    # === 1. 按类型分组分析 ===
    by_category = defaultdict(list)
    for f in game_fixes:
        by_category[f.get("category", "未分类")].append(f)

    for cat, group in sorted(by_category.items(), key=lambda x: -len(x[1])):
        if len(group) < 2:
            continue

        root_cause = _analyze_root_causes(group)
        prevention = _generate_prevention(cat, root_cause)

        game_insights.append({
            "category": cat,
            "count": len(group),
            "root_cause": root_cause,
            "prevention": prevention,
            "examples": [f.get("description", "")[:50] for f in group[-3:]],
        })

        report.append(f"\n[{cat}] {len(group)}次")
        report.append(f"  根因: {root_cause}")
        report.append(f"  预防: {prevention}")
        for ex in game_insights[-1]["examples"]:
            report.append(f"    -> {ex}")

    # === 2. 高频根因排名 ===
    all_causes = []
    for f in game_fixes:
        desc = f.get("description", "").lower()
        cause_kws = {
            "计时器问题": ["计时", "定时", "setTimeout", "timer"],
            "状态未重置": ["重置", "reset", "残留", "遗留"],
            "条件分支错误": ["短路", "漏判", "条件", "else"],
            "坐标/偏移": ["偏移", "错位", "坐标", "位置"],
            "双重执行": ["双重", "重复", "叠加"],
            "功能未生效": ["不生效", "无效果", "只有视觉", "只有显示"],
        }
        for cause, kws in cause_kws.items():
            if any(kw in desc for kw in kws):
                all_causes.append(cause)

    if all_causes:
        cause_counter = Counter(all_causes)
        report.append(f"\n[高频根因 Top3]")
        for cause, count in cause_counter.most_common(3):
            report.append(f"  {cause}: {count}次")

    # === 3. 跨游戏同类洞察 ===
    cross_insights = [i for i in insights_data.get("insights", [])
                      if game in i.get("games", [])]
    if cross_insights:
        report.append(f"\n[跨游戏关联洞察]")
        for i in cross_insights[:3]:
            other_games = [g for g in i.get("games", []) if g != game]
            report.append(f"  * {i['pattern']}: 与{', '.join(other_games[:3])}有相同模式")
            report.append(f"    预防: {i.get('prevention', '?')[:50]}")

    return {
        "game": game,
        "total_fixes": len(game_fixes),
        "insights": game_insights,
        "report": "\n".join(report),
    }


# ============================================================
# 5. 基础功能（改进版）
# ============================================================

def load_brain_pool():
    """加载brain_pool.json数据"""
    pool_path = ROOT / ".dna" / "brain_pool.json"
    if pool_path.exists():
        with open(pool_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"entities": []}


DEVELOPMENT_RECORD_KEYWORDS = [
    "新游戏开发", "新建", "开发完成", "部署完成", "增强开发", "新增", "测试记录",
]


def classify_record_type(description: str, category: str = None) -> str:
    """区分真实Bug修复和开发/功能记录，避免污染Bug模式统计。"""
    text = str(description or "")
    if category in ("开发记录", "功能更新"):
        return "development"
    if any(kw in text for kw in DEVELOPMENT_RECORD_KEYWORDS):
        return "development"
    return "bug_fix"


def canonicalize_fix(fix: dict) -> dict:
    """返回标准化后的fix记录副本，不直接修改输入对象。"""
    normalized = dict(fix)
    game = normalized.get("game", "unknown")
    normalized["game"] = normalize_game(_FIX_LOG_ALIASES.get(game, game))
    normalized.setdefault("description", "")
    normalized.setdefault("category", "未分类")
    normalized.setdefault("severity", "low")
    normalized["record_type"] = classify_record_type(
        normalized.get("description", ""),
        normalized.get("category"),
    )
    if normalized["record_type"] == "bug_fix" and normalized.get("category") == "未分类":
        cls = classify_bug(normalized.get("description", ""))
        if cls.get("primary") != "开发记录":
            normalized["category"] = cls.get("primary", "未分类")
            normalized["severity"] = normalized.get("severity") or cls.get("severity", "low")
    return normalized


def get_canonical_fixes(include_development: bool = False) -> list[dict]:
    """加载并标准化fix_log记录。默认只返回真实Bug修复。"""
    fixes = [canonicalize_fix(f) for f in load_fix_log().get("fixes", [])]
    if include_development:
        return fixes
    return [f for f in fixes if f.get("record_type") == "bug_fix"]


def rebuild_patterns_from_fixes(fixes: list[dict]) -> dict:
    """按真实Bug修复重建patterns索引。"""
    patterns = {}
    for fix in fixes:
        if fix.get("record_type") != "bug_fix":
            continue
        key = fix.get("pattern", fix.get("category", "未分类"))
        patterns.setdefault(key, {"count": 0, "games": []})
        patterns[key]["count"] += 1
        game = fix.get("game", "?")
        if game not in patterns[key]["games"]:
            patterns[key]["games"].append(game)
    return patterns


def real_stats():
    """统一统计口径：strands + brain_pool + 结构化fix_log。"""
    all_records = get_canonical_fixes(include_development=True)
    fixes = [f for f in all_records if f.get("record_type") == "bug_fix"]
    development_records = [f for f in all_records if f.get("record_type") == "development"]

    # 从fix_log直接获取每游戏Bug数（结构化数据，O(1) per game）
    game_bugs = defaultdict(lambda: {"total": 0})
    for fix in fixes:
        game = fix.get("game", "unknown")
        game_bugs[game]["total"] += 1

    # 文件计数（不读内容）
    strand_count = len(list(STRANDS.glob("*.json"))) if STRANDS.exists() else 0
    brain_data = load_brain_pool()
    brain_count = len(brain_data.get("entities", []))

    # 今日/批次记录（轻量扫描brain entity ID）
    today = datetime.now().strftime("%Y%m%d")
    brain_entities = brain_data.get("entities", [])
    today_count = sum(1 for e in brain_entities if today in str(e.get("id", "")))
    batch_count = sum(1 for e in brain_entities if "batch" in str(e.get("id", "")).lower())

    return {
        "total_strands": strand_count + brain_count,
        "bug_related": len(fixes),
        "fixes_recorded": len(fixes),
        "records_total": len(all_records),
        "development_records": len(development_records),
        "by_game": {k: v["total"] for k, v in sorted(game_bugs.items())},
        "data_sources": {
            "strands": strand_count,
            "brain_pool": brain_count,
        },
        "today_development": {
            "today_records": today_count,
            "batch_records": batch_count,
            "total_games": len(ALL_GAMES),
        }
    }


def lookup_bugs(game_name):
    """查找某游戏的Bug历史"""
    game_name = normalize_game(game_name)
    strands = load_strands()
    fixes = get_canonical_fixes()

    results = {"from_strands": [], "from_fix_log": []}

    for s in strands:
        content = _content_text(s)
        tags = s.get("tags", [])
        tag_str = " ".join(str(t) for t in tags)

        if game_name in content or game_name in tag_str:
            bug_kws = ["bug", "fix", "修复", "问题", "错误", "异常"]
            if any(kw in content.lower() for kw in bug_kws):
                results["from_strands"].append({
                    "preview": content[:150],
                    "tags": tags[:3],
                })

    for fix in fixes:
        if game_name in fix.get("game", ""):
            results["from_fix_log"].append(fix)

    return results


def classify_bug(text):
    """
    对Bug描述进行分类（改进版）

    改进点：
    - 更多关键词覆盖
    - 上下文感知判断
    - 更精确的严重度判定
    """
    text_lower = text.lower()

    if classify_record_type(text) == "development":
        return {
            "primary": "开发记录",
            "severity": "low",
            "record_type": "development",
            "scores": {"开发记录": 1},
        }

    categories = {
        "渲染异常": ["不显示", "显示异常", "花屏", "闪烁", "透明", "绘制", "渲染",
                    "draw", "sprite", "消失", "黑色", "白屏", "canvas", "图层",
                    "不绘制", "残影", "模糊", "错位", "重叠", "遮挡", "显示偏移"],
        "碰撞/判定": ["碰撞", "collision", "穿透", "重叠", "判定", "hitbox", "穿墙",
                    "打不中", "打不到", "击中", "hitThisFrame", "碰撞检测"],
        "逻辑错误": ["逻辑", "计算错误", "数值不对", "分数", "金币", "计数", "回合",
                    "死循环", "卡死", "公式", "倍率", "短路", "漏判", "状态",
                    "重置", "残留", "竞态", "定时器", "计时"],
        "UI/交互": ["按钮", "点击", "界面", "UI", "弹窗", "菜单", "面板", "panel",
                   "btn", "overlay", "无法操作", "点不了", "触屏", "触摸", "偏移",
                   "错位", "重叠", "遮挡", "不显示", "显示异常", "触摸区域"],
        "音频": ["声音", "音频", "音效", "音乐", "sound", "audio", "sfx"],
        "性能": ["卡顿", "掉帧", "性能", "内存", "泄漏", "lag", "fps", "慢", "优化"],
        "道具系统": ["道具", "powerup", "buff", "效果", "磁铁", "冰冻", "加速", "护盾"],
        "兼容性": ["兼容", "旧浏览器", "polyfill", "roundrect", "浏览器", "无法启动"],
    }

    scores = {}
    for cat, kws in categories.items():
        score = sum(1 for kw in kws if kw in text_lower)
        if score > 0:
            scores[cat] = score

    # 严重度判定（独立于分类，先判严重度）
    critical_words = ["崩溃", "闪退", "白屏", "进不去", "致命", "数据丢失",
                      "死循环", "卡死", "无法启动", "黑屏", "白屏"]
    high_words = ["穿墙", "没反应", "偏移", "错位", "不一致", "丢失",
                  "不显示", "无法操作", "点不了", "卡死", "穿透", "不生效",
                  "无效果", "只有视觉", "只有显示"]

    if any(w in text_lower for w in critical_words):
        severity = "critical"
    elif any(w in text_lower for w in high_words):
        severity = "high"
    elif not scores:
        severity = "low"
    elif max(scores.values()) >= 3:
        severity = "medium"
    else:
        severity = "low"

    if not scores:
        return {"primary": "未分类", "severity": severity, "record_type": "bug_fix"}

    # 上下文感知：如果包含"显示/位置/偏移"但不含"计算/逻辑"，倾向UI
    ui_signal = any(w in text_lower for w in ["显示", "位置", "偏移", "错位"])
    logic_signal = any(w in text_lower for w in ["计算", "逻辑", "公式", "数值"])
    if ui_signal and not logic_signal:
        scores["UI/交互"] = scores.get("UI/交互", 0) + 2

    primary = max(scores, key=scores.get)

    return {"primary": primary, "severity": severity, "record_type": "bug_fix", "scores": scores}


def find_patterns():
    """查找跨游戏的Bug模式"""
    fixes = get_canonical_fixes()

    if not fixes:
        return {"message": "暂无修复记录，使用 'record' 命令记录修复结果", "patterns": {}}

    patterns = {}
    for fix in fixes:
        key = fix.get("pattern", fix.get("category", "未分类"))
        if key not in patterns:
            patterns[key] = {"count": 0, "games": set(), "examples": []}
        patterns[key]["count"] += 1
        patterns[key]["games"].add(fix.get("game", "?"))
        if len(patterns[key]["examples"]) < 3:
            patterns[key]["examples"].append(fix.get("description", "")[:80])

    for p in patterns.values():
        p["games"] = list(p["games"])

    return {"total_fixes": len(fixes), "patterns": patterns}


def record_fix(game, description, category=None, severity=None):
    """记录一次Bug修复"""
    game = normalize_game(game)
    fix_log = load_fix_log()

    record_type = classify_record_type(description, category)
    if not category or not severity:
        cls = classify_bug(description)
        category = category or cls["primary"]
        severity = severity or cls["severity"]
        record_type = cls.get("record_type", record_type)

    fix = {
        "game": game,
        "description": description,
        "category": category,
        "severity": severity,
        "record_type": record_type,
        "timestamp": datetime.now().isoformat(),
    }

    fix_log.setdefault("fixes", []).append(fix)

    if record_type == "bug_fix":
        pattern_key = category
        patterns = fix_log.setdefault("patterns", {})
        if pattern_key not in patterns:
            patterns[pattern_key] = {"count": 0, "games": []}
        patterns[pattern_key]["count"] += 1
        if game not in patterns[pattern_key]["games"]:
            patterns[pattern_key]["games"].append(game)

    # 保存时添加安全字段
    record_info = {
        "action": "record_fix",
        "game": game,
        "category": category,
        "record_type": record_type,
        "fix_count": len(fix_log.get("fixes", []))
    }
    save_fix_log(fix_log, record_info)
    return fix


def clean_fix_log(dry_run: bool = True) -> dict:
    """标准化fix_log：补record_type、统一游戏名、按真实Bug重建patterns。"""
    fix_log = load_fix_log()
    original = fix_log.get("fixes", [])
    cleaned = [canonicalize_fix(f) for f in original]

    changed = 0
    development = 0
    renamed_games = []
    for old, new in zip(original, cleaned):
        if new.get("record_type") == "development":
            development += 1
        if old.get("game") != new.get("game"):
            renamed_games.append((old.get("game"), new.get("game")))
        if old != new:
            changed += 1

    bug_fixes = [f for f in cleaned if f.get("record_type") == "bug_fix"]
    result = {
        "records_total": len(cleaned),
        "bug_fixes": len(bug_fixes),
        "development_records": development,
        "changed_records": changed,
        "renamed_games": renamed_games[:20],
        "dry_run": dry_run,
    }

    if dry_run:
        return result

    backup = FIX_LOG.with_suffix(f".backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    if FIX_LOG.exists():
        backup.write_text(FIX_LOG.read_text(encoding="utf-8"), encoding="utf-8")
    fix_log["fixes"] = cleaned
    fix_log["patterns"] = rebuild_patterns_from_fixes(cleaned)
    fix_log["last_cleaned"] = datetime.now().isoformat()
    fix_log["schema_version"] = 2
    save_fix_log(fix_log)
    result["backup"] = str(backup)
    return result


# ============================================================
# CLI
# ============================================================

def _parse_query_limit(args: list[str], default_limit: int = 6, max_limit: int = 10) -> tuple[str, int]:
    """解析 Agent 查询参数；最后一项为数字时视作 top_k。"""
    if not args:
        return "", default_limit

    limit = default_limit
    query_parts = args
    if args[-1].isdigit():
        limit = max(1, min(int(args[-1]), max_limit))
        query_parts = args[:-1]

    return " ".join(query_parts).strip(), limit


def _compact_line(text: object, limit: int = 120) -> str:
    """压缩为单行，避免把长记忆直接塞进 Agent 上下文。"""
    line = re.sub(r"\s+", " ", str(text or "")).strip()
    if len(line) <= limit:
        return line
    return line[: max(0, limit - 1)].rstrip() + "…"


def _brain_check_safe(memory_dir: str, context: str) -> list:
    """兼容旧 Brain：当前类实例可能没有 check()，模块级 check() 会返回空列表。"""
    try:
        from dna_system.core import brain as brain_module

        brain = brain_module.get_brain(memory_dir)
        if hasattr(brain, "check"):
            return brain.check(context) or []
        if hasattr(brain_module, "check"):
            return brain_module.check(context) or []
    except Exception:
        return []
    return []


def _agent_context(task: str, top_k: int = 6) -> int:
    """
    Agent Token预算入口。

    目标：先查 DNA，只输出少量可带入当前模型上下文的摘要；需要深挖时再按 ID 查询。

    v3.0 优化：缓存 + 修复模板匹配
    """
    import hashlib

    # ── 缓存检查 ──
    cache_dir = ROOT / ".dna" / "cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    task_hash = hashlib.md5(task.encode('utf-8')).hexdigest()[:12]
    cache_file = cache_dir / f"ac_{task_hash}.json"
    CACHE_TTL = 300  # 5分钟

    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text(encoding='utf-8'))
            age = time.time() - cached.get("ts", 0)
            if age < CACHE_TTL:
                print(f"[AGENT-CONTEXT] {_compact_line(task, 80)}")
                print(f"CACHE: {cached['summary']} (age: {age:.0f}s)")
                print("NEXT_STEP: cached result above; re-run with 'nocache' prefix if stale.")
                return 0
        except Exception:
            pass  # 缓存损坏，忽略

    sys.path.insert(0, str(ROOT))
    from dna_system.system import DNASystem

    system = DNASystem(str(ROOT), show_status=False)
    result = system.smart_recall(task, top_k=top_k)
    alerts = _brain_check_safe(str(ROOT / '.dna'), task)[:3]
    stats = result.get("stats", {})
    memories = result.get("results", [])[:top_k]

    # ── 修复模板匹配 ──
    templates = _load_fix_templates()
    matched = _match_templates(task, templates)

    print(f"[AGENT-CONTEXT] {_compact_line(task, 80)}")
    print("TOKEN_POLICY: use summaries below first; do not load full files or full DNA unless an ID is clearly needed.")
    print(
        "STATS: "
        f"preloaded={stats.get('preloaded', 0)} "
        f"brain={stats.get('brain_hits', 0)} "
        f"cluster={stats.get('cluster_hits', 0)} "
        f"total={stats.get('total_unique', len(memories))}"
    )

    if memories:
        print("MEMORY_SUMMARIES:")
        for idx, item in enumerate(memories, 1):
            score = item.get("_score", 0)
            rid = item.get("id", item.get("dna_id", ""))
            text = item.get("text")
            if text is None:
                text = item.get("summary", item.get("content", ""))
            print(f"{idx}. [{score:.4f}] {rid}: {_compact_line(text, 120)}")
    else:
        print("MEMORY_SUMMARIES: none")

    if alerts:
        print("RISK_HINTS:")
        for idx, alert in enumerate(alerts, 1):
            if isinstance(alert, dict):
                text = alert.get("text") or alert.get("message") or alert.get("content") or alert
            else:
                text = alert
            print(f"{idx}. {_compact_line(text, 120)}")
    else:
        print("RISK_HINTS: none")

    if matched:
        print(f"FIX_TEMPLATES: {len(matched)} matched")
        for m in matched:
            print(f"  [{m['severity'].upper()}] {m['bug']}")
            print(f"  Fix: {m['fix']}")

    print("NEXT_STEP: proceed from these summaries; run targeted lookup/recall only if the summaries are insufficient.")

    # ── 写入缓存 ──
    cache_data = {
        "ts": time.time(),
        "task": task,
        "summary": f"{len(memories)} memories, {len(alerts)} risks, {len(matched)} templates",
        "memory_count": len(memories),
        "risk_count": len(alerts),
        "template_count": len(matched),
    }
    try:
        cache_file.write_text(json.dumps(cache_data, ensure_ascii=False), encoding='utf-8')
    except Exception:
        pass

    return 0


def _load_fix_templates():
    """加载修复模板"""
    tmpl_path = ROOT / "dna_system" / "fix_templates.json"
    if tmpl_path.exists():
        try:
            data = json.loads(tmpl_path.read_text(encoding='utf-8'))
            return data.get("templates", [])
        except Exception:
            pass
    return []


def _match_templates(task: str, templates: list) -> list:
    """匹配修复模板"""
    matched = []
    task_lower = task.lower()
    for t in templates:
        for kw in t.get("pattern", []):
            if kw.lower() in task_lower:
                matched.append(t)
                break
    # 按严重度排序
    severity_order = {"high": 0, "medium": 1, "low": 2}
    matched.sort(key=lambda x: severity_order.get(x.get("severity", "low"), 3))
    return matched[:3]  # 最多3个


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]

    if cmd == "stats":
        stats = real_stats()
        print(f"\n[STATS] DNA系统真实统计")
        print(f"{'='*40}")
        print(f"DNA总数: {stats['total_strands']}")
        print(f"Bug相关: {stats['bug_related']}")
        print(f"已记录修复: {stats['fixes_recorded']}")
        print(f"开发记录: {stats.get('development_records', 0)}")
        print(f"原始记录总数: {stats.get('records_total', stats['fixes_recorded'])}")

        # 数据源统计
        sources = stats.get("data_sources", {})
        print(f"\n数据源:")
        print(f"  strands目录: {sources.get('strands', 0)}条")
        print(f"  brain_pool: {sources.get('brain_pool', 0)}条")

        # 今日开发统计
        today_dev = stats.get("today_development", {})
        if today_dev:
            print(f"\n今日开发:")
            print(f"  今日记录: {today_dev.get('today_records', 0)}条")
            print(f"  批次记录: {today_dev.get('batch_records', 0)}条")
            print(f"  游戏总数: {today_dev.get('total_games', 0)}款")

        print(f"\n各游戏Bug相关条目:")
        for game, count in stats["by_game"].items():
            print(f"  {game}: {count}")

    elif cmd == "lookup":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py lookup <游戏名>")
            return
        game = sys.argv[2]
        results = lookup_bugs(game)
        print(f"\n[LOOKUP] {game} Bug历史")
        print(f"{'='*40}")
        print(f"Strands中: {len(results['from_strands'])} 条")
        print(f"修复记录: {len(results['from_fix_log'])} 条")
        if results['from_fix_log']:
            print("\n最近修复:")
            for fix in results['from_fix_log'][-5:]:
                print(f"  [{fix.get('severity','?')}] {fix.get('description','')[:60]}")
        # 记录Token节省
        total_hits = len(results['from_strands']) + len(results['from_fix_log'])
        if total_hits > 0:
            try:
                from dna_system.core.token_tracker import tracker
                # Bug历史查询节省大量调试时间，每条记录200 tokens
                tracker.record_hit(
                    query=game,
                    hit_count=total_hits,
                    hit_type='lookup',
                    estimated_tokens_per_hit=200
                )
            except:
                pass

    elif cmd == "classify":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py classify <Bug描述>")
            return
        text = " ".join(sys.argv[2:])
        result = classify_bug(text)
        print(f"\n[CLASSIFY] Bug分类")
        print(f"{'='*40}")
        print(f"描述: {text[:60]}")
        print(f"类型: {result['primary']}")
        print(f"严重度: {result['severity']}")
        if result.get("scores"):
            print(f"匹配: {result['scores']}")

    elif cmd == "patterns":
        result = find_patterns()
        print(f"\n[PATTERNS] 跨游戏Bug模式")
        print(f"{'='*40}")
        if result.get("message"):
            print(result["message"])
        else:
            print(f"总修复数: {result['total_fixes']}")
            for name, p in result["patterns"].items():
                print(f"\n  [{name}] {p['count']}次, 涉及: {', '.join(p['games'])}")
                for ex in p["examples"]:
                    print(f"    -> {ex}")
            # 记录Token节省
            try:
                from dna_system.core.token_tracker import tracker
                # 跨游戏模式分析节省大量时间，每条记录100 tokens
                tracker.record_hit(
                    query='patterns',
                    hit_count=result['total_fixes'],
                    hit_type='patterns',
                    estimated_tokens_per_hit=100
                )
            except:
                pass

    elif cmd == "record":
        if len(sys.argv) < 4:
            print("用法: python dna_tool.py record <游戏名> <修复描述>")
            return
        game = sys.argv[2]
        desc = " ".join(sys.argv[3:])
        fix = record_fix(game, desc)
        print(f"\n[RECORD] 已记录修复")
        print(f"  游戏: {fix['game']}")
        print(f"  类型: {fix['category']}")
        print(f"  严重度: {fix['severity']}")
        print(f"  记录类型: {fix.get('record_type', 'bug_fix')}")
        print(f"  描述: {fix['description'][:60]}")

    elif cmd == "clean-fix-log":
        dry_run = "--apply" not in sys.argv[2:]
        result = clean_fix_log(dry_run=dry_run)
        mode = "预览" if dry_run else "已应用"
        print(f"\n[CLEAN-FIX-LOG] {mode}")
        print(f"{'='*40}")
        print(f"原始记录: {result['records_total']}")
        print(f"真实Bug修复: {result['bug_fixes']}")
        print(f"开发/功能记录: {result['development_records']}")
        print(f"需更新记录: {result['changed_records']}")
        if result.get("renamed_games"):
            print("游戏名标准化:")
            for old, new in result["renamed_games"]:
                print(f"  {old} -> {new}")
        if dry_run:
            print("\n应用清洗: python dna_system/dna_tool.py clean-fix-log --apply")
        else:
            print(f"备份: {result.get('backup')}")

    # ===== 新增命令 =====

    elif cmd == "brief":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py brief <游戏名> [任务描述]")
            return
        game = sys.argv[2]
        task = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        print(brief(game, task))

    elif cmd == "consolidate":
        result = consolidate()
        if result.get("report"):
            print(result["report"])
        else:
            print(result.get("message", "巩固完成"))

    elif cmd == "risk":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py risk <代码改动描述>")
            return
        desc = " ".join(sys.argv[2:])
        result = risk(desc)
        print(result["message"])

    elif cmd == "insight":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py insight <游戏名>")

    # ===== 🧠 持续记忆命令 =====

    elif cmd == "decay":
        # 手动触发记忆衰减+清理（像人脑睡眠巩固）
        hours = float(sys.argv[2]) if len(sys.argv) > 2 else 24.0
        sys.path.insert(0, str(ROOT))
        from dna_system.system import DNASystem
        system = DNASystem(str(ROOT), show_status=False)
        before = len(system.pool)
        system.tick(hours=hours)
        # 清理死DNA文件
        alive_ids = {d.id for d in system.pool}
        removed = system.store.cleanup_dead(alive_ids)
        after = len(system.pool)
        print(f"[DECAY] {hours:.0f}h衰减: {before}→{after}条记忆 (+{removed}文件清理)")
        stats = system.lifecycle.stats()
        print(f"  存活: {after}, 碎片: {stats['fragment_count']}")
        system.save()

    elif cmd == "remember":
        # 持续记忆：任何想法/互动都自动记录（像人脑一样）
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py remember <描述文本> [能量0-1]")
            return
        text = " ".join(sys.argv[2:-1]) if len(sys.argv) > 3 and sys.argv[-1].replace('.', '').isdigit() else " ".join(sys.argv[2:])
        energy = float(sys.argv[-1]) if len(sys.argv) > 3 and sys.argv[-1].replace('.', '').isdigit() else None
        sys.path.insert(0, str(ROOT))
        from dna_system.auto_recorder import AutoRecorder, grade_energy
        recorder = AutoRecorder()
        if energy is None:
            energy, level = grade_energy(text)
        dna = recorder.record_thought(text, energy=energy)
        if dna:
            print(f"[REMEMBER] 已记录 (能量={energy:.2f})")
            print(f"  ID: {dna.id}")
            print(f"  内容: {text[:60]}")
        else:
            print(f"[REMEMBER] 跳过（太短/重复/无意义）")

    elif cmd == "insight":
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py insight <游戏名>")
            return
        game = sys.argv[2]
        result = insight(game)
        print(result.get("report", result.get("message", "")))

    # ===== 联想大脑命令 =====

    elif cmd == "recall":
        # 联想大脑：被动联想
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py recall <查询文本>")
            return
        query = " ".join(sys.argv[2:])
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))
        results = brain.recall(query, top_k=5)
        print(f"\n[BRAIN RECALL] 联想结果: {query}")
        print(f"{'='*40}")
        if results:
            for r in results:
                hop = r.get("wormhole_hop", 0)
                tag = f" [虫洞hop={hop}]" if hop > 0 else ""
                print(f"  [{r.get('_score', 0):.4f}] {r['id']}: {r['text'][:60]}{tag}")
            # 记录Token节省
            try:
                from dna_system.core.token_tracker import tracker
                # 联想大脑回忆，每个结果300 tokens
                tracker.record_hit(
                    query=query,
                    hit_count=len(results),
                    hit_type='recall',
                    estimated_tokens_per_hit=300
                )
            except:
                pass
        else:
            print("  无相关记忆")

    elif cmd == "check":
        # 联想大脑：主动监控
        context = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not context:
            print("用法: python dna_tool.py check <任务上下文>")
            return
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))
        alerts = []  # monitor removed
        print(f"{'='*40}")
        if alerts:
            for alert in alerts:
                print(f"  {alert}")
        else:
            print("  无提醒")

    elif cmd == "brain-stats":
        # 联想大脑：统计（增强版，包含命中追踪）
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))
        stats = brain.stats()
        print(f"\n[BRAIN STATS] 联想大脑统计")
        print(f"{'='*40}")
        print(f"记忆总数: {stats.get('pool_total', 0)}")
        print(f"联想次数: {stats.get('recall_count', 0)}")
        print(f"\n四层记忆池:")
        for layer, info in stats.get('pool', {}).items():
            print(f"  {layer}: {info.get('count', 0)}条, 平均能量{info.get('avg_energy', 0)}")
        
        try:
            from dna_system.core.access_tracker import get_access_tracker
            tracker = get_access_tracker(str(ROOT))
            query_stats = tracker.get_query_stats()
            weekly_report = tracker.get_weekly_report()
            top_dnas = tracker.get_top_dnas(10)
            
            print(f"\n{'='*40}")
            print(f"[命中追踪统计]")
            print(f"查询总数: {query_stats['total_queries']}")
            print(f"最近24小时查询: {query_stats['recent_queries']}")
            print(f"平均结果数: {query_stats['avg_results']}")
            print(f"被使用的结果总数: {query_stats['total_used_results']}")
            print(f"平均每次查询使用: {query_stats['avg_used_per_query']}条")
            
            if top_dnas:
                print(f"\n[高价值记忆 Top10]")
                for dna_id, score, used_count in top_dnas:
                    print(f"  [{score:.2f}] {used_count}次使用: {dna_id[:30]}")
            
            high_value_clusters = tracker.get_high_value_clusters()
            if high_value_clusters:
                print(f"\n[高价值记忆簇]")
                for cluster in high_value_clusters:
                    print(f"  簇{cluster['cluster_id']}: {cluster['hit_count']}次命中, {cluster['query_count']}次查询")
                    
        except Exception as e:
            print(f"\n[命中追踪] 不可用: {str(e)[:50]}")

    elif cmd == "brain-add":
        # 联想大脑：添加记忆
        if len(sys.argv) < 4:
            print("用法: python dna_tool.py brain-add <ID> <文本> [能量]")
            return
        eid = sys.argv[2]
        text = sys.argv[3]
        energy = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))
        entity = brain.add(eid, text, energy)
        brain.save()
        print(f"\n[BRAIN ADD] 已添加记忆")
        print(f"  ID: {entity.id}")
        print(f"  文本: {text[:60]}")
        print(f"  能量: {energy}")

    # ===== Agent专用命令 =====

    elif cmd == "agent-context":
        # Agent专用：Token预算入口（少量摘要 + 风险提示）
        query, top_k = _parse_query_limit(sys.argv[2:], default_limit=6, max_limit=10)
        if not query:
            print("用法: python dna_tool.py agent-context <任务描述> [top_k]")
            return
        _agent_context(query, top_k)

    elif cmd == "brain-recall":
        # Agent专用：被动联想（简洁输出）— v3轻量版：直接用Brain，不用完整DNASystem
        query, top_k = _parse_query_limit(sys.argv[2:], default_limit=5, max_limit=10)
        if not query:
            print("用法: python dna_tool.py brain-recall <查询文本> [top_k]")
            return
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))
        results = brain.recall(query, top_k=top_k)
        # 记录Token节省
        if results:
            try:
                from dna_system.core.token_tracker import tracker
                tracker.record_hit(
                    query=query,
                    hit_count=len(results),
                    hit_type='brain_recall',
                    estimated_tokens_per_hit=300
                )
            except:
                pass
        # 简洁输出，便于Agent解析
        for r in results:
            score = r.get('_score', 0)
            eid = r['id']
            text = r['text'][:80].replace('\n', ' ')
            print(f"[{score:.4f}] {eid}: {text}")

    elif cmd == "brain-check":
        # Agent专用：主动监控（简洁输出）
        context = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""
        if not context:
            print("用法: python dna_tool.py brain-check <任务上下文>")
            return
        alerts = _brain_check_safe(str(ROOT / '.dna'), context)
        # 记录Token节省
        if alerts:
            try:
                from dna_system.core.token_tracker import tracker
                tracker.record_hit(
                    query=context,
                    hit_count=len(alerts),
                    hit_type='brain_check',
                    estimated_tokens_per_hit=100
                )
            except:
                pass
        # 简洁输出
        for a in alerts:
            print(f"[{a.alert_type}] {a.message}")

    elif cmd == "brain-brief":
        # Agent专用：开工简报
        game = sys.argv[2] if len(sys.argv) > 2 else ""
        task = " ".join(sys.argv[3:]) if len(sys.argv) > 3 else ""
        sys.path.insert(0, str(ROOT))
        from dna_system.core.brain import get_brain
        brain = get_brain(str(ROOT / '.dna'))

        # 构建查询
        query = game
        if task:
            query = f"{game} {task}"

        # 被动联想
        results = brain.recall(query, top_k=5)
        if results:
            print(f"[BRAIN BRIEF] {game} 相关记忆:")
            for r in results:
                score = r.get('_score', 0)
                text = r['text'][:60].replace('\n', ' ')
                print(f"  [{score:.4f}] {text}")
            # 记录Token节省
            try:
                from dna_system.core.token_tracker import tracker
                # 开工简报节省大量时间，每个结果500 tokens
                tracker.record_hit(
                    query=query,
                    hit_count=len(results),
                    hit_type='brain_brief',
                    estimated_tokens_per_hit=500
                )
            except:
                pass

        # 主动监控（已精简）

    # ===== 智能回忆命令（W5：串联完整记忆管线）=====

    elif cmd == "preload":
        # 预加载相关记忆簇
        if len(sys.argv) < 3:
            print("用法: python dna_tool.py preload <上下文文本>")
            return
        context = " ".join(sys.argv[2:])
        sys.path.insert(0, str(ROOT))
        from dna_system.system import DNASystem
        system = DNASystem(str(ROOT), show_status=False)
        preloaded = system.smart_preload(context)
        loader_stats = system.cluster_loader.stats()
        print(f"[PRELOAD] Context: \"{context[:50]}\"")
        print(f"  Preloaded DNAs: {len(preloaded)}")
        print(f"  Loaded clusters: {loader_stats['loaded_clusters']}")
        if preloaded:
            sample_ids = [d.id[:24] for d in preloaded[:5]]
            print(f"  Sample DNA IDs: {', '.join(sample_ids)}")

    elif cmd == "smart-recall":
        # 智能回忆：串联完整记忆管线
        query, top_k = _parse_query_limit(sys.argv[2:], default_limit=10, max_limit=20)
        if not query:
            print("用法: python dna_tool.py smart-recall <查询文本> [top_k]")
            return
        sys.path.insert(0, str(ROOT))
        from dna_system.system import DNASystem
        system = DNASystem(str(ROOT), show_status=False)
        result = system.smart_recall(query, top_k)
        stats = result["stats"]
        print(f"[SMART-RECALL] \"{query[:50]}\"")
        print(f"  Preloaded: {stats['preloaded']} | Brain: {stats['brain_hits']} | Cluster: {stats['cluster_hits']} | Total unique: {stats['total_unique']}")
        
        result_ids = [r.get("id", r.get("dna_id", "")) for r in result["results"]]
        cluster_info = {}
        if "cluster_hits" in stats:
            cluster_info["cluster"] = stats["cluster_hits"]
        
        try:
            from dna_system.core.access_tracker import get_access_tracker
            tracker = get_access_tracker(str(ROOT))
            tracker.record_query(query, result_ids, cluster_info)
        except Exception:
            pass
        
        if result["results"]:
            try:
                from dna_system.core.token_tracker import tracker
                tracker.record_hit(
                    query=query,
                    hit_count=len(result["results"]),
                    hit_type='smart_recall',
                    estimated_tokens_per_hit=150
                )
            except:
                pass
        for r in result["results"]:
            score = r.get("_score", 0)
            rid = r.get("id", r.get("dna_id", ""))
            text = r.get("text", str(r.get("content", "")))[:80].replace("\n", " ")
            print(f"  [{score:.4f}] {rid}: {text}")

    elif cmd == "sync-games":
        # 同步deploy目录的游戏列表到DNA系统（按title去重）
        global ALL_GAMES
        ALL_GAMES = _discover_games()
        deploy_dir = ROOT / "deploy"
        deploy_count = len([f for f in deploy_dir.glob("*.html") if f.name not in ("index.html", "精灵选择器.html")]) if deploy_dir.exists() else 0
        print(f"\n[SYNC-GAMES] 已同步游戏列表（按title去重）")
        print(f"{'='*40}")
        print(f"deploy文件: {deploy_count}个")
        print(f"唯一游戏: {len(ALL_GAMES)}款")
        print(f"\n完整游戏列表:")
        for i, g in enumerate(ALL_GAMES, 1):
            print(f"  {i:3d}. {g}")

    elif cmd == "auto-record":
        # 修完Bug自动记录到DNA
        if len(sys.argv) < 4:
            print("用法: python dna_tool.py auto-record <游戏名> <修复描述>")
            print("示例: python dna_tool.py auto-record 2048 修复碰撞双重判定")
            return
        game = sys.argv[2]
        desc = " ".join(sys.argv[3:])
        record_ok = record_fix(game, desc)
        if record_ok:
            print(f"[AUTO-RECORD] {game}: {desc[:60]}")
            print("SUCCESS: recorded to fix_log + brain pool")
        else:
            print("[AUTO-RECORD] FAILED")
        return 0 if record_ok else 1

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
