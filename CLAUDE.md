# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ADE Mapper is a web application that displays events for Amsterdam Dance Event (ADE) 2025 on an interactive map. The project consists of two main components:

1. **Python CLI tool** (`src/ade_mapper/`) - Scrapes event data from the ADE API and Google Places API, producing a GeoJSON file
2. **Svelte web app** (`svelte/`) - Interactive map interface using Mapbox GL to display the events

## Architecture

### Python Backend (Data Collection)

The Python CLI scrapes and geocodes ADE event data:

- `main.py` - Core scraping logic that fetches events, venues, addresses, and locations from multiple APIs
- `cache.py` - Decorator-based caching system using platformdirs to avoid redundant API calls
- `cli.py` - Typer-based CLI with `collect` and `clean` commands
- `constants.py` - API endpoints and configuration (requires `GOOGLE_API_KEY` environment variable)

**Data flow**: ADE API → venue extraction → address lookup → Google Places geocoding → GeoJSON output

The scraper uses a caching system to avoid hitting rate limits and stores results in `~/.cache/ade-mapper/` (Linux/macOS) or equivalent platform cache directory.

### Svelte Frontend (Visualization)

The Svelte app (`svelte/src/App.svelte`) provides the interactive map:

- Uses Mapbox GL JS for map rendering with clustering support
- Reads from `svelte/public/ade-events.geojson` (or `dist/ade-events.geojson` after build)
- Features category-based filtering using a drawer UI
- Modal view for event details with links to ADE website
- Built with Vite, Tailwind CSS, and Flowbite Svelte components

## Common Commands

### Python Development

```bash
# Install dependencies and setup environment (using uv)
uv sync --python 3.10 --all-extras
source .venv/bin/activate
pre-commit install --install-hooks

# Run the data collection script
ade-mapper collect

# Clean cached API responses
ade-mapper clean

# Run tests
poe test
# Or directly with pytest
pytest

# Run linting
poe lint
# Or directly
pre-commit run --all-files

# Type checking
mypy src/

# Generate documentation
poe docs --serve
```

### Svelte Development

```bash
# Install dependencies
cd svelte
npm install

# Run development server (with hot reload)
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

## Environment Setup

**Required**: Create a `.env` file in the project root with:

```
GOOGLE_API_KEY=your_google_places_api_key_here
```

The Google Places API key is required for geocoding venue addresses.

## Deployment

The GitHub Actions workflow (`.github/workflows/website.yml`) automatically:

1. Builds the Svelte app when pushing to `main` branch
2. Deploys to GitHub Pages from the `svelte/dist` directory

The GeoJSON file must be generated manually using `ade-mapper collect` and committed to the repository before deploying, as the workflow only builds the frontend.

## Code Style

- Python: Strict type hints enabled, Ruff for formatting/linting, line length 100
- Follows Conventional Commits for versioning
- Uses `commitizen` for changelog generation
- Pre-commit hooks enforce code quality

## Testing

- Python tests use pytest with coverage reporting (minimum 50% coverage)
- Test files in `tests/` directory
- Run with coverage: `poe test` or `coverage run -m pytest && coverage report`


You are able to use the Svelte MCP server, where you have access to comprehensive Svelte 5 and SvelteKit documentation. Here's how to use the available tools effectively:

## Available MCP Tools:

### 1. list-sections

Use this FIRST to discover all available documentation sections. Returns a structured list with titles, use_cases, and paths.
When asked about Svelte or SvelteKit topics, ALWAYS use this tool at the start of the chat to find relevant sections.

### 2. get-documentation

Retrieves full documentation content for specific sections. Accepts single or multiple sections.
After calling the list-sections tool, you MUST analyze the returned documentation sections (especially the use_cases field) and then use the get-documentation tool to fetch ALL documentation sections that are relevant for the user's task.

### 3. svelte-autofixer

Analyzes Svelte code and returns issues and suggestions.
You MUST use this tool whenever writing Svelte code before sending it to the user. Keep calling it until no issues or suggestions are returned.

### 4. playground-link

Generates a Svelte Playground link with the provided code.
After completing the code, ask the user if they want a playground link. Only call this tool after user confirmation and NEVER if code was written to files in their project.