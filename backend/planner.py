"""
WanderOn Planner — grounded in real web data.
Hotels come from Booking.com/SerpAPI scrape, not LLM imagination.
LLM only formats and narrates — it does not invent facts.
"""

import re
import logging
from llm import LLMClient, supports_vision
from travel_data import geocode, nearest_airport, get_attractions, get_weather, is_international, convert_currency
from search import fetch_hotels, web_search_context, google_flights_link, skyscanner_link, booking_link
from security import contains_sensitive_data, sanitize

log = logging.getLogger("wanderon.planner")

NARRATOR_SYSTEM = """You are WanderOn, a travel guide assistant. Your job is to FORMAT and NARRATE real data you are given — you do NOT invent hotel names, prices, or facts. If real data is provided, use ONLY that data. If no hotel data is provided, say so honestly and provide booking links instead of guessing names."""

ITINERARY_SYSTEM = """You are WanderOn, an expert local travel guide. Generate detailed day-by-day itineraries based on the destination. Be specific with real place names, opening hours, transport, and meal spots. Do not fabricate hotel names or prices — those are provided separately."""

GUIDE_SYSTEM = """You are WanderOn, a knowledgeable travel assistant with deep local knowledge. Give accurate, practical, specific information. Never invent hotel names or prices. For factual questions, stick to what you know is accurate."""

VISION_SYSTEM = """You are WanderOn's visual assistant. When shown a photo:
- LANDMARK: name it, city/country, opening hours, entry cost, how to get there, 2 insider tips.
- FOOD/MENU: identify dishes, typical cost, where to find the best version, any dietary notes.
- SIGN/TEXT in foreign language: translate fully and explain context.
- MAP/DOCUMENT: read and explain travel-relevant information.
- UNKNOWN PLACE: describe what you see and offer to help plan a visit.
Keep response under 200 words."""


def _parse_dates(dates_str: str) -> tuple[str, str, int]:
    """
    Try to extract check-in, check-out, nights from freeform date string.
    Returns (check_in_iso, check_out_iso, nights) — empty strings if cannot parse.
    """
    import datetime
    text = dates_str.lower().strip()

    # Try to find day numbers
    nums = re.findall(r"\d+", text)
    months = {
        "jan":"01","feb":"02","mar":"03","apr":"04","may":"05","jun":"06",
        "jul":"07","aug":"08","sep":"09","oct":"10","nov":"11","dec":"12",
        "january":"01","february":"02","march":"03","april":"04","june":"06",
        "july":"07","august":"08","september":"09","october":"10","november":"11","december":"12",
    }

    # "X days" pattern
    days_match = re.search(r"(\d+)\s*day", text)
    if days_match:
        nights = int(days_match.group(1))
        # Try to find a month
        for m_name, m_num in months.items():
            if m_name in text:
                year = datetime.date.today().year
                try:
                    day_match = re.search(r"(\d{1,2})\s*" + m_name[:3], text)
                    start_day = int(day_match.group(1)) if day_match else 1
                    ci = datetime.date(year, int(m_num), start_day)
                    co = ci + datetime.timedelta(days=nights)
                    return ci.isoformat(), co.isoformat(), nights
                except Exception:
                    pass
        return "", "", nights

    # "15 jan to 22 jan" or "dec 20 to dec 27"
    found_months = [(m_name, m_num) for m_name, m_num in months.items() if m_name in text]
    if found_months and len(nums) >= 2:
        year = datetime.date.today().year
        try:
            mn = found_months[0][1]
            d1, d2 = int(nums[0]), int(nums[1] if len(nums) > 1 else nums[0])
            ci = datetime.date(year, int(mn), min(d1, d2))
            co = datetime.date(year, int(mn), max(d1, d2))
            if co <= ci:
                co = ci + datetime.timedelta(days=3)
            nights = (co - ci).days
            return ci.isoformat(), co.isoformat(), nights
        except Exception:
            pass

    # If just "5 days" or similar with no month
    if nums:
        nights = int(nums[0]) if int(nums[0]) < 60 else 3
        return "", "", nights

    return "", "", 3  # default 3 nights


def _format_hotels(hotel_data: dict, budget: int, currency: str, destination: str) -> str:
    """Format real hotel data into a clean Telegram-friendly message section."""
    hotels = hotel_data.get("hotels", [])
    source = hotel_data.get("source", "")
    booking_url = hotel_data.get("booking_url", booking_link(destination))
    google_url  = hotel_data.get("google_url", "")
    agoda_url   = hotel_data.get("agoda_url", "")

    if not hotels:
        return (
            f"HOTELS & STAYS\n"
            f"Live hotel data could not be retrieved right now. Search directly:\n"
            f"• Booking.com: {booking_url}\n"
            f"• Google Hotels: {google_url}\n"
            f"• Agoda: {agoda_url}\n"
            f"\nFilter by your budget of {budget:,} {currency} total."
        )

    # Split into tiers by price
    priced = [h for h in hotels if h.get("price_num", 0) > 0]
    unpriced = [h for h in hotels if not h.get("price_num", 0)]
    priced.sort(key=lambda x: x["price_num"])

    total = priced + unpriced
    budget_hotels = total[:3]
    mid_hotels    = total[3:6]
    luxury_hotels = total[6:9]

    lines = ["HOTELS & STAYS (Live Data)\n"]
    lines.append(f"Data source: {source}\n")

    def fmt_hotel(h: dict) -> str:
        rating = f" | ⭐ {h['rating']}" if h.get("rating") else ""
        price  = f" | {h['price']}/night" if h.get("price") and h["price"] != "Check site" else ""
        loc    = f"\n   📍 {h['address']}" if h.get("address") and h["address"] != destination else ""
        tips   = f"\n   ✓ {h['highlights']}" if h.get("highlights") else ""
        link   = f"\n   🔗 Book: {h['url']}" if h.get("url") else ""
        return f"• {h['name']}{rating}{price}{loc}{tips}{link}"

    if budget_hotels:
        lines.append("BUDGET OPTIONS")
        for h in budget_hotels:
            lines.append(fmt_hotel(h))
        lines.append("")

    if mid_hotels:
        lines.append("MID-RANGE OPTIONS")
        for h in mid_hotels:
            lines.append(fmt_hotel(h))
        lines.append("")

    if luxury_hotels:
        lines.append("UPSCALE OPTIONS")
        for h in luxury_hotels:
            lines.append(fmt_hotel(h))
        lines.append("")

    lines.append(f"Search all options:")
    lines.append(f"• Booking.com → {booking_url}")
    lines.append(f"• Google Hotels → {google_url}")
    lines.append(f"• Agoda → {agoda_url}")

    return "\n".join(lines)


class TravelPlanner:
    def __init__(self, llm: LLMClient, otm_key="", owm_key="", er_key="", serpapi_key=""):
        self.llm = llm
        self.otm_key = otm_key
        self.owm_key = owm_key
        self.er_key  = er_key
        self.serpapi_key = serpapi_key

    def vision_ok(self) -> bool:
        return supports_vision(self.llm.provider, self.llm.model)

    async def generate_plan(self, destination, source_city, dates, members, budget, currency="INR") -> tuple[str, dict]:
        """
        Returns (full_plan_text, hotel_data_dict)
        hotel_data contains raw real hotel info for the bot to forward directly.
        """
        # 1. Geocode
        dest_geo = await geocode(destination)
        dest_country = dest_geo["country"] if dest_geo else "IN"
        src_geo  = await geocode(source_city) if source_city else None
        src_country = src_geo["country"] if src_geo else "IN"

        # 2. Airports
        airport_lines = ""
        if dest_geo:
            da = await nearest_airport(dest_geo["lat"], dest_geo["lon"])
            if da:
                airport_lines += f"Nearest airport to {destination}: {da['name']} ({da['iata']}) — {da['dist_km']} km\n"
        if src_geo:
            sa = await nearest_airport(src_geo["lat"], src_geo["lon"])
            if sa:
                airport_lines += f"Nearest airport from {source_city}: {sa['name']} ({sa['iata']}) — {sa['dist_km']} km\n"

        # 3. Attractions
        attr_text = ""
        if dest_geo and self.otm_key:
            spots = await get_attractions(dest_geo["lat"], dest_geo["lon"], self.otm_key, limit=10)
            if spots:
                attr_text = "\n".join(f"  - {s['name']} ({s['dist']} km) [{s['kinds'][:40]}]" for s in spots)

        # 4. Weather
        weather = ""
        if dest_geo and self.owm_key:
            weather = await get_weather(dest_geo["lat"], dest_geo["lon"], self.owm_key)

        # 5. Currency
        budget_digits = re.sub(r"[^\d]", "", str(budget)) or "0"
        budget_int = int(budget_digits)
        currency_info = ""
        if self.er_key and currency != "USD":
            currency_info = await convert_currency(budget_int, currency, "USD", self.er_key)

        # 6. REAL hotel data — fetch before LLM call
        check_in, check_out, nights = _parse_dates(dates)
        hotel_data = await fetch_hotels(
            destination, check_in, check_out,
            adults=members, total_budget=budget_int,
            nights=nights, currency=currency,
            serpapi_key=self.serpapi_key
        )
        hotel_section = _format_hotels(hotel_data, budget_int, currency, destination)

        # 7. Web search for live context (cab apps, SIM, safety)
        web_ctx = await web_search_context(f"{destination} tourist tips 2024 SIM card transport")

        trip_type = "INTERNATIONAL" if src_geo and is_international(src_country, dest_country) else "DOMESTIC"
        per_person = budget_int // max(members, 1)

        # 8. LLM generates everything EXCEPT hotel section (which is real data)
        prompt = f"""Generate a complete WanderOn travel guide for this trip. 
DO NOT invent hotel names or prices — the hotel section is provided below with real scraped data.

TRIP:
- Destination: {destination} ({dest_country})
- From: {source_city or "India"}
- Type: {trip_type}
- Dates: {dates} (~{nights} nights)
- Group: {members} people
- Budget: {budget} {currency} total (≈{per_person} {currency}/person)
{f'- Currency note: {currency_info}' if currency_info else ''}

AIRPORTS:
{airport_lines or "Look up nearest airports."}

LIVE ATTRACTIONS DATA:
{attr_text or "Use your knowledge of top attractions here."}

LIVE WEATHER:
{weather or "Use your knowledge of typical weather for these dates."}

LIVE WEB CONTEXT:
{web_ctx or "Use your knowledge."}

Generate these sections (DO NOT generate the Hotels section — it will be appended from real data):

DESTINATION OVERVIEW
Brief intro, best time, overall vibe, what it is famous for.

GETTING THERE
All transport options with real estimated costs. Flight options with booking links below:
- Google Flights: {google_flights_link(source_city or 'India', destination)}
- Skyscanner: {skyscanner_link(source_city or 'India', destination)}
For INTERNATIONAL trips: visa requirements for Indian passport, processing time, cost.

DAY-WISE ITINERARY
Detailed plan for each of the {nights} days. 
Each day: Morning (8am-12pm) / Afternoon (12pm-6pm) / Evening (6pm-10pm)
Include specific restaurants with typical meal cost. Transport between spots. Entry fees.

FULL COST BREAKDOWN (per person, in {currency})
- Flights/transport to destination
- Local transport (cab/metro/bus)
- Accommodation (total {nights} nights)
- Food (daily average x {nights} days)
- Major attractions (list each with entry fee)
- SIM card
- Miscellaneous & tips
TOTAL per person | TOTAL for group of {members}

CAB & LOCAL TRANSPORT
Which ride apps work here (exact app names). Estimated fares: airport→city, typical in-city ride. Metro/bus pass options and cost.

LANGUAGE CHEATSHEET
15 essential phrases in local language with pronunciation.

SIM CARD GUIDE
Best 2-3 carriers, where to buy, data plan costs, eSIM options.

MONEY & PAYMENTS
Cash vs card advice. ATM tips. Tipping customs (exact percentages). Price benchmarks (coffee, meal, taxi per km).

SAFETY & SCAM ALERTS
Top 5 tourist scams specific to {destination} with how to avoid each.
Safe vs risky areas. Emergency numbers (police, ambulance, tourist helpline). Indian embassy/consulate details.

CULTURAL ETIQUETTE
Dress code, photography rules, religious customs, taboos, bargaining norms.

WEATHER & PACKING LIST
Expected weather for travel dates. Packing list tailored to this destination and season.

VISA & HEALTH
For international: visa type, cost, documents, where to apply.
Recommended vaccinations. Water safety. Common health issues tourists face here."""

        llm_plan = await self.llm.chat(ITINERARY_SYSTEM, prompt, max_tokens=4000)

        # 9. Assemble: LLM output + real hotel section
        full_plan = llm_plan.strip() + "\n\n" + "="*40 + "\n\n" + hotel_section

        return full_plan, hotel_data

    async def estimate_cost(self, destination, source_city, duration_days, members, currency="INR") -> str:
        # Ground with web search
        web_ctx = await web_search_context(f"cost of travel to {destination} tourist budget {duration_days} days 2024")

        prompt = f"""How much does it cost to visit {destination} from {source_city or 'India'} for {duration_days} days with {members} people? Budget in {currency}.

WEB CONTEXT (use this for accuracy):
{web_ctx or "Use your knowledge."}

Give a COMPLETE cost breakdown:

TRIP COST ESTIMATE: {destination} ({duration_days} days, {members} people)

FLIGHTS: Return economy from {source_city or 'India'} — budget/mid/peak season price range

ACCOMMODATION (per night):
- Budget (hostel/guesthouse): X {currency}
- Mid-range hotel: Y {currency}
- Luxury hotel: Z {currency}

FOOD (per person per day):
- Budget (street food/local): X {currency}
- Mid-range (sit-down restaurants): Y {currency}
- Fine dining: Z {currency}

LOCAL TRANSPORT:
- Airport to city: X {currency}
- Daily transport (metro/bus/cab): Y {currency}/day
- Total for {duration_days} days: Z {currency}

TOP 8 ATTRACTIONS with entry fees (list each one)

SIM CARD: X {currency}
VISA: X {currency} (if applicable)

DAILY BUDGET TIERS (per person):
- Backpacker: X {currency}/day → Total: Y {currency} for trip
- Mid-range: X {currency}/day → Total: Y {currency} for trip
- Comfort: X {currency}/day → Total: Y {currency} for trip

TOTAL TRIP COST for {members} people:
- Budget option: X {currency}
- Mid-range option: Y {currency}
- Comfort option: Z {currency}

Direct booking links:
- Hotels: {booking_link(destination)}
- Flights: {google_flights_link(source_city or 'India', destination)}"""

        return await self.llm.chat(GUIDE_SYSTEM, prompt, max_tokens=2000)

    async def city_guide(self, destination, aspect) -> str:
        web_ctx = await web_search_context(f"{destination} {aspect} tourists 2024 guide")
        prompts = {
            "language": f"Give a language cheatsheet for tourists in {destination}. Top 20 essential phrases with local script, pronunciation, and when to use them.",
            "sim":      f"SIM card guide for tourists visiting {destination}. Best carriers, where to buy at the airport, costs, data plans, eSIM options.",
            "safety":   f"Safety guide for tourists in {destination}. Top 10 common scams with how to avoid each, safe vs risky areas, emergency numbers, Indian embassy contact.",
            "money":    f"Money and payments guide for {destination}. Cash vs card, ATM tips, best currency exchange, tipping customs (exact %%), typical price benchmarks.",
            "culture":  f"Cultural etiquette for {destination}. Dress code, photography rules, religious norms, things that are considered rude, bargaining customs.",
            "food":     f"Complete food guide for {destination}. Top 10 must-try dishes, best areas for food, recommended restaurants at budget/mid/luxury, food safety, dietary options.",
            "transport":f"Local transport guide for {destination}. Ride apps (exact names), estimated fares for common routes, metro/bus info, tourist passes, tips for getting around.",
            "packing":  f"Packing list for a trip to {destination}. What to definitely bring, what to leave at home, destination-specific items, clothing for the weather and culture.",
        }
        prompt = prompts.get(aspect, f"Guide about {aspect} for tourists in {destination}.")
        if web_ctx:
            prompt += f"\n\nLive web context for accuracy:\n{web_ctx}"
        return await self.llm.chat(GUIDE_SYSTEM, prompt, max_tokens=1500)

    async def describe_image(self, img_b64: str, mime: str, caption: str = "") -> str:
        prompt = sanitize(caption or "What is this? Identify it and give travel-relevant context.", 300)
        return await self.llm.chat_vision(VISION_SYSTEM, prompt, img_b64, mime, max_tokens=500)

    async def answer_followup(self, question: str, plan: str) -> str:
        if contains_sensitive_data(question):
            return "For your security, please do not share card numbers, UPI IDs, or banking credentials here."
        q = sanitize(question)
        # Web search for the specific question if it asks for live data
        web_ctx = ""
        if any(w in q.lower() for w in ["hotel", "price", "cost", "book", "cheap", "best", "recommend"]):
            topic = re.sub(r"\s+", " ", q)[:80]
            web_ctx = await web_search_context(topic)

        ctx = f"Previous plan:\n{plan[:1500]}\n"
        if web_ctx:
            ctx += f"\nLive web data for your question:\n{web_ctx}\n"
        ctx += f"\nQuestion: {q}\n\nAnswer specifically. If hotels are asked, do not invent names — say to check the booking links in the plan."
        return await self.llm.chat(NARRATOR_SYSTEM, ctx, max_tokens=1200)
