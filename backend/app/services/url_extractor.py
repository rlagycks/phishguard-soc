"""Extract feature vectors from URLs for the ML model."""

import re
from urllib.parse import urlparse
from dataclasses import dataclass, field

_SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".club", ".site", ".online", ".info", ".biz",
    ".tk", ".ml", ".ga", ".cf", ".gq",
}

_PHISHING_KEYWORDS = {
    "login", "verify", "update", "secure", "account", "reset",
    "password", "confirm", "banking", "signin", "security",
    "authorize", "validation",
}

_SHORTENERS = {
    "bit.ly", "tinyurl.com", "t.co", "goo.gl", "ow.ly",
    "short.link", "rebrand.ly", "cutt.ly",
}


@dataclass
class URLFeatures:
    url: str
    url_length: int
    domain_length: int
    path_length: int
    num_digits: int
    num_special_chars: int  # @, -, _, %, =, ?, &
    at_symbol: bool
    double_slash: bool
    prefix_suffix_dash: bool  # dash in domain
    subdomain_count: int
    is_ip_address: bool
    is_https: bool
    suspicious_tld: bool
    shortener: bool
    phishing_keyword_count: int
    query_param_count: int
    has_port: bool

    def to_list(self) -> list[float]:
        return [
            self.url_length,
            self.domain_length,
            self.path_length,
            self.num_digits,
            self.num_special_chars,
            int(self.at_symbol),
            int(self.double_slash),
            int(self.prefix_suffix_dash),
            self.subdomain_count,
            int(self.is_ip_address),
            int(self.is_https),
            int(self.suspicious_tld),
            int(self.shortener),
            self.phishing_keyword_count,
            self.query_param_count,
            int(self.has_port),
        ]


_IP_RE = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")


def extract_features(url: str) -> URLFeatures:
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    path = parsed.path or ""
    query = parsed.query or ""

    # Remove port from domain for counting
    hostname = parsed.hostname or ""

    subdomain_parts = hostname.split(".")
    # Example: sub.example.com → 1 subdomain; example.com → 0
    subdomain_count = max(0, len(subdomain_parts) - 2)

    special_chars = sum(url.count(c) for c in "@-_%=?&")
    query_params = len(query.split("&")) if query else 0

    tld = "." + subdomain_parts[-1] if subdomain_parts else ""
    kw_count = sum(1 for kw in _PHISHING_KEYWORDS if kw in url.lower())

    return URLFeatures(
        url=url,
        url_length=len(url),
        domain_length=len(hostname),
        path_length=len(path),
        num_digits=sum(c.isdigit() for c in url),
        num_special_chars=special_chars,
        at_symbol="@" in parsed.netloc,
        double_slash=url.count("//") > 1,
        prefix_suffix_dash="-" in hostname,
        subdomain_count=subdomain_count,
        is_ip_address=bool(_IP_RE.match(hostname)),
        is_https=parsed.scheme == "https",
        suspicious_tld=tld in _SUSPICIOUS_TLDS,
        shortener=hostname in _SHORTENERS,
        phishing_keyword_count=kw_count,
        query_param_count=query_params,
        has_port=bool(parsed.port),
    )


def extract_features_batch(urls: list[str]) -> list[URLFeatures]:
    return [extract_features(u) for u in urls]
