"""
DNA-Strand 自动记录引擎 v2 — 持续记忆（像人脑一样）
触发点:
  ① record_commit()   — Git Hook: 每次 commit 自动提取 diff
  ② record_session()  — 会话钩子: 对话结束时自动摘要
  ③ record_snapshot()  — 定时快照: 项目状态快照
  ④ record_thought()  — 持续记忆: 任何想法/互动/决策都自动记录

能量自动分级（像人脑注意力机制）：
  🔴 重要 (0.7-1.0): Bug修复、设计决策、核心改动 → 长期保留
  🟡 中等 (0.4-0.7): 功能实现、代码审查、用户反馈 → 中期保留
  🟢 一般 (0.2-0.4): 状态检查、任务分派、日常操作 → 短期保留
  ⚪ 琐碎 (0.05-0.2): 问候、闲聊、无实质内容 → 快速遗忘

自带去重、分类、过滤、衰减。
"""
import hashlib
import json
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from .core.dna import DNA, DNAType
from .core.compile import CompileChain
from .core.magnetic import MagneticEngine
from .storage.store import DNAStore


# ===== 自动分类规则 =====
CLASSIFICATION_RULES: dict[str, list[str]] = {
    "暗影幸存者": ["割草", "暗影", "survivor", "弹幕", "怪物", "波次", "经验", "升级", "素材工厂"],
    "四川麻将":   ["麻将", "mahjong", "血战", "川麻", "胡牌", "碰杠", "听牌", "番型"],
    "贪吃蛇":     ["贪吃蛇", "snake", "蛇", "NPC", "吞噬", "食物"],
    "塔防保卫战": ["塔防", "td", "炮塔", "敌人", "波次", "路径", "水晶塔", "冰塔", "火塔"],
    "迷雾之塔":   ["迷雾", "misty", "tower", "爬塔", "楼层", "roguelike", "房间"],
    "修仙":       ["修仙", "xian", "练气", "筑基", "金丹", "渡劫"],
    "苍穹射击":   ["苍穹", "射击", "shooter", "太空", "子弹"],
    "象棋翻翻乐": ["象棋", "翻翻乐", "chess", "flip"],
    "像素冒险":   ["像素", "平台跳跃", "platformer", "跳跃"],
    "火柴人格斗": ["火柴人", "fighter", "格斗"],
    "Bug修复":    ["fix", "bug", "修复", "崩溃", "报错", "错误", "异常", "死循环"],
    "设计决策":   ["设计", "决定", "方案", "架构", "重构", "模式"],
    "流程改进":   ["流程", "优化", "Agent", "工作流", "铁律", "模板"],
    "部署发布":   ["部署", "deploy", "同步", "git push", "发布"],
}

# ===== 能量自动分级（像人脑注意力机制）=====
ENERGY_GRADING = {
    # 🔴 重要 — 长期保留
    "critical": {
        "keywords": ["崩溃", "闪退", "白屏", "进不去", "致命", "数据丢失",
                     "安全", "加密", "核心逻辑", "渲染系统", "碰撞系统",
                     "重写", "重构架构", "协议设计", "breaking change"],
        "energy": 0.9,
    },
    "important": {
        "keywords": ["修复", "fix", "bug", "解决", "完成", "实现",
                     "设计", "决定", "方案", "架构", "新增", "新游戏",
                     "部署", "发布", "同步", "铁律", "规则"],
        "energy": 0.65,
    },
    # 🟡 中等 — 中期保留
    "moderate": {
        "keywords": ["修改", "调整", "优化", "改进", "审查", "测试",
                     "反馈", "建议", "任务", "派活", "Agent",
                     "数值", "UI", "界面", "音效", "道具"],
        "energy": 0.4,
    },
    # 🟢 一般 — 短期保留
    "light": {
        "keywords": ["检查", "查看", "状态", "统计", "查询",
                     "仪表盘", "Dashboard", "DNA", "记忆"],
        "energy": 0.2,
    },
    # ⚪ 琐碎 — 快速遗忘
    "trivial": {
        "keywords": ["你好", "谢谢", "好的", "嗯", "ok"],
        "energy": 0.08,
    },
}
# 默认能量（无关键词匹配时）
DEFAULT_ENERGY = 0.15


def grade_energy(text: str) -> tuple[float, str]:
    """自动分析文本重要性，返回 (能量值, 等级名)"""
    text_lower = text.lower()
    best_energy = DEFAULT_ENERGY
    best_level = "trivial"

    for level, cfg in ENERGY_GRADING.items():
        for kw in cfg["keywords"]:
            if kw.lower() in text_lower:
                if cfg["energy"] > best_energy:
                    best_energy = cfg["energy"]
                    best_level = level
                    break  # 找到该等级的最高能级即可

    # 文本长度加成（长文本通常更有内容）
    length_bonus = min(0.15, len(text) / 500 * 0.15)
    return min(1.0, best_energy + length_bonus), best_level


# 噪音模式 — 匹配到的变更不记录
NOISE_PATTERNS = [
    r"^\s*$",                          # 空行
    r"^[+-]\s*//.*$",                  # 纯注释变更
    r"console\.log",                   # 调试日志
    r"^\s*[+-]\s*$",                   # 空白行变更
]


# 存储上限（5GB ≈ 45万条记忆，约27年容量）
MAX_STRANDS = 500000      # 最多50万条DNA strand
MIN_KEEP_STRANDS = 400000 # 清理后至少保留40万条


class AutoRecorder:
    """DNA 自动记录引擎 v2（持续记忆 + 自动衰减 + 存储上限）"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.store = DNAStore(str(self.base_dir))
        self.magnetic = MagneticEngine(threshold=0.65)
        self.compiler = CompileChain(self.magnetic)
        self.pool: list[DNA] = []
        self._load_pool()

    def _load_pool(self):
        """加载已有DNA到内存池"""
        loaded = self.store.load_all()
        self.pool = [d for d in loaded if d.is_alive]

    def _content_hash(self, text: str) -> str:
        """生成内容的语义哈希（去重用）"""
        # 去除空白和标点后哈希
        normalized = re.sub(r'\s+', ' ', text.strip().lower())
        normalized = re.sub(r'[^\w一-鿿]', '', normalized)
        return hashlib.md5(normalized.encode('utf-8')).hexdigest()[:16]

    def _is_duplicate(self, content_hash: str, similarity_threshold: float = 0.85) -> bool:
        """检查是否与已有记忆重复"""
        for dna in self.pool:
            if not dna.content:
                continue
            existing_text = json.dumps(dna.content, ensure_ascii=False)
            existing_hash = self._content_hash(existing_text)
            if existing_hash == content_hash:
                return True
        return False

    def _classify(self, text: str) -> list[str]:
        """自动分类: 匹配游戏名/Bug/设计等标签"""
        tags = []
        text_lower = text.lower()
        for category, keywords in CLASSIFICATION_RULES.items():
            for kw in keywords:
                if kw.lower() in text_lower:
                    tags.append(category)
                    break
        return tags if tags else ["其他"]

    def _filter_noise(self, lines: list[str]) -> list[str]:
        """过滤噪音行，只保留有意义的变更"""
        filtered = []
        for line in lines:
            is_noise = False
            for pattern in NOISE_PATTERNS:
                if re.match(pattern, line):
                    is_noise = True
                    break
            if not is_noise:
                filtered.append(line)
        return filtered

    def _is_meaningful(self, text: str, min_chars: int = 20) -> bool:
        """判断变更是否有记录价值"""
        text = text.strip()
        if not text:
            return False
        # 按字符数判断（适用于会话摘要等单行文本）
        if len(text) >= min_chars:
            return True
        # 按行数判断（适用于 diff 等多行文本）
        lines = [l for l in text.split('\n') if l.strip()]
        if len(lines) < 2:
            return False
        meaningful = self._filter_noise(lines)
        if len(meaningful) < 2:
            return False
        return True

    # ===== 触发点①: Git Hook =====

    def record_commit(self, repo_dir: str = None) -> Optional[DNA]:
        """
        Git Hook 触发: 从最近一次 commit 提取 diff 并记录
        返回生成的 DNA，如果无意义则返回 None
        """
        repo = Path(repo_dir) if repo_dir else self.base_dir

        # 获取最近 commit 信息
        commit_info = self._get_commit_info(repo)
        if not commit_info:
            return None

        # 获取 diff
        diff_text = self._get_commit_diff(repo)
        if not diff_text:
            return None

        # 获取变更文件列表
        changed_files = self._get_changed_files(repo)

        # 组装记忆内容
        content = {
            "type": "commit",
            "message": commit_info.get("message", ""),
            "author": commit_info.get("author", ""),
            "date": commit_info.get("date", ""),
            "hash": commit_info.get("hash", ""),
            "files_changed": changed_files,
            "diff_summary": self._summarize_diff(diff_text),
        }

        # 去重
        chash = self._content_hash(json.dumps(content, ensure_ascii=False))
        if self._is_duplicate(chash):
            print(f"[AutoRecorder] 跳过重复记忆: {commit_info.get('message', '')[:50]}")
            return None

        # 分类
        tags = self._classify(json.dumps(content, ensure_ascii=False))
        tags.append("commit")

        # 编译为 DNA
        dna = self.compiler.compile(content, source="auto:commit", tags=tags)
        self.pool.append(dna)
        self.store.save(dna)
        print(f"[AutoRecorder] 记录 commit: {commit_info.get('message', '')[:50]}")
        return dna

    # ===== 触发点②: 会话钩子 =====

    def record_session(self, summary: str, session_id: str = None) -> Optional[DNA]:
        """
        会话钩子触发: 从会话摘要提取记忆
        summary: 军师生成的会话摘要文本
        """
        if not summary or not summary.strip():
            return None

        # 判断是否有意义
        if not self._is_meaningful(summary):
            print("[AutoRecorder] 会话摘要太短，跳过记录")
            return None

        # 去重
        chash = self._content_hash(summary)
        if self._is_duplicate(chash):
            print("[AutoRecorder] 跳过重复会话记忆")
            return None

        # 分类
        tags = self._classify(summary)
        tags.append("session")

        content = {
            "type": "session",
            "summary": summary,
            "session_id": session_id or datetime.now().strftime("%Y%m%d_%H%M%S"),
            "recorded_at": datetime.now().isoformat(),
        }

        dna = self.compiler.compile(content, source="auto:session", tags=tags)
        self.pool.append(dna)
        self.store.save(dna)
        print(f"[AutoRecorder] 记录会话: {summary[:50]}...")
        return dna

    # ===== 触发点④: 持续记忆（像人脑一样自动记录）=====

    def record_thought(self, text: str, energy: float = None,
                       source: str = "auto:thought", tags: list[str] = None) -> Optional[DNA]:
        """
        持续记忆：任何想法/互动/决策都自动形成记忆痕迹。

        像人脑一样工作：
        - 重要的事自动获得高能量 → 长期保留
        - 琐碎的事自动获得低能量 → 自然衰减遗忘
        - 重复的内容自动去重（不重复记）
        - 太短/无意义的内容自动跳过

        Args:
            text: 记忆内容（一句话描述）
            energy: 手动指定能量（0-1），不指定则自动分级
            source: 来源标签
            tags: 手动标签，不指定则自动分类

        Returns:
            生成的DNA，None表示被过滤（太短/重复/无意义）
        """
        if not text or len(text.strip()) < 4:
            return None

        text = text.strip()

        # 自动能量分级（像人脑注意力机制）
        if energy is None:
            energy, level = grade_energy(text)
        else:
            level = "manual"
            energy = max(0.01, min(1.0, energy))

        # 低于阈值的琐碎记忆直接跳过（节省存储）
        if energy < 0.05:
            return None

        # 自动分类标签
        if tags is None:
            tags = self._classify(text)
        tags.append("thought")
        tags.append(f"e:{level}")  # 能量等级标签

        # 去重
        chash = self._content_hash(text)
        if self._is_duplicate(chash):
            # 重复记忆：不新增，但强化已有记忆
            for dna in self.pool:
                existing = json.dumps(dna.content, ensure_ascii=False)
                if self._content_hash(existing) == chash:
                    dna.access()  # 强化
                    return None

        # 组装记忆内容
        content = {
            "type": "thought",
            "text": text,
            "energy": round(energy, 2),
            "level": level,
            "recorded_at": datetime.now().isoformat(),
            "source": source,
        }

        # 编译为DNA，初始生命值=能量*100
        dna = self.compiler.compile(content, source=source, tags=tags)
        dna.lifetime = energy * 100  # 能量直接决定初始生命值
        self.pool.append(dna)
        self.store.save(dna)

        # 🧠 存储上限保护：超过MAX_STRANDS时自动清理最弱的记忆
        self._enforce_capacity()

        return dna

    def _enforce_capacity(self):
        """存储上限保护：超过上限时移除生命值最低的记忆（像人脑遗忘最弱的记忆）"""
        if len(self.pool) <= MAX_STRANDS:
            return

        # 按生命值排序，移除最弱的
        self.pool.sort(key=lambda d: d.lifetime)
        overflow = len(self.pool) - MIN_KEEP_STRANDS
        to_remove = self.pool[:overflow]

        for dna in to_remove:
            try:
                self.store.remove(dna.id)
            except Exception:
                pass

        self.pool = self.pool[overflow:]
        print(f"[AutoRecorder] 存储上限保护: 移除{len(to_remove)}条最弱记忆 (保留{len(self.pool)}条)")

    def extract_episode_from_session(self, summary: str) -> Optional[dict]:
        """
        从会话摘要中提取情景事件

        解析常见模式:
          - "任务: X，做了Y，结果Z"
          - "修复了X，通过Y方式，成功解决"
          - 多行摘要中的动作行

        Returns:
            dict with trigger/actions/outcome, or None
        """
        if not summary or len(summary.strip()) < 20:
            return None

        trigger = ""
        actions = []
        outcome = ""

        lines = [l.strip() for l in summary.split('\n') if l.strip()]

        # 尝试从结构化文本中提取
        full_text = " ".join(lines)

        # 模式1: 包含明确的"做了/完成/修复"动作
        action_markers = ["做了", "完成", "修复", "实现", "新增", "修改", "重构", "优化", "解决", "处理"]
        for marker in action_markers:
            if marker in full_text:
                # 提取标记后的内容作为动作
                idx = full_text.index(marker)
                chunk = full_text[idx:idx + 80]
                # 截断到下一个句号/逗号
                for sep in ["。", "，", "；", "\n"]:
                    if sep in chunk:
                        chunk = chunk[:chunk.index(sep)]
                actions.append(chunk.strip())
                break

        # 模式2: 从行首提取触发上下文
        trigger_patterns = [
            r"^(任务|问题|需求|Bug|优化)[:：]\s*(.+)",
            r"^(.+?)(?:，|,|\s)(?:做了|完成|修复|实现)",
        ]
        for pattern in trigger_patterns:
            import re
            m = re.search(pattern, full_text)
            if m:
                trigger = m.group(m.lastindex).strip()[:100]
                break

        # 模式3: 提取结果
        outcome_markers = ["结果", "成功", "失败", "完成", "通过", "解决"]
        for marker in outcome_markers:
            if marker in full_text:
                idx = full_text.index(marker)
                chunk = full_text[idx:idx + 60]
                for sep in ["。", "；", "\n"]:
                    if sep in chunk:
                        chunk = chunk[:chunk.index(sep)]
                outcome = chunk.strip()
                break

        # 降级: 如果没解析出结构，用整段摘要
        if not actions:
            # 取前100字作为触发，中间作为动作，最后作为结果
            if len(full_text) > 60:
                trigger = full_text[:30]
                actions = [full_text[30:60]]
                outcome = full_text[60:100]
            else:
                trigger = full_text[:30]
                actions = [full_text]

        if not outcome:
            outcome = "待记录"

        return {
            "trigger": trigger[:100],
            "actions": actions,
            "outcome": outcome[:100],
        }

    # ===== 触发点③: 定时快照 =====

    def record_snapshot(self) -> Optional[DNA]:
        """
        定时快照: 扫描项目当前状态并记录
        适合每天首次开工时调用
        """
        snapshot = self._collect_snapshot()
        if not snapshot:
            return None

        # 去重
        chash = self._content_hash(json.dumps(snapshot, ensure_ascii=False))
        if self._is_duplicate(chash):
            print("[AutoRecorder] 跳过重复快照")
            return None

        tags = self._classify(json.dumps(snapshot, ensure_ascii=False))
        tags.append("snapshot")

        dna = self.compiler.compile(snapshot, source="auto:snapshot", tags=tags)
        self.pool.append(dna)
        self.store.save(dna)
        print(f"[AutoRecorder] 记录项目快照")
        return dna

    # ===== 内部方法 =====

    def _get_commit_info(self, repo: Path) -> Optional[dict]:
        """获取最近 commit 的元信息"""
        try:
            # 设置环境变量确保 UTF-8 输出
            env = os.environ.copy()
            env['GIT_LOG_ENCODING'] = 'utf-8'
            result = subprocess.run(
                ["git", "log", "-1", "--format=%H%n%an%n%ai%n%s"],
                cwd=str(repo), capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace', env=env
            )
            if result.returncode != 0:
                return None
            lines = result.stdout.strip().split('\n')
            if len(lines) < 4:
                return None
            return {
                "hash": lines[0][:12],
                "author": lines[1],
                "date": lines[2],
                "message": lines[3],
            }
        except Exception:
            return None

    def _get_commit_diff(self, repo: Path) -> str:
        """获取最近 commit 的 diff 统计"""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD", "--stat"],
                cwd=str(repo), capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            if result.returncode != 0:
                return ""
            return result.stdout.strip()
        except Exception:
            return ""

    def _get_changed_files(self, repo: Path) -> list[str]:
        """获取最近 commit 变更的文件列表"""
        try:
            result = subprocess.run(
                ["git", "diff", "HEAD~1", "HEAD", "--name-only"],
                cwd=str(repo), capture_output=True, text=True, timeout=10,
                encoding='utf-8', errors='replace'
            )
            if result.returncode != 0:
                return []
            return [f.strip() for f in result.stdout.strip().split('\n') if f.strip()]
        except Exception:
            return []

    def _summarize_diff(self, diff_text: str) -> str:
        """从 diff 统计中提取摘要"""
        lines = diff_text.strip().split('\n')
        # 取最后的统计行
        if lines:
            return lines[-1].strip()
        return ""

    def _collect_snapshot(self) -> Optional[dict]:
        """收集项目快照信息"""
        tests_dir = self.base_dir / "tests"
        serve_dir = self.base_dir / "游戏工坊-serve"
        dna_dir = self.base_dir / ".dna" / "strands"

        # 统计游戏文件
        game_files = []
        if tests_dir.exists():
            for f in tests_dir.glob("*.html"):
                stat = f.stat()
                game_files.append({
                    "name": f.name,
                    "size_kb": round(stat.st_size / 1024, 1),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })

        # 统计 DNA 数量
        dna_count = len(list(dna_dir.glob("*.json"))) if dna_dir.exists() else 0

        if not game_files:
            return None

        snapshot = {
            "type": "snapshot",
            "recorded_at": datetime.now().isoformat(),
            "games": game_files,
            "game_count": len(game_files),
            "dna_count": dna_count,
        }
        return snapshot


# ===== 命令行入口 =====

def main():
    """独立运行: python -m dna_strand.auto_recorder [commit|session|snapshot] [args...]"""
    import sys

    action = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    recorder = AutoRecorder()

    if action == "commit":
        dna = recorder.record_commit()
        if dna:
            print(f"✅ 已记录 commit 记忆: {dna.id}")
        else:
            print("⏭️ 无有意义的 commit 变更")

    elif action == "session":
        # 从 stdin 或参数读取摘要
        if len(sys.argv) > 2:
            summary = " ".join(sys.argv[2:])
        else:
            summary = sys.stdin.read()
        dna = recorder.record_session(summary)
        if dna:
            print(f"✅ 已记录会话记忆: {dna.id}")
        else:
            print("⏭️ 会话摘要无记录价值")

    elif action == "snapshot":
        dna = recorder.record_snapshot()
        if dna:
            print(f"✅ 已记录快照记忆: {dna.id}")
        else:
            print("⏭️ 快照无变化")

    else:
        print("用法: python -m dna_strand.auto_recorder [commit|session|snapshot] [文本]")


if __name__ == "__main__":
    main()
