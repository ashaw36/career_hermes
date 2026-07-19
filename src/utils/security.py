"""
CareerCraft Agent — 安全工具

API Key 加密存储、数据库敏感字段加密。
Sprint 1 实现基础版，预留扩展口。
"""

from __future__ import annotations

import base64
import hashlib
import os
from pathlib import Path
from typing import Optional

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    keyring = None  # type: ignore
    KEYRING_AVAILABLE = False

try:
    from cryptography.fernet import Fernet
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False


# 存储路径
SECURE_DIR = Path.home() / ".careercraft" / "secure"
SECURE_DIR.mkdir(parents=True, exist_ok=True)

SALT_FILE = SECURE_DIR / ".salt"
KEY_FILE = SECURE_DIR / ".key"


def _get_or_create_salt() -> bytes:
    """获取或创建随机 salt"""
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    # 设置文件权限为当前用户可读写
    os.chmod(SALT_FILE, 0o600)
    return salt


def _derive_key(password: str, salt: bytes) -> bytes:
    """从主密码派生加密密钥"""
    if not CRYPTO_AVAILABLE:
        # 降级方案：简单 hash
        return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000, dklen=32)

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def _get_fernet(password: str) -> Optional["Fernet"]:
    if not CRYPTO_AVAILABLE:
        return None
    salt = _get_or_create_salt()
    key = _derive_key(password, salt)
    return Fernet(key)


class SecureStorage:
    """
    安全存储类

    优先尝试系统 keyring；不可用时回退到本地加密文件。
    """

    SERVICE_NAME = "careercraft-agent"

    @classmethod
    def store_api_key(cls, provider_name: str, api_key: str, master_password: Optional[str] = None) -> bool:
        """
        存储 API Key

        Args:
            provider_name: 供应商名称，e.g. "tongyi"
            api_key: 明文 API Key
            master_password: 主密码（本地加密时需要）

        Returns:
            是否存储成功
        """
        # 尝试 keyring
        if KEYRING_AVAILABLE:
            try:
                keyring.set_password(cls.SERVICE_NAME, provider_name, api_key)
                return True
            except Exception:
                pass  # 降级到本地加密

        # 本地加密存储
        if not CRYPTO_AVAILABLE:
            raise RuntimeError("无法存储 API Key: cryptography 库未安装")
        if not master_password:
            raise ValueError("本地加密存储需要主密码")

        fernet = _get_fernet(master_password)
        if fernet is None:
            raise RuntimeError("加密初始化失败")

        encrypted = fernet.encrypt(api_key.encode())
        key_path = SECURE_DIR / f"{provider_name}.key"
        key_path.write_bytes(encrypted)
        os.chmod(key_path, 0o600)
        return True

    @classmethod
    def retrieve_api_key(cls, provider_name: str, master_password: Optional[str] = None) -> Optional[str]:
        """
        获取 API Key

        Args:
            provider_name: 供应商名称
            master_password: 主密码（本地加密时需要）

        Returns:
            明文 API Key 或 None
        """
        # 尝试 keyring
        if KEYRING_AVAILABLE:
            try:
                key = keyring.get_password(cls.SERVICE_NAME, provider_name)
                if key:
                    return key
            except Exception:
                pass

        # 本地加密文件
        key_path = SECURE_DIR / f"{provider_name}.key"
        if not key_path.exists():
            return None

        if not CRYPTO_AVAILABLE:
            raise RuntimeError("无法解密 API Key: cryptography 库未安装")
        if not master_password:
            raise ValueError("本地加密存储需要主密码")

        fernet = _get_fernet(master_password)
        if fernet is None:
            raise RuntimeError("解密初始化失败")

        encrypted = key_path.read_bytes()
        try:
            return fernet.decrypt(encrypted).decode()
        except Exception:
            raise RuntimeError("API Key 解密失败，可能主密码错误")

    @classmethod
    def has_api_key(cls, provider_name: str) -> bool:
        """检查是否存在 API Key"""
        if KEYRING_AVAILABLE:
            try:
                if keyring.get_password(cls.SERVICE_NAME, provider_name):
                    return True
            except Exception:
                pass
        return (SECURE_DIR / f"{provider_name}.key").exists()

    @classmethod
    def delete_api_key(cls, provider_name: str) -> bool:
        """删除 API Key"""
        deleted = False
        if KEYRING_AVAILABLE:
            try:
                keyring.delete_password(cls.SERVICE_NAME, provider_name)
                deleted = True
            except Exception:
                pass
        key_path = SECURE_DIR / f"{provider_name}.key"
        if key_path.exists():
            key_path.unlink()
            deleted = True
        return deleted
