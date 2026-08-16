"""
🧠 DNA-Strand 记忆系统 — 通用联想大脑核心

零模型依赖的记忆系统：从文本固有结构提取 DNA 信号，用坐标共振匹配相关记忆，
四层记忆池按生命周期自动晋升/淘汰。支持磁吸匹配、虫洞展开、多模型辩证。

本包是「通用向量/联想记忆核心」，不绑定任何业务垂直领域。

使用方法:
    from dna_system.core.brain import Brain

    brain = Brain(memory_dir=".dna")
    brain.load()
    brain.add("id-1", "碰撞检测Bug", energy=0.6)
    results = brain.recall("碰撞", top_k=5)
"""

__version__ = "3.1.0"

from .core.brain import Brain, get_brain, recall, check, add

__all__ = [
    "Brain",
    "get_brain",
    "recall",
    "check",
    "add",
]
