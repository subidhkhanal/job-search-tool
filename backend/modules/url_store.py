"""
url_store.py — Persistent seen-URL tracking via a JSON file.
Used to distinguish NEW jobs from previously-seen jobs across nightly runs.
On GitHub Actions, seen_urls.json is committed back to the repo after each run.
"""

import json
import hashlib
import os

STORE_PATH = os.path.join(os.path.dirname(__file__), "seen_urls.json")


def _hash_url(url):
    """Return a 16-character hex SHA-256 hash of the URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def load_seen():
    """Load the set of seen URL hashes from disk. Returns empty set if missing."""
    if not os.path.exists(STORE_PATH):
        return set()
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return set(data.get("seen", []))
    except (json.JSONDecodeError, IOError):
        return set()


def save_seen(seen):
    """Persist the seen URL hashes to disk."""
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump({"seen": sorted(seen)}, f, indent=2)


def is_new(url, seen):
    """Check if a URL has not been seen before."""
    if not url:
        return True
    return _hash_url(url) not in seen


def mark_seen(url, seen):
    """Add a URL hash to the in-memory seen set."""
    if url:
        seen.add(_hash_url(url))
