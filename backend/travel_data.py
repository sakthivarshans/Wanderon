"""
WanderOn Travel Data API Integration Layer.
Integrates Nominatim Geocoder, OpenFlights Database, OpenTripMap, OpenWeatherMap,
and ExchangeRate-API for real-world factual context retrieval.
"""
import httpx, csv, io, math, logging

log = logging.getLogger("wanderon.data")
_airports: list[dict] | None = None

async def geocode(place: str) -> dict | None:
    """
    Performs forward geocoding using OpenStreetMap's Nominatim API.
    
    Args:
        place (str): The text-based destination or city name.
        
    Returns:
        dict: Coordinate mapping {lat, lon, country, display} or None.
    """
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://nominatim.openstreetmap.org/search",
                params={"q": place, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": "WanderOn/2.0"})
            data = r.json()
        if data:
            d = data[0]
            return {
                "lat": float(d["lat"]), "lon": float(d["lon"]),
                "country": d.get("address", {}).get("country_code", "").upper(),
                "display": d["display_name"],
            }
    except Exception as e:
        log.warning(f"geocode fail '{place}': {e}")
    return None

def is_international(src: str, dst: str) -> bool:
    """
    Compares two country codes to determine if international travel guidelines apply.
    
    Args:
        src (str): Origin country code.
        dst (str): Destination country code.
        
    Returns:
        bool: True if countries differ, False otherwise.
    """
    return src.upper() != dst.upper()

async def _load_airports() -> list[dict]:
    """
    Lazily fetches and parses the OpenFlights airports CSV database.
    
    Returns:
        list[dict]: List of parsed airports with their coordinates and IATA codes.
    """
    global _airports
    if _airports is not None:
        return _airports
    try:
        async with httpx.AsyncClient(timeout=20) as c:
            r = await c.get("https://raw.githubusercontent.com/jpatokal/openflights/master/data/airports.dat")
        rows = list(csv.reader(io.StringIO(r.text)))
        _airports = []
        for row in rows:
            try:
                iata = row[4]
                if not iata or iata == r"\N":
                    continue
                _airports.append({"name": row[1], "city": row[2], "country": row[3],
                    "iata": iata, "lat": float(row[6]), "lon": float(row[7])})
            except (IndexError, ValueError):
                continue
    except Exception as e:
        log.warning(f"airports load fail: {e}")
        _airports = []
    return _airports

def _haversine(la1, lo1, la2, lo2) -> float:
    """
    Calculates great-circle distance between two points on the Earth's surface
    using the Haversine formula.
    
    Args:
        la1 (float): Latitude of point 1.
        lo1 (float): Longitude of point 1.
        la2 (float): Latitude of point 2.
        lo2 (float): Longitude of point 2.
        
    Returns:
        float: Distance in kilometers.
    """
    R = 6371
    dl = math.radians(la2 - la1); dlo = math.radians(lo2 - lo1)
    a = math.sin(dl/2)**2 + math.cos(math.radians(la1)) * math.cos(math.radians(la2)) * math.sin(dlo/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

async def nearest_airport(lat: float, lon: float) -> dict | None:
    """
    Finds the geographically closest airport to a set of coordinates.
    
    Args:
        lat (float): Latitude.
        lon (float): Longitude.
        
    Returns:
        dict: Closest airport record annotated with 'dist_km' or None.
    """
    apts = await _load_airports()
    if not apts:
        return None
    best = min(apts, key=lambda a: _haversine(lat, lon, a["lat"], a["lon"]))
    best["dist_km"] = round(_haversine(lat, lon, best["lat"], best["lon"]))
    return best

async def get_attractions(lat: float, lon: float, key: str, limit: int = 10) -> list[dict]:
    """
    Fetches interesting tourist points/attractions from the OpenTripMap API within a 15km radius.
    
    Args:
        lat (float): Latitude.
        lon (float): Longitude.
        key (str): OpenTripMap API authorization key.
        limit (int): Max results count (default: 10).
        
    Returns:
        list[dict]: Curated tourist places and category markers.
    """
    if not key:
        return []
    try:
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get("https://api.opentripmap.com/0.1/en/places/radius",
                params={"radius": 15000, "lon": lon, "lat": lat,
                    "kinds": "interesting_places,cultural,natural,historic,architecture",
                    "rate": "2", "format": "json", "limit": limit, "apikey": key})
            data = r.json()
        return [{"name": p.get("name",""), "kinds": p.get("kinds","").replace(",",", "),
                 "dist": round(p.get("dist",0)/1000, 1)}
                for p in data if p.get("name") and p["name"] != ""][:limit]
    except Exception as e:
        log.warning(f"attractions fail: {e}")
        return []

async def get_weather(lat: float, lon: float, key: str) -> str:
    if not key:
        return ""
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get("https://api.openweathermap.org/data/2.5/forecast",
                params={"lat": lat, "lon": lon, "appid": key, "units": "metric", "cnt": 8})
            data = r.json()
        items = data.get("list", [])
        if not items:
            return ""
        avg = round(sum(i["main"]["temp"] for i in items) / len(items))
        desc = items[0]["weather"][0]["description"]
        return f"{avg}°C, {desc}"
    except Exception as e:
        log.warning(f"weather fail: {e}")
        return ""

async def convert_currency(amount: float, src: str, dst: str, key: str) -> str:
    if not key or src.upper() == dst.upper():
        return f"{amount:,.0f} {src.upper()}"
    try:
        async with httpx.AsyncClient(timeout=10) as c:
            r = await c.get(f"https://v6.exchangerate-api.com/v6/{key}/pair/{src}/{dst}/{amount}")
            d = r.json()
        if d.get("result") == "success":
            return f"{amount:,.0f} {src.upper()} ≈ {d['conversion_result']:,.0f} {dst.upper()}"
    except Exception as e:
        log.warning(f"currency fail: {e}")
    return f"{amount:,.0f} {src.upper()}"
