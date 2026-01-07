"""Web-related tools."""

import json
from typing import Any
from urllib.parse import quote_plus

import httpx

from honolulu.tools.base import Tool, ToolResult


class WebFetchTool(Tool):
    """Fetch content from a URL."""

    name = "web_fetch"
    description = "Fetch the content of a web page or API endpoint."
    parameters = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to fetch",
            },
            "method": {
                "type": "string",
                "enum": ["GET", "POST"],
                "description": "HTTP method (default: GET)",
                "default": "GET",
            },
            "headers": {
                "type": "object",
                "description": "Optional HTTP headers",
            },
            "body": {
                "type": "string",
                "description": "Optional request body for POST requests",
            },
        },
        "required": ["url"],
    }
    requires_confirmation = False

    async def execute(
        self,
        url: str,
        method: str = "GET",
        headers: dict | None = None,
        body: str | None = None,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    response = await client.post(url, headers=headers, content=body)

                # Try to parse as JSON, otherwise return as text
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type:
                    try:
                        content = response.json()
                    except json.JSONDecodeError:
                        content = response.text
                else:
                    content = response.text

                return ToolResult(
                    success=response.is_success,
                    output={
                        "status_code": response.status_code,
                        "headers": dict(response.headers),
                        "content": content,
                    },
                    error=None if response.is_success else f"HTTP {response.status_code}",
                )

        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                output=None,
                error="Request timed out",
            )
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )


class WebSearchTool(Tool):
    """Search the web using DuckDuckGo."""

    name = "web_search"
    description = "Search the web for information using DuckDuckGo."
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query",
            },
            "max_results": {
                "type": "integer",
                "description": "Maximum number of results (default: 5)",
                "default": 5,
            },
        },
        "required": ["query"],
    }
    requires_confirmation = False

    async def execute(
        self,
        query: str,
        max_results: int = 5,
        **kwargs: Any,
    ) -> ToolResult:
        try:
            # Use DuckDuckGo HTML search (no API key needed)
            encoded_query = quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                )

                if not response.is_success:
                    return ToolResult(
                        success=False,
                        output=None,
                        error=f"Search failed with status {response.status_code}",
                    )

                # Parse results from HTML (basic extraction)
                html = response.text
                results = self._parse_duckduckgo_html(html, max_results)

                return ToolResult(
                    success=True,
                    output={
                        "query": query,
                        "results": results,
                    },
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e),
            )

    def _parse_duckduckgo_html(self, html: str, max_results: int) -> list[dict]:
        """Parse DuckDuckGo HTML results (simple extraction)."""
        import re

        results = []

        # Find result blocks
        result_pattern = r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>([^<]+)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>([^<]+)</a>'

        links = re.findall(result_pattern, html)
        snippets = re.findall(snippet_pattern, html)

        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            results.append(
                {
                    "title": title.strip(),
                    "url": url,
                    "snippet": snippet.strip(),
                }
            )

        return results


def get_web_tools() -> list[Tool]:
    """Get all web tools."""
    return [WebFetchTool(), WebSearchTool()]
