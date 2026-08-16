"""DNA-Strand 核心模块（精简版）"""

# 原有模块
from .magnetic import MagneticEngine
from .wormhole import Axis
from .compile import CompileChain
from .lifecycle import LifecycleManager
from .evolution import EvolutionEngine
from .smart_tagger import SmartTagger
from .quality_filter import QualityFilter
from .access_tracker import AccessTracker
from .temporal_index import TemporalIndex
from .intelligence import IntelligenceEngine

# 海马体进化模块 (Phase 2-5)
from .episodic import EpisodicMemory, Episode
from .consolidation import MemoryConsolidation
from .pattern_completion import PatternCompletion
from .cognitive_map import CognitiveMap

# 联想大脑模块
from .brain import Brain, get_brain, recall, check, add
from .brain_encoder import extract_dna, encode_game_memory, identify_game, identify_system
from .brain_resonance import magnetic_resonance, cross_game_resonance, coordinate_resonance
from .brain_pool import BrainPool, MemoryEntity
from .brain_wormhole import wormhole_expand, smart_wormhole_expand, game_wormhole_expand
from .semantic_cluster import SemanticCluster
from .cluster_loader import ClusterLoader
from .cluster_tracker import ClusterHitTracker
from .hit_graph import HitGraph
from .topic_extractor import TopicExtractor
from .smart_loader import SmartLoader

__all__ = [
    "MagneticEngine", "Axis", "CompileChain", "LifecycleManager",
    "EvolutionEngine", "SmartTagger", "QualityFilter", "AccessTracker",
    "TemporalIndex", "IntelligenceEngine",
    # 海马体进化模块 (Phase 2-5)
    "EpisodicMemory", "Episode", "MemoryConsolidation",
    "PatternCompletion", "CognitiveMap",
    "Brain", "get_brain", "recall", "check", "add",
    "extract_dna", "encode_game_memory", "identify_game", "identify_system",
    "magnetic_resonance", "cross_game_resonance", "coordinate_resonance",
    "BrainPool", "MemoryEntity",
    "wormhole_expand", "smart_wormhole_expand", "game_wormhole_expand",
    "SemanticCluster", "ClusterLoader", "ClusterHitTracker",
    "HitGraph", "TopicExtractor", "SmartLoader",
]
