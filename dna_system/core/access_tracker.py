"""
访问反馈追踪器 —— 记录查询结果是否被使用
增强版：添加命中路径记录、每周报告、高价值记忆簇识别
"""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from typing import List, Dict, Tuple, Optional


class AccessTracker:
    """访问反馈追踪器"""

    def __init__(self, base_dir: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.feedback_file = self.base_dir / ".dna" / "access_feedback.json"
        self.feedback_data = self._load_feedback()

    def _load_feedback(self) -> dict:
        """加载反馈数据"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "query_results": {},
            "dna_scores": {},
            "query_history": [],
            "hit_paths": [],
            "cluster_hits": {},
            "weekly_reports": [],
        }

    def _save_feedback(self):
        """保存反馈数据"""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump(self.feedback_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def record_query(self, query: str, result_ids: list[str], cluster_info: dict = None) -> str:
        """
        记录一次查询及其结果
        返回: query_id（用于后续标记哪些结果被使用）
        """
        query_id = f"q_{int(time.time() * 1000)}"
        self.feedback_data["query_results"][query_id] = {
            "query": query,
            "result_ids": result_ids,
            "timestamp": time.time(),
            "used_ids": [],
            "cluster_info": cluster_info or {},
        }

        if len(self.feedback_data["query_history"]) > 2000:
            self.feedback_data["query_history"] = self.feedback_data["query_history"][-1000:]

        self.feedback_data["query_history"].append({
            "query_id": query_id,
            "query": query,
            "result_count": len(result_ids),
            "timestamp": time.time(),
        })

        if cluster_info:
            for cluster_id, hits in cluster_info.items():
                if cluster_id not in self.feedback_data["cluster_hits"]:
                    self.feedback_data["cluster_hits"][cluster_id] = {"hits": 0, "queries": []}
                self.feedback_data["cluster_hits"][cluster_id]["hits"] += hits
                self.feedback_data["cluster_hits"][cluster_id]["queries"].append({
                    "query": query,
                    "timestamp": time.time(),
                })

        self._save_feedback()
        return query_id

    def mark_used(self, query_id: str, dna_id: str, usage_context: str = ""):
        """标记某个结果被使用"""
        if query_id in self.feedback_data["query_results"]:
            if dna_id not in self.feedback_data["query_results"][query_id]["used_ids"]:
                self.feedback_data["query_results"][query_id]["used_ids"].append(dna_id)

                if dna_id not in self.feedback_data["dna_scores"]:
                    self.feedback_data["dna_scores"][dna_id] = {"used": 0, "ignored": 0}
                self.feedback_data["dna_scores"][dna_id]["used"] += 1

                self.feedback_data["hit_paths"].append({
                    "query_id": query_id,
                    "dna_id": dna_id,
                    "query": self.feedback_data["query_results"][query_id]["query"],
                    "timestamp": time.time(),
                    "usage_context": usage_context,
                })

                if len(self.feedback_data["hit_paths"]) > 5000:
                    self.feedback_data["hit_paths"] = self.feedback_data["hit_paths"][-2500:]

                self._save_feedback()

    def mark_ignored(self, query_id: str, dna_id: str):
        """标记某个结果被忽略"""
        if query_id in self.feedback_data["query_results"]:
            if dna_id not in self.feedback_data["query_results"][query_id]["used_ids"]:
                if dna_id not in self.feedback_data["dna_scores"]:
                    self.feedback_data["dna_scores"][dna_id] = {"used": 0, "ignored": 0}
                self.feedback_data["dna_scores"][dna_id]["ignored"] += 1

                self._save_feedback()

    def get_dna_score(self, dna_id: str) -> float:
        """获取DNA的使用分数"""
        if dna_id not in self.feedback_data["dna_scores"]:
            return 0.5

        scores = self.feedback_data["dna_scores"][dna_id]
        total = scores["used"] + scores["ignored"]
        if total == 0:
            return 0.5

        return scores["used"] / total

    def get_top_dnas(self, limit: int = 20) -> List[Tuple[str, float, int]]:
        """获取被使用最多的DNA，返回 (dna_id, score, used_count)"""
        scored = []
        for dna_id, scores in self.feedback_data["dna_scores"].items():
            total = scores["used"] + scores["ignored"]
            if total > 0:
                score = scores["used"] / total
                scored.append((dna_id, score, scores["used"]))

        scored.sort(key=lambda x: x[2], reverse=True)
        return scored[:limit]

    def get_query_stats(self) -> dict:
        """获取查询统计"""
        queries = self.feedback_data.get("query_history", [])
        if not queries:
            return {"total_queries": 0, "avg_results": 0}

        total_queries = len(queries)
        avg_results = sum(q["result_count"] for q in queries) / total_queries

        recent_cutoff = time.time() - 86400
        recent_queries = [q for q in queries if q["timestamp"] > recent_cutoff]

        hit_paths = self.feedback_data.get("hit_paths", [])
        total_used = sum(1 for path in hit_paths)

        return {
            "total_queries": total_queries,
            "recent_queries": len(recent_queries),
            "avg_results": round(avg_results, 1),
            "total_used_results": total_used,
            "avg_used_per_query": round(total_used / total_queries, 1) if total_queries > 0 else 0,
        }

    def get_weekly_report(self, days: int = 7) -> dict:
        """生成每周报告"""
        cutoff = time.time() - (days * 86400)

        recent_queries = [q for q in self.feedback_data.get("query_history", []) if q["timestamp"] > cutoff]
        recent_hit_paths = [p for p in self.feedback_data.get("hit_paths", []) if p["timestamp"] > cutoff]

        dna_usage_count = defaultdict(int)
        for path in recent_hit_paths:
            dna_usage_count[path["dna_id"]] += 1

        query_keywords = defaultdict(int)
        for q in recent_queries:
            for kw in ["Bug", "修复", "碰撞", "渲染", "UI", "逻辑"]:
                if kw in q["query"]:
                    query_keywords[kw] += 1

        top_dnas = sorted(dna_usage_count.items(), key=lambda x: -x[1])[:10]

        cluster_hits = {}
        for cluster_id, info in self.feedback_data.get("cluster_hits", {}).items():
            recent_cluster_queries = [q for q in info.get("queries", []) if q["timestamp"] > cutoff]
            if recent_cluster_queries:
                cluster_hits[cluster_id] = {
                    "total_hits": info["hits"],
                    "recent_queries": len(recent_cluster_queries),
                    "sample_queries": [q["query"] for q in recent_cluster_queries[:3]],
                }

        return {
            "period": f"最近{days}天",
            "generated_at": datetime.now().isoformat(),
            "query_stats": {
                "total_queries": len(recent_queries),
                "total_used_results": len(recent_hit_paths),
                "avg_results_per_query": round(sum(q["result_count"] for q in recent_queries) / len(recent_queries), 1) if recent_queries else 0,
            },
            "top_dnas": [{"dna_id": dna_id, "usage_count": count} for dna_id, count in top_dnas],
            "query_keywords": dict(query_keywords),
            "cluster_hits": cluster_hits,
        }

    def get_high_value_clusters(self, min_hits: int = 3) -> List[dict]:
        """识别高价值记忆簇"""
        high_value = []
        for cluster_id, info in self.feedback_data.get("cluster_hits", {}).items():
            if info["hits"] >= min_hits:
                high_value.append({
                    "cluster_id": cluster_id,
                    "hit_count": info["hits"],
                    "query_count": len(info.get("queries", [])),
                    "sample_queries": [q["query"] for q in info.get("queries", [])[:5]],
                })

        high_value.sort(key=lambda x: -x["hit_count"])
        return high_value


# 全局实例
access_tracker = None

def get_access_tracker(base_dir: str = None) -> AccessTracker:
    """获取全局访问追踪器实例"""
    global access_tracker
    if access_tracker is None:
        access_tracker = AccessTracker(base_dir)
    return access_tracker
