import logging
import os
from typing import Set

# --- State Management for Posted Links ---
POSTED_DB_FILE = "posted_links.txt"
_posted_keys: Set[str] = set()

def load_posted_keys():
    """
    Loads the set of already posted keys from the persistence file.
    """
    if not os.path.exists(POSTED_DB_FILE):
        return
    with open(POSTED_DB_FILE, "r", encoding="utf-8") as f:
        for line in f:
            stripped_line = line.strip()
            if stripped_line:
                _posted_keys.add(stripped_line)
    logging.info(f"Loaded {len(_posted_keys)} posted keys from {POSTED_DB_FILE}.")

def is_posted(key: str) -> bool:
    """
    Checks if a given key (ASIN or URL) has already been posted.
    """
    return key in _posted_keys

def mark_as_posted(key: str):
    """
    Adds a key to the in-memory set and appends it to the persistence file.
    """
    _posted_keys.add(key)
    try:
        with open(POSTED_DB_FILE, "a", encoding="utf-8") as f:
            f.write(key + "\n")
    except Exception as e:
        logging.error(f"Error persisting key '{key}': {e}")

# --- Initial Load ---
load_posted_keys()
