"""
CareerCraft Agent — 异步数据库引擎与会话管理

SQLAlchemy 2.0 async + aiosqlite，启用 WAL 模式保证性能和崩溃恢复能力。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator, Optional

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

# 数据库文件路径：~/.careercraft/career.db
DEFAULT_DB_DIR = Path.home() / ".careercraft"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "career.db"

# 确保目录存在
DEFAULT_DB_DIR.mkdir(parents=True, exist_ok=True)

# 异步引擎，启用 WAL 模式
engine = create_async_engine(
    f"sqlite+aiosqlite:///{DEFAULT_DB_PATH}",
    echo=False,
    connect_args={"check_same_thread": False},
    # WAL 模式通过 PRAGMA 在初始化时设置
)

# 异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# 声明性基类
Base = declarative_base()


async def init_db() -> None:
    """初始化数据库：创建所有表结构。
    应用启动时调用一次。"""
    async with engine.begin() as conn:
        # 启用 WAL 模式以支持读写并发
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
        await conn.exec_driver_sql("PRAGMA foreign_keys=ON")
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """异步会话依赖注入器。
    用于 FastAPI 或其他异步框架的会话管理。"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """关闭数据库引擎，释放连接池。
    应用退出时调用。"""
    await engine.dispose()
