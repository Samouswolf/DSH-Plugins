"""
DNA-Strand Git同步模块
支持记忆数据的上传、下载、双向同步
"""
import json
import os
import subprocess
import time
from pathlib import Path
from datetime import datetime


class GitSync:
    """Git同步管理器"""

    def __init__(self, dna_dir: str = None, config: dict = None):
        """
        初始化Git同步

        Args:
            dna_dir: .dna目录路径
            config: Git配置
        """
        self.dna_dir = Path(dna_dir) if dna_dir else Path.cwd() / ".dna"
        self.config = config or {}
        self.repo_url = self.config.get("repo", "")
        self.branch = self.config.get("branch", "main")

    def _run_git(self, args: list[str], cwd: str = None) -> tuple[int, str, str]:
        """
        执行git命令

        Returns:
            (returncode, stdout, stderr)
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=cwd or str(self.dna_dir),
                capture_output=True,
                text=True,
                timeout=60,
                encoding='utf-8',
                errors='replace'
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Git命令超时"
        except Exception as e:
            return -1, "", str(e)

    def is_initialized(self) -> bool:
        """检查是否已初始化git仓库"""
        git_dir = self.dna_dir / ".git"
        return git_dir.exists()

    def init(self, repo_url: str = None) -> tuple[bool, str]:
        """
        初始化git仓库

        Args:
            repo_url: 远程仓库URL

        Returns:
            (成功, 消息)
        """
        if self.is_initialized():
            return True, "仓库已初始化"

        # 初始化本地仓库
        code, out, err = self._run_git(["init"])
        if code != 0:
            return False, f"初始化失败: {err}"

        # 添加远程仓库
        if repo_url:
            self.repo_url = repo_url
            code, out, err = self._run_git(["remote", "add", "origin", repo_url])
            if code != 0:
                return False, f"添加远程仓库失败: {err}"

        # 创建.gitignore
        gitignore = self.dna_dir / ".gitignore"
        gitignore.write_text("""# 临时文件
*.tmp
*.log
watch_heartbeat.json

# Python缓存
__pycache__/
*.pyc

# 系统文件
.DS_Store
Thumbs.db
""", encoding='utf-8')

        return True, "初始化成功"

    def status(self) -> dict:
        """
        获取仓库状态

        Returns:
            {
                "initialized": bool,
                "remote": str,
                "branch": str,
                "modified": int,
                "untracked": int,
                "last_commit": str,
            }
        """
        if not self.is_initialized():
            return {
                "initialized": False,
                "remote": "",
                "branch": "",
                "modified": 0,
                "untracked": 0,
                "last_commit": "",
            }

        # 获取远程仓库
        code, remote, _ = self._run_git(["remote", "get-url", "origin"])
        remote = remote if code == 0 else ""

        # 获取当前分支
        code, branch, _ = self._run_git(["branch", "--show-current"])
        branch = branch if code == 0 else "main"

        # 获取状态
        code, status_out, _ = self._run_git(["status", "--porcelain"])
        modified = 0
        untracked = 0
        if code == 0:
            for line in status_out.split('\n'):
                if line.startswith(' M') or line.startswith('M'):
                    modified += 1
                elif line.startswith('??'):
                    untracked += 1

        # 获取最后提交
        code, last_commit, _ = self._run_git(["log", "-1", "--format=%s"])
        last_commit = last_commit if code == 0 else ""

        return {
            "initialized": True,
            "remote": remote,
            "branch": branch,
            "modified": modified,
            "untracked": untracked,
            "last_commit": last_commit,
        }

    def commit(self, message: str = None) -> tuple[bool, str]:
        """
        提交更改

        Args:
            message: 提交消息

        Returns:
            (成功, 消息)
        """
        if not self.is_initialized():
            return False, "仓库未初始化"

        # 添加所有更改
        code, out, err = self._run_git(["add", "-A"])
        if code != 0:
            return False, f"添加文件失败: {err}"

        # 检查是否有更改
        code, status, _ = self._run_git(["status", "--porcelain"])
        if not status:
            return True, "没有更改需要提交"

        # 生成提交消息
        if not message:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            message = f"Auto sync: {now}"

        # 提交
        code, out, err = self._run_git(["commit", "-m", message])
        if code != 0:
            return False, f"提交失败: {err}"

        return True, f"提交成功: {message}"

    def push(self, remote: str = "origin", branch: str = None) -> tuple[bool, str]:
        """
        推送到远程仓库

        Args:
            remote: 远程仓库名
            branch: 分支名

        Returns:
            (成功, 消息)
        """
        if not self.is_initialized():
            return False, "仓库未初始化"

        branch = branch or self.branch

        # 先commit
        self.commit()

        # 推送
        code, out, err = self._run_git(["push", remote, branch])
        if code != 0:
            # 尝试设置上游分支
            code, out, err = self._run_git(["push", "-u", remote, branch])
            if code != 0:
                return False, f"推送失败: {err}"

        return True, f"推送到 {remote}/{branch} 成功"

    def pull(self, remote: str = "origin", branch: str = None) -> tuple[bool, str]:
        """
        从远程仓库拉取

        Args:
            remote: 远程仓库名
            branch: 分支名

        Returns:
            (成功, 消息)
        """
        if not self.is_initialized():
            return False, "仓库未初始化"

        branch = branch or self.branch

        # 拉取
        code, out, err = self._run_git(["pull", remote, branch])
        if code != 0:
            return False, f"拉取失败: {err}"

        return True, f"从 {remote}/{branch} 拉取成功"

    def sync(self, remote: str = "origin", branch: str = None) -> tuple[bool, str]:
        """
        双向同步（先pull再push）

        Args:
            remote: 远程仓库名
            branch: 分支名

        Returns:
            (成功, 消息)
        """
        if not self.is_initialized():
            return False, "仓库未初始化"

        branch = branch or self.branch

        # 先commit本地更改
        self.commit()

        # 拉取远程更改
        code, out, err = self._run_git(["pull", "--rebase", remote, branch])
        if code != 0:
            # 如果rebase失败，尝试普通pull
            self._run_git(["rebase", "--abort"])
            code, out, err = self._run_git(["pull", remote, branch])
            if code != 0:
                return False, f"拉取失败: {err}"

        # 推送本地更改
        code, out, err = self._run_git(["push", remote, branch])
        if code != 0:
            return False, f"推送失败: {err}"

        return True, f"同步成功"

    def clone(self, repo_url: str = None) -> tuple[bool, str]:
        """
        克隆远程仓库

        Args:
            repo_url: 远程仓库URL

        Returns:
            (成功, 消息)
        """
        repo_url = repo_url or self.repo_url
        if not repo_url:
            return False, "未指定仓库URL"

        # 如果目录已存在，先备份
        if self.dna_dir.exists() and any(self.dna_dir.iterdir()):
            backup_dir = self.dna_dir.parent / f".dna_backup_{int(time.time())}"
            self.dna_dir.rename(backup_dir)

        # 克隆
        code, out, err = self._run_git(
            ["clone", repo_url, str(self.dna_dir)],
            cwd=str(self.dna_dir.parent)
        )
        if code != 0:
            return False, f"克隆失败: {err}"

        return True, f"克隆成功: {repo_url}"


class GitSyncConfig:
    """Git同步配置管理"""

    def __init__(self, config_path: str = None):
        self.config_path = Path(config_path) if config_path else Path.cwd() / "config" / "dna_config.json"
        self.config = self._load()

    def _load(self) -> dict:
        """加载配置"""
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return self._default_config()

    def _default_config(self) -> dict:
        """默认配置"""
        return {
            "git": {
                "repo": "",
                "branch": "main",
                "auto_sync": False,
                "sync_interval": 3600,
                "commit_message": "Auto sync: {timestamp}"
            },
            "system": {
                "threshold": 0.3,
                "evolution_threshold": 0.95,
                "auto_record": True
            },
            "web": {
                "port": 8080,
                "auto_open": False
            }
        }

    def save(self):
        """保存配置"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def get(self, key: str, default=None):
        """获取配置值"""
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def set(self, key: str, value):
        """设置配置值"""
        keys = key.split('.')
        config = self.config
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        config[keys[-1]] = value
        self.save()
