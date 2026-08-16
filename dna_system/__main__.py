"""
DNA-Strand CLI 入口

用法:
    python -m dna_system [command] [args...]

命令:
    status          显示系统状态
    query <问题>    查询记忆
    ingest <文件>   摄入文件
    evolve          触发进化
    maintenance     运行维护
    quality         质量报告
    auto-commit     自动记录commit
    auto-session    自动记录会话
    auto-snapshot   自动记录快照
"""
import sys
import os
import io

# 强制 UTF-8 输出 (Windows 兼容)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 确保 dna_system 在 path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dna_system import DNASystem


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1]
    args = sys.argv[2:]

    # 初始化系统（显示状态窗口）
    system = DNASystem()

    if cmd == "status":
        # 已经在初始化时显示了
        pass

    elif cmd == "query":
        if not args:
            print("用法: python -m dna_system query <问题>")
            return
        question = " ".join(args)
        results, query_id = system.query_with_feedback(question)
        print(f"查询ID: {query_id}")

    elif cmd == "ingest":
        if not args:
            print("用法: python -m dna_system ingest <文件路径>")
            return
        source = " ".join(args)
        dnas = system.ingest(source)
        print(f"摄入 {len(dnas)} 条DNA")

    elif cmd == "evolve":
        system.evolve()

    elif cmd == "maintenance":
        system.run_maintenance()

    elif cmd == "quality":
        system.get_quality_report()

    elif cmd == "auto-commit":
        dna = system.auto_commit()
        if dna:
            print(f"✅ 已记录 commit: {dna.id}")
        else:
            print("⏭️ 无有意义的 commit")

    elif cmd == "auto-session":
        if args:
            summary = " ".join(args)
        else:
            print("请输入会话摘要 (Ctrl+D 结束):")
            summary = sys.stdin.read()
        dna = system.auto_session(summary)
        if dna:
            print(f"✅ 已记录会话: {dna.id}")
        else:
            print("⏭️ 会话摘要无记录价值")

    elif cmd == "auto-snapshot":
        dna = system.auto_snapshot()
        if dna:
            print(f"✅ 已记录快照: {dna.id}")
        else:
            print("⏭️ 快照无变化")

    else:
        print(f"未知命令: {cmd}")
        print(__doc__)


if __name__ == "__main__":
    main()
