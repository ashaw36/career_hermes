"""
CareerCraft Agent — 爬虫基类

封装 Playwright 浏览器启动、页面等待、反检测。
"""

from __future__ import annotations

import asyncio
import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    logger.warning("playwright 未安装，爬虫功能不可用")


class CrawlerError(Exception):
    """爬虫异常"""


class BaseCrawler(ABC):
    """
    爬虫基类

    子类实现 search() 方法即可。
    """

    def __init__(self, headless: bool = True, slow_mo: int = 100) -> None:
        self.headless = headless
        self.slow_mo = slow_mo
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _launch(self) -> Page:
        """启动浏览器"""
        if not PLAYWRIGHT_AVAILABLE:
            raise CrawlerError("playwright 未安装，请运行: pip install playwright && playwright install")

        if self._browser is None:
            p = await async_playwright().start()
            self._browser = await p.chromium.launch(
                headless=self.headless,
                slow_mo=self.slow_mo,
            )
            self._context = await self._browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1920, "height": 1080},
            )
            self._page = await self._context.new_page()
        return self._page

    async def _safe_goto(self, url: str, wait_until: str = "networkidle") -> None:
        """安全访问 URL，带随机延迟"""
        page = await self._launch()
        await asyncio.sleep(random.uniform(1.0, 3.0))
        await page.goto(url, wait_until=wait_until)
        await asyncio.sleep(random.uniform(0.5, 1.5))

    async def _random_scroll(self) -> None:
        """随机滚动页面模拟人类行为"""
        if self._page:
            for _ in range(random.randint(2, 5)):
                await self._page.mouse.wheel(0, random.randint(300, 800))
                await asyncio.sleep(random.uniform(0.3, 1.0))

    async def close(self) -> None:
        """关闭浏览器"""
        if self._context:
            await self._context.close()
            self._context = None
        if self._browser:
            await self._browser.close()
            self._browser = None
        self._page = None

    @abstractmethod
    async def search(self, keyword: str, city: Optional[str] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索岗位，子类实现

        Returns:
            岗位列表，每个岗位为 dict：{
                "title": str,
                "company": str,
                "location": str,
                "salary": str,
                "url": str,
                "raw_text": str,  # 完整 JD 文本
            }
        """
        raise NotImplementedError
