"""
虫洞路由系统
轴心(天然的万象隧道)收到命令 → 提取为DNA → 通过虫洞分发
→ 复制体到达虫洞位置 → 磁力指向目标 → 精准匹配
→ 目标DNA反向发送指针(复制体) → 回到轴心 → 完成

整个过程非常快且没有能力递归，风险由游离DNA带走，用完即毁。

v2: 双链闭环强化 —— 正链匹配到目标并收到反链后，关联网络整体强化
"""
import time
import uuid
from dataclasses import dataclass, field
from typing import Callable, Optional
from .dna import DNA, DNAType, StrandType
from .magnetic import MagneticEngine


@dataclass
class WormholeRoute:
    """虫洞路由记录"""
    route_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    source_dna_id: str = ""
    target_dna_id: str = ""
    resolved: bool = False
    created_at: float = field(default_factory=time.time)


class Axis:
    """轴心 —— 天然的万象隧道，系统的核心调度器"""

    def __init__(self, magnetic: MagneticEngine):
        self.magnetic = magnetic
        self.routes: list[WormholeRoute] = []
        self.handlers: dict[str, Callable] = {}  # DNA类型 → 处理函数

    def register_handler(self, dna_type: str, handler: Callable):
        """注册DNA处理函数"""
        self.handlers[dna_type] = handler

    def receive(self, command: str, context: dict = None) -> DNA:
        """
        接收命令，提取为DNA（基本单位）
        这是架构的核心入口：一切外部输入都通过轴心转化为DNA
        """
        cmd_dna = DNA(
            dna_type=DNAType.COMMAND,
            strand=StrandType.FORWARD,
            content={"command": command, "context": context or {}},
            magnetic_vector=self.magnetic.generate_vector(command),
            source="axis",
        )
        return cmd_dna

    def dispatch(self, cmd_dna: DNA, target_pool: list[DNA]) -> list[DNA]:
        """
        通过虫洞分发DNA
        原理：复制DNA → 通过虫洞到目标 → 磁力匹配 → 销毁复制体
        v2: 双链闭环强化 —— 正链匹配后，关联网络整体强化
        """
        # 寻找虫洞节点（与命令最匹配的目标DNA们）
        wormhole_targets = self.magnetic.find_wormhole(cmd_dna, target_pool)

        responses = []
        for target in wormhole_targets:
            # 复制体DNA（指针）从母体复制
            pointer = DNA(
                dna_type=DNAType.POINTER,
                strand=StrandType.FORWARD,
                content=cmd_dna.content.copy(),
                magnetic_vector=cmd_dna.magnetic_vector.copy(),
                source=cmd_dna.id,
                target=target.id,
                lifetime=1.0,  # 用完即毁
                parent_id=cmd_dna.id,
            )

            # 记录路由
            route = WormholeRoute(
                source_dna_id=pointer.id,
                target_dna_id=target.id,
            )
            self.routes.append(route)

            # 目标DNA被访问（生命值回升）
            target.access()

            # 创建反向指针（目标DNA的响应）
            reverse_pointer = DNA(
                dna_type=DNAType.POINTER,
                strand=StrandType.REVERSE,
                content=target.content.copy(),
                magnetic_vector=target.magnetic_vector.copy(),
                source=target.id,
                target=cmd_dna.id,
                lifetime=1.0,
                parent_id=target.id,
            )
            route.resolved = True
            responses.append(reverse_pointer)

            # 正向指针销毁
            pointer.lifetime = 0

            # === 双链闭环强化 (v3: 用索引找 top-K 共振，不再全量 cluster) ===
            # 找与目标最相似的 3 个 DNA（共振强化）
            resonance_results = self.magnetic.index.search_top_k(
                target.magnetic_vector, k=4  # 包含自己，实际取3个
            )
            for rid, sim in resonance_results:
                if rid == target.id:
                    continue
                # 找到对应的 DNA 并强化
                for candidate in target_pool:
                    if candidate.id == rid and candidate.is_alive:
                        candidate.lifetime = min(100, candidate.lifetime + 2)
                        break
            # 目标DNA本身获得更多加成
            target.lifetime = min(100, target.lifetime + 5)
            target.access_count += 2

        return responses

    def execute(self, command: str, target_pool: list[DNA], context: dict = None) -> list[DNA]:
        """
        完整执行流程：接收 → 提取DNA → 虫洞分发 → 磁吸匹配 → 返回指针
        """
        cmd_dna = self.receive(command, context)
        responses = self.dispatch(cmd_dna, target_pool)

        # 命令DNA用完即毁
        cmd_dna.lifetime = 0

        return responses
