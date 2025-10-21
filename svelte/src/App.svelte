<script>
import { Map, GeolocateControl, NavigationControl} from 'mapbox-gl';
import { Modal, Card, Button, Drawer, Range, P} from 'flowbite-svelte';
import {
  StarSolid,
  StarOutline,
  ArrowUpRightFromSquareOutline,
  GridPlusSolid,
  HeartSolid,
  FilterSolid
} from 'flowbite-svelte-icons';
import 'mapbox-gl/dist/mapbox-gl.css';
import { onMount, onDestroy } from 'svelte';
import Svelecte from 'svelecte';
import { localStorageStore } from './lib/localStorageStore.js';

let map;
let mapContainer;
let lng, lat, zoom;
let geoJson = null;
const GEOJSON_URL = "./ade-events.geojson";
const VENUES_SOURCE = "venues";

lng = 4.895168;
lat =  52.370216;
zoom = 12;

let initialState = { lng, lat, zoom };

// Modal state
let isModalOpen = $state(false);
let modalTitle = $state('');
let modalEvents = $state([]);

// Start time filter value
let startTime = $state(0);

// Drawer state
let isDrawerOpen = $state(false);
let activeTab = $state('filters'); // 'filters' or 'favorites'

// Favorites store
const favorites = localStorageStore('ade-favorites', []);
let showOnlyFavorites = $state(false);

// Event specific
let categories = $state([]);
let selectedCategories = $state([]);

// Date filtering
const eventDates = [
  { label: 'All Dates', value: 'all' },
  { label: 'Wed, Oct 22', value: '2025-10-22' },
  { label: 'Thu, Oct 23', value: '2025-10-23' },
  { label: 'Fri, Oct 24', value: '2025-10-24' },
  { label: 'Sat, Oct 25', value: '2025-10-25' },
  { label: 'Sun, Oct 26', value: '2025-10-26' },
];
let selectedDate = $state('all');

function openModal(title, events) {
  modalTitle = title;
  modalEvents = events;
  isModalOpen = true;
}

function parseCategories(geoJson) {
  const categorySet = new Set();

  geoJson.features.forEach(feature => {
    const events = feature.properties.events;
    events.forEach(event => {
      if (event.categories) {
        event.categories.forEach(category => {
          let cat = category.trim();
          if (cat !== "") categorySet.add(cat);
        });
      }
    });
  });

  categories = Array.from(categorySet).map(cat => ({
    value: cat, name: cat
  }));
}

function filterGeoJson(geoJson, categories, selectedDate) {
  function filterEvents(events, categories, selectedDate) {
    return events.filter(event => {
      // Filter by category
      let categoryMatch = true;
      if (categories.length > 0) {
        const eventCatSet = new Set(event.categories);
        const result = categories.map(elm => eventCatSet.has(elm));
        categoryMatch = result.filter(x => x === true).length >= categories.length;
      }

      // Filter by date and start time
      let dateMatch = true;
      const eventDate = new Date(event.start_date_time.date);
      const eventDateStr = eventDate.toISOString().split('T')[0];
      const startHour = eventDate.getHours();

      if (selectedDate !== 'all') {
        dateMatch = eventDateStr === selectedDate && startHour >= startTime;
      } else {
        dateMatch = startHour >= startTime;
      }

      return categoryMatch && dateMatch;
    });
  }

  const filteredEvents = filterEvents(geoJson.features.flatMap(f => f.properties.events), categories, selectedDate);

  const filteredFeatures = geoJson.features.filter(feature => {
    const events = feature.properties.events;
    const filtered = filterEvents(events, categories, selectedDate);

    return filtered.length > 0;

  }).map(feature => {
    const events = feature.properties.events;
    const filtered = filterEvents(events, categories, selectedDate);

    return { ...feature, properties: { ...feature.properties, events: filtered } };
  });

  return {
    type: "FeatureCollection",
    features: filteredFeatures
  };
}

onMount(async () => {
  map = new Map({
    container: mapContainer,
    accessToken: "pk.eyJ1IjoidGhhdGgiLCJhIjoiY2lsMnc1OW9yM2pqcXV5a3NtMXh3b3I4ZCJ9.Mn1daTFDAN18C38dOS0SjQ",
    center: [initialState.lng, initialState.lat],
    zoom: initialState.zoom
  });


  // Add geolocate control to the map.
  map.addControl(
      new GeolocateControl({
          positionOptions: {
              enableHighAccuracy: true
          },
          // When active the map will receive updates to the device's location as it changes.
          trackUserLocation: true,
          // Draw an arrow next to the location dot to indicate which direction the device is heading.
          showUserHeading: true
      })
  );

  map.on("load", async () => {
    geoJson = await fetch(GEOJSON_URL).then(res => res.json());
    parseCategories(geoJson);

    map.addSource(VENUES_SOURCE, {
        type: "geojson",
        data: geoJson,
        generateId: true,
        cluster: true,
    });

    // Add zoom and rotation controls to the map
    map.addControl(new NavigationControl(), 'top-right');

    map.addLayer({
        id: "clusters",
        type: "circle",
        source: "venues",
        filter: ["has", "point_count"],
        paint: {
            // Use step expressions (https://docs.mapbox.com/style-spec/reference/expressions/#step)
            // with three steps to implement three types of circles:
            //   * Blue, 20px circles when point count is less than 100
            //   * Yellow, 30px circles when point count is between 100 and 750
            //   * Pink, 40px circles when point count is greater than or equal to 750
            'circle-color': [
                'step',
                ['get', 'point_count'],
                '#51bbd6',
                100,
                '#f1f075',
                750,
                '#f28cb1'
            ],
            'circle-radius': [
                'step',
                ['get', 'point_count'],
                20,
                100,
                30,
                750,
                40
            ],
            'circle-emissive-strength': 1
        }
    });

    map.addLayer({
        id: 'cluster-count',
        type: 'symbol',
        source: 'venues',
        filter: ['has', 'point_count'],
        layout: {
            'text-field': ['get', 'point_count_abbreviated'],
            'text-font': ['DIN Offc Pro Medium', 'Arial Unicode MS Bold'],
            'text-size': 12
        }
    });

    map.addLayer({
        id: 'unclustered-point',
        type: 'circle',
        source: 'venues',
        filter: ['!', ['has', 'point_count']],
        paint: {
            'circle-color': '#000000',
            'circle-radius': 8,
            'circle-stroke-width': 1,
            'circle-stroke-color': '#fff',
            'circle-emissive-strength': 1
        }
    });

    // inspect a cluster on click
    map.on('click', 'clusters', (e) => {
        const features = map.queryRenderedFeatures(e.point, {
            layers: ['clusters']
        });
        const clusterId = features[0].properties.cluster_id;
        map.getSource('venues').getClusterExpansionZoom(
            clusterId,
            (err, zoom) => {
                if (err) return;

                map.easeTo({
                    center: features[0].geometry.coordinates,
                    zoom: zoom
                });
            }
        );
    });

    // When a click event occurs on a feature in the places layer, open a popup at the
    // location of the feature, with description HTML from its properties.
    map.on('click', 'unclustered-point', (e) => {
        // Copy coordinates array.
        const coordinates = e.features[0].geometry.coordinates.slice();

        const events = JSON.parse(e.features[0].properties.events).map(element => {
          const start = new Date(element.start_date_time.date).toLocaleString();
          const end = new Date(element.end_date_time.date).toLocaleString();

          return {
            id: element.id,
            title: element.title,
            subtitle: element.subtitle,
            start: start,
            end: end,
            url: element.url,
            categories: element.categories
          }
        });

        // Open the modal with the venue name and events
        openModal(e.features[0].properties.venue, events);
    });

    // Change the cursor to a pointer when the mouse is over a POI.
    map.on('mouseenter', 'clusters', () => {
        map.getCanvas().style.cursor = 'pointer';
    });

    // Change the cursor back to a pointer when it stops hovering over a POI.
    map.on('mouseleave', 'clusters', () => {
        map.getCanvas().style.cursor = '';
    });

    // Change the cursor to a pointer when the mouse is over a POI.
    map.on('mouseenter', 'unclustered-point', () => {
        map.getCanvas().style.cursor = 'pointer';
    });

    // Change the cursor back to a pointer when it stops hovering over a POI.
    map.on('mouseleave', 'unclustered-point', () => {
        map.getCanvas().style.cursor = '';
    });
  });
});

onDestroy(() => {
  map.remove();
});

// Helper functions for favorites
function toggleFavorite(eventId) {
  favorites.update(favs => {
    if (favs.includes(eventId)) {
      return favs.filter(id => id !== eventId);
    } else {
      return [...favs, eventId];
    }
  });
}

function isFavorite(eventId) {
  return $favorites.includes(eventId);
}

function getFavoriteEvents() {
  if (!geoJson) return [];

  const allEvents = [];
  geoJson.features.forEach(feature => {
    feature.properties.events.forEach(event => {
      if ($favorites.includes(event.id)) {
        allEvents.push({
          id: event.id,
          title: event.title,
          subtitle: event.subtitle,
          start: new Date(event.start_date_time.date).toLocaleString(),
          end: new Date(event.end_date_time.date).toLocaleString(),
          url: event.url,
          categories: event.categories,
          venue: feature.properties.venue
        });
      }
    });
  });

  return allEvents;
}

function formatStartTime(startTime) {
  const hours = String(Math.floor(startTime)).padStart(2, '0');
  if (startTime % 1 !== 0) {
    return `${hours}:30`;
  }
  return `${hours}:00`;
}

// TODO: Could be nice to use "actions" instead here because $effect should only
//       be used sparingly. It's okay for now though.
$effect(() => {
  // Explicitly read all reactive dependencies to ensure tracking
  const cats = selectedCategories;
  const date = selectedDate;
  const favOnly = showOnlyFavorites;
  const favs = $favorites;
  const start = startTime;

  if (map && geoJson != null) {
    const source = map.getSource(VENUES_SOURCE);
    if (source) {
      let filteredData = filterGeoJson(geoJson, cats, date);

      // Further filter by favorites if the toggle is on
      if (favOnly && favs.length > 0) {
        filteredData = {
          type: "FeatureCollection",
          features: filteredData.features.filter(feature => {
            return feature.properties.events.some(event => favs.includes(event.id));
          })
        };
      }

      source.setData(filteredData);
    }
  }
});

</script>

<main>
  <div class="map" bind:this={mapContainer}></div>
  
  <!--Flowbite Modal -->
  <Modal bind:open={isModalOpen} size="md">
    <div class="text-center">
      <h3 class="text-3xl mb-4 font-extrabold tracking-tight text-gray-900 dark:text-white">
        {modalTitle}
      </h3>
      <div class="text-left prose max-w-none">
        {#each modalEvents as event}
          <Card size="lg" class="mb-4 p-4 sm:p-6 md:p-8">
              <h3 class="text-2xl mb-2 font-semibold tracking-tight text-gray-900 dark:text-white">{event.title}</h3>
              <h4 class="text-lg mb-2">{event.subtitle || ""}</h4>
              <p class="mb-2"><span class="font-semibold">From</span> {event.start} <span class="font-semibold">to</span> {event.end}</p>
              <div class="mb-4">
                <p class="font-semibold mb-1">Categories:</p>
                <p class="text-sm text-gray-500 dark:text-gray-400">{event.categories}</p>
              </div>
              
              <div class="sm:flex sm:space-y-0 sm:space-x-4">
                <Button href={event.url} target="_blank">
                  Event link <ArrowUpRightFromSquareOutline class="ml-1 h-4 w-4"/>
                </Button>
                <Button
                  color={isFavorite(event.id) ? "red" : "alternative"}
                  onclick={() => toggleFavorite(event.id)}
                >
                  {isFavorite(event.id) ? 'Remove from favorites' : 'Add to favorites'}
                  {#if isFavorite(event.id)}
                    <StarSolid class="ml-1 h-4 w-4"/>
                  {:else}
                    <StarOutline class="ml-1 h-4 w-4"/>
                  {/if}
                </Button>
              </div>
          </Card>
        {/each}
      </div>
    </div>
  </Modal>

  <div class="fixed top-0 left-0 w-full h-16 flex items-center px-4">
    <Button size="md" class="mt-4" onclick={() => {
      activeTab = 'filters';
      isDrawerOpen = true;
    }}>
      <span class="hidden md:inline font-semibold mr-2">Menu</span>
      <GridPlusSolid class="h-4 w-4"/>
    </Button>
  </div>


  <Drawer bind:open={isDrawerOpen} placement="left" class="rounded-t-lg" aria-labelledby="drawer-label">
    <div class="p-4">
      <!-- Pill-style tabs -->
      <div class="flex gap-2 mb-6 bg-gray-100 dark:bg-gray-800 p-1 rounded-full">
        <button
          class="flex-1 px-4 py-2 rounded-full text-sm font-medium transition-all {activeTab === 'filters' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
          onclick={() => activeTab = 'filters'}
        >
          <FilterSolid class="inline h-4 w-4 mr-1"/>
          Filters
        </button>
        <button
          class="flex-1 px-4 py-2 rounded-full text-sm font-medium transition-all {activeTab === 'favorites' ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm' : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'}"
          onclick={() => activeTab = 'favorites'}
        >
          <HeartSolid class="inline h-4 w-4 mr-1"/>
          Favorites
          {#if $favorites.length > 0}
            <span class="ml-1 bg-red-500 text-white rounded-full px-2 py-0.5 text-xs font-bold">{$favorites.length}</span>
          {/if}
        </button>
      </div>

      <!-- Tab content -->
      {#if activeTab === 'filters'}
        <div class="grid grid-cols-1 gap-4">
          <h3 class="text-lg font-semibold">Filter by Date</h3>
          <div class="flex flex-wrap gap-2">
            {#each eventDates as date}
              <button
                class="px-3 py-2 rounded-lg text-sm font-medium transition-colors {selectedDate === date.value ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'}"
                onclick={() => selectedDate = date.value}
              >
                {date.label}
              </button>
            {/each}
          </div>

          <h3 class="text-lg font-semibold">Starts After</h3>
          <div class="gap-2">
            <Range id="range-steps" min="0" max="23.5" bind:value={startTime} step="0.5" />
              <P size="3xl" class="text-center">{formatStartTime(startTime)}</P>
            </div>

            <h3 class="text-lg font-semibold">Filter by Category</h3>
            <div class="mr-2">
              <Svelecte
                options={categories}
                bind:value={selectedCategories}
                placeholder="Select categories to filter"
                multiple={true}
                clearable={true}
              />
            </div>

            <hr class="my-4" />

            <h3 class="text-lg font-semibold">Show Favorites Only</h3>
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {showOnlyFavorites ? 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600' : 'bg-red-600 text-white' }"
              onclick={() => {
                showOnlyFavorites = !showOnlyFavorites;
                selectedCategories = [];
                selectedDate = 'all';
              }}
            >
              {showOnlyFavorites ? 'Show All Venues' : 'Show Favorites Only'}
            </button>
          </div>
        {:else}
          <div class="grid grid-cols-1 gap-4">
            <h3 class="text-2xl font-bold text-red-600">
              <HeartSolid class="inline h-6 w-6 mr-2"/>
              My Favorites
            </h3>

            {#if $favorites.length === 0}
              <div class="text-center py-8 text-gray-500 dark:text-gray-400">
                <StarOutline class="mx-auto h-16 w-16 mb-4 opacity-30"/>
                <p class="text-lg">No favorites yet!</p>
                <p class="text-sm mt-2">Click on a venue on the map and add events to your favorites.</p>
              </div>
            {:else}
              <p class="text-sm text-gray-600 dark:text-gray-400">
                You have {$favorites.length} favorite event{$favorites.length !== 1 ? 's' : ''}
              </p>

              {#each getFavoriteEvents() as event}
                <Card size="lg" class="mb-2 p-4">
                  <div class="flex justify-between items-start mb-2">
                    <h4 class="text-lg font-semibold text-gray-900 dark:text-white flex-1">{event.title}</h4>
                    <button
                      class="text-red-600 hover:text-red-800 ml-2"
                      onclick={() => toggleFavorite(event.id)}
                      title="Remove from favorites"
                    >
                      <StarSolid class="h-5 w-5"/>
                    </button>
                  </div>
                  {#if event.subtitle}
                    <p class="text-sm text-gray-600 dark:text-gray-400 mb-2">{event.subtitle}</p>
                  {/if}
                  <p class="text-xs text-gray-500 dark:text-gray-500 mb-1">
                    <span class="font-semibold">Venue:</span> {event.venue}
                  </p>
                  <p class="text-xs text-gray-500 dark:text-gray-500 mb-2">
                    <span class="font-semibold">From</span> {event.start} <span class="font-semibold">to</span> {event.end}
                  </p>
                  <Button size="xs" href={event.url} target="_blank">
                    View Event <ArrowUpRightFromSquareOutline class="ml-1 h-3 w-3"/>
                  </Button>
                </Card>
              {/each}
            {/if}
          </div>
        {/if}
      </div>
    </Drawer>
  </main>
  <style>
    .map {
      position: absolute;
      width: 100%;
      height: 100%;
    }
</style>