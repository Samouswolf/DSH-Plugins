"""
🧠 联想大脑 — 四层记忆池

核心思想：记忆按生命周期分层管理，自动晋升/淘汰。

四层结构：
  热层 (hot)      — 当前会话临时缓冲，纯内存，不写盘
  冷层 (cold)     — 几天内记忆，能量衰减(0.05/24h)，自动清理噪音
  沉淀层 (settle) — 稳定长期记忆，从冷层升级得来
  保护层 (protect) — 永久锁定，铁律/已验证经验，不可删除

生命周期：
  新记忆 → 冷层(能量≤0.5)
  冷层能量≥0.5 → 沉淀层
  冷层能量≤0 → 删除
  热层查3次以上 → 冷层
"""

from __future__ import annotations
import json
import time
import os
from typing import Dict, List, Optional, Set
from .brain_encoder import extract_dna


# ════════════════════════════════════════════════════════════
# 记忆实体
# ════════════════════════════════════════════════════════════

class MemoryEntity:
    """记忆实体"""

    def __init__(
        self,
        eid: str,
        text: str,
        dna: Optional[Dict[str, List[str]]] = None,
        energy: float = 0.5,
        pinned: bool = False,
        layer: str = "cold",
        source: str = "manual",
        meta: Optional[Dict] = None,
    ):
        self.id = eid
        self.text = text
        self.dna = dna or extract_dna(text)
        self.energy = energy
        self.pinned = pinned
        self.layer = layer
        self.source = source
        self.meta = meta or {}
        self.created = time.time()
        self.last_accessed = time.time()
        self.access_count = 0

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "text": self.text,
            "dna": self.dna,
            "energy": self.energy,
            "pinned": self.pinned,
            "layer": self.layer,
            "source": self.source,
            "meta": self.meta,
            "created": self.created,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "MemoryEntity":
        ent = cls(
            eid=data["id"],
            text=data["text"],
            dna=data.get("dna"),
            energy=data.get("energy", 0.5),
            pinned=data.get("pinned", False),
            layer=data.get("layer", "cold"),
            source=data.get("source", "manual"),
            meta=data.get("meta", {}),
        )
        ent.created = data.get("created", time.time())
        ent.last_accessed = data.get("last_accessed", ent.created)
        ent.access_count = data.get("access_count", 0)
        return ent

    def touch(self):
        """更新访问时间"""
        self.last_accessed = time.time()
        self.access_count += 1


# ════════════════════════════════════════════════════════════
# 四层记忆池
# ════════════════════════════════════════════════════════════

class BrainPool:
    """
    四层记忆池。

    热层 (hot)      — 当前会话临时缓冲，纯内存，不写盘
    冷层 (cold)     — 几天内记忆，能量衰减，自动清理噪音
    沉淀层 (settle) — 稳定长期记忆，从冷层升级得来
    保护层 (protect) — 永久锁定，铁律/已验证经验，不可删除
    """

    LAYER_ORDER = ["hot", "cold", "settle", "protect"]

    def __init__(self):
        # 四层存储
        self.layers: Dict[str, List[MemoryEntity]] = {
            "hot": [],       # 纯内存，不持久化
            "cold": [],      # 冷层
            "settle": [],    # 沉淀层
            "protect": [],   # 保护层
        }

        # 索引
        self._entity_map: Dict[str, MemoryEntity] = {}
        self._pinned: Set[str] = set()

        # 热层参数
        self.hot_query_count: Dict[str, int] = {}
        self.hot_promote_threshold = 3  # 查3次以上推冷层

        # 冷层参数
        self.cold_decay_per_cycle = 0.05      # 每24h周期衰减
        self.cold_promote_threshold = 0.5     # 超过此值进沉淀
        self.cold_delete_threshold = 0.0      # 低于此值删除

        # 版本
        self._version = 0

    # ── 添加记忆 ──

    def add(
        self,
        eid: str,
        text: str,
        energy: float = 0.5,
        pinned: bool = False,
        layer: Optional[str] = None,
        source: str = "manual",
        meta: Optional[Dict] = None,
    ) -> MemoryEntity:
        """添加一条记忆。pinned实体进保护层，否则进冷层。"""
        # 确定层级
        if layer:
            target_layer = layer
        elif pinned:
            target_layer = "protect"
        else:
            target_layer = "cold"

        # 创建实体
        entity = MemoryEntity(
            eid=eid,
            text=text,
            energy=min(energy, 0.5) if target_layer == "cold" else energy,
            pinned=pinned,
            layer=target_layer,
            source=source,
            meta=meta,
        )

        # 修复(Bug2): 同 eid 先移除全部旧条目, 避免僵尸条目(recall 召回矛盾记忆)
        for lay_name, lay in list(self.layers.items()):
            keep = [e for e in lay if e.id != eid]
            if len(keep) != len(lay):
                self.layers[lay_name] = keep
                if eid in self._pinned:
                    self._pinned.discard(eid)
        self._entity_map.pop(eid, None)

        # 添加到对应层
        self.layers[target_layer].append(entity)
        self._entity_map[eid] = entity

        if pinned or target_layer == "protect":
            self._pinned.add(eid)

        self._version += 1
        return entity

    def add_hot(self, text: str, source: str = "session") -> MemoryEntity:
        """添加一个热层实体（当前会话临时记忆）。"""
        hot_id = f"hot_{int(time.time())}_{len(self.layers['hot'])}"
        return self.add(
            eid=hot_id,
            text=text,
            energy=0.3,
            layer="hot",
            source=source,
        )

    # ── 查询记忆 ──

    def get(self, eid: str) -> Optional[MemoryEntity]:
        """获取实体"""
        return self._entity_map.get(eid)

    def get_all(self) -> List[MemoryEntity]:
        """获取所有实体（四层合并）"""
        result = []
        for layer in self.LAYER_ORDER:
            result.extend(self.layers[layer])
        return result

    def get_by_layer(self, layer: str) -> List[MemoryEntity]:
        """获取指定层的实体"""
        return self.layers.get(layer, [])

    def count(self) -> int:
        """总实体数"""
        return len(self._entity_map)

    def layer_stats(self) -> Dict:
        """各层统计"""
        return {
            layer: {
                "count": len(ents),
                "avg_energy": round(
                    sum(e.energy for e in ents) / max(len(ents), 1), 3
                ),
            }
            for layer, ents in self.layers.items()
        }

    # ── 热层操作 ──

    def promote_hot_to_cold(self, eid: str) -> Optional[MemoryEntity]:
        """将热实体升级为冷层实体。"""
        entity = None
        for i, e in enumerate(self.layers["hot"]):
            if e.id == eid:
                entity = self.layers["hot"].pop(i)
                break

        if entity is None:
            return None

        entity.layer = "cold"
        entity.id = f"cold_{int(time.time())}_{len(self.layers['cold'])}"
        entity.energy = 0.3  # 冷层起始能量

        # 更新索引
        del self._entity_map[eid]
        self._entity_map[entity.id] = entity

        self.layers["cold"].append(entity)
        self._version += 1
        return entity

    def clear_hot(self) -> Dict:
        """清空热层，返回被查询次数超过阈值的实体（待推冷层）。"""
        promotable = []
        for e in self.layers["hot"]:
            count = self.hot_query_count.get(e.id, 0)
            if count >= self.hot_promote_threshold:
                promotable.append(e)

        self.layers["hot"] = []
        self.hot_query_count.clear()
        self._version += 1

        return {
            "cleared": len(promotable),
            "promotable": promotable,
        }

    # ── 冷层衰减 ──

    def decay_cold(self, cycles: int = 1) -> Dict:
        """
        冷层能量衰减。
        衰减后能量 ≥ promote_threshold → 进沉淀层
        衰减后能量 ≤ delete_threshold → 删除
        其余保持冷层。
        """
        promoted = []
        deleted = []
        kept = []

        for e in self.layers["cold"]:
            e.energy -= self.cold_decay_per_cycle * cycles
            if e.energy >= self.cold_promote_threshold:
                e.layer = "settle"
                promoted.append(e)
            elif e.energy <= self.cold_delete_threshold:
                deleted.append(e)
            else:
                kept.append(e)

        self.layers["cold"] = kept
        self.layers["settle"].extend(promoted)

        # 更新索引
        for e in deleted:
            del self._entity_map[e.id]

        self._version += 1
        return {
            "promoted": len(promoted),
            "deleted": len(deleted),
            "kept": len(kept),
        }

    # ── 删除/更新 ──

    def remove(self, eid: str) -> bool:
        """从所有层删除实体。保护层的不让删。"""
        if eid in self._pinned:
            return False

        for layer in ["hot", "cold", "settle"]:
            before = len(self.layers[layer])
            self.layers[layer] = [e for e in self.layers[layer] if e.id != eid]
            if len(self.layers[layer]) < before:
                if eid in self._entity_map:
                    del self._entity_map[eid]
                self._version += 1
                return True
        return False

    def update_energy(self, eid: str, delta: float):
        """更新实体能量"""
        entity = self._entity_map.get(eid)
        if entity:
            entity.energy = max(0.0, min(2.0, entity.energy + delta))
            entity.touch()

    # ── 访问追踪 ──

    def track_access(self, eid: str):
        """追踪实体被访问"""
        entity = self._entity_map.get(eid)
        if entity:
            entity.touch()
            # 热层追踪
            if entity.layer == "hot":
                self.hot_query_count[eid] = self.hot_query_count.get(eid, 0) + 1

    # ── 持久化 ──

    def save(self, path: str):
        """保存到文件（hot层不保存）"""
        data = {
            "version": self._version,
            "pinned": list(self._pinned),
            "entities": [],
            "saved_at": time.time(),
        }

        # 只保存 cold/settle/protect
        for layer in ["cold", "settle", "protect"]:
            for e in self.layers[layer]:
                data["entities"].append(e.to_dict())

        # 原子写入
        import tempfile
        tmp = tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8",
            dir=os.path.dirname(path) or ".",
            prefix=".brain_pool_",
            suffix=".json",
            delete=False,
        )
        try:
            json.dump(data, tmp, ensure_ascii=False, indent=2)
            tmp.close()
            os.replace(tmp.name, path)
        except Exception:
            try:
                os.unlink(tmp.name)
            except OSError:
                pass
            raise

    @classmethod
    def load(cls, path: str) -> "BrainPool":
        """从文件加载"""
        pool = cls()

        if not os.path.exists(path):
            return pool

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        pinned_ids = set(data.get("pinned", []))

        for ent_data in data.get("entities", []):
            entity = MemoryEntity.from_dict(ent_data)

            # 确定层级
            layer = entity.layer
            if layer not in ("cold", "settle", "protect"):
                layer = "protect" if entity.id in pinned_ids else "cold"
            entity.layer = layer

            # 添加到对应层
            pool.layers[layer].append(entity)
            pool._entity_map[entity.id] = entity

            if layer == "protect" or entity.id in pinned_ids:
                pool._pinned.add(entity.id)

        pool._version = data.get("version", 0)
        return pool

    # ── 从旧系统迁移 ──

    @classmethod
    def from_legacy_dna(cls, dna_list: List[Dict]) -> "BrainPool":
        """从旧DNA系统迁移"""
        pool = cls()

        for i, dna_data in enumerate(dna_list):
            # 提取内容
            content = dna_data.get("content", {})
            if isinstance(content, dict):
                text = content.get("text", "")
                if not text:
                    text = str(content)[:200]
            elif isinstance(content, str):
                text = content
            else:
                text = str(content)[:200]

            if not text:
                continue

            # 提取能量
            energy = dna_data.get("energy", 0.5)

            # 判断是否保护层
            pinned = energy > 0.8

            pool.add(
                eid=dna_data.get("id", f"legacy_{i}"),
                text=text,
                energy=energy,
                pinned=pinned,
                source="legacy",
            )

        return pool
