import os

from .errors import ConfigurationError

# Nominatim base URL
NOM_URL = "https://nominatim.openstreetmap.org/search"

#: Amsterdam Dance Event API URL
ADE_URL = "https://www.amsterdam-dance-event.nl/api/program/filter/"

#: Google Places API URL
GOOGLE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

#: Nominatim request headers
NOM_HEADER = {"User-Agent": "ade-mapper/0.1.0"}

#: Application name and author for cache directory
APP_NAME = "ade-mapper"

#: Application author
APP_AUTHOR = "thath"

#:  Google API key from environment variable
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY is None:
    raise ConfigurationError("GOOGLE_API_KEY must be defined as an environment variable")