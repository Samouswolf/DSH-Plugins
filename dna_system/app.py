"""
DNA-Strand 应用入口
用于打包成.exe文件
"""
import sys
import os
import io
import argparse

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 设置基础目录
if getattr(sys, 'frozen', False):
    # 打包后的路径
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 确保能导入dna_system
sys.path.insert(0, BASE_DIR)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DNA-Strand 神经记忆系统')
    parser.add_argument('--window', action='store_true', help='打开原生窗口')
    parser.add_argument('--port', type=int, default=8080, help='Web端口')
    parser.add_argument('--no-gui', action='store_true', help='无界面模式')
    parser.add_argument('--git-push', action='store_true', help='推送记忆到Git')
    parser.add_argument('--git-pull', action='store_true', help='从Git拉取记忆')
    parser.add_argument('--git-sync', action='store_true', help='双向同步')
    args = parser.parse_args()

    # 导入DNA系统
    from dna_system import DNASystem

    # 初始化系统
    system = DNASystem(base_dir=BASE_DIR, show_status=not args.no_gui)

    # Git操作
    if args.git_push:
        success, msg = system.git_push()
        print(f"Push: {msg}")
        return

    if args.git_pull:
        success, msg = system.git_pull()
        print(f"Pull: {msg}")
        return

    if args.git_sync:
        success, msg = system.git_sync()
        print(f"Sync: {msg}")
        return

    # 启动界面
    if args.window:
        system.open_window(port=args.port)
    elif not args.no_gui:
        url = system.open_browser(port=args.port)
        print(f"\n仪表盘: {url}")
        print("按 Ctrl+C 退出\n")

        # 保持运行
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            system.stop_web()
            print("\n程序已退出")
    else:
        # 无界面模式
        print("DNA-Strand 已启动（无界面模式）")
        print("使用 --window 或 --port 参数启动界面")

        # 保持运行
        try:
            import time
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n程序已退出")


if __name__ == "__main__":
    main()
