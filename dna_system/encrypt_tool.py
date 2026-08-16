"""
DNA-Strand 加密工具
独立的加密/解密工具，可打包成.exe
"""
import sys
import os
import io
import argparse
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# 强制 UTF-8 输出
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 设置基础目录
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)


class EncryptToolGUI:
    """加密工具图形界面"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DNA-Strand 加密工具")
        self.root.geometry("500x400")
        self.root.resizable(False, False)

        # 设置样式
        style = ttk.Style()
        style.theme_use('clam')

        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        # 主框架
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="DNA-Strand 加密工具", font=('Arial', 16, 'bold'))
        title_label.pack(pady=(0, 20))

        # 密钥输入
        key_frame = ttk.LabelFrame(main_frame, text="加密密钥", padding="10")
        key_frame.pack(fill=tk.X, pady=(0, 10))

        self.key_var = tk.StringVar(value="DNA-Strand-Default-Key")
        key_entry = ttk.Entry(key_frame, textvariable=self.key_var, show="*", width=40)
        key_entry.pack(side=tk.LEFT, padx=(0, 10))

        show_key_var = tk.BooleanVar()
        def toggle_show():
            key_entry.config(show="" if show_key_var.get() else "*")
        show_check = ttk.Checkbutton(key_frame, text="显示", variable=show_key_var, command=toggle_show)
        show_check.pack(side=tk.LEFT)

        # 操作选择
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="10")
        action_frame.pack(fill=tk.X, pady=(0, 10))

        self.action_var = tk.StringVar(value="encrypt")
        ttk.Radiobutton(action_frame, text="加密数据", variable=self.action_var, value="encrypt").pack(anchor=tk.W)
        ttk.Radiobutton(action_frame, text="解密数据", variable=self.action_var, value="decrypt").pack(anchor=tk.W)
        ttk.Radiobutton(action_frame, text="验证完整性", variable=self.action_var, value="verify").pack(anchor=tk.W)

        # 目录选择
        dir_frame = ttk.LabelFrame(main_frame, text="数据目录", padding="10")
        dir_frame.pack(fill=tk.X, pady=(0, 10))

        self.dir_var = tk.StringVar(value=os.path.join(BASE_DIR, ".dna"))
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=35)
        dir_entry.pack(side=tk.LEFT, padx=(0, 10))

        browse_btn = ttk.Button(dir_frame, text="浏览", command=self.browse_directory)
        browse_btn.pack(side=tk.LEFT)

        # 执行按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(10, 0))

        execute_btn = ttk.Button(btn_frame, text="执行", command=self.execute)
        execute_btn.pack(side=tk.LEFT, padx=(0, 10))

        close_btn = ttk.Button(btn_frame, text="关闭", command=self.root.quit)
        close_btn.pack(side=tk.LEFT)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN)
        status_label.pack(fill=tk.X, pady=(10, 0))

    def browse_directory(self):
        """浏览目录"""
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)

    def execute(self):
        """执行操作"""
        action = self.action_var.get()
        key = self.key_var.get()
        directory = self.dir_var.get()

        if not key:
            messagebox.showerror("错误", "请输入加密密钥")
            return

        if not os.path.exists(directory):
            messagebox.showerror("错误", f"目录不存在: {directory}")
            return

        try:
            from dna_system.security import DataProtector, IntegrityChecker

            self.status_var.set("正在执行...")
            self.root.update()

            if action == "encrypt":
                self.encrypt_data(directory, key)
                messagebox.showinfo("完成", "数据加密完成")
            elif action == "decrypt":
                self.decrypt_data(directory, key)
                messagebox.showinfo("完成", "数据解密完成")
            elif action == "verify":
                self.verify_data(directory, key)

            self.status_var.set("执行完成")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("执行失败")

    def encrypt_data(self, directory: str, key: str):
        """加密数据"""
        from dna_system.security import DataProtector

        protector = DataProtector(key)
        count = 0

        # 加密strands
        strands_dir = Path(directory) / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()
                count += 1

        # 加密patterns
        patterns_dir = Path(directory) / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()
                count += 1

        # 加密配置文件
        config_file = Path(directory) / "manifest.json"
        if config_file.exists():
            encrypted_path = str(config_file) + ".enc"
            protector.encrypt_file(str(config_file), encrypted_path)
            config_file.unlink()

        return count

    def decrypt_data(self, directory: str, key: str):
        """解密数据"""
        from dna_system.security import DataProtector

        protector = DataProtector(key)
        count = 0

        # 解密strands
        strands_dir = Path(directory) / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]
                protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()
                count += 1

        # 解密patterns
        patterns_dir = Path(directory) / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]
                protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()
                count += 1

        # 解密配置文件
        config_file = Path(directory) / "manifest.json.enc"
        if config_file.exists():
            decrypted_path = str(config_file)[:-4]
            protector.decrypt_file(str(config_file), decrypted_path)
            config_file.unlink()

        return count

    def verify_data(self, directory: str, key: str):
        """验证数据完整性"""
        from dna_system.security import IntegrityChecker

        checker = IntegrityChecker(key)
        manifest_path = Path(directory) / "integrity_manifest.json"

        if not manifest_path.exists():
            # 生成清单
            manifest = checker.generate_manifest(directory, str(manifest_path))
            messagebox.showinfo("完成", f"已生成完整性清单，包含 {len(manifest)} 个文件")
            return

        # 验证
        is_valid, errors = checker.verify_directory(directory, str(manifest_path))
        if is_valid:
            messagebox.showinfo("验证结果", "数据完整性验证通过")
        else:
            error_msg = "\n".join(errors[:10])
            if len(errors) > 10:
                error_msg += f"\n... 还有 {len(errors) - 10} 个错误"
            messagebox.showerror("验证结果", f"数据完整性验证失败:\n{error_msg}")

    def run(self):
        """运行工具"""
        self.root.mainloop()


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='DNA-Strand 加密工具')
    parser.add_argument('--gui', action='store_true', help='图形界面模式')
    parser.add_argument('--encrypt', action='store_true', help='加密数据')
    parser.add_argument('--decrypt', action='store_true', help='解密数据')
    parser.add_argument('--verify', action='store_true', help='验证完整性')
    parser.add_argument('--key', type=str, default='DNA-Strand-Default-Key', help='加密密钥')
    parser.add_argument('--dir', type=str, help='数据目录')
    args = parser.parse_args()

    # 图形界面模式
    if args.gui or len(sys.argv) == 1:
        app = EncryptToolGUI()
        app.run()
        return

    # 命令行模式
    directory = args.dir or os.path.join(BASE_DIR, '.dna')

    if not os.path.exists(directory):
        print(f"错误: 目录不存在: {directory}")
        return

    from dna_system.security import DataProtector, IntegrityChecker

    if args.encrypt:
        print("加密数据...")
        protector = DataProtector(args.key)
        count = 0

        # 加密strands
        strands_dir = Path(directory) / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()
                count += 1

        # 加密patterns
        patterns_dir = Path(directory) / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.json"):
                encrypted_path = str(file_path) + ".enc"
                protector.encrypt_file(str(file_path), encrypted_path)
                file_path.unlink()
                count += 1

        print(f"加密完成: {count} 个文件")

    elif args.decrypt:
        print("解密数据...")
        protector = DataProtector(args.key)
        count = 0

        # 解密strands
        strands_dir = Path(directory) / "strands"
        if strands_dir.exists():
            for file_path in strands_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]
                protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()
                count += 1

        # 解密patterns
        patterns_dir = Path(directory) / "patterns"
        if patterns_dir.exists():
            for file_path in patterns_dir.glob("*.enc"):
                decrypted_path = str(file_path)[:-4]
                protector.decrypt_file(str(file_path), decrypted_path)
                file_path.unlink()
                count += 1

        print(f"解密完成: {count} 个文件")

    elif args.verify:
        print("验证完整性...")
        checker = IntegrityChecker(args.key)
        manifest_path = Path(directory) / "integrity_manifest.json"

        if not manifest_path.exists():
            manifest = checker.generate_manifest(directory, str(manifest_path))
            print(f"已生成完整性清单: {len(manifest)} 个文件")
        else:
            is_valid, errors = checker.verify_directory(directory, str(manifest_path))
            if is_valid:
                print("验证通过")
            else:
                print(f"验证失败: {len(errors)} 个错误")
                for error in errors[:5]:
                    print(f"  - {error}")


if __name__ == "__main__":
    main()
