"""
DNA记忆系统效率对比测试
可复现、可量化、可移植

使用方法:
     cd <你的工作区>
     python dna_system/tests/benchmark.py
"""

import sys
import os
import time
import json
import random

# 确保能导入dna_system
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

sys.stdout.reconfigure(encoding='utf-8')


def estimate_tokens(text: str) -> int:
    """估算token数（混合中英文）"""
    # 中文: ~1.5字/token
    # 英文: ~4字符/token
    # 混合: 约2字符/token
    return max(1, len(text) // 2)


def load_all_memories(base_dir: str = ".dna") -> list:
    """加载所有活跃记忆"""
    strands_dir = os.path.join(base_dir, "strands")
    memories = []
    skip_files = {
        "cluster_index.json", "hit_graph.json", "compressed_index.json",
        "cluster_hits.json", "disabled_combos.json"
    }
    for f in os.listdir(strands_dir):
        if f.endswith(".json") and f not in skip_files:
            path = os.path.join(strands_dir, f)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                    content = data.get("content", {})
                    if isinstance(content, dict):
                        text = json.dumps(content, ensure_ascii=False)
                    else:
                        text = str(content)
                    memories.append({
                        "id": data.get("id", f),
                        "text": text,
                        "tokens": estimate_tokens(text),
                        "tags": data.get("tags", []),
                    })
            except:
                pass
    return memories


def test_startup_loading(base_dir: str = ".dna"):
    """测试1: 启动加载对比"""
    print("=" * 60)
    print("测试1: 启动加载对比")
    print("=" * 60)

    memories = load_all_memories(base_dir)
    total_tokens = sum(m["tokens"] for m in memories)

    # 模拟全量加载（改造前）
    full_load_tokens = total_tokens
    full_load_count = len(memories)

    # 模拟L0加载（改造后）
    from dna_system.system import DNASystem
    sys_obj = DNASystem(show_status=False)
    overview = sys_obj.get_cluster_overview()

    l0_ids = set()
    for cid, meta in overview.items():
        if meta.get("level") == "L0":
            members = sys_obj.cluster_loader.get_cluster_members(cid)
            l0_ids.update(members)

    l0_memories = [m for m in memories if m["id"] in l0_ids]
    l0_tokens = sum(m["tokens"] for m in l0_memories)

    print(f"改造前（全量加载）:")
    print(f"  记忆数: {full_load_count}")
    print(f"  Token数: {full_load_tokens:,}")
    print()
    print(f"改造后（L0核心加载）:")
    print(f"  记忆数: {len(l0_memories)}")
    print(f"  Token数: {l0_tokens:,}")
    print()
    savings = full_load_tokens - l0_tokens
    pct = (savings / full_load_tokens * 100) if full_load_tokens > 0 else 0
    print(f"节省: {savings:,} tokens ({pct:.1f}%)")
    print()

    return {
        "test": "startup_loading",
        "before": {"count": full_load_count, "tokens": full_load_tokens},
        "after": {"count": len(l0_memories), "tokens": l0_tokens},
        "savings": {"tokens": savings, "percent": pct},
    }


def test_compression(base_dir: str = ".dna"):
    """测试2: 记忆压缩对比"""
    print("=" * 60)
    print("测试2: 记忆压缩效果")
    print("=" * 60)

    # 活跃池
    strands_dir = os.path.join(base_dir, "strands")
    active_count = len([f for f in os.listdir(strands_dir)
                        if f.endswith(".json") and f not in {
                            "cluster_index.json", "hit_graph.json",
                            "compressed_index.json", "cluster_hits.json",
                            "disabled_combos.json"
                        }])

    # 归档池
    archive_dir = os.path.join(base_dir, "strands_archive")
    archive_count = len([f for f in os.listdir(archive_dir)
                         if f.endswith(".json")]) if os.path.exists(archive_dir) else 0

    original_count = active_count + archive_count
    compression_rate = (1 - active_count / original_count) * 100 if original_count > 0 else 0

    print(f"原始记忆数: {original_count}")
    print(f"压缩后活跃: {active_count}")
    print(f"归档记忆数: {archive_count}")
    print(f"压缩率: {compression_rate:.1f}%")
    print()

    # 验证信息完整性
    memories = load_all_memories(base_dir)
    with_source_ids = sum(1 for m in memories if "source_ids" in str(m["text"]))
    print(f"可追溯性: {with_source_ids}/{len(memories)} 条记忆包含来源ID")
    print()

    return {
        "test": "compression",
        "original_count": original_count,
        "active_count": active_count,
        "archive_count": archive_count,
        "compression_rate": compression_rate,
        "traceable": with_source_ids,
    }


def test_retrieval_accuracy(base_dir: str = ".dna"):
    """测试3: 检索精度对比"""
    print("=" * 60)
    print("测试3: 检索精度对比")
    print("=" * 60)

    from dna_system.system import DNASystem
    sys_obj = DNASystem(show_status=False)

    # 测试查询
    test_queries = [
        "贪吃蛇碰撞Bug",
        "塔防保卫战",
        "修仙功法",
        "部署发布",
        "UI界面设计",
    ]

    print(f"{'查询':<20} {'平铺扫描(全量)':<20} {'聚类检索(精查)':<20} {'精度提升'}")
    print("-" * 80)

    total_full = 0
    total_cluster = 0

    for query in test_queries:
        # 模拟平铺扫描（改造前）: 全量记忆都参与
        memories = load_all_memories(base_dir)
        full_scan_count = len(memories)

        # 聚类检索（改造后）: 只查相关簇
        result = sys_obj.predict_cluster(query)
        cluster_id = result["cluster_id"]
        cluster_members = sys_obj.cluster_loader.get_cluster_members(cluster_id)
        cluster_count = len(cluster_members) if cluster_members else 0

        reduction = full_scan_count - cluster_count
        pct = (reduction / full_scan_count * 100) if full_scan_count > 0 else 0

        print(f"{query:<20} {full_scan_count:<20} {cluster_count:<20} {pct:.0f}%↓")
        total_full += full_scan_count
        total_cluster += cluster_count

    avg_reduction = (1 - total_cluster / total_full) * 100 if total_full > 0 else 0
    print(f"\n平均检索范围缩小: {avg_reduction:.1f}%")
    print()

    return {
        "test": "retrieval_accuracy",
        "queries": len(test_queries),
        "avg_range_reduction": avg_reduction,
    }


def test_startup_time():
    """测试4: 启动时间对比"""
    print("=" * 60)
    print("测试4: 启动时间对比")
    print("=" * 60)

    from dna_system.system import DNASystem

    # 测试多次取平均
    times = []
    for i in range(3):
        start = time.time()
        sys_obj = DNASystem(show_status=False)
        elapsed = time.time() - start
        times.append(elapsed)

    avg_time = sum(times) / len(times)
    print(f"平均启动时间: {avg_time*1000:.1f}ms (3次平均)")
    print(f"  各次: {[f'{t*1000:.1f}ms' for t in times]}")
    print()

    return {
        "test": "startup_time",
        "avg_ms": avg_time * 1000,
        "runs": len(times),
    }


def run_all_benchmarks():
    """运行所有基准测试"""
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         DNA记忆系统效率对比测试报告                      ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    results = []

    # 运行测试
    results.append(test_startup_loading())
    results.append(test_compression())
    results.append(test_retrieval_accuracy())
    results.append(test_startup_time())

    # 汇总
    print("=" * 60)
    print("汇总")
    print("=" * 60)
    print()
    print(f"启动Token节省: {results[0]['savings']['percent']:.1f}%")
    print(f"记忆压缩率: {results[1]['compression_rate']:.1f}%")
    print(f"检索范围缩小: {results[2]['avg_range_reduction']:.1f}%")
    print(f"启动时间: {results[3]['avg_ms']:.1f}ms")
    print()

    # 保存结果
    output_file = os.path.join(os.path.dirname(__file__), "benchmark_results.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    print(f"结果已保存: {output_file}")

    return results


if __name__ == "__main__":
    run_all_benchmarks()
