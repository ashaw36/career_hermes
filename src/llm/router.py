"""
CareerCraft Agent — LLM 路由器

统一对外 LLM 调用接口，支持流式输出、超时控制、故障降级。
Sprint 1 实现单模型通义千问集成，预留多模型扩展口。
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from src.config.settings import CareerCraftSettings, LLMProviderConfig, get_settings


class LLMError(Exception):
    """LLM 调用异常基类"""

    def __init__(self, message: str, provider: str = "", model: str = "") -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model


class LLMTimeoutError(LLMError):
    """LLM 超时"""


class LLMRateLimitError(LLMError):
    """LLM 限流"""


class LLMContentError(LLMError):
    """LLM 返回内容异常"""


class LLMRouter:
    """
    LLM 路由器

    使用示例：
        router = LLMRouter()
        # 非流式
        response = await router.chat(messages=[...])
        # 流式
        async for chunk in router.chat(messages=[...], stream=True):
            print(chunk, end="")
    """

    def __init__(self, settings: Optional[CareerCraftSettings] = None) -> None:
        self.settings = settings or get_settings()
        self._client: Optional[httpx.AsyncClient] = None
        self._provider: Optional[LLMProviderConfig] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(30.0, connect=10.0),
                limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
            )
        return self._client

    def _resolve_provider(self) -> LLMProviderConfig:
        """解析当前使用的 LLM 供应商配置"""
        if not self._provider:
            default_name = self.settings.default_llm_provider
            for p in self.settings.llm_providers:
                if p.name == default_name and p.enabled:
                    self._provider = p
                    break
            if not self._provider:
                raise LLMError(f"未找到启用的 LLM 供应商: {default_name}")
        return self._provider

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = False,
        json_mode: bool = False,
    ) -> str | AsyncIterator[str]:
        """
        统一对话接口

        Args:
            messages: OpenAI 格式消息列表，e.g. [{"role": "user", "content": "..."}]
            model: 指定模型，None 时使用供应商默认模型
            temperature: 采样温度
            stream: 是否流式输出
            json_mode: 是否强制返回 JSON

        Returns:
            非流式时返回完整字符串；流式时返回 AsyncIterator[str]
        """
        provider = self._resolve_provider()
        use_model = model or provider.default_model

        if not provider.api_key:
            raise LLMError("API Key 未配置", provider=provider.name, model=use_model)

        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {
            "model": use_model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        base_url = provider.base_url or "https://api.openai.com/v1"
        url = f"{base_url.rstrip('/')}/chat/completions"

        client = await self._get_client()

        try:
            if stream:
                return self._stream_chat(client, url, headers, payload, provider.name, use_model)
            else:
                return await self._complete_chat(
                    client, url, headers, payload, provider.name, use_model
                )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"LLM 请求超时: {e}", provider=provider.name, model=use_model
            )
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMRateLimitError(
                    "LLM 限流，请稍后重试", provider=provider.name, model=use_model
                )
            raise LLMError(
                f"LLM HTTP 错误 {e.response.status_code}: {e.response.text}",
                provider=provider.name,
                model=use_model,
            )
        except Exception as e:
            raise LLMError(
                f"LLM 调用失败: {e}", provider=provider.name, model=use_model
            )

    async def _complete_chat(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        provider_name: str,
        model: str,
    ) -> str:
        """非流式对话"""
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        if "choices" not in data or not data["choices"]:
            raise LLMContentError("LLM 返回格式异常，缺少 choices", provider_name, model)

        content = data["choices"][0].get("message", {}).get("content", "")
        return content.strip()

    async def _stream_chat(
        self,
        client: httpx.AsyncClient,
        url: str,
        headers: Dict[str, str],
        payload: Dict[str, Any],
        provider_name: str,
        model: str,
    ) -> AsyncIterator[str]:
        """流式对话，逐字返回"""
        async with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data_str = line[6:]  # 去掉 "data: "
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                    delta = (
                        data.get("choices", [{}])[0]
                        .get("delta", {})
                        .get("content", "")
                    )
                    if delta:
                        yield delta
                except json.JSONDecodeError:
                    continue

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None
