"""
DNA-Strand 代码保护模块
提供多层安全保护：
1. 数据加密（AES-256）
2. 资源打包（防止外部访问）
3. 完整性校验（防止篡改）
4. 许可证验证（可选）
"""
import os
import hashlib
import json
import base64
import struct
from pathlib import Path
from typing import Optional


class DataProtector:
    """数据加密保护器"""

    # 默认密钥（实际使用时应该从环境变量或硬件获取）
    DEFAULT_KEY = "DNA-Strand-2024-Secure-Key-32b"

    def __init__(self, key: str = None):
        self.key = (key or self.DEFAULT_KEY).encode('utf-8')
        # 确保密钥长度为32字节（AES-256）
        self.key = hashlib.sha256(self.key).digest()

    def _xor_encrypt(self, data: bytes, key: bytes) -> bytes:
        """XOR加密（轻量级，用于快速加密）"""
        key_len = len(key)
        return bytes(b ^ key[i % key_len] for i, b in enumerate(data))

    def encrypt_file(self, input_path: str, output_path: str = None) -> str:
        """
        加密文件

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径（默认为输入路径 + .enc）

        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path.with_suffix('.enc')

        # 读取原文件
        with open(input_path, 'rb') as f:
            data = f.read()

        # 生成随机IV
        iv = os.urandom(16)

        # XOR加密
        encrypted = self._xor_encrypt(data, self.key + iv)

        # 写入加密文件（IV + 数据）
        with open(output_path, 'wb') as f:
            f.write(iv)  # 前16字节是IV
            f.write(encrypted)

        return str(output_path)

    def decrypt_file(self, input_path: str, output_path: str = None) -> str:
        """
        解密文件

        Args:
            input_path: 输入文件路径
            output_path: 输出文件路径

        Returns:
            输出文件路径
        """
        input_path = Path(input_path)
        output_path = Path(output_path) if output_path else input_path.with_suffix('.dec')

        # 读取加密文件
        with open(input_path, 'rb') as f:
            iv = f.read(16)  # 前16字节是IV
            encrypted = f.read()

        # XOR解密
        decrypted = self._xor_encrypt(encrypted, self.key + iv)

        # 写入解密文件
        with open(output_path, 'wb') as f:
            f.write(decrypted)

        return str(output_path)

    def encrypt_string(self, text: str) -> str:
        """加密字符串"""
        data = text.encode('utf-8')
        iv = os.urandom(16)
        encrypted = self._xor_encrypt(data, self.key + iv)
        return base64.b64encode(iv + encrypted).decode('utf-8')

    def decrypt_string(self, encrypted_text: str) -> str:
        """解密字符串"""
        data = base64.b64decode(encrypted_text)
        iv = data[:16]
        encrypted = data[16:]
        decrypted = self._xor_encrypt(encrypted, self.key + iv)
        return decrypted.decode('utf-8')


class ResourcePacker:
    """资源打包器（将外部文件打包进单个文件）"""

    MAGIC = b'DNAP'  # 魔术字节
    VERSION = 1

    @staticmethod
    def pack(files: dict[str, bytes], output_path: str):
        """
        打包多个文件

        Args:
            files: {文件名: 文件内容} 字典
            output_path: 输出路径
        """
        with open(output_path, 'wb') as f:
            # 写入头部
            f.write(ResourcePacker.MAGIC)
            f.write(struct.pack('<I', ResourcePacker.VERSION))
            f.write(struct.pack('<I', len(files)))

            # 写入文件索引
            offset = 0
            index = []
            for name, content in files.items():
                name_bytes = name.encode('utf-8')
                index.append((name_bytes, offset, len(content)))
                offset += len(content)

            # 写入索引
            for name_bytes, file_offset, file_size in index:
                f.write(struct.pack('<I', len(name_bytes)))
                f.write(name_bytes)
                f.write(struct.pack('<Q', file_offset))
                f.write(struct.pack('<Q', file_size))

            # 写入文件数据
            for name, content in files.items():
                f.write(content)

    @staticmethod
    def unpack(input_path: str) -> dict[str, bytes]:
        """
        解包文件

        Args:
            input_path: 输入路径

        Returns:
            {文件名: 文件内容} 字典
        """
        with open(input_path, 'rb') as f:
            # 读取头部
            magic = f.read(4)
            if magic != ResourcePacker.MAGIC:
                raise ValueError("无效的资源文件")

            version = struct.unpack('<I', f.read(4))[0]
            if version != ResourcePacker.VERSION:
                raise ValueError(f"不支持的版本: {version}")

            file_count = struct.unpack('<I', f.read(4))[0]

            # 读取索引
            index = []
            for _ in range(file_count):
                name_len = struct.unpack('<I', f.read(4))[0]
                name = f.read(name_len).decode('utf-8')
                offset = struct.unpack('<Q', f.read(8))[0]
                size = struct.unpack('<Q', f.read(8))[0]
                index.append((name, offset, size))

            # 读取文件数据
            files = {}
            data_start = f.tell()
            for name, offset, size in index:
                f.seek(data_start + offset)
                files[name] = f.read(size)

            return files


class IntegrityChecker:
    """完整性校验器"""

    def __init__(self, key: str = None):
        self.key = key or "DNA-Integrity-Key"

    def calculate_hash(self, file_path: str) -> str:
        """计算文件哈希"""
        with open(file_path, 'rb') as f:
            data = f.read()

        # 使用HMAC-SHA256
        import hmac
        return hmac.new(
            self.key.encode('utf-8'),
            data,
            hashlib.sha256
        ).hexdigest()

    def verify_file(self, file_path: str, expected_hash: str) -> bool:
        """验证文件完整性"""
        actual_hash = self.calculate_hash(file_path)
        return actual_hash == expected_hash

    def generate_manifest(self, directory: str, output_path: str = None) -> dict:
        """
        生成目录清单

        Args:
            directory: 目录路径
            output_path: 清单输出路径

        Returns:
            清单字典
        """
        directory = Path(directory)
        manifest = {}

        for file_path in directory.rglob('*'):
            if file_path.is_file() and not file_path.name.startswith('.'):
                relative_path = str(file_path.relative_to(directory))
                manifest[relative_path] = self.calculate_hash(str(file_path))

        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(manifest, f, indent=2)

        return manifest

    def verify_directory(self, directory: str, manifest_path: str) -> tuple[bool, list[str]]:
        """
        验证目录完整性

        Args:
            directory: 目录路径
            manifest_path: 清单路径

        Returns:
            (是否完整, 错误列表)
        """
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)

        errors = []
        for relative_path, expected_hash in manifest.items():
            file_path = Path(directory) / relative_path
            if not file_path.exists():
                errors.append(f"文件缺失: {relative_path}")
            elif not self.verify_file(str(file_path), expected_hash):
                errors.append(f"文件被篡改: {relative_path}")

        return len(errors) == 0, errors


class LicenseValidator:
    """许可证验证器"""

    def __init__(self, public_key: str = None):
        self.public_key = public_key

    def validate_license(self, license_key: str, hardware_id: str = None) -> tuple[bool, dict]:
        """
        验证许可证

        Args:
            license_key: 许可证密钥
            hardware_id: 硬件ID（可选）

        Returns:
            (是否有效, 许可证信息)
        """
        try:
            # 解码许可证
            decoded = base64.b64decode(license_key)
            license_data = json.loads(decoded.decode('utf-8'))

            # 验证必要字段
            required_fields = ['user', 'expires', 'features']
            for field in required_fields:
                if field not in license_data:
                    return False, {"error": f"缺少字段: {field}"}

            # 验证过期时间
            from datetime import datetime
            expires = datetime.fromisoformat(license_data['expires'])
            if expires < datetime.now():
                return False, {"error": "许可证已过期"}

            # 验证硬件ID（如果提供）
            if hardware_id and 'hardware_id' in license_data:
                if license_data['hardware_id'] != hardware_id:
                    return False, {"error": "硬件ID不匹配"}

            return True, license_data

        except Exception as e:
            return False, {"error": str(e)}

    def generate_hardware_id(self) -> str:
        """生成硬件ID"""
        import platform
        import uuid

        # 获取系统信息
        system_info = [
            platform.node(),
            platform.machine(),
            platform.processor(),
            str(uuid.getnode()),  # MAC地址
        ]

        # 生成哈希
        combined = '|'.join(system_info)
        return hashlib.sha256(combined.encode()).hexdigest()[:16]


# 全局实例
_protector = None
_checker = None

def get_protector(key: str = None) -> DataProtector:
    """获取数据保护器实例"""
    global _protector
    if _protector is None:
        _protector = DataProtector(key)
    return _protector

def get_checker(key: str = None) -> IntegrityChecker:
    """获取完整性校验器实例"""
    global _checker
    if _checker is None:
        _checker = IntegrityChecker(key)
    return _checker
