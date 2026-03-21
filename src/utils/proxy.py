"""
Proxy rotation interface.

Defines the abstract ProxyProvider contract and ships a simple
round-robin implementation. Production deployments typically plug
in a paid proxy service (BrightData, Oxylabs, etc.) by implementing
the same interface.

Note: full integration with commercial proxy providers is available
on request. This module demonstrates the architecture pattern.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional

from src.utils.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ProxyConfig:
    """Configuration for a single proxy endpoint."""

    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    protocol: str = "http"

    @property
    def url(self) -> str:
        auth = f"{self.username}:{self.password}@" if self.username else ""
        return f"{self.protocol}://{auth}{self.host}:{self.port}"


class ProxyProvider(ABC):
    """
    Abstract proxy provider interface.

    All proxy rotation strategies implement this contract, allowing
    the engine to swap providers without changing scraper code.
    """

    @abstractmethod
    async def get_proxy(self) -> Optional[ProxyConfig]:
        """Return the next proxy to use, or None if unavailable."""
        ...

    @abstractmethod
    async def report_failure(self, proxy: ProxyConfig, error: str) -> None:
        """Report a failed request so the provider can deprioritize the proxy."""
        ...

    @abstractmethod
    async def health_check(self) -> dict:
        """Return provider health status."""
        ...


class RoundRobinProvider(ProxyProvider):
    """
    Simple round-robin proxy rotation.

    Cycles through a static list of proxies. Suitable for development
    and testing. Production usage should implement a provider that
    connects to a proxy API with automatic rotation and health checking.
    """

    def __init__(self, proxies: Optional[List[ProxyConfig]] = None) -> None:
        self._proxies = proxies or []
        self._index = 0
        self._failures: dict[str, int] = {}

    async def get_proxy(self) -> Optional[ProxyConfig]:
        if not self._proxies:
            return None
        proxy = self._proxies[self._index % len(self._proxies)]
        self._index += 1
        return proxy

    async def report_failure(self, proxy: ProxyConfig, error: str) -> None:
        key = proxy.url
        self._failures[key] = self._failures.get(key, 0) + 1
        logger.warning("proxy.failure", proxy=proxy.host, error=error)

    async def health_check(self) -> dict:
        return {
            "provider": "round-robin",
            "total_proxies": len(self._proxies),
            "failure_counts": dict(self._failures),
        }
