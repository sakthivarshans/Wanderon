"""
WanderOn Search Layer — grounded real-world data via web search + scraping.
Strategy:
  1. SerpAPI (Google Hotels) if user provides key — most accurate
  2. DuckDuckGo HTML search (no key needed) — free fallback
  3. Parse Booking.com search results for hotel data
All results are returned as structured dicts for the LLM to format.
"""

import httpx
import logging
import re
import json
import urllib.parse
from bs4 import BeautifulSoup

log = logging.getLogger("wanderon.search")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


# ── DuckDuckGo search (no key needed) ────────────────────────────────────────

async def ddg_search(query: str, max_results: int = 8) -> list[dict]:
    """Search DuckDuckGo HTML and return list of {title, url, snippet}."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        async with httpx.AsyncClient(timeout=15, headers=HEADERS, follow_redirects=True) as c:
            r = await c.get(url)
        soup = BeautifulSoup(r.text, "lxml")
        results = []
        for result in soup.select(".result__body")[:max_results]:
            title_el = result.select_one(".result__title")
            url_el   = result.select_one(".result__url")
            snip_el  = result.select_one(".result__snippet")
            if title_el and url_el:
                raw_url = url_el.get_text(strip=True)
                if not raw_url.startswith("http"):
                    raw_url = "https://" + raw_url
                results.append({
                    "title":   title_el.get_text(strip=True),
                    "url":     raw_url,
                    "snippet": snip_el.get_text(strip=True) if snip_el else "",
                })
        return results
    except Exception as e:
        log.warning(f"DDG search failed: {e}")
        return []


# ── SerpAPI hotel search (key required) ──────────────────────────────────────

async def serpapi_hotels(destination: str, check_in: str, check_out: str,
                          adults: int, budget_per_night: int,
                          currency: str, api_key: str) -> list[dict]:
    """
    Use SerpAPI Google Hotels endpoint.
    Returns list of {name, rating, price_per_night, url, address, highlights}
    """
    try:
        params = {
            "engine":      "google_hotels",
            "q":           f"hotels in {destination}",
            "check_in_date":  check_in,
            "check_out_date": check_out,
            "adults":      adults,
            "currency":    currency,
            "gl":          "us",
            "hl":          "en",
            "api_key":     api_key,
        }
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get("https://serpapi.com/search", params=params)
            data = r.json()

        hotels = []
        for h in data.get("properties", [])[:12]:
            price = h.get("rate_per_night", {})
            price_val = price.get("lowest", "") if isinstance(price, dict) else str(price)
            price_num = int(re.sub(r"[^\d]", "", str(price_val)) or 0)
            if budget_per_night and price_num > budget_per_night * 1.3:
                continue
            hotels.append({
                "name":      h.get("name", ""),
                "rating":    h.get("overall_rating", ""),
                "reviews":   h.get("reviews", ""),
                "price":     price_val or "check site",
                "price_num": price_num,
                "address":   h.get("description", ""),
                "url":       h.get("link", f"https://www.google.com/travel/hotels/{urllib.parse.quote(destination)}"),
                "highlights": ", ".join(h.get("amenities", [])[:5]),
                "source":    "Google Hotels",
            })
        hotels.sort(key=lambda x: x.get("price_num", 999999))
        return hotels[:9]
    except Exception as e:
        log.warning(f"SerpAPI hotels failed: {e}")
        return []


# ── Booking.com scrape (no key needed) ───────────────────────────────────────

async def scrape_booking(destination: str, check_in: str, check_out: str,
                          adults: int = 2) -> list[dict]:
    """
    Scrape Booking.com search page for real hotel data.
    Returns list of {name, rating, price, url, location, highlights}
    """
    try:
        enc_dest = urllib.parse.quote(destination)
        # Build Booking.com search URL
        ci = check_in.replace("-", "") if "-" in check_in else check_in
        co = check_out.replace("-", "") if "-" in check_out else check_out
        url = (
            f"https://www.booking.com/searchresults.html"
            f"?ss={enc_dest}&checkin={check_in}&checkout={check_out}"
            f"&group_adults={adults}&no_rooms=1&lang=en-gb"
        )
        async with httpx.AsyncClient(timeout=20, headers=HEADERS, follow_redirects=True) as c:
            r = await c.get(url)

        soup = BeautifulSoup(r.text, "lxml")
        hotels = []

        # Booking.com data is often in JSON-LD scripts
        for script in soup.find_all("script", type="application/ld+json"):
            try:
                data = json.loads(script.string or "")
                if isinstance(data, list):
                    for item in data:
                        if item.get("@type") == "Hotel":
                            hotels.append(_parse_ld_hotel(item, destination))
                elif data.get("@type") == "Hotel":
                    hotels.append(_parse_ld_hotel(data, destination))
            except Exception:
                pass

        # Fallback: parse property cards
        if not hotels:
            for card in soup.select("[data-testid='property-card']")[:10]:
                try:
                    name_el  = card.select_one("[data-testid='title']")
                    price_el = card.select_one("[data-testid='price-and-discounted-price']")
                    score_el = card.select_one("[data-testid='review-score']")
                    loc_el   = card.select_one("[data-testid='address']")
                    link_el  = card.select_one("a[data-testid='title-link']")

                    name  = name_el.get_text(strip=True) if name_el else ""
                    price = price_el.get_text(strip=True) if price_el else "Check site"
                    score = score_el.get_text(strip=True)[:3] if score_el else ""
                    loc   = loc_el.get_text(strip=True) if loc_el else destination
                    href  = link_el.get("href", "") if link_el else ""
                    if not href.startswith("http"):
                        href = "https://www.booking.com" + href

                    if name:
                        hotels.append({
                            "name":      name,
                            "rating":    score,
                            "price":     price,
                            "price_num": int(re.sub(r"[^\d]", "", price) or 0),
                            "address":   loc,
                            "url":       href.split("?")[0] if href else f"https://www.booking.com/searchresults.html?ss={enc_dest}",
                            "highlights":"",
                            "source":    "Booking.com",
                        })
                except Exception:
                    continue

        return [h for h in hotels if h.get("name")][:9]

    except Exception as e:
        log.warning(f"Booking.com scrape failed: {e}")
        return []


def _parse_ld_hotel(data: dict, destination: str) -> dict:
    return {
        "name":      data.get("name", ""),
        "rating":    str(data.get("aggregateRating", {}).get("ratingValue", "")),
        "price":     "",
        "price_num": 0,
        "address":   data.get("address", {}).get("streetAddress", destination) if isinstance(data.get("address"), dict) else str(data.get("address", "")),
        "url":       data.get("url", f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote(destination)}"),
        "highlights":"",
        "source":    "Booking.com",
    }


# ── Google Hotels deep link (always works, no key needed) ────────────────────

def google_hotels_link(destination: str, check_in: str = "", check_out: str = "") -> str:
    q = urllib.parse.quote(f"hotels in {destination}")
    base = f"https://www.google.com/travel/hotels?q={q}"
    if check_in:
        base += f"&ved=&ap=aAA&hl=en&gl=us"
    return base

def booking_link(destination: str) -> str:
    return f"https://www.booking.com/searchresults.html?ss={urllib.parse.quote(destination)}&lang=en-gb"

def agoda_link(destination: str) -> str:
    return f"https://www.agoda.com/search?city={urllib.parse.quote(destination)}"

def hostelworld_link(destination: str) -> str:
    return f"https://www.hostelworld.com/st/hostels/{urllib.parse.quote(destination.lower().replace(' ','-'))}"


# ── Flight search links (no scraping needed — deep links work) ───────────────

def google_flights_link(origin: str, destination: str, depart: str = "") -> str:
    o = urllib.parse.quote(origin)
    d = urllib.parse.quote(destination)
    return f"https://www.google.com/travel/flights?q=Flights+from+{o}+to+{d}"

def skyscanner_link(origin: str, destination: str) -> str:
    o = origin.replace(" ", "-").lower()
    d = destination.replace(" ", "-").lower()
    return f"https://www.skyscanner.net/transport/flights/{o}/{d}/"


# ── Unified hotel fetch — tries best available source ────────────────────────

async def fetch_hotels(destination: str, check_in: str, check_out: str,
                        adults: int, total_budget: int, nights: int,
                        currency: str, serpapi_key: str = "") -> dict:
    """
    Master hotel fetch. Returns:
    {
        hotels: [...],          # list of hotel dicts
        source: str,            # where data came from
        booking_url: str,       # direct booking search link
        google_url: str,
        no_data: bool
    }
    """
    budget_per_night = (total_budget // max(nights, 1)) if nights else 0
    hotels = []
    source = ""

    # Try SerpAPI first (most accurate)
    if serpapi_key:
        hotels = await serpapi_hotels(destination, check_in, check_out, adults, budget_per_night, currency, serpapi_key)
        if hotels:
            source = "Google Hotels (SerpAPI)"

    # Try Booking.com scrape
    if not hotels and check_in and check_out:
        hotels = await scrape_booking(destination, check_in, check_out, adults)
        if hotels:
            source = "Booking.com"

    # DDG search for hotels as final fallback
    if not hotels:
        query = f"best hotels in {destination} budget {total_budget} {currency}"
        results = await ddg_search(query, max_results=6)
        if results:
            for r in results:
                if any(k in r["url"].lower() for k in ["booking.com", "tripadvisor", "hotels.com", "agoda"]):
                    hotels.append({
                        "name":    r["title"].split(" - ")[0].split(" | ")[0][:60],
                        "price":   "Check site",
                        "price_num": 0,
                        "rating":  "",
                        "address": destination,
                        "url":     r["url"],
                        "highlights": r["snippet"][:100],
                        "source":  "Web search",
                    })
            source = "Web search"

    return {
        "hotels":      hotels,
        "source":      source,
        "booking_url": booking_link(destination),
        "google_url":  google_hotels_link(destination, check_in, check_out),
        "agoda_url":   agoda_link(destination),
        "no_data":     len(hotels) == 0,
    }


# ── General web search for any live info ─────────────────────────────────────

async def web_search_context(query: str) -> str:
    """
    Run a web search and return a plain-text summary of top results.
    Used to ground LLM answers in real current data.
    """
    results = await ddg_search(query, max_results=5)
    if not results:
        return ""
    lines = []
    for r in results:
        lines.append(f"Source: {r['url']}")
        lines.append(f"{r['title']}: {r['snippet']}")
        lines.append("")
    return "\n".join(lines)[:3000]
