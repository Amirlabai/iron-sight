import re
from functools import lru_cache

@lru_cache(maxsize=1000)
def standardize_name(name):
    """Normalize city names for consistent mapping across various data sources."""
    if not name: return ""
    # Remove dashes, commas, parentheses, and spaces for structural normalization
    name = re.sub(r'[\-\,\(\)\s]+', '', name)
    return name.strip()
