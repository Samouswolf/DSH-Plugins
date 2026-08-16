"""
DNA-Strand 主系统 v3.0
整合所有模块，提供统一接口
"""
import time
import json
from pathlib import Path
from typing import Any, Optional

from .core.dna import DNA, DNAType, StrandType
from .core.magnetic import MagneticEngine
from .core.wormhole import Axis
from .core.compile import CompileChain
from .core.lifecycle import LifecycleManager
from .core.evolution import EvolutionEngine
from .core.smart_tagger import SmartTagger
from .core.quality_filter import QualityFilter
from .core.access_tracker import AccessTracker
from .core.maintenance import MaintenanceEngine
from .core.git_sync import GitSync, GitSyncConfig
from .core.temporal_index import TemporalIndex
from .core.intelligence import IntelligenceEngine
# 海马体进化模块 (Phase 2-5)
from .core.episodic import EpisodicMemory, Episode
from .core.consolidation import MemoryConsolidation
from .core.pattern_completion import PatternCompletion
from .core.cognitive_map import CognitiveMap
from .core.brain import Brain
from .core.brain_encoder import TFIDFEncoder
from .core.semantic_cluster import SemanticCluster
from .core.cluster_loader import ClusterLoader
from .core.cluster_tracker import ClusterHitTracker
from .core.hit_graph import HitGraph
from .core.smart_loader import SmartLoader
from .storage.store import DNAStore
from .auto_recorder import AutoRecorder
from .status_display import get_display
from .security.protector import DataProtector, IntegrityChecker

class DNASystem:
    """
    DNA-Strand 主系统 v3.0

    特性:
    - 向量索引加速查询
    - 智能标签自动提取
    - 内容质量过滤
    - 访问反馈追踪
    - 定期维护优化
    - 自动记录机制
    - 状态显示窗口
    """

    def __init__(self, base_dir: str = None, show_status: bool = True):
        """
        初始化系统

        Args:
            base_dir: 基础目录，默认为当前目录
            show_status: 是否显示启动状态窗口
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.display = get_display()

        # 记录启动时间
        boot_start = time.time()

        # 核心引擎
        self.magnetic = MagneticEngine(threshold=0.3)
        self.compile_chain = CompileChain(self.magnetic)
        self.axis = Axis(self.magnetic)
        self.lifecycle = LifecycleManager(self.magnetic)
        self.evolution = EvolutionEngine(self.magnetic)

        # 精细化模块
        self.tagger = SmartTagger()
        self.quality_filter = QualityFilter()
        self.access_tracker = AccessTracker(str(self.base_dir))
        self.maintenance = MaintenanceEngine(self)

        # 持久化
        self.store = DNAStore(str(self.base_dir))

        # Git同步配置
        self.git_config = GitSyncConfig(str(self.base_dir / "config" / "dna_config.json"))
        self.git = None

        # 加密保护
        self.protector = DataProtector()
        self.checker = IntegrityChecker()
        self._encryption_enabled = False

        # 自动记录引擎
        self.recorder = AutoRecorder(str(self.base_dir))

        # 时间索引（Phase 1: 海马体进化）
        self.temporal_index = TemporalIndex()

        # 🧠 智能引擎（游戏工坊AI副驾驶）
        self.intelligence = IntelligenceEngine()
        self.intelligence.set_system(self)

        # 🧠 海马体进化模块 (Phase 2-5)
        self.episodic = EpisodicMemory(self)
        self.consolidation = MemoryConsolidation(self)
        self.pattern_completion = PatternCompletion(self)
        self.cognitive_map = CognitiveMap(self)

        # 🧠 联想大脑（被动联想 + 主动监控 + 反链免疫）
        self.brain = Brain(memory_dir=str(self.base_dir / '.dna'))
        self.brain.load()

        # 🧠 Phase 4: 语义聚类引擎（记忆按需加载）
        cluster_index_path = str(self.base_dir / '.dna' / 'strands' / 'cluster_index.json')
        cluster_hit_path = str(self.base_dir / '.dna' / 'strands' / 'cluster_hits.json')
        self.tfidf_encoder = TFIDFEncoder(dim=128)
        self.semantic_cluster = SemanticCluster(n_clusters=12, tfidf_encoder=self.tfidf_encoder)
        self.cluster_loader = ClusterLoader(self.semantic_cluster)
        self.cluster_hit_tracker = ClusterHitTracker(persist_path=cluster_hit_path)
        # 尝试加载已有聚类索引（启动时不重新计算）
        self.semantic_cluster.load(cluster_index_path)

        # 🧠 Phase 6: 智能按需加载（命中学习）
        hit_graph_path = str(self.base_dir / '.dna' / 'strands' / 'hit_graph.json')
        disabled_combos_path = str(self.base_dir / '.dna' / 'strands' / 'disabled_combos.json')
        self.hit_graph = HitGraph(persist_path=hit_graph_path)
        self.smart_loader = SmartLoader(self.hit_graph, self.cluster_loader,
                                        persist_path=disabled_combos_path)

        # 绑定生命周期管理器到主系统（用于模式补全辅助重构）
        self.lifecycle.bind_system(self)

        # 聚类索引脏标记（ingest/evolve/consolidate 后置 True）
        self._cluster_dirty = False
        # 聚类索引就绪标记（Bug修复: _boot 提前 return 时不会赋值, 冷缓存必崩）
        self._clusters_ready = False

        # 当前内存中的DNA池
        self.pool: list[DNA] = []

        # 🧠 海马体优化：O(1)查找索引
        self._dna_by_id: dict[str, DNA] = {}       # id -> DNA 快速查找
        self._episode_ids: set[str] = set()         # EPISODE类型的DNA ID集合

        # 启动时加载已有记忆
        self._boot()

        # 计算启动时间
        boot_time = time.time() - boot_start

        # 显示启动状态
        if show_status:
            stats = self.stats()
            stats['boot_time'] = boot_time
            self.display.show_boot_status(stats)

    def _boot(self):
        """启动：加载 .dna/ 中的所有记忆，自动衰减，构建索引"""
        # 🧠 v3.1: 自动衰减 —— 计算距离上次启动的时间，衰减所有DNA
        boot_info = self._load_boot_info()
        last_boot = boot_info.get("last_boot", time.time())
        elapsed_hours = (time.time() - last_boot) / 3600
        self._save_boot_info()

        loaded = self.store.load_all()
        self.pool = [d for d in loaded if d.is_alive]

        # 加载进化模式
        patterns = self.store.load_patterns()
        self.evolution.patterns = [p for p in patterns if p.is_alive]

        # 🧠 v3.1: 自动衰减（距上次启动超过1小时才触发）
        if elapsed_hours > 1.0 and self.pool:
            before = len(self.pool)
            self.lifecycle.tick(self.pool, elapsed_hours)
            # 清理已死亡和碎片化的DNA
            alive = [d for d in self.pool if d.is_alive and not d.is_fragmented]
            dead_ids = {d.id for d in self.pool if not d.is_alive}
            self.pool = alive
            # 从磁盘清理死DNA
            if dead_ids:
                removed = self.store.cleanup_dead({d.id for d in self.pool})
                print(f"[DNA Boot] 自动衰减 {elapsed_hours:.0f}h: {before}→{len(self.pool)} (+{removed}文件清理)")

        if not self.pool:
            return

        # 构建 TF-IDF 语料库（启动时一次性计算 IDF）
        corpus = [self._extract_text(d) for d in self.pool]
        self.tfidf_encoder.build_idf(corpus)

        # 检查向量维度一致性（纯确定性引擎，只检查维度）
        expected_dim = 512
        need_revector = any(
            len(d.magnetic_vector) != expected_dim for d in self.pool[:5]
        )
        if need_revector:
            for d in self.pool:
                text = self._extract_text(d)
                d.magnetic_vector = self.magnetic.generate_vector(text, dim=expected_dim)
            self.store.save_all(self.pool)

        # 构建向量索引
        self.magnetic.rebuild_index(self.pool)

        # 构建时间索引
        self.temporal_index.rebuild(self.pool)

        # 🧠 构建海马体快速查找索引
        self._rebuild_lookup_indexes()

        # 🧠 Phase 4-6: 聚类索引和预加载 —— 延迟到首次查询（v3.1懒加载优化）
        self._clusters_ready = False

    def _ensure_clusters(self):
        """延迟构建语义聚类索引和预加载（首次查询时触发，节省启动时间）"""
        if self._clusters_ready:
            return

        need_rebuild = False
        if not self.semantic_cluster._built:
            if len(self.pool) >= 5:
                need_rebuild = True
        elif self._cluster_dirty:
            need_rebuild = True
        else:
            cluster_stats = self.semantic_cluster.stats()
            indexed_count = cluster_stats.get("total_dnas", 0)
            if indexed_count > 0:
                deviation = abs(len(self.pool) - indexed_count) / indexed_count
                if deviation > 0.2:
                    need_rebuild = True
            elif len(self.pool) >= 5:
                need_rebuild = True

        if need_rebuild:
            self._build_cluster_index()
            self._cluster_dirty = False

        # 先标记ready再预加载（防止smart_preload递归触发_ensure_clusters）
        self._clusters_ready = True
        # Phase 6: 智能预加载高频簇
        self._smart_preload_on_boot()

    def _load_boot_info(self) -> dict:
        """加载上次启动信息（用于计算衰减时间）"""
        boot_path = self.base_dir / '.dna' / 'boot_info.json'
        try:
            if boot_path.exists():
                with open(boot_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"first_boot": time.time(), "last_boot": time.time()}

    def _save_boot_info(self):
        """保存本次启动时间"""
        boot_path = self.base_dir / '.dna' / 'boot_info.json'
        try:
            boot_path.parent.mkdir(parents=True, exist_ok=True)
            info = {"last_boot": time.time()}
            # 保留第一次启动时间
            old = self._load_boot_info()
            info["first_boot"] = old.get("first_boot", time.time())
            with open(boot_path, 'w', encoding='utf-8') as f:
                json.dump(info, f)
        except Exception:
            pass

    def _rebuild_lookup_indexes(self):
        """重建O(1)查找索引（海马体优化）"""
        self._dna_by_id = {d.id: d for d in self.pool}
        self._episode_ids = {d.id for d in self.pool if d.dna_type == DNAType.EPISODE}

    def _build_cluster_index(self):
        """构建语义聚类索引并持久化"""
        result = self.semantic_cluster.fit(self.pool, self.tagger)
        # 持久化
        cluster_index_path = str(self.base_dir / '.dna' / 'strands' / 'cluster_index.json')
        self.semantic_cluster.save(cluster_index_path)

    def get_dna_by_id(self, dna_id: str) -> Optional[DNA]:
        """O(1) DNA查找（海马体优化）"""
        return self._dna_by_id.get(dna_id)

    def get_episodes(self) -> list[DNA]:
        """O(n_episodes) 获取所有情景DNA（海马体优化）"""
        return [self._dna_by_id[eid] for eid in self._episode_ids if eid in self._dna_by_id]

    def is_episode(self, dna_id: str) -> bool:
        """O(1) 判断是否为EPISODE类型（海马体优化）"""
        return dna_id in self._episode_ids

    def _smart_preload_on_boot(self):
        """
        🧠 Phase 6: 启动时智能预加载高频簇 + L0核心记忆

        C3修复: 启动预加载是推测性的，不标记为"命中"。
        只有实际使用簇时才通过 learn_hit() 记录命中。

        W5修复: 启动时实际调用 load_core_memories() 加载L0核心记忆，
        避免 cluster_loader.loaded_clusters 始终为0。
        """
        if not self.semantic_cluster._built:
            return

        # Phase 6: 基于命中图的高频话题预加载
        all_topics = self.hit_graph.get_all_topics()
        if all_topics:
            # 按命中次数排序，取前5个高频话题
            sorted_topics = sorted(
                all_topics,
                key=lambda t: self.hit_graph.topic_totals.get(t, 0),
                reverse=True,
            )[:5]

            # 获取预加载簇ID
            preload_cids = self.hit_graph.get_preload_clusters(sorted_topics, threshold=0.4)
            if preload_cids and self.cluster_loader.is_ready():
                already_loaded = self.cluster_loader.get_loaded_clusters()
                for cid in preload_cids:
                    if cid in already_loaded:
                        continue
                    member_ids = self.cluster_loader.get_cluster_members(cid)
                    if member_ids:
                        self.cluster_loader.mark_cluster_loaded(cid)

        # W5修复: 实际加载L0核心记忆（之前只标记了簇但未加载DNA内容）
        if self.cluster_loader.is_ready():
            self.load_core_memories()

    def smart_preload(self, context_text: str) -> list:
        """
        🧠 Phase 6: 根据上下文智能预加载相关簇

        Args:
            context_text: 当前对话上下文文本

        Returns:
            预加载的DNA列表
        """
        self._ensure_clusters()
        return self.smart_loader.preload_for_context(
            context_text, self.pool, self._dna_by_id, self.magnetic
        )

    def learn_hit(self, context_text: str, cluster_ids: list[int]):
        """
        🧠 Phase 6: 学习命中关联

        记录"话题→簇"的命中关系，用于改进预加载预测。

        Args:
            context_text: 上下文文本
            cluster_ids: 实际使用的簇ID列表
        """
        self.smart_loader.learn(context_text, cluster_ids)
        self.smart_loader.mark_preload_hit(cluster_ids)

    def smart_recall(self, query: str, top_k: int = 10, use_brain: bool = True) -> dict:
        self._ensure_clusters()
        """
        🧠 智能回忆：串联完整记忆管线

        流程:
        1. smart_loader.preload_for_context() — 智能预加载相关簇
        2. cluster_loader.load_l1_topic() — 加载话题记忆
        3. brain.recall() — 联想大脑被动联想
        4. cluster_hit_tracker.record_hit() — 记录命中
        5. 返回合并去重结果 + 统计信息

        Args:
            query: 查询文本
            top_k: 最大返回数
            use_brain: 是否启用联想大脑

        Returns:
            {
                "results": [{id, text, source, _score, ...}, ...],
                "stats": {preloaded, brain_hits, cluster_hits, total_unique}
            }
        """
        stats = {"preloaded": 0, "brain_hits": 0, "cluster_hits": 0, "total_unique": 0}

        # 1. smart_loader.preload_for_context() — 智能预加载相关簇
        preloaded = self.smart_loader.preload_for_context(
            query, self.pool, self._dna_by_id, self.magnetic
        )
        stats["preloaded"] = len(preloaded)

        # 2. cluster_loader.load_l1_topic() — 加载话题记忆
        topic_loaded, hit_cid = self.cluster_loader.load_l1_topic(
            query, self.pool, self._dna_by_id, self.magnetic
        )

        # 3. brain.recall() — 联想大脑被动联想
        brain_results = []
        if use_brain:
            brain_results = self.brain.recall(query, top_k=top_k)
            stats["brain_hits"] = len(brain_results)

        # 4. cluster_hit_tracker.record_hit() — 记录命中
        if hit_cid is not None:
            self.cluster_hit_tracker.record_hit(hit_cid, "L1", query)

        # 4b. 记录 smart_loader 预加载命中
        if preloaded:
            self.smart_loader.mark_preload_hit([1])

        # 5. 合并去重 + 统计
        seen_ids = set()
        merged = []

        for dna in preloaded:
            if dna.id not in seen_ids:
                seen_ids.add(dna.id)
                merged.append(self._dna_to_result(dna))

        for dna in topic_loaded:
            if dna.id not in seen_ids:
                seen_ids.add(dna.id)
                merged.append(self._dna_to_result(dna))

        for br in brain_results:
            bid = br.get("id", str(id(br)))
            if bid not in seen_ids:
                seen_ids.add(bid)
                merged.append(br)

        stats["cluster_hits"] = len(topic_loaded)
        stats["total_unique"] = len(merged)

        # 记录Token节省
        total_hits = len(merged)
        if total_hits > 0:
            from dna_system.core.token_tracker import tracker
            tracker.record_hit(
                query=query,
                hit_count=total_hits,
                hit_type='smart_recall',
                estimated_tokens_per_hit=150
            )

        return {
            "results": merged[:top_k],
            "stats": stats,
        }

    def _dna_to_result(self, dna) -> dict:
        """将DNA对象转换为结果字典（用于smart_recall输出）"""
        content = dna.content
        text = ""
        if isinstance(content, dict):
            for key in ('summary', 'description', 'text', 'pattern_name', 'compressed_text'):
                if key in content and content[key]:
                    text = str(content[key])
                    break
            if not text:
                import json as _json
                text = _json.dumps(content, ensure_ascii=False)[:200]
        elif isinstance(content, str):
            text = content[:200]
        else:
            text = str(content)[:200]

        return {
            "id": dna.id,
            "text": text,
            "source": dna.source or "",
            "_score": getattr(dna, 'lifetime', 0.5),
            "_from_dna": True,
        }

    def preload_stats(self) -> dict:
        self._ensure_clusters()
        """
        🧠 Phase 6: 获取智能预加载统计

        Returns:
            预加载统计信息
        """
        return self.smart_loader.stats()

    def hippocampus_health_check(self) -> dict:
        """海马体健康检查（检查所有海马体子系统）"""
        return {
            "lookup_indexes": {
                "dna_by_id": len(self._dna_by_id),
                "episode_ids": len(self._episode_ids),
                "pool_size": len(self.pool),
            },
            "temporal_index": self.temporal_index.stats(),
            "episodic": self.episodic.stats(),
            "consolidation": self.consolidation.stats(),
            "pattern_completion": self.pattern_completion.stats(),
            "cognitive_map": self.cognitive_map.stats(),
        }

    def _extract_text(self, dna: DNA) -> str:
        """从DNA中提取用于生成向量的文本"""
        content = dna.content
        if not content:
            return dna.source or ""
        # 优先用 summary/文本内容
        for key in ('summary', 'text', 'full_text', 'command', 'pattern_name', 'compressed_text'):
            if key in content and content[key]:
                return str(content[key])
        # 否则拼接所有字段
        return json.dumps(content, ensure_ascii=False)[:500]

    def query(self, question: str) -> list[dict]:
        """
        查询：通过轴心分发命令，磁吸匹配返回结果
        """
        responses = self.axis.execute(question, self.pool)

        results = []
        for resp in responses:
            results.append({
                "dna_id": resp.source,
                "content": resp.content,
                "summary": self.compile_chain.decompile(resp, "summary"),
                "lifetime": resp.parent_id
            })

        # 同时查询进化出的模式
        patterns = self.evolution.query_by_pattern(question)
        for p in patterns:
            results.append({
                "dna_id": p.id,
                "content": p.content,
                "summary": f"[洞察] {p.content.get('pattern_name', '')}",
                "type": "pattern"
            })

        return results

    def query_with_feedback(self, question: str, show: bool = True) -> tuple[list[dict], str]:
        """
        带反馈的查询

        Returns:
            (结果列表, query_id)
        """
        start_time = time.time()
        results = self.query(question)
        query_time = time.time() - start_time

        # 记录查询
        result_ids = [r.get("dna_id") for r in results if r.get("dna_id")]
        query_id = self.access_tracker.record_query(question, result_ids)

        # 记录Token节省
        if results:
            from dna_system.core.token_tracker import tracker
            tracker.record_hit(
                query=question,
                hit_count=len(results),
                hit_type='dna',
                estimated_tokens_per_hit=150
            )

        # 显示结果
        if show:
            self.display.show_query_result(question, results, query_time)

        return results, query_id

    def mark_result_used(self, query_id: str, dna_id: str):
        """标记查询结果被使用"""
        self.access_tracker.mark_used(query_id, dna_id)
        # 🧠 海马体优化：O(1)查找DNA并增加访问计数
        dna = self._dna_by_id.get(dna_id)
        if dna:
            dna.access()

    # ===== 时间查询 API (Phase 1: 海马体进化) =====

    def query_by_date(self, date_str: str) -> list[dict]:
        """
        查询某天的所有记忆

        Args:
            date_str: 日期字符串，格式 "2026-06-03"

        Returns:
            匹配的DNA信息列表
        """
        dna_ids = self.temporal_index.query_by_date(date_str)
        return self._resolve_ids(dna_ids)

    def query_by_time_range(self, start: str, end: str) -> list[dict]:
        """
        查询时间范围内的记忆

        Args:
            start: 起始时间，格式 "2026-06-03" 或 "2026-06-03 14:00"
            end: 结束时间，格式 "2026-06-04" 或 "2026-06-04 18:00"

        Returns:
            匹配的DNA信息列表
        """
        from datetime import datetime as dt
        fmts = ["%Y-%m-%d %H:%M", "%Y-%m-%d"]
        start_dt = end_dt = None
        for fmt in fmts:
            try:
                start_dt = dt.strptime(start, fmt)
                break
            except ValueError:
                continue
        for fmt in fmts:
            try:
                end_dt = dt.strptime(end, fmt)
                break
            except ValueError:
                continue

        if not start_dt or not end_dt:
            return []

        dna_ids = self.temporal_index.query_by_range(start_dt, end_dt)
        return self._resolve_ids(dna_ids)

    def query_recent(self, hours: int = 24) -> list[dict]:
        """
        查询最近N小时的记忆

        Args:
            hours: 小时数，默认24

        Returns:
            匹配的DNA信息列表
        """
        dna_ids = self.temporal_index.query_recent(hours)
        return self._resolve_ids(dna_ids)

    def query_today(self) -> list[dict]:
        """查询今天的记忆"""
        dna_ids = self.temporal_index.query_today()
        return self._resolve_ids(dna_ids)

    def query_by_episode(self, episode_id: str) -> list[dict]:
        """
        查询某个情景下的所有记忆

        Args:
            episode_id: 情景ID

        Returns:
            匹配的DNA信息列表
        """
        dna_ids = self.temporal_index.query_by_episode(episode_id)
        return self._resolve_ids(dna_ids)

    def get_memory_timeline(self) -> dict:
        """获取记忆时间线概览"""
        dates = self.temporal_index.get_date_list()
        timeline = {}
        for date_str in dates:
            timeline[date_str] = len(self.temporal_index.query_by_date(date_str))
        return {
            "dates": timeline,
            "total_days": len(dates),
            "index_stats": self.temporal_index.stats(),
        }

    # ===== 情景记忆 API (Phase 2: 海马体进化) =====

    def record_episode(self, trigger: str, actions, outcome: str,
                       context: dict = None) -> dict:
        """
        记录一个情景事件

        Args:
            trigger: 触发器描述
            actions: 执行的动作（字符串或列表）
            outcome: 结果描述
            context: 额外上下文信息

        Returns:
            创建的Episode信息字典
        """
        episode = self.episodic.record_episode(trigger, actions, outcome, context)
        return episode.to_dict()

    def recall_episodes(self, trigger: str, top_k: int = 5) -> list[dict]:
        """
        通过触发器回忆相关情景

        Args:
            trigger: 触发器文本
            top_k: 返回前K个匹配

        Returns:
            匹配的Episode信息列表
        """
        results = self.episodic.recall_by_trigger(trigger, top_k)
        return [
            {
                "episode": ep.to_dict(),
                "score": score,
            }
            for ep, score in results
        ]

    # ===== 睡眠巩固 API (Phase 3: 海马体进化) =====

    def run_consolidation(self, hours: float = 24) -> dict:
        """
        运行一个睡眠巩固周期

        Args:
            hours: 回顾最近多少小时的情景

        Returns:
            巩固报告 dict
        """
        return self.consolidation.consolidate(hours)

    # ===== 模式补全 API (Phase 4: 海马体进化) =====

    def complete_memory(self, partial_cue: dict) -> dict | None:
        """
        从部分线索重建完整记忆

        Args:
            partial_cue: 部分线索字典

        Returns:
            补全后的Episode字典，无匹配则返回None
        """
        result = self.pattern_completion.complete(partial_cue)
        if result is None:
            return None
        return result.to_dict()

    def hint_memory(self, partial_text: str, top_k: int = 5) -> list[dict]:
        """
        轻量提示：返回相关DNA摘要

        Args:
            partial_text: 部分文本/线索
            top_k: 返回前K个

        Returns:
            相关DNA摘要列表
        """
        return self.pattern_completion.hint(partial_text, top_k)

    # ===== 认知地图 API (Phase 5: 海马体进化) =====

    def build_memory_map(self, method: str = "pca") -> dict:
        """
        构建记忆认知地图

        Args:
            method: 降维方法 ("pca")

        Returns:
            {dna_id: (x, y), ...} 坐标字典
        """
        return self.cognitive_map.build_map(method=method)

    def get_memory_map_data(self, edge_radius: float = 0.5) -> dict:
        """
        获取记忆地图可视化数据

        Args:
            edge_radius: 边连接半径阈值

        Returns:
            {"nodes": [...], "edges": [...]}
        """
        return self.cognitive_map.export_map_data(edge_radius=edge_radius)

    def find_nearby_memories(self, dna_id: str, radius: float = 1.0) -> list[str]:
        """
        找到某个记忆附近的其它记忆

        Args:
            dna_id: 目标DNA ID
            radius: 搜索半径

        Returns:
            附近DNA ID列表
        """
        return self.cognitive_map.find_nearby(dna_id, radius)

    # ===== 语义聚类 API (Phase 4: 记忆按需加载) =====

    def rebuild_cluster_index(self) -> dict:
        """
        重建语义聚类索引

        Returns:
            聚类结果摘要
        """
        result = self.semantic_cluster.fit(self.pool, self.tagger)
        cluster_index_path = str(self.base_dir / '.dna' / 'strands' / 'cluster_index.json')
        self.semantic_cluster.save(cluster_index_path)
        return result

    def load_core_memories(self) -> list:
        self._ensure_clusters()
        """
        加载L0核心记忆（启动时调用）

        Returns:
            核心DNA列表
        """
        loaded = self.cluster_loader.load_l0_core(self.pool, self._dna_by_id)
        # 记录命中：为每个 L0 簇记录 hit
        if loaded:
            l0_clusters = self.semantic_cluster.get_level_clusters("L0")
            for cid in l0_clusters:
                self.cluster_hit_tracker.record_hit(cid, "L0", "启动核心加载")
        return loaded

    def load_topic_memories(self, query_text: str) -> list:
        self._ensure_clusters()
        """
        加载L1话题记忆（用户提到游戏名时调用）

        Args:
            query_text: 用户输入文本

        Returns:
            话题DNA列表
        """
        loaded, hit_cid = self.cluster_loader.load_l1_topic(
            query_text, self.pool, self._dna_by_id, self.magnetic
        )
        # 记录命中（使用 load_l1_topic 返回的 cluster_id，避免重复 predict）
        if loaded and hit_cid is not None:
            self.cluster_hit_tracker.record_hit(hit_cid, "L1", query_text)
        return loaded

    def load_deep_memories(self, query_text: str) -> list:
        self._ensure_clusters()
        """
        加载L2深层记忆（具体问题触发）

        Args:
            query_text: 用户输入文本

        Returns:
            深层DNA列表
        """
        loaded = self.cluster_loader.load_l2_deep(
            query_text, self.pool, self._dna_by_id, self.magnetic
        )
        if loaded:
            cid, _ = self.semantic_cluster.predict(query_text, self.magnetic)
            if cid is not None:
                self.cluster_hit_tracker.record_hit(cid, "L2", query_text)
        return loaded

    def predict_cluster(self, query_text: str) -> dict:
        self._ensure_clusters()
        """
        预测查询应该加载哪个簇

        Args:
            query_text: 查询文本

        Returns:
            {cluster_id, similarity, meta} 或 {cluster_id: None}
        """
        cid, sim = self.semantic_cluster.predict(query_text, self.magnetic)
        if cid is not None:
            meta = self.semantic_cluster.get_meta(cid)
            return {"cluster_id": cid, "similarity": round(sim, 4), "meta": meta}
        return {"cluster_id": None, "similarity": 0.0, "meta": None}

    def get_cluster_overview(self) -> dict:
        self._ensure_clusters()
        """获取聚类概览"""
        return self.semantic_cluster.get_all_meta()

    def get_hot_clusters(self, hours: int = 24) -> list:
        self._ensure_clusters()
        """获取高频命中簇"""
        return self.cluster_hit_tracker.get_hot_clusters(window_secs=hours * 3600)

    def reset_cluster_loader(self):
        """重置簇加载状态（新一轮会话开始时）"""
        self.cluster_loader.reset()

        return True

    def _resolve_ids(self, dna_ids: list[str]) -> list[dict]:
        """将DNA ID列表解析为信息字典列表（海马体优化：O(1)查找）"""
        results = []
        for dna_id in dna_ids:
            dna = self._dna_by_id.get(dna_id)
            if dna:
                results.append({
                    "dna_id": dna.id,
                    "content": dna.content,
                    "summary": self.compile_chain.decompile(dna, "summary"),
                    "created_at": dna.created_at,
                    "tags": dna.tags,
                    "episode_id": dna.episode_id,
                })
        return results

    def ingest(self, source: str, data: Any = None, tags: list[str] = None) -> list[DNA]:
        """
        摄入：把外部信息编译为DNA
        source 可以是文件路径或文本
        """
        if Path(source).exists():
            # 文件摄入
            dnas = self.compile_chain.compile_file(source)
        else:
            # 文本摄入
            dnas = [self.compile_chain.compile(data or source, source="user", tags=tags)]

        if dnas:
            self.pool.extend(dnas)
            self.store.save_all(dnas)
            # 增量更新索引
            self.magnetic.index.add_batch(dnas)
            # 增量更新时间索引
            for dna in dnas:
                self.temporal_index.add(dna)
            # 🧠 增量更新查找索引
            for dna in dnas:
                self._dna_by_id[dna.id] = dna
                if dna.dna_type == DNAType.EPISODE:
                    self._episode_ids.add(dna.id)
            # 标记聚类索引需重建
            self._cluster_dirty = True

        return dnas

    def ingest_with_quality(self, source: str, data: Any = None, tags: list[str] = None) -> list[DNA]:
        """
        带质量过滤的摄入
        """
        # 先检查内容质量
        if data and isinstance(data, str):
            should_ingest, score = self.quality_filter.should_ingest(data)
            if not should_ingest:
                return []

        # 正常摄入（ingest内部已维护查找索引）
        dnas = self.ingest(source, data, tags)

        # 为每个DNA添加智能标签
        for dna in dnas:
            content_text = str(dna.content)
            smart_tags = self.tagger.extract_tags(content_text, dna.tags)
            dna.tags = smart_tags

        return dnas

    def evolve(self, safe_mode: bool = True, show: bool = True) -> dict:
        """
        触发养蛊进化

        Args:
            safe_mode: 安全模式先备份
            show: 是否显示结果

        Returns:
            进化报告
        """
        before = len(self.pool)

        # 安全模式：先备份
        if safe_mode and before > 10:
            self.store.save_all(self.pool)

        self.pool = self.evolution.devour(self.pool)
        # 异种杂交：跨类型DNA重组
        self.evolution.cross_breed(self.pool)
        patterns = self.evolution.get_patterns()
        self.store.save_all(self.pool)
        # 保存进化模式
        self.store.save_patterns(patterns)
        # 重建索引
        self.magnetic.rebuild_index(self.pool)
        # 重建时间索引
        self.temporal_index.rebuild(self.pool)
        # 🧠 重建查找索引
        self._rebuild_lookup_indexes()
        # 标记聚类索引需重建
        self._cluster_dirty = True

        after = len(self.pool)

        # 显示结果
        if show:
            self.display.show_evolution_result(before, after, len(patterns))

        return {
            "before": before,
            "after": after,
            "patterns": len(patterns),
        }

    def tick(self, hours: float = 24):
        """时间推进：衰减、碎片化、重构"""
        self.pool = self.lifecycle.tick(self.pool, hours)
        self.pool = self.lifecycle.check_and_reconstruct(self.pool)
        self.store.save_all(self.pool)
        # 重建索引
        self.magnetic.rebuild_index(self.pool)
        # 重建时间索引
        self.temporal_index.rebuild(self.pool)
        # 🧠 重建查找索引
        self._rebuild_lookup_indexes()

    def stats(self) -> dict:
        """系统状态"""
        patterns = self.evolution.get_patterns()
        vec_info = self.magnetic.get_vector_info()
        temporal_stats = self.temporal_index.stats()

        # 实时读取DNA文件数量（包括新记录的）
        import os
        strand_dir = str(self.base_dir / '.dna' / 'strands')
        if os.path.exists(strand_dir):
            real_count = len([f for f in os.listdir(strand_dir) if f.endswith('.json')])
        else:
            real_count = len(self.pool)

        # 联想大脑统计
        brain_stats = self.brain.stats()

        # 语义聚类统计
        cluster_stats = self.semantic_cluster.stats()
        cluster_loader_stats = self.cluster_loader.stats()
        cluster_hit_stats = self.cluster_hit_tracker.stats()

        # 记忆压缩统计

        # Phase 6: 智能预加载统计
        smart_loader_stats = self.smart_loader.stats()

        # 海马体进化统计 (Phase 2-5)
        episodic_stats = self.episodic.stats()
        consolidation_stats = self.consolidation.stats()
        pattern_completion_stats = self.pattern_completion.stats()
        cognitive_map_stats = self.cognitive_map.stats()

        return {
            "dna_count": real_count,
            "patterns": len(patterns),
            "storage": self.store.size(),
            "fragments": self.lifecycle.stats()["fragment_count"],
            "magnetic_threshold": self.magnetic.threshold,
            "vector_engine": vec_info,
            "temporal_index": temporal_stats,
            "episodic": episodic_stats,
            "consolidation": consolidation_stats,
            "pattern_completion": pattern_completion_stats,
            "cognitive_map": cognitive_map_stats,
            "brain": brain_stats,
            "semantic_cluster": cluster_stats,
            "cluster_loader": cluster_loader_stats,
            "cluster_hits": cluster_hit_stats,
            "smart_loader": smart_loader_stats,
        }

    def run_maintenance(self, show: bool = True) -> dict:
        """
        运行维护

        Args:
            show: 是否显示报告

        Returns:
            维护报告
        """
        report = self.maintenance.run_full_maintenance()

        if show:
            self.display.show_maintenance_report(report)

        return report

    def get_quality_report(self, show: bool = True) -> dict:
        """
        获取质量报告

        Args:
            show: 是否显示报告

        Returns:
            质量报告
        """
        report = self.maintenance.get_quality_report()

        if show:
            self.display.show_quality_report(report)

        return report

    def save(self):
        """手动保存"""
        self.store.save_all(self.pool)
        self.brain.save()
        # 保存聚类命中记录
        self.cluster_hit_tracker.save()
        # 保存命中关联图（Phase 6）
        self.hit_graph.save()

    # ===== 联想大脑快捷方法 =====

    def recall_brain(self, query: str, top_k: int = 5, enable_wormhole: bool = True) -> list[dict]:
        """
        联想大脑：被动联想

        Args:
            query: 查询文本
            top_k: 最大返回数
            enable_wormhole: 启用虫洞展开

        Returns:
            相关记忆列表
        """
        results = self.brain.recall(query, top_k, enable_wormhole)

        # 记录Token节省
        if results:
            from dna_system.core.token_tracker import tracker
            tracker.record_hit(
                query=query,
                hit_count=len(results),
                hit_type='brain',
                estimated_tokens_per_hit=200  # 联想大脑的命中通常更精准
            )

        return results

    def check_brain(self, context: str) -> list:
        """
        联想大脑：主动监控

        Args:
            context: 当前任务/对话上下文

        Returns:
            提醒列表
        """
        return self.brain.check(context)

    def add_brain(self, eid: str, text: str, energy: float = 0.5, pinned: bool = False) -> dict:
        """
        联想大脑：添加记忆

        Args:
            eid: 记忆ID
            text: 记忆内容
            energy: 能量值
            pinned: 是否永久锁定

        Returns:
            添加的记忆实体
        """
        entity = self.brain.add(eid, text, energy, pinned)
        return entity.to_dict()

    def format_brain_alerts(self, alerts: list) -> str:
        """格式化联想大脑提醒"""
        return self.brain.format_alerts(alerts)

    # ===== 自动记录快捷方法 =====

    def auto_commit(self) -> Optional[DNA]:
        """自动记录最近一次 commit"""
        dna = self.recorder.record_commit()
        if dna:
            self.pool.append(dna)
            self.magnetic.index.add(dna)
            self._dna_by_id[dna.id] = dna
        return dna

    def auto_session(self, summary: str, show: bool = True) -> Optional[DNA]:
        """自动记录会话摘要，并尝试提取情景事件"""
        dna = self.recorder.record_session(summary)
        if dna:
            self.pool.append(dna)
            self.magnetic.index.add(dna)
            self._dna_by_id[dna.id] = dna

            if show:
                self.display.show_session_summary(summary)
        return dna

    def auto_snapshot(self) -> Optional[DNA]:
        """自动记录项目快照"""
        dna = self.recorder.record_snapshot()
        if dna:
            self.pool.append(dna)
            self.magnetic.index.add(dna)
            self._dna_by_id[dna.id] = dna
        return dna

    # ===== Web服务器 =====

    def start_web(self, host: str = '127.0.0.1', port: int = 8080, background: bool = True):
        """
        启动Web服务器，提供实时仪表盘

        Args:
            host: 监听地址
            port: 监听端口
            background: 是否后台运行

        Returns:
            服务器URL
        """
        from .web.server import DNAWebServer
        self.web_server = DNAWebServer(self, host, port)
        self.web_server.start(background)
        return self.web_server.get_url()

    def stop_web(self):
        """停止Web服务器"""
        if hasattr(self, 'web_server') and self.web_server:
            self.web_server.stop()

    def open_window(self, port: int = 8080):
        """
        打开仪表盘窗口（阻塞）

        Args:
            port: 端口号
        """
        from .web.window import open_dashboard_window
        open_dashboard_window(self, port)

    def open_browser(self, port: int = 8080):
        """
        在浏览器中打开仪表盘（非阻塞）

        Args:
            port: 端口号

        Returns:
            仪表盘URL
        """
        from .web.window import open_dashboard_background
        return open_dashboard_background(self, port)

    # ===== Git同步 =====

    def git_init(self, repo_url: str = None) -> tuple[bool, str]:
        """
        初始化Git仓库

        Args:
            repo_url: 远程仓库URL

        Returns:
            (成功, 消息)
        """
        dna_dir = str(self.store.root)
        self.git = GitSync(dna_dir, self.git_config.get("git"))
        return self.git.init(repo_url)

    def git_push(self, message: str = None) -> tuple[bool, str]:
        """
        推送记忆到Git仓库

        Args:
            message: 提交消息

        Returns:
            (成功, 消息)
        """
        if not self.git:
            self.git = GitSync(str(self.store.root), self.git_config.get("git"))

        # 先保存当前状态
        self.save()

        # 推送
        return self.git.push()

    def git_pull(self) -> tuple[bool, str]:
        """
        从Git仓库拉取记忆

        Returns:
            (成功, 消息)
        """
        if not self.git:
            self.git = GitSync(str(self.store.root), self.git_config.get("git"))

        # 拉取
        success, msg = self.git.pull()

        if success:
            # 重新加载记忆
            self._boot()
            self.magnetic.rebuild_index(self.pool)

        return success, msg

    def git_sync(self) -> tuple[bool, str]:
        """
        双向同步记忆

        Returns:
            (成功, 消息)
        """
        if not self.git:
            self.git = GitSync(str(self.store.root), self.git_config.get("git"))

        # 先保存
        self.save()

        # 同步
        success, msg = self.git.sync()

        if success:
            # 重新加载记忆
            self._boot()
            self.magnetic.rebuild_index(self.pool)

        return success, msg

    def git_status(self) -> dict:
        """
        获取Git状态

        Returns:
            状态信息
        """
        if not self.git:
            self.git = GitSync(str(self.store.root), self.git_config.get("git"))

        return self.git.status()

    # ===== 数据加密 =====

    def enable_encryption(self, key: str = None) -> bool:
        """
        启用数据加密

        Args:
            key: 加密密钥（不提供则使用默认密钥）

        Returns:
            是否成功
        """
        try:
            self.protector = DataProtector(key)
            self._encryption_enabled = True

            # 加密现有数据
            self._encrypt_all_data()

            return True
        except Exception as e:
            print(f"启用加密失败: {e}")
            return False

    def disable_encryption(self) -> bool:
        """
        禁用数据加密（解密所有数据）

        Returns:
            是否成功
        """
        try:
            # 解密所有数据
            self._decrypt_all_data()
            self._encryption_enabled = False

            return True
        except Exception as e:
            print(f"禁用加密失败: {e}")
            return False

    def _encrypt_all_data(self):
        """加密所有数据文件"""
        if not self._encryption_enabled:
            return

        # 加密strands目录
        strands_dir = self.store.root / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                self.protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()  # 删除原文件

        # 加密patterns目录
        patterns_dir = self.store.root / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                self.protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()

        # 加密配置文件
        config_file = self.store.root / "manifest.json"
        if config_file.exists():
            encrypted_path = str(config_file) + ".enc"
            self.protector.encrypt_file(str(config_file), encrypted_path)
            config_file.unlink()

    def _decrypt_all_data(self):
        """解密所有数据文件"""
        # 解密strands目录
        strands_dir = self.store.root / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]  # 移除.enc后缀
                self.protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()  # 删除加密文件

        # 解密patterns目录
        patterns_dir = self.store.root / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]
                self.protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()

        # 解密配置文件
        config_file = self.store.root / "manifest.json.enc"
        if config_file.exists():
            decrypted_path = str(config_file)[:-4]
            self.protector.decrypt_file(str(config_file), decrypted_path)
            config_file.unlink()

    def encrypt_string(self, text: str) -> str:
        """
        加密字符串

        Args:
            text: 原文

        Returns:
            加密后的字符串
        """
        return self.protector.encrypt_string(text)

    def decrypt_string(self, encrypted_text: str) -> str:
        """
        解密字符串

        Args:
            encrypted_text: 加密字符串

        Returns:
            解密后的原文
        """
        return self.protector.decrypt_string(encrypted_text)

    def verify_integrity(self) -> tuple[bool, list[str]]:
        """
        验证数据完整性

        Returns:
            (是否完整, 错误列表)
        """
        manifest_path = self.store.root / "integrity_manifest.json"

        if not manifest_path.exists():
            # 生成清单
            self.checker.generate_manifest(str(self.store.root), str(manifest_path))
            return True, []

        # 验证
        return self.checker.verify_directory(str(self.store.root), str(manifest_path))

    def generate_integrity_manifest(self) -> dict:
        """
        生成完整性清单

        Returns:
            清单字典
        """
        manifest_path = self.store.root / "integrity_manifest.json"
        return self.checker.generate_manifest(str(self.store.root), str(manifest_path))
