import re, time, hashlib

_SENSITIVE = [
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"\b(cvv|cvc|otp|atm\s*pin|net\s*banking|password)\b", re.I),
    re.compile(r"\b[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}\b"),
    re.compile(r"\bifsc\b", re.I),
]

def contains_sensitive_data(text: str) -> bool:
    return any(p.search(text or "") for p in _SENSITIVE)

def sanitize(text: str, max_len: int = 800) -> str:
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", (text or ""))[:max_len].strip()

def hash_uid(uid: str) -> str:
    return hashlib.sha256(uid.encode()).hexdigest()[:12]

def valid_tg_token(t: str) -> bool:
    return bool(re.match(r"^\d{6,12}:[A-Za-z0-9_-]{30,50}$", t.strip()))

_buckets: dict[str, list[float]] = {}

def is_rate_limited(uid: str, max_req: int = 15, window: int = 60) -> bool:
    now = time.time()
    b = _buckets.setdefault(uid, [])
    while b and b[0] < now - window:
        b.pop(0)
    if len(b) >= max_req:
        return True
    b.append(now)
    return False

MAX_IMG_BYTES = 5 * 1024 * 1024
