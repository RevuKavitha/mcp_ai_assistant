from __future__ import annotations

from typing import Any, Dict, List

import httpx
from bs4 import BeautifulSoup


def _extract_results(html: str, max_items: int = 5) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[Dict[str, str]] = []
    for result in soup.select("div.result")[:max_items]:
        title_el = result.select_one("a.result__a")
        snippet_el = result.select_one("a.result__snippet") or result.select_one("div.result__snippet")
        if not title_el:
            continue
        items.append(
            {
                "title": title_el.get_text(strip=True),
                "url": title_el.get("href", ""),
                "snippet": snippet_el.get_text(" ", strip=True) if snippet_el else "",
            }
        )
    return items


def web_search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required"}

    url = "https://duckduckgo.com/html/"
    try:
        with httpx.Client(timeout=15.0, follow_redirects=True) as client:
            response = client.get(url, params={"q": query}, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        results = _extract_results(response.text)
        if not results:
            return {"query": query, "results": [], "summary": "No search results found."}

        summary = " | ".join(
            f"{idx + 1}. {item['title']}: {item['snippet']}" for idx, item in enumerate(results)
        )
        return {"query": query, "results": results, "summary": summary}
    except Exception as exc:
        # Fallback keeps demo usable when internet is unavailable.
        return {
            "query": query,
            "results": [
                {
                    "title": "Mock Search Result",
                    "url": "https://example.com",
                    "snippet": f"Unable to reach live search. Mocked response for: {query}",
                }
            ],
            "summary": f"Mock search summary for '{query}' (live search unavailable: {exc}).",
        }
