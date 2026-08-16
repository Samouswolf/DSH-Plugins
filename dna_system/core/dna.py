"""
DNA 基本单元 —— 万能用译文本
计算机上一切信息都有一个相同的元信息，抽象为 DNA。
它是坐标，是代码本身，是遗传信息，是编译链。
"""
import uuid
import time
import hashlib
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Any
from enum import Enum


class StrandType(Enum):
    FORWARD = "forward"    # 正链：主动请求/命令
    REVERSE = "reverse"    # 反链：响应/指针返回


class DNAType(Enum):
    COMMAND = "command"    # 命令
    DATA = "data"          # 数据
    MEMORY = "memory"      # 记忆
    POINTER = "pointer"    # 指针（游离DNA）
    PATTERN = "pattern"    # 模式（归纳产物）
    EPISODE = "episode"    # 情景（事件链记忆）


@dataclass
class DNA:
    """DNA 基本单元"""
    # 唯一坐标
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    # 类型
    dna_type: DNAType = DNAType.DATA
    strand: StrandType = StrandType.FORWARD

    # 多模态内容（万能语言）
    content: dict[str, Any] = field(default_factory=dict)

    # 磁吸向量（归一性）
    magnetic_vector: np.ndarray = field(default_factory=lambda: np.zeros(512))

    # 来源坐标
    source: str = ""
    # 目标坐标（虫洞指向）
    target: str = ""

    # 生命周期
    lifetime: float = 100.0       # 初始生命值
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0

    # 链路
    parent_id: Optional[str] = None
    child_ids: list[str] = field(default_factory=list)

    # 多模态标签
    tags: list[str] = field(default_factory=list)
    modality: str = "text"  # text|code|schema|image|audio

    # 时间索引字段（Phase 1: 海马体进化）
    temporal_tags: list[str] = field(default_factory=list)  # ["2026-06-03", "下午", "14:00"]
    episode_id: Optional[str] = None  # 所属情景ID
    sequence_index: Optional[int] = None  # 在情景中的顺序

    @property
    def coord(self) -> str:
        """DNA 的3D坐标哈希"""
        return hashlib.md5(self.id.encode()).hexdigest()[:16]

    @property
    def is_alive(self) -> bool:
        return self.lifetime > 0

    @property
    def is_fragmented(self) -> bool:
        """坍缩为碎片（life < 20 时视为碎片化）"""
        return 0 < self.lifetime <= 20

    def access(self) -> None:
        """被访问：生命值回升"""
        self.last_accessed = time.time()
        self.access_count += 1
        # 每次访问恢复少量生命值
        self.lifetime = min(100, self.lifetime + 5)

    def decay(self, elapsed_hours: float) -> None:
        """随时间衰减"""
        decay_rate = 0.5  # 每小时衰减量
        self.lifetime = max(0, self.lifetime - decay_rate * elapsed_hours)

    def fragment(self) -> list['DNA']:
        """坍缩为碎片"""
        fragments = []
        # 将内容拆分为碎片（保留关键信息）
        for key, value in self.content.items():
            frag = DNA(
                dna_type=DNAType.POINTER,
                strand=StrandType.REVERSE,
                content={"key": key, "fragment": str(value)[:100]},
                magnetic_vector=self.magnetic_vector * 0.5,
                source=self.id,
                lifetime=5.0,
                tags=self.tags,
                parent_id=self.id
            )
            fragments.append(frag)
        return fragments

    def to_dict(self) -> dict:
        result = {
            "id": self.id,
            "dna_type": self.dna_type.value,
            "strand": self.strand.value,
            "content": self.content,
            "magnetic_vector": self.magnetic_vector.tolist(),
            "source": self.source,
            "target": self.target,
            "lifetime": self.lifetime,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "tags": self.tags,
            "modality": self.modality,
            "coord": self.coord
        }
        # 时间索引字段（仅在非空时写入，减小文件体积）
        if self.temporal_tags:
            result["temporal_tags"] = self.temporal_tags
        if self.episode_id is not None:
            result["episode_id"] = self.episode_id
        if self.sequence_index is not None:
            result["sequence_index"] = self.sequence_index
        return result

    @classmethod
    def from_dict(cls, data: dict) -> 'DNA':
        return cls(
            id=data["id"],
            dna_type=DNAType(data["dna_type"]),
            strand=StrandType(data["strand"]),
            content=data["content"],
            magnetic_vector=np.array(data["magnetic_vector"]),
            source=data.get("source", ""),
            target=data.get("target", ""),
            lifetime=data["lifetime"],
            created_at=data["created_at"],
            last_accessed=data.get("last_accessed", time.time()),
            access_count=data.get("access_count", 0),
            parent_id=data.get("parent_id"),
            child_ids=data.get("child_ids", []),
            tags=data.get("tags", []),
            modality=data.get("modality", "text"),
            temporal_tags=data.get("temporal_tags", []),
            episode_id=data.get("episode_id"),
            sequence_index=data.get("sequence_index")
        )
