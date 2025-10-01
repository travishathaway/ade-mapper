import os
import json
import re
from functools import wraps
from pathlib import Path
from hashlib import md5

import geojson
import httpx
from platformdirs import user_cache_dir
from pymdownx.emoji import gemoji
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from geojson import Point, FeatureCollection, Feature, geometry

from .errors import ConfigurationError

# Nominatim base URL
NOM_URL = "https://nominatim.openstreetmap.org/search"
ADE_URL = "https://www.amsterdam-dance-event.nl/api/program/filter/"
GOOGLE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"
NOM_HEADER = {"User-Agent": "ade-mapper/0.1.0"}
APP_NAME = "ade-mapper"
APP_AUTHOR = "thath"
CACHE_DIR = user_cache_dir(APP_NAME, APP_AUTHOR)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY is None:
    raise ConfigurationError("GOOGLE_API_KEY must be defined as an environment variable")


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


def cache_request(cache_key_func):
    """Cache request in specified directory using cache key function"""
    def wrapper(func):
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


@cache_request(get_ade_event_page_cache_key)
def get_ade_events(page: int) -> list[dict]:
    params = {
        "page": page,
        "section": "events",
        "from": "2025-10-22",
        "to": "2025-10-26",
        "type": "8262,8263"
    }
    with httpx.Client() as client:
        response = client.get(ADE_URL, params=params)
        data = response.json().get("data")
        return data


def get_venues(events: list[dict]) -> list[str]:
    return list(filter(None, set([event.get("venue", {}).get("title") for event in events])))


@cache_request(get_ade_venue_address_cache_key)
def get_venue_address(event_id: int) -> str | None:
    """
    Retrieve venue address given an event id
    """
    url = f"https://www.amsterdam-dance-event.nl/api/event/{event_id}"

    with httpx.Client() as client:
        resp = client.get(url, follow_redirects=True)
        mat = re.search(r'"https://www.google.com/maps/search/\?api=1&query=(.+?)"', resp.text)

        if mat:
            return mat.group(1).replace("+", " ")

        return None


@cache_request(get_ade_venue_location_cache_key)
def get_venue_location(venue: str, area: str) -> dict[str, dict]:
    params = {
        "q": f"{venue} {area}",
        "format": "json",
        "limit": 1
    }

    with httpx.Client() as client:
        response = client.get(NOM_URL, params=params, headers=NOM_HEADER)
        data = response.json()
        return data


@cache_request(get_ade_venue_place_info_cache_key)
def get_place_info(address: str) -> dict[str, dict]:
    """
    Retrieve place info from Google API given an address
    """
    data = {}

    params = {
        "query": address,
        "key": GOOGLE_API_KEY,
    }

    with httpx.Client() as client:
        response = client.get(GOOGLE_URL, params=params, follow_redirects=True)
        results = response.json().get("results", [])

        if len(results) > 0:
            data = results[0]

    return data


def get_events_for_venue(events: list[dict], venue: str) -> list[dict]:
    """
    Filters events for a specific venue
    """
    return [
        event
        for event in events
        if event.get("venue", {}).get("title") == venue
    ]


def parse_event_address_from_url(url: str) -> str | None:
    """
    Given an events URL return the street address

    We know that somewhere buried in the HTML is a link to Google Maps.
    This is just a brute force way of plucking it out.
    """
    with httpx.Client() as client:
        resp = client.get(url)
        mat = re.search(r'"https://www.google.com/maps/search/\?api=1&query=(.+?)"', resp.text)

        if mat:
            return mat.group(1).replace("+", " ")


def get_feature_collection(
    venue_locations: dict[str, dict],
    events: list[dict]
) -> FeatureCollection:
    """
    Converts venue locations to a GeoJSON FeatureCollection

    Includes events for each venue in the properties
    """
    features = []

    for venue, location in venue_locations.items():
        if location is None:
            continue

        geom = location.get("geometry", {}).get("location", {})

        if not geom.get("lng", None) or not geom.get("lat", None):
            continue

        feature = Feature(
            id=md5(venue.encode("utf-8")).hexdigest(),
            geometry=Point((geom.get("lng"), geom.get("lat"))),
            properties={
                "venue": venue,
                "events": get_events_for_venue(events, venue),
                "google_place": location
            }
        )
        features.append(feature)

    return FeatureCollection(features)


def main():
    # init cache dir
    os.makedirs(CACHE_DIR, exist_ok=True)

    page = 0

    progress = Progress(
        SpinnerColumn(),
        BarColumn(bar_width=40),
        TextColumn("[progress.description]{task.description}"),
    )

    events = []

    with progress:
        task = progress.add_task("Fetching events...", total=None)

        while data := get_ade_events(page):
            progress.advance(task)
            page += 1

            events.extend(data)

        progress.update(task, description="Done!")

    venues = get_venues(events)

    progress = Progress(
        SpinnerColumn(),
        BarColumn(bar_width=40),
        TextColumn("[progress.description]{task.description}"),
    )
    venue_addresses = {}

    with progress:
        task = progress.add_task("Fetching venue addresses...", total=None)

        for event in events:
            event_venue_title = event.get("venue", {}).get("title")
            event_id = event.get("id")
            if event_venue_title is not None:
                venue_addresses[event_venue_title] = get_venue_address(event_id)

        progress.update(task, description="Done!")

    progress = Progress(
        SpinnerColumn(),
        BarColumn(bar_width=40),
        TextColumn("[progress.description]{task.description}"),
    )

    venue_locations = {}

    with progress:
        task = progress.add_task("Fetching location...", total=None)

        for venue in venues:
            address = venue_addresses.get(venue)
            venue_locations[venue] = get_place_info(address)

        progress.update(task, description="Done!")

    feature_collection = get_feature_collection(venue_locations, events)

    output_path = Path.cwd() / Path("ade-events.geojson")
    with output_path.open("w") as fp:
        geojson.dump(feature_collection, fp)
