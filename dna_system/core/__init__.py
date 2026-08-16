"""DNA-Strand 核心模块 — 通用联想大脑"""

# 联想大脑模块
from .brain import Brain, get_brain, recall, check, add
from .brain_encoder import extract_dna, extract_tokens, TFIDFEncoder
from .brain_resonance import magnetic_resonance, coordinate_resonance, compute_idf, text_fallback
from .brain_pool import BrainPool, MemoryEntity
from .brain_wormhole import wormhole_expand, smart_wormhole_expand

__all__ = [
    "Brain", "get_brain", "recall", "check", "add",
    "extract_dna", "extract_tokens", "TFIDFEncoder",
    "magnetic_resonance", "coordinate_resonance", "compute_idf", "text_fallback",
    "BrainPool", "MemoryEntity",
    "wormhole_expand", "smart_wormhole_expand",
]
