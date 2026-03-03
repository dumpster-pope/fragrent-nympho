"""
Researcher — DuckDuckGo search + page scraper for improvement research.
Copied from BookAgent/web_research.py and adapted.
HTTP-only: no Selenium, no Instagram interaction.
"""

import logging
import re
import time
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

log = logging.getLogger("improvement.researcher")

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

_QUERIES = {
    "PROMPT_EXPAND": [
        "AI art prompt ideas unique artistic subjects 2025",
        "stable diffusion creative art styles painting techniques",
        "unusual artistic environments moods for image generation",
    ],
    "API_SCOUT": [
        "free image generation API no key 2025",
        "open source text to image REST API self hosted",
        "free AI image API tier unlimited",
    ],
    "ENGAGEMENT_TUNE": [
        "best Instagram hashtags art 2025 engagement",
        "Instagram comment strategy art accounts growth 2025",
        "AI art Instagram hashtag strategy reach",
    ],
    "BUG_FIX": [
        "Python selenium instagram automation common errors fix",
        "selenium webdriver wait element timeout fix",
    ],
    "FEATURE_PROPOSE": [
        "Instagram reels strategy art accounts 2025",
        "Instagram stories features engagement art creators",
        "Instagram carousel post template art gallery",
    ],
}


def _get(url: str, timeout: int = 15) -> str:
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        r.raise_for_status()
        return r.text
    except Exception as exc:
        log.debug(f"GET failed {url}: {exc}")
        return ""


def _clean_text(html: str, max_chars: int = 4000) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]


def search_duckduckgo(query: str, max_results: int = 6) -> list[dict]:
    url  = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html = _get(url)
    if not html:
        return []
    soup    = BeautifulSoup(html, "html.parser")
    results = []
    for result in soup.select(".result")[:max_results + 4]:
        a    = result.select_one(".result__a")
        snip = result.select_one(".result__snippet")
        if not a:
            continue
        href = a.get("href", "")
        if not href.startswith("http"):
            continue
        results.append({
            "title":   a.get_text(strip=True),
            "url":     href,
            "snippet": snip.get_text(strip=True) if snip else "",
        })
        if len(results) >= max_results:
            break
    return results


def scrape_page(url: str, max_chars: int = 3000) -> str:
    html = _get(url)
    return _clean_text(html, max_chars) if html else ""


def research_category(category: str) -> str:
    """
    Run DuckDuckGo queries for a category and return combined snippet text.
    Scrapes the top result for each query to get richer content.
    """
    queries = _QUERIES.get(category, [])
    if not queries:
        return ""

    chunks = []
    for query in queries:
        log.info(f"Searching: {query}")
        results = search_duckduckgo(query, max_results=4)
        for r in results[:2]:
            chunks.append(f"[{r['title']}] {r['snippet']}")
        # Scrape top result for more detail
        if results:
            time.sleep(1)
            page_text = scrape_page(results[0]["url"], max_chars=2000)
            if page_text:
                chunks.append(f"--- Page content from {results[0]['url']} ---\n{page_text}")
        time.sleep(1)

    return "\n\n".join(chunks)
