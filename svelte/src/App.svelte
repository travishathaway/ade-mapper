<script>
import { Map, GeolocateControl, NavigationControl} from 'mapbox-gl';
import { Modal } from 'flowbite-svelte';
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
let modalContent = '';

function openModal(title, content) {
  modalTitle = title;
  modalContent = content;
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

          return `
              <h3>${element.title}</h3>
              <h4>${element.subtitle || ""}</h4>
              <p><span class="date-prefix">From</span> ${start} <span class="date-prefix">to</span> ${end}</p>
              <a href="${element.url}">Event link</a>
              <p>${element.categories}</p>
              <hr/>
          `;
        });

        // Open the modal with the venue name and events
        openModal(e.features[0].properties.venue, events.join(''));
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
      <h3>
        {modalTitle}
      </h3>
      <div class="text-left prose max-w-none">
        {@html modalContent}
      </div>
    </div>
  </Modal>
</main>
<style>
  .map {
    position: absolute;
    width: 100%;
    height: 100%;
  }
</style>