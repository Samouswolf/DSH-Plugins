"""
.dna/ 存储层
自带空间，不需沙盘基座，环境无关。
复制 .dna/ 到任何工程即可使用，记忆随身携带。

v2: 批量写入优化 + 进化模式持久化
"""
import json
import os
import time
from datetime import datetime, date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from ..core.dna import DNA


class _DNAEncoder(json.JSONEncoder):
    """处理 datetime、numpy 等非标量类型"""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                return float(obj)
            if isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return str(obj)


class DNAStore:
    """DNA 持久化存储 (v2: 批量写入 + 模式持久化)"""

    def __init__(self, base_dir: str = None):
        if base_dir:
            self.root = Path(base_dir) / ".dna"
        else:
            self.root = Path(".dna")
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "strands").mkdir(exist_ok=True)
        (self.root / "wormholes").mkdir(exist_ok=True)
        (self.root / "compile_chain").mkdir(exist_ok=True)
        (self.root / "patterns").mkdir(exist_ok=True)  # 进化模式存储
        self._ensure_manifest()
        self._executor = ThreadPoolExecutor(max_workers=4)  # 并行写入

    def _ensure_manifest(self):
        manifest_path = self.root / "manifest.json"
        if not manifest_path.exists():
            manifest = {
                "version": "2.0",
                "created_at": time.time(),
                "project": os.getcwd(),
                "description": "DNA-Strand 记忆库 —— 即插即用，环境无关"
            }
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, ensure_ascii=False, indent=2)

    def _write_json(self, filepath: Path, data: dict):
        """单个JSON文件写入"""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2, cls=_DNAEncoder)

    def save(self, dna: DNA):
        """保存单个DNA"""
        filepath = self.root / "strands" / f"{dna.id}.json"
        self._write_json(filepath, dna.to_dict())

    def save_all(self, dnas: list[DNA]):
        """批量保存（并行写入）"""
        alive = [d for d in dnas if d.is_alive]
        if not alive:
            return

        # 并行写入
        futures = []
        for dna in alive:
            filepath = self.root / "strands" / f"{dna.id}.json"
            futures.append(self._executor.submit(self._write_json, filepath, dna.to_dict()))

        # 等待全部完成
        for f in futures:
            f.result()

    def save_patterns(self, patterns: list[DNA]):
        """保存进化模式（单独存储）"""
        for pattern in patterns:
            if pattern.is_alive:
                filepath = self.root / "patterns" / f"{pattern.id}.json"
                self._write_json(filepath, pattern.to_dict())

    def load_patterns(self) -> list[DNA]:
        """加载进化模式"""
        patterns = []
        patterns_dir = self.root / "patterns"
        if not patterns_dir.exists():
            return patterns

        # 加载普通JSON文件
        for filepath in patterns_dir.glob("*.json"):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                patterns.append(DNA.from_dict(data))
            except Exception:
                pass

        # 加载加密文件
        for filepath in patterns_dir.glob("*.enc"):
            try:
                from ..security.protector import DataProtector
                protector = DataProtector()
                # 解密到临时文件
                temp_path = str(filepath) + ".tmp"
                protector.decrypt_file(str(filepath), temp_path)
                with open(temp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                patterns.append(DNA.from_dict(data))
                # 删除临时文件
                Path(temp_path).unlink()
            except Exception:
                pass

        return patterns

    def load(self, dna_id: str) -> DNA | None:
        """加载单个DNA"""
        filepath = self.root / "strands" / f"{dna_id}.json"
        if not filepath.exists():
            return None
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return DNA.from_dict(data)

    def _load_one(self, filepath: Path) -> DNA | None:
        """加载单个JSON文件为DNA（供并行加载使用）"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return DNA.from_dict(data)
        except Exception:
            return None

    def load_all(self) -> list[DNA]:
        """加载所有DNA（v3: 并行读取，4线程加速）"""
        strands_dir = self.root / "strands"
        if not strands_dir.exists():
            return []

        # 收集所有JSON文件路径
        json_files = list(strands_dir.glob("*.json"))
        enc_files = list(strands_dir.glob("*.enc"))

        dnas = []

        # 并行加载普通JSON文件
        if json_files:
            futures = [self._executor.submit(self._load_one, fp) for fp in json_files]
            for f in futures:
                result = f.result()
                if result is not None:
                    dnas.append(result)

        # 加密文件保持串行（解密操作可能非线程安全）
        for filepath in enc_files:
            try:
                from ..security.protector import DataProtector
                protector = DataProtector()
                temp_path = str(filepath) + ".tmp"
                protector.decrypt_file(str(filepath), temp_path)
                with open(temp_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                dnas.append(DNA.from_dict(data))
                Path(temp_path).unlink()
            except Exception:
                pass

        return dnas

    def remove(self, dna_id: str):
        """删除DNA"""
        filepath = self.root / "strands" / f"{dna_id}.json"
        if filepath.exists():
            filepath.unlink()

    def count(self) -> int:
        return len(list((self.root / "strands").glob("*.json")))

    def clear(self):
        """清空所有DNA"""
        for f in (self.root / "strands").glob("*.json"):
            f.unlink()
        for f in (self.root / "wormholes").glob("*"):
            f.unlink()
        for f in (self.root / "patterns").glob("*"):
            f.unlink()

    def size(self) -> str:
        """存储空间大小"""
        total = 0
        for f in self.root.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        if total < 1024:
            return f"{total} B"
        elif total < 1024 * 1024:
            return f"{total / 1024:.1f} KB"
        else:
            return f"{total / (1024 * 1024):.1f} MB"

    def cleanup_dead(self, alive_ids: set[str], min_age_hours: float = 24):
        """清理已死亡的DNA文件（仅清理超过min_age_hours的）"""
        import time
        now = time.time()
        removed = 0
        for filepath in (self.root / "strands").glob("*.json"):
            dna_id = filepath.stem
            if dna_id not in alive_ids:
                # 检查文件年龄，太新的不删
                file_age_hours = (now - filepath.stat().st_mtime) / 3600
                if file_age_hours >= min_age_hours:
                    filepath.unlink()
                    removed += 1
        return removed
