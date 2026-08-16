"""
DNA Memory Engine — 可移植的智能体记忆优化引擎

用法:
    from dna_memory_engine import MemoryEngine

    engine = MemoryEngine("./my_memory")
    engine.add("记忆内容", tags=["标签"])
    core = engine.load_core()
"""

from .engine import MemoryEngine, Memory

__version__ = "1.0.0"
__all__ = ["MemoryEngine", "Memory"]
