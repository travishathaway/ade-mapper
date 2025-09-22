from hashlib import md5
import os
import json
from pathlib import Path
from pprint import pprint

import geojson
import httpx
from platformdirs import user_cache_dir
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from geojson import Point, FeatureCollection, Feature

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
    name = venue.replace(" ", "-").lower()

    return f"ade-venue-location-place-info--{name}.json"


def get_ade_events(page: int) -> list[dict]:
    cache_obj = Path(CACHE_DIR) / Path(get_ade_event_page_cache_key(page))
    if cache_obj.exists():
        try:
            return json.load(cache_obj.open())
        except json.decoder.JSONDecodeError:
            pass

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
        cache = Path(CACHE_DIR) / Path(get_ade_event_page_cache_key(page))
        with cache.open("w") as fp:
            json.dump(data, fp)
            return data


def get_venues(events: list[dict]) -> list[str]:
    return list(filter(None, set([event.get("venue", {}).get("title") for event in events])))


def get_venue_location(venue: str, area: str) -> dict[str, dict]:
    cache_obj = Path(CACHE_DIR) / Path(get_ade_venue_location_cache_key(venue))

    if cache_obj.exists():
        try:
            return json.load(cache_obj.open())
        except json.decoder.JSONDecodeError:
            pass

    params = {
        "q": f"{venue} {area}",
        "format": "json",
        "limit": 1
    }

    with httpx.Client() as client:
        response = client.get(NOM_URL, params=params, headers=NOM_HEADER)
        data = response.json()
        cache_obj = Path(CACHE_DIR) / Path(get_ade_venue_location_cache_key(venue))

        with cache_obj.open("w") as fp:
            json.dump(data, fp)
            return data

    return data


def get_place_info(venue: str, area: str) -> dict[str, dict]:
    cache_obj = Path(CACHE_DIR) / Path(get_ade_venue_place_info_cache_key(venue))

    if cache_obj.exists():
        try:
            return json.load(cache_obj.open())
        except json.decoder.JSONDecodeError:
            pass

    params = {
        "query": f"{venue} in {area}",
        "key": GOOGLE_API_KEY,
    }

    with httpx.Client() as client:
        response = client.get(GOOGLE_URL, params=params, follow_redirects=True)
        results = response.json().get("results", [])

        if len(results) > 0:
            data = results[0]
            cache_obj = Path(CACHE_DIR) / Path(get_ade_venue_place_info_cache_key(venue))

            with cache_obj.open("w") as fp:
                json.dump(data, fp)
                return data

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

        geometry = location.get("geometry", {}).get("location", {})

        feature = Feature(
            id=md5(venue.encode("utf-8")).hexdigest(),
            geometry=Point((geometry.get("lng"), geometry.get("lat"))),
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

    venue_locations = {}

    with progress:
        task = progress.add_task("Fetching location...", total=None)

        for venue in venues:
            venue_locations[venue] = get_place_info(venue, "Amsterdam")

    feature_collection = get_feature_collection(venue_locations, events)

    output_path = Path.cwd() / Path("ade-events.geojson")
    with output_path.open("w") as fp:
        geojson.dump(feature_collection, fp)


if __name__ == "__main__":
    main()

