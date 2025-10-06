import os
import json
from collections.abc import Callable
from functools import wraps
from hashlib import md5
from pathlib import Path

from platformdirs import user_cache_dir

from .constants import APP_NAME, APP_AUTHOR
from .errors import ADECacheError

#: Cache directory
CACHE_DIR = user_cache_dir(APP_NAME, APP_AUTHOR)


def clear_cache() -> None:
    """Clears the cache directory."""
    if not os.path.exists(CACHE_DIR):
        raise ADECacheError("Cache directory does not exist.")

    for filename in os.listdir(CACHE_DIR):
        file_path = os.path.join(CACHE_DIR, filename)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
        except Exception as e:
            raise ADECacheError(f"Failed to delete {file_path}. Reason: {e}")


def get_ade_event_page_cache_key(page: int) -> str:
    return f"ade-event-page-{page}.json"


def get_ade_venue_location_cache_key(venue: str) -> str:
    name = venue.replace(" ", "-").lower()

    return f"ade-venue-location--{name}.json"


def get_ade_venue_place_info_cache_key(venue: str) -> str:
    name = md5(venue.encode("utf-8")).hexdigest()

    return f"ade-venue-location-place-info--{name}.json"


def get_ade_venue_address_cache_key(event_id: int) -> str:
    return f"ade-venue-address--{event_id}.json"


def cache_request(cache_key_func: Callable[[str | int], str]) -> Callable:
    """Cache request in specified directory using cache key function"""
    def wrapper(func: Callable[[str | int], dict]) -> Callable[[str | int], dict]:
        @wraps(func)
        def wrapped(key: str | int):
            cache_key = cache_key_func(key)
            cache = Path(CACHE_DIR) / Path(cache_key)

            if cache.exists():
                try:
                    return json.load(cache.open())
                except json.decoder.JSONDecodeError:
                    pass

            data = func(key)

            with cache.open("w") as fp:
                json.dump(data, fp)
                return data

        return wrapped

    return wrapper

