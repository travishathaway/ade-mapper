<script>
import { Map, GeolocateControl, NavigationControl} from 'mapbox-gl';
import { Modal, Card, Button, Drawer, DrawerHandle } from 'flowbite-svelte';
import { StarSolid, ArrowUpRightFromSquareOutline, GridPlusSolid } from 'flowbite-svelte-icons';
import 'mapbox-gl/dist/mapbox-gl.css';
import { onMount, onDestroy } from 'svelte';

let map;
let mapContainer;
let lng, lat, zoom;

lng = 4.895168;
lat =  52.370216;
zoom = 12;

let initialState = { lng, lat, zoom };

// Modal state
let isModalOpen = false;
let modalTitle = '';
let modalEvents = [];

// Drawer state
let open = false;

function openModal(title, events) {
  modalTitle = title;
  modalEvents = events;
  isModalOpen = true;
}

onMount(() => {
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

  map.on("load", () => {
    map.addSource("venues", {
        type: "geojson",
        data: "./ade-events.geojson",
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

  <Drawer bind:open offset="52px" placement="left" class="rounded-t-lg" aria-labelledby="drawer-swipe-label">
    <DrawerHandle onclick={() => (open = !open)} class="hover:bg-gray-50 dark:hover:bg-gray-700">
      <h5 id="drawer-swipe-label" class="inline-flex items-center gap-2 text-base font-medium text-gray-500 dark:text-gray-400">
        <GridPlusSolid />
      </h5>
    </DrawerHandle>

    <div class="mt-16 grid grid-cols-1 gap-4 lg:grid-cols-1">
      <h3>Oh Hai!</h3>
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