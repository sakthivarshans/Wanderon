"""
WanderOn Security Module.
Provides functions for input sanitization, rate limiting, and PII/sensitive data filtering.
"""
import re, time, hashlib

_SENSITIVE = [
    re.compile(r"\b\d{13,19}\b"),
    re.compile(r"\b(cvv|cvc|otp|atm\s*pin|net\s*banking|password)\b", re.I),
    re.compile(r"\b[a-zA-Z0-9.\-_]{2,}@[a-zA-Z]{2,}\b"),
    re.compile(r"\bifsc\b", re.I),
]

def contains_sensitive_data(text: str) -> bool:
    """
    Checks if the provided text contains potentially sensitive data such as
    credit card numbers, CVVs, passwords, OTPs, or email addresses.
    
    Args:
        text (str): The input text message to inspect.
        
    Returns:
        bool: True if sensitive patterns match, False otherwise.
    """
    return any(p.search(text or "") for p in _SENSITIVE)

def sanitize(text: str, max_len: int = 800) -> str:
    """
    Sanitizes raw input text by stripping out control characters, limiting the length,
    and trimming surrounding whitespace to prevent injection and buffer issues.
    
    Args:
        text (str): The raw string input to sanitize.
        max_len (int): Maximum allowed length of the sanitized string (default: 800).
        
    Returns:
        str: The sanitized and truncated string.
    """
    return re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", (text or ""))[:max_len].strip()

def hash_uid(uid: str) -> str:
    """
    Generates a secure, truncated SHA-256 hash of a user identifier for logging purposes.
    This protects user privacy in logs while maintaining auditability.
    
    Args:
        uid (str): The raw Telegram user ID.
        
    Returns:
        str: A 12-character hexadecimal representation of the user ID hash.
    """
    return hashlib.sha256(uid.encode()).hexdigest()[:12]

def valid_tg_token(t: str) -> bool:
    """
    Validates the format of a Telegram Bot API token using regex.
    
    Args:
        t (str): The raw token string to validate.
        
    Returns:
        bool: True if the token matches the standard Telegram format, False otherwise.
    """
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
