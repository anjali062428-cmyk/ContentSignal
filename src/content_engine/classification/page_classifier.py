"""
Page Classifier & Domain Extraction Module.
Provides deterministic, explainable extraction and classification for domain and URL data.
Zero ML feature leakage: These fields are descriptive metadata only.
"""
from typing import Optional, Tuple
from urllib.parse import urlparse
import re


def extract_and_normalize_domain(url_str: Optional[str]) -> Optional[str]:
    """
    Extracts and normalizes domain from a URL string.
    - lowercase
    - strip protocol (http://, https://)
    - strip www.
    - strip trailing slash and path
    - preserve valid subdomains (e.g. blog.example.com)
    """
    if not url_str or not isinstance(url_str, str):
        return None
    
    clean = url_str.strip()
    if not clean:
        return None

    # Handle protocol absence
    if not (clean.startswith("http://") or clean.startswith("https://")):
        if "/" in clean or "." in clean:
            clean = "https://" + clean
        else:
            return None

    try:
        parsed = urlparse(clean)
        netloc = parsed.netloc.lower() if parsed.netloc else ""
        if not netloc and parsed.path and not parsed.path.startswith("/"):
            # Could be parsed as path if scheme was tricky
            netloc = parsed.path.split("/")[0].lower()

        # Remove port if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]

        # Remove www.
        if netloc.startswith("www."):
            netloc = netloc[4:]

        netloc = netloc.strip("/.")
        # Validate domain structure (at least one dot and valid chars)
        if "." in netloc and all(c.isalnum() or c in ".-" for c in netloc):
            return netloc
        return None
    except Exception:
        return None


def normalize_domain(domain_str: Optional[str]) -> Optional[str]:
    """
    Normalizes an explicitly provided domain string.
    """
    if not domain_str or not isinstance(domain_str, str):
        return None
    
    clean = domain_str.strip().lower()
    if not clean or clean in ["none", "nan", "null"]:
        return None

    # If domain contains full URL, extract it
    if "://" in clean or "/" in clean:
        extracted = extract_and_normalize_domain(clean)
        if extracted:
            return extracted

    if clean.startswith("www."):
        clean = clean[4:]

    clean = clean.strip("/.")
    if "." in clean and all(c.isalnum() or c in ".-" for c in clean):
        return clean
    return clean if clean else None


def clean_url_display(url_str: Optional[str]) -> Optional[str]:
    """
    Cleans URL for display without stripping path structure.
    Removes bulky tracking query parameters while preserving path.
    """
    if not url_str or not isinstance(url_str, str):
        return None
    clean = url_str.strip()
    if not clean or clean in ["none", "nan", "null"]:
        return None
    return clean


def classify_page_type(
    explicit_page_type: Optional[str] = None,
    content_type: Optional[str] = None,
    url: Optional[str] = None,
    page_title: Optional[str] = None,
    title: Optional[str] = None,
) -> Tuple[str, str]:
    """
    Deterministic rule-based page classification with explainable source attribution.
    Priority:
    1. Explicit page_type from uploaded dataset.
    2. Existing content_type match (e.g. comparison).
    3. URL path patterns.
    4. Page title patterns.
    5. Fallback ('Other' or 'Other / Unclassified').

    Returns:
        (page_type: str, page_type_source: str)
    """
    if not page_title and title:
        page_title = title
    # 1. Explicit page_type field
    if explicit_page_type and isinstance(explicit_page_type, str):
        clean_exp = explicit_page_type.strip()
        if clean_exp and clean_exp.lower() not in ["none", "nan", "null", "unknown", ""]:
            return clean_exp, "explicit_field"

    # Normalize url path, title, and content_type
    path = ""
    if url and isinstance(url, str):
        clean_url = url.strip()
        try:
            if "://" in clean_url:
                path = urlparse(clean_url).path.lower()
            else:
                path = clean_url.split("?")[0].lower()
                if not path.startswith("/"):
                    # Strip domain part if present
                    if "/" in path:
                        path = "/" + path.split("/", 1)[1]
                    else:
                        path = "/"
        except Exception:
            path = clean_url.lower()

    title = str(page_title).strip().lower() if page_title and isinstance(page_title, str) else ""
    ctype = str(content_type).strip().lower() if content_type and isinstance(content_type, str) else ""

    # 2. Existing content_type field match
    if "comparison" in ctype or "compare" in ctype:
        return "Comparison", "content_type"

    # 3. URL path pattern rules
    if path:
        # Documentation
        if any(p in path for p in ["/docs", "/doc/", "/documentation", "/api-ref", "/reference"]):
            return "Documentation", "url_pattern"
        # FAQ
        if any(p in path for p in ["/faq", "/frequently-asked-questions", "/help/faq"]):
            return "FAQ", "url_pattern"
        # Product
        if any(p in path for p in ["/product", "/products", "/item/", "/p/", "/shop/", "/store/"]):
            return "Product", "url_pattern"
        # Category
        if any(p in path for p in ["/category", "/categories", "/collection", "/collections", "/c/"]):
            return "Category", "url_pattern"
        # Comparison
        if any(p in path for p in ["/vs/", "-vs-", "/versus/", "/comparison", "/compare"]):
            return "Comparison", "url_pattern"
        # Guide / Resource
        if any(p in path for p in ["/guide", "/guides", "/resource", "/resources", "/tutorial", "/learn", "/whitepaper"]):
            return "Guide / Resource", "url_pattern"
        # News
        if any(p in path for p in ["/news", "/press", "/press-release", "/media/"]):
            return "News", "url_pattern"
        # Contact / About
        if any(p in path for p in ["/contact", "/about", "/team", "/careers"]):
            return "Contact / About", "url_pattern"
        # Blog / Article
        if any(p in path for p in ["/blog", "/posts", "/post/", "/articles", "/article/", "/insights", "/stories"]):
            return "Blog / Article", "url_pattern"
        # Search
        if any(p in path for p in ["/search", "/find", "/results"]):
            return "Search", "url_pattern"
        # Landing Page
        if path in ["", "/", "/home", "/features", "/solutions", "/pricing"]:
            return "Landing Page", "url_pattern"

    # 4. Page title pattern rules
    if title:
        if any(w in title for w in [" vs ", " versus ", " compared to ", " comparison "]):
            return "Comparison", "page_title"
        if any(w in title for w in ["how to", "complete guide", "ultimate guide", "tutorial", "step-by-step"]):
            return "Guide / Resource", "page_title"
        if any(w in title for w in ["faq", "frequently asked questions", "q&a"]):
            return "FAQ", "page_title"
        if any(w in title for w in ["pricing", "review", "product features", "buy online"]):
            return "Product", "page_title"
        if any(w in title for w in ["documentation", "api reference", "developer guide"]):
            return "Documentation", "page_title"
        if any(w in title for w in ["announcing", "press release", "industry news", "launches"]):
            return "News", "page_title"

    # Fallback to content_type if available
    if "product" in ctype:
        return "Product", "content_type"
    if "how_to" in ctype or "how to" in ctype or "guide" in ctype:
        return "Guide / Resource", "content_type"
    if "faq" in ctype:
        return "FAQ", "content_type"
    if "article" in ctype or "blog" in ctype or "feedly" in ctype or "post" in ctype:
        return "Blog / Article", "content_type"

    # 5. Fallback
    if url or page_title:
        return "Other", "default_fallback"
    return "Other / Unclassified", "default_fallback"
