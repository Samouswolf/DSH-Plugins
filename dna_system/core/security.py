"""
DNA-Strand 安全模块
====================
提供数据完整性保护和审计追踪功能

功能：
1. 版本控制 - 每条记录都有版本号
2. HMAC签名 - 防篡改签名机制
3. 审计日志 - 记录所有操作历史
4. 软删除 - 不真正删除，保留历史
"""

import hashlib
import hmac
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from functools import wraps

# 安全配置
SECURITY_CONFIG = {
    "secret_key_env": "DNA_SECRET_KEY",  # 秘钥环境变量名
    "audit_log_file": ".dna/audit_log.json",  # 审计日志文件
    "current_version": 1,  # 当前数据版本
}

# 审计日志目录
ROOT = Path(__file__).parent.parent
AUDIT_LOG = ROOT / SECURITY_CONFIG["audit_log_file"]


def get_secret_key() -> str:
    """获取签名秘钥"""
    env_key = SECURITY_CONFIG["secret_key_env"]
    key = os.environ.get(env_key)
    if not key:
        # 如果没有设置秘钥，使用默认警告秘钥（生产环境应该设置）
        import warnings
        warnings.warn(
            f"环境变量 {env_key} 未设置，使用默认秘钥。"
            "生产环境请设置: export DNA_SECRET_KEY=your-secret-key",
            UserWarning
        )
        key = "DNA-DEFAULT-DEV-KEY-CHANGE-IN-PRODUCTION"
    return key


def compute_signature(data: Dict[str, Any], secret_key: str) -> str:
    """
    计算数据的HMAC-SHA256签名
    
    Args:
        data: 要签名的数据字典
        secret_key: 秘钥
    
    Returns:
        签名字符串
    """
    # 排除签名字段本身
    signable_data = {k: v for k, v in data.items() if k not in ["signature", "checksum"]}
    # 按key排序确保一致性
    content = json.dumps(signable_data, sort_keys=True, ensure_ascii=False, default=str)
    signature = hmac.new(
        secret_key.encode('utf-8'),
        content.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


def verify_signature(data: Dict[str, Any]) -> bool:
    """
    验证数据签名
    
    Args:
        data: 包含签名的数据字典
    
    Returns:
        签名是否有效
    """
    if "signature" not in data:
        return False
    
    secret_key = get_secret_key()
    expected_signature = compute_signature(data, secret_key)
    return hmac.compare_digest(data["signature"], expected_signature)


def add_security_fields(record: Dict[str, Any], is_new: bool = True) -> Dict[str, Any]:
    """
    为记录添加安全字段
    
    Args:
        record: 原始记录
        is_new: 是否是新记录
    
    Returns:
        添加安全字段后的记录
    """
    now = datetime.now().isoformat()
    secret_key = get_secret_key()
    
    if is_new:
        # 新记录
        record["version"] = SECURITY_CONFIG["current_version"]
        record["created_at"] = now
        record["updated_at"] = now
        record["created_by"] = "dna_tool"
        record["deleted"] = False  # 软删除标记
        record["delete_reason"] = None
    else:
        # 更新记录
        record["updated_at"] = now
        record["version"] = record.get("version", 1) + 1
    
    # 计算签名
    record["signature"] = compute_signature(record, secret_key)
    return record


def record_operation(
    operation: str,
    target_id: str,
    target_type: str,
    details: Dict[str, Any],
    operator: str = "dna_tool",
    success: bool = True
) -> None:
    """
    记录操作到审计日志
    
    Args:
        operation: 操作类型 (create, update, delete, verify, access)
        target_id: 目标ID
        target_type: 目标类型 (strand, fix_log, insight, etc.)
        details: 操作详情
        operator: 操作者
        success: 是否成功
    """
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "operation": operation,
        "target_id": target_id,
        "target_type": target_type,
        "details": details,
        "operator": operator,
        "success": success,
        "ip_address": "localhost",  # 本地使用
    }
    
    # 加载现有审计日志
    audit_log = load_audit_log()
    audit_log["entries"].append(audit_entry)
    
    # 只保留最近10000条记录，防止文件过大
    if len(audit_log["entries"]) > 10000:
        audit_log["entries"] = audit_log["entries"][-5000:]
    
    # 保存审计日志
    save_audit_log(audit_log)


def load_audit_log() -> Dict[str, Any]:
    """加载审计日志"""
    if AUDIT_LOG.exists():
        try:
            with open(AUDIT_LOG, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    
    return {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "entries": []
    }


def save_audit_log(log: Dict[str, Any]) -> None:
    """保存审计日志"""
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(AUDIT_LOG, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)


def soft_delete(
    record: Dict[str, Any],
    reason: str,
    operator: str = "dna_tool"
) -> Dict[str, Any]:
    """
    软删除记录（不真正删除，保留历史）
    
    Args:
        record: 要删除的记录
        reason: 删除原因
        operator: 操作者
    
    Returns:
        标记为已删除的记录
    """
    record["deleted"] = True
    record["delete_reason"] = reason
    record["deleted_at"] = datetime.now().isoformat()
    record["deleted_by"] = operator
    
    # 重新计算签名
    record = add_security_fields(record, is_new=False)
    
    # 记录审计日志
    record_operation(
        operation="soft_delete",
        target_id=record.get("id", record.get("dna_id", "unknown")),
        target_type=record.get("dna_type", "unknown"),
        details={"reason": reason},
        operator=operator,
        success=True
    )
    
    return record


def verify_and_fix_record(
    record: Dict[str, Any],
    strict: bool = False
) -> tuple[bool, str]:
    """
    验证并尝试修复记录
    
    Args:
        record: 要验证的记录
        strict: 是否严格模式（严格模式不允许修复）
    
    Returns:
        (是否有效, 状态消息)
    """
    record_id = record.get("id", record.get("dna_id", "unknown"))
    
    # 检查是否已删除
    if record.get("deleted", False):
        return True, f"Record {record_id} is soft-deleted"
    
    # 检查是否有签名
    if "signature" not in record:
        if strict:
            return False, f"Record {record_id} has no signature"
        else:
            # 尝试修复：重新计算签名
            record = add_security_fields(record, is_new=False)
            return True, f"Record {record_id} signature was missing, fixed"
    
    # 验证签名
    if not verify_signature(record):
        if strict:
            return False, f"Record {record_id} signature mismatch (possible tampering)"
        else:
            # 尝试修复：重新计算签名（但记录原始签名用于审计）
            record["original_signature"] = record["signature"]
            record = add_security_fields(record, is_new=False)
            record["signature_fixed"] = True
            record["signature_fixed_at"] = datetime.now().isoformat()
            return True, f"Record {record_id} signature was invalid, fixed (original logged)"
    
    return True, f"Record {record_id} is valid"


def get_audit_log(
    target_id: Optional[str] = None,
    operation: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    查询审计日志
    
    Args:
        target_id: 目标ID过滤
        operation: 操作类型过滤
        limit: 返回条数限制
    
    Returns:
        符合条件的审计记录列表
    """
    audit_log = load_audit_log()
    entries = audit_log.get("entries", [])
    
    # 过滤
    if target_id:
        entries = [e for e in entries if e.get("target_id") == target_id]
    if operation:
        entries = [e for e in entries if e.get("operation") == operation]
    
    # 按时间倒序
    entries = sorted(entries, key=lambda x: x.get("timestamp", ""), reverse=True)
    
    return entries[:limit]


def audit_operation(operation_type: str):
    """
    装饰器：自动记录操作到审计日志
    
    Usage:
        @audit_operation("create")
        def create_record(data):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = None
            success = True
            error_msg = None
            
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                success = False
                error_msg = str(e)
                raise
            finally:
                record_operation(
                    operation=operation_type,
                    target_id=str(args[0]) if args else str(kwargs),
                    target_type=func.__name__,
                    details={
                        "args": str(args)[:200],
                        "kwargs": str(kwargs)[:200],
                        "error": error_msg
                    },
                    success=success
                )
        
        return wrapper
    return decorator


# ============================================================
# 批量迁移工具
# ============================================================

def migrate_existing_data():
    """
    迁移现有数据，添加安全字段
    
    用于首次启用安全模块时，为现有数据添加版本控制和签名
    """
    import warnings
    
    warnings.warn(
        "migrate_existing_data() 已被弃用，请使用 dna_tool.py 的 --migrate 选项",
        DeprecationWarning
    )


def generate_security_report() -> Dict[str, Any]:
    """
    生成数据安全报告
    
    Returns:
        安全报告字典
    """
    audit_log = load_audit_log()
    entries = audit_log.get("entries", [])
    
    # 统计操作类型
    operations = {}
    for entry in entries:
        op = entry.get("operation", "unknown")
        operations[op] = operations.get(op, 0) + 1
    
    # 统计失败操作
    failed = sum(1 for e in entries if not e.get("success", True))
    
    # 最近24小时的活跃度
    from datetime import timedelta
    cutoff = (datetime.now() - timedelta(hours=24)).isoformat()
    recent = sum(1 for e in entries if e.get("timestamp", "") > cutoff)
    
    return {
        "total_operations": len(entries),
        "operation_breakdown": operations,
        "failed_operations": failed,
        "recent_24h": recent,
        "secret_key_set": bool(os.environ.get(SECURITY_CONFIG["secret_key_env"])),
        "audit_log_size_kb": AUDIT_LOG.stat().st_size / 1024 if AUDIT_LOG.exists() else 0,
    }
