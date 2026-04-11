import json
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


def _http_get_json(url: str, timeout: int = 12) -> dict[str, Any]: # 发送 HTTP GET 请求并解析 JSON 响应
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "ai-product-team-copilot/1.0",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        payload = response.read().decode("utf-8")
        return json.loads(payload)


def _extract_duckduckgo_topics(related_topics: list[dict[str, Any]]) -> list[dict[str, str]]: # 从 DuckDuckGo 的 RelatedTopics 中提取结果
    results: list[dict[str, str]] = []
    for item in related_topics:
        if "Topics" in item and isinstance(item["Topics"], list):
            results.extend(_extract_duckduckgo_topics(item["Topics"]))
            continue

        text = item.get("Text")
        first_url = item.get("FirstURL")
        if text and first_url:
            title = text.split(" - ", 1)[0].strip()
            results.append(
                {
                    "title": title or "Related Topic",
                    "url": first_url,
                    "snippet": text,
                }
            )
    return results


def web_search(args: dict[str, Any]) -> dict[str, Any]:
    query = str(args.get("query", "")).strip()
    if not query:
        return {"query": "", "results": [], "error": "query is required"}

    max_results = args.get("max_results", 5)
    try:
        max_results = max(1, min(int(max_results), 8))
    except (TypeError, ValueError):
        max_results = 5

    results: list[dict[str, str]] = []

    try:
        ddg_url = (
            "https://api.duckduckgo.com/?q="
            f"{quote_plus(query)}&format=json&no_redirect=1&no_html=1"
        )
        ddg_data = _http_get_json(ddg_url)

        abstract = ddg_data.get("AbstractText")
        abstract_url = ddg_data.get("AbstractURL")
        heading = ddg_data.get("Heading")
        if abstract and abstract_url:
            results.append(
                {
                    "title": heading or query,
                    "url": abstract_url,
                    "snippet": abstract,
                }
            )

        related = ddg_data.get("RelatedTopics")
        if isinstance(related, list):
            results.extend(_extract_duckduckgo_topics(related))
    except Exception as exc:
        return {
            "query": query,
            "results": [],
            "error": f"duckduckgo request failed: {str(exc)}",
        }

    # Fallback to Wikipedia OpenSearch when DDG has sparse results.
    if len(results) < max_results:
        try:
            wiki_url = (
                "https://en.wikipedia.org/w/api.php?action=opensearch&format=json"
                f"&search={quote_plus(query)}&limit={max_results}"
            )
            wiki_data = _http_get_json(wiki_url)
            if isinstance(wiki_data, list) and len(wiki_data) >= 4:
                titles = wiki_data[1] if isinstance(wiki_data[1], list) else []
                descriptions = wiki_data[2] if isinstance(wiki_data[2], list) else []
                links = wiki_data[3] if isinstance(wiki_data[3], list) else []

                for title, description, link in zip(titles, descriptions, links):
                    if not title or not link:
                        continue
                    results.append(
                        {
                            "title": str(title),
                            "url": str(link),
                            "snippet": str(description) if description else "Wikipedia result",
                        }
                    )
                    if len(results) >= max_results:
                        break
        except Exception:
            pass

    deduped: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for item in results:
        url = item.get("url", "")
        if not url or url in seen_urls:
            continue
        deduped.append(item)
        seen_urls.add(url)
        if len(deduped) >= max_results:
            break

    return {"query": query, "results": deduped}


def market_scan(args: dict[str, Any]) -> dict[str, Any]:
    product = str(args.get("product", "")).strip()
    region = str(args.get("region", "global")).strip() or "global"
    max_results = args.get("max_results", 5)

    if not product:
        return {"product": "", "results": [], "error": "product is required"}

    query = f"{product} market size trends growth forecast {region}"
    base_result = web_search({"query": query, "max_results": max_results})
    return {
        "product": product,
        "region": region,
        "query": query,
        "results": base_result.get("results", []),
        "error": base_result.get("error"),
    }


def competitor_scan(args: dict[str, Any]) -> dict[str, Any]:
    product = str(args.get("product", "")).strip()
    max_results = args.get("max_results", 5)

    if not product:
        return {"product": "", "results": [], "error": "product is required"}

    query = f"top competitors alternatives for {product} pricing positioning"
    base_result = web_search({"query": query, "max_results": max_results})
    return {
        "product": product,
        "query": query,
        "results": base_result.get("results", []),
        "error": base_result.get("error"),
    }


def user_pain_scan(args: dict[str, Any]) -> dict[str, Any]:
    product = str(args.get("product", "")).strip()
    target_users = str(args.get("target_users", "")).strip()
    max_results = args.get("max_results", 5)

    if not product:
        return {"product": "", "results": [], "error": "product is required"}

    user_clause = f" for {target_users}" if target_users else ""
    query = f"common pain points problems complaints {product}{user_clause}"
    base_result = web_search({"query": query, "max_results": max_results})
    return {
        "product": product,
        "target_users": target_users,
        "query": query,
        "results": base_result.get("results", []),
        "error": base_result.get("error"),
    }