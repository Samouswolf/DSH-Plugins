"""
DNA-Strand 加密工具（精简版）
只包含加密/解密功能，不依赖其他模块
"""
import sys
import os
import io
import hashlib
import json
import base64
import struct
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

# 强制 UTF-8 输出（GUI模式下stdout可能为None）
if sys.stdout and hasattr(sys.stdout, 'encoding') and sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
if sys.stderr and hasattr(sys.stderr, 'encoding') and sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class SimpleProtector:
    """轻量级加密器（不依赖外部库）"""

    DEFAULT_KEY = "DNA-Strand-2024-Secure-Key-32b"

    def __init__(self, key: str = None):
        self.key = (key or self.DEFAULT_KEY).encode('utf-8')
        self.key = hashlib.sha256(self.key).digest()

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR加密"""
        key_len = len(key)
        return bytes(b ^ key[i % key_len] for i, b in enumerate(data))

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """加密文件"""
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path.with_suffix('.enc')

        with open(input_path, 'rb') as f:
            data = f.read()

        iv = os.urandom(16)
        encrypted = self._xor_encrypt(data, self.key + iv)

        with open(output_path, 'wb') as f:
            f.write(iv)
            f.write(encrypted)

        return str(output_path)

    def decrypt_file(self, input_path: str, output_path: str = None) -> str:
        """解密文件"""
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path.with_suffix('.dec')

        with open(input_path, 'rb') as f:
            iv = f.read(16)
            encrypted = f.read()

        decrypted = self._xor_encrypt(encrypted, self.key + iv)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

        return str(output_path)

    def calculate_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        import hmac
        with open(file_path, 'rb') as f:
            data = f.read()
        return hmac.new(self.key, data, hashlib.sha256).hexdigest()

    def generate_manifest(self, directory: str) -> dict:
        """生成完整性清单"""
        manifest = {}
        for file_path in Path(directory).rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                relative_path = str(file_path.relative_to(directory))
                manifest[relative_path] = self.calculate_hash(str(file_path))
        return manifest

    def verify_directory(self, directory: str, manifest_path: str) -> tuple:
        """验证目录完整性"""
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        errors = []
        for relative_path, expected_hash in manifest.items():
            file_path = Path(directory) / relative_path
            if not file_path.exists():
                errors.append(f"文件缺失: {relative_path}")
            elif self.calculate_hash(str(file_path)) != expected_hash:
                errors.append(f"文件被篡改: {relative_path}")

        return len(errors) == 0, errors


class EncryptToolGUI:
    """加密工具图形界面"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("DNA-Strand 加密工具")
        self.root.geometry("450x350")
        self.root.resizable(False, False)

        # 设置图标（如果存在）
        try:
            self.root.iconbitmap(default='')
        except:
            pass

        self.create_widgets()

    def create_widgets(self):
        """创建界面组件"""
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 标题
        title_label = ttk.Label(main_frame, text="DNA-Strand 加密工具", font=('Arial', 14, 'bold'))
        title_label.pack(pady=(0, 15))

        # 密钥输入
        key_frame = ttk.LabelFrame(main_frame, text="加密密钥", padding="8")
        key_frame.pack(fill=tk.X, pady=(0, 8))

        self.key_var = tk.StringVar(value="DNA-Strand-Default-Key")
        key_entry = ttk.Entry(key_frame, textvariable=self.key_var, show="*", width=35)
        key_entry.pack(side=tk.LEFT, padx=(0, 8))

        self.show_key_var = tk.BooleanVar()
        def toggle_show():
            key_entry.config(show="" if self.show_key_var.get() else "*")
        ttk.Checkbutton(key_frame, text="显示", variable=self.show_key_var, command=toggle_show).pack(side=tk.LEFT)

        # 操作选择
        action_frame = ttk.LabelFrame(main_frame, text="操作", padding="8")
        action_frame.pack(fill=tk.X, pady=(0, 8))

        self.action_var = tk.StringVar(value="encrypt")
        ttk.Radiobutton(action_frame, text="加密数据", variable=self.action_var, value="encrypt").pack(anchor=tk.W)
        ttk.Radiobutton(action_frame, text="解密数据", variable=self.action_var, value="decrypt").pack(anchor=tk.W)
        ttk.Radiobutton(action_frame, text="验证完整性", variable=self.action_var, value="verify").pack(anchor=tk.W)

        # 目录选择
        dir_frame = ttk.LabelFrame(main_frame, text="数据目录", padding="8")
        dir_frame.pack(fill=tk.X, pady=(0, 8))

        # 默认目录
        default_dir = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".dna")
        if not os.path.exists(default_dir):
            default_dir = os.path.expanduser("~/.dna")

        self.dir_var = tk.StringVar(value=default_dir)
        ttk.Entry(dir_frame, textvariable=self.dir_var, width=30).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(dir_frame, text="浏览", command=self.browse_directory).pack(side=tk.LEFT)

        # 按钮
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(8, 0))

        ttk.Button(btn_frame, text="执行", command=self.execute).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(btn_frame, text="关闭", command=self.root.quit).pack(side=tk.LEFT)

        # 状态栏
        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(fill=tk.X, pady=(8, 0))

    def browse_directory(self):
        directory = filedialog.askdirectory(initialdir=self.dir_var.get())
        if directory:
            self.dir_var.set(directory)

    def execute(self):
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
            protector = SimpleProtector(key)
            self.status_var.set("正在执行...")
            self.root.update()

            if action == "encrypt":
                count = self.encrypt_data(protector, directory)
                messagebox.showinfo("完成", f"加密完成: {count} 个文件")
            elif action == "decrypt":
                count = self.decrypt_data(protector, directory)
                messagebox.showinfo("完成", f"解密完成: {count} 个文件")
            elif action == "verify":
                self.verify_data(protector, directory)

            self.status_var.set("执行完成")

        except Exception as e:
            messagebox.showerror("错误", str(e))
            self.status_var.set("执行失败")

    def encrypt_data(self, protector, directory):
        count = 0
        for subdir in ["strands", "patterns"]:
            dir_path = Path(directory) / subdir
            if dir_path.exists():
                for file_path in dir_path.glob("*.json"):
                    protector.encrypt_file(str(file_path), str(file_path) + ".enc")
                    file_path.unlink()
                    count += 1

        # 加密配置文件
        config_file = Path(directory) / "manifest.json"
        if config_file.exists():
            protector.encrypt_file(str(config_file), str(config_file) + ".enc")
            config_file.unlink()

        return count

    def decrypt_data(self, protector, directory):
        count = 0
        for subdir in ["strands", "patterns"]:
            dir_path = Path(directory) / subdir
            if dir_path.exists():
                for file_path in dir_path.glob("*.enc"):
                    decrypted_path = str(file_path)[:-4]
                    protector.decrypt_file(str(file_path), decrypted_path)
                    file_path.unlink()
                    count += 1

        # 解密配置文件
        config_file = Path(directory) / "manifest.json.enc"
        if config_file.exists():
            protector.decrypt_file(str(config_file), str(config_file)[:-4])
            config_file.unlink()

        return count

    def verify_data(self, protector, directory):
        manifest_path = Path(directory) / "integrity_manifest.json"

        if not manifest_path.exists():
            manifest = protector.generate_manifest(directory)
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            messagebox.showinfo("完成", f"已生成清单: {len(manifest)} 个文件")
            return

        is_valid, errors = protector.verify_directory(directory, str(manifest_path))
        if is_valid:
            messagebox.showinfo("验证结果", "数据完整性验证通过")
        else:
            error_msg = "\n".join(errors[:10])
            messagebox.showerror("验证结果", f"验证失败:\n{error_msg}")

    def run(self):
        self.root.mainloop()


def main():
    """主函数"""
    # 无参数时显示GUI
    if len(sys.argv) == 1:
        app = EncryptToolGUI()
        app.run()
        return

    # 命令行模式
    import argparse
    parser = argparse.ArgumentParser(description='DNA-Strand 加密工具')
    parser.add_argument('--encrypt', action='store_true', help='加密数据')
    parser.add_argument('--decrypt', action='store_true', help='解密数据')
    parser.add_argument('--verify', action='store_true', help='验证完整性')
    parser.add_argument('--key', type=str, default='DNA-Strand-Default-Key', help='加密密钥')
    parser.add_argument('--dir', type=str, help='数据目录')
    args = parser.parse_args()

    directory = args.dir or os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), ".dna")
    protector = SimpleProtector(args.key)

    if args.encrypt:
        count = 0
        for subdir in ["strands", "patterns"]:
            dir_path = Path(directory) / subdir
            if dir_path.exists():
                for file_path in dir_path.glob("*.json"):
                    protector.encrypt_file(str(file_path), str(file_path) + ".enc")
                    file_path.unlink()
                    count += 1
        print(f"加密完成: {count} 个文件")

    elif args.decrypt:
        count = 0
        for subdir in ["strands", "patterns"]:
            dir_path = Path(directory) / subdir
            if dir_path.exists():
                for file_path in dir_path.glob("*.enc"):
                    protector.decrypt_file(str(file_path), str(file_path)[:-4])
                    file_path.unlink()
                    count += 1
        print(f"解密完成: {count} 个文件")

    elif args.verify:
        manifest_path = Path(directory) / "integrity_manifest.json"
        if not manifest_path.exists():
            manifest = protector.generate_manifest(directory)
            with open(manifest_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)
            print(f"已生成清单: {len(manifest)} 个文件")
        else:
            is_valid, errors = protector.verify_directory(directory, str(manifest_path))
            if is_valid:
                print("验证通过")
            else:
                print(f"验证失败: {len(errors)} 个错误")


if __name__ == "__main__":
    main()
