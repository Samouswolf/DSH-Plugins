"""
DNA-Strand 记忆系统 v3.0

一个完整的AI Agent记忆生态系统，支持:
- 向量索引加速查询
- 智能标签自动提取
- 内容质量过滤
- 访问反馈追踪
- 定期维护优化
- 自动记录机制
- 太空驾驶舱仪表盘
- 脑形神经元网络
- 自动窗口（最小化/关闭）

使用方法:
    from dna_system import DNASystem

    # 初始化系统（自动显示状态窗口）
    system = DNASystem()

    # 查询记忆
    results = system.query("暗影幸存者")

    # 带反馈的查询
    results, query_id = system.query_with_feedback("贪吃蛇")
    system.mark_result_used(query_id, results[0]["dna_id"])

    # 摄入新记忆
    system.ingest("path/to/file.md")
    system.ingest("新记忆内容", tags=["标签1", "标签2"])

    # 进化
    system.evolve()

    # 维护
    system.run_maintenance()
    system.get_quality_report()

    # 自动记录
    system.auto_commit()
    system.auto_session("会话摘要")
    system.auto_snapshot()

    # 打开仪表盘窗口
    system.open_window()  # 阻塞，支持最小化/关闭
    system.open_browser() # 非阻塞，在浏览器中打开
"""

__version__ = "3.0.0"
__author__ = "小德"

from .system import DNASystem
from .core.dna import DNA, DNAType, StrandType
from .core.smart_tagger import SmartTagger
from .core.quality_filter import QualityFilter
from .core.access_tracker import AccessTracker
from .core.maintenance import MaintenanceEngine

__all__ = [
    "DNASystem",
    "DNA",
    "DNAType",
    "StrandType",
    "SmartTagger",
    "QualityFilter",
    "AccessTracker",
    "MaintenanceEngine",
]
