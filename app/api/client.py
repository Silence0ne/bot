from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class APIClient:
    """
    Async HTTP client for the Natiq API.
    """

    def __init__(self) -> None:
        self._settings = get_settings()

        self._client = httpx.AsyncClient(
            base_url=self._settings.NATIQ_PRIMARY_API.rstrip("/"),
            headers=self._settings.api_headers,
            timeout=httpx.Timeout(
                connect=self._settings.NATIQ_API_TIMEOUT,
                read=self._settings.NATIQ_API_TIMEOUT * 2,
                write=self._settings.NATIQ_API_TIMEOUT,
                pool=self._settings.NATIQ_API_TIMEOUT * 2,
            ),
            follow_redirects=True,
        )

        logger.info(
            "API client initialized (%s)",
            self._settings.NATIQ_PRIMARY_API,
        )

    # ==================================================
    # Internal
    # ==================================================

    @staticmethod
    def _normalize_endpoint(
        endpoint: str,
    ) -> str:
        if endpoint.startswith("/"):
            return endpoint

        return f"/{endpoint}"

    async def _request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:

        endpoint = self._normalize_endpoint(
            endpoint,
        )

        logger.debug(
            "%s %s",
            method,
            endpoint,
        )

        try:
            response = await self._client.request(
                method=method,
                url=endpoint,
                params=params,
                json=json,
            )
        except (httpx.ConnectError, httpx.TimeoutException) as exc:
            # If primary fails, try secondary if configured
            secondary_api = getattr(self._settings, "NATIQ_SECONDARY_API", None)
            if secondary_api and secondary_api != str(self._client.base_url):
                logger.warning(
                    "Primary API failed, trying secondary: %s. Error: %s",
                    secondary_api,
                    exc,
                )
                # This is a bit simplified, ideally we'd re-initialize client or just change base_url.
                # Since client is initialized once, let's just make a direct request to the secondary.
                async with httpx.AsyncClient(
                    base_url=secondary_api.rstrip("/"),
                    headers=self._settings.api_headers,
                    timeout=self._client.timeout,
                    follow_redirects=True,
                ) as client:
                    response = await client.request(
                        method=method,
                        url=endpoint,
                        params=params,
                        json=json,
                    )
            else:
                raise

        if response.is_error:
            logger.warning(
                "API %s %s -> %s\n%s",
                method,
                endpoint,
                response.status_code,
                response.text[:500],
            )

            response.raise_for_status()

        return response

    # ==================================================
    # Public HTTP methods
    # ==================================================

    async def get(
        self,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> httpx.Response:

        return await self._request(
            "GET",
            endpoint,
            params=params,
        )

    async def post(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:

        return await self._request(
            "POST",
            endpoint,
            json=json,
        )

    async def put(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:

        return await self._request(
            "PUT",
            endpoint,
            json=json,
        )

    async def patch(
        self,
        endpoint: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:

        return await self._request(
            "PATCH",
            endpoint,
            json=json,
        )

    async def delete(
        self,
        endpoint: str,
    ) -> httpx.Response:

        return await self._request(
            "DELETE",
            endpoint,
        )

    # ==================================================
    # Lifecycle
    # ==================================================

    async def close(self) -> None:
        await self._client.aclose()

        logger.info(
            "API client closed.",
        )
