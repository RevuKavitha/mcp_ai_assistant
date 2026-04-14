from __future__ import annotations

import os
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


def _summarize_results(results: List[Dict[str, str]]) -> str:
    if not results:
        return "No search results found."
    return " | ".join(
        f"{idx + 1}. {item.get('title', '').strip()}: {item.get('snippet', '').strip()}"
        for idx, item in enumerate(results)
    )


def _tavily_search(query: str, api_key: str, max_items: int = 5) -> Dict[str, Any]:
    payload = {
        "api_key": api_key,
        "query": query,
        "search_depth": "basic",
        "max_results": max_items,
        "include_answer": False,
        "include_raw_content": False,
    }
    with httpx.Client(timeout=20.0) as client:
        response = client.post("https://api.tavily.com/search", json=payload)
        response.raise_for_status()
        body = response.json()

    results: List[Dict[str, str]] = []
    for item in body.get("results", [])[:max_items]:
        results.append(
            {
                "title": str(item.get("title", "")).strip(),
                "url": str(item.get("url", "")).strip(),
                "snippet": str(item.get("content", "")).strip(),
            }
        )
    return {
        "query": query,
        "provider": "tavily",
        "results": results,
        "summary": _summarize_results(results),
    }


def _duckduckgo_search(query: str) -> Dict[str, Any]:
    url = "https://duckduckgo.com/html/"
    with httpx.Client(timeout=20.0, follow_redirects=True) as client:
        response = client.get(url, params={"q": query}, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    results = _extract_results(response.text)
    return {
        "query": query,
        "provider": "duckduckgo_html",
        "results": results,
        "summary": _summarize_results(results),
    }


def web_search_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"error": "query is required"}

    tavily_api_key = os.getenv("TAVILY_API_KEY", "").strip()
    try:
        # Prefer API-backed search in production for better reliability.
        if tavily_api_key:
            return _tavily_search(query=query, api_key=tavily_api_key)
        return _duckduckgo_search(query=query)
    except Exception as exc:
        # Final fallback keeps the demo usable even when internet or providers are unavailable.
        return {
            "query": query,
            "provider": "mock_fallback",
            "results": [
                {
                    "title": "Mock Search Result",
                    "url": "https://example.com",
                    "snippet": f"Unable to reach live search. Mocked response for: {query}",
                }
            ],
            "summary": f"Mock search summary for '{query}' (live search unavailable: {exc}).",
        }
