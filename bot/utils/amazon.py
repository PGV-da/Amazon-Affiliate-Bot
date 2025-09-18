import re
from typing import List, Optional
from bot.config import AFFILIATE_TAG

# Regex patterns for Amazon URLs and ASINs
AMAZON_URL_RE = re.compile(r'https?://[^\s]*amazon\.[^\s/]+[^\s]*', re.I)
ASIN_PATTERNS = [
    re.compile(r'/dp/([A-Z0-9]{10})', re.I),
    re.compile(r'/gp/product/([A-Z0-9]{10})', re.I),
    re.compile(r'[?&]asin=([A-Z0-9]{10})', re.I),
]

def extract_amazon_urls(text: str) -> List[str]:
    """
    Extracts all Amazon URLs from a given string.
    """
    return AMAZON_URL_RE.findall(text or "")

def get_asin(url: str) -> Optional[str]:
    """
    Extracts the 10-digit ASIN from an Amazon URL.
    """
    for pat in ASIN_PATTERNS:
        m = pat.search(url)
        if m:
            return m.group(1).upper()
    return None

def normalize_url_remove_tracking(url: str) -> str:
    """
    Removes affiliate tags and common tracking parameters from a URL.
    """
    url = re.sub(r'([?&])tag=[^&]*', '', url, flags=re.I)
    url = re.sub(r'([?&])utm_[^=]+=[^&]*', '', url, flags=re.I)
    url = re.sub(r'#.*$', '', url)
    return url.rstrip('?&')

def replace_amazon_tag(url: str) -> str:
    """
    Replaces or adds the affiliate tag to a clean Amazon URL.
    """
    clean_url = normalize_url_remove_tracking(url)
    separator = '&' if '?' in clean_url else '?'
    return f"{clean_url}{separator}tag={AFFILIATE_TAG}"
