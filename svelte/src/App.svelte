<script>
import { Map, GeolocateControl, NavigationControl} from 'mapbox-gl';
import { Modal, Card, Button, Drawer, DrawerHandle, MultiSelect} from 'flowbite-svelte';
import { StarSolid, ArrowUpRightFromSquareOutline, GridPlusSolid } from 'flowbite-svelte-icons';
import 'mapbox-gl/dist/mapbox-gl.css';
import { onMount, onDestroy } from 'svelte';
import Svelecte from 'svelecte';

let map;
let mapContainer;
let lng, lat, zoom;
let geoJson = null;
let filteredGeoJson = null;
const GEOJSON_URL = "./ade-events.geojson";
const VENUES_SOURCE = "venues";

lng = 4.895168;
lat =  52.370216;
zoom = 12;

let initialState = { lng, lat, zoom };

// Modal state
let isModalOpen = false;
let modalTitle = '';
let modalEvents = [];

// Drawer state
let isDrawerOpen = false;

// Event specific
let categories = [];
let selectedCategories = [];

// Date filtering
const eventDates = [
  { label: 'All Dates', value: 'all' },
  { label: 'Wed, Oct 22', value: '2025-10-22' },
  { label: 'Thu, Oct 23', value: '2025-10-23' },
  { label: 'Fri, Oct 24', value: '2025-10-24' },
  { label: 'Sat, Oct 25', value: '2025-10-25' },
  { label: 'Sun, Oct 26', value: '2025-10-26' },
  { label: 'Mon, Oct 27', value: '2025-10-27' }
];
let selectedDate = 'all';

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

      // Filter by date
      let dateMatch = true;
      if (selectedDate !== 'all') {
        const eventDate = new Date(event.start_date_time.date);
        const eventDateStr = eventDate.toISOString().split('T')[0];
        dateMatch = eventDateStr === selectedDate;
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

$: if (map) {
  let source = map.getSource(VENUES_SOURCE);
  if (source && geoJson != null) {
    source.setData(
      filterGeoJson(geoJson, selectedCategories, selectedDate)
    );
  }
}

</script>

<main>
  <div class="map" bind:this={mapContainer}></div>
  
  <!--Flowbite Modal -->
  <Modal bind:open={isModalOpen} size="md" autoclose>
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
                <Button href="{event.url}" target="_blank">
                  Event link <ArrowUpRightFromSquareOutline class="ml-1 h-4 w-4"/>
                </Button>
                <Button href="{event.url}" target="_blank">
                  Favorite <StarSolid class="ml-1 h-4 w-4"/>
                </Button>
              </div>
          </Card>
        {/each}
      </div>
    </div>
  </Modal>

  <Button class="absolute top-4 left-4 z-10" onclick={() => (isDrawerOpen = !isDrawerOpen)}>
    <span class="text-lg font-semibold mr-2">Menu</span> <GridPlusSolid class="h-6 w-6"/>
  </Button>

  <Drawer bind:open={isDrawerOpen} placement="left" class="rounded-t-lg" aria-labelledby="drawer-swipe-label">

    <div class="mt-16 grid grid-cols-1 gap-4 lg:grid-cols-1">
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