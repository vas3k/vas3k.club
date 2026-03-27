<template>
    <div>
        <div ref="map" class="people-map-gl"></div>
        <slot></slot>
    </div>
</template>

<script>
import mapboxgl from "mapbox-gl";

export default {
    name: "PeopleMap",
    props: {
        geojson: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {
            accessToken: "pk.eyJ1IjoidmFzM2siLCJhIjoiY2thZ254NXVwMDhkbjJ5dDk5eGh5Y21wbyJ9.wYXG58PrErQfRHTflvdSfA",
            mapStyle: "mapbox://styles/vas3k/ckagmhzm90tkd1inu8pg76p9s/draft",
            coordinates: [18.3, 51.06],
            defaultAvatar: "https://media.pmi.moscow/30095075d17a92786cfea143a73d68f5f1b3e71173e3f4ecf16f90d25834e45e.png",
        };
    },
    mounted() {
        mapboxgl.accessToken = this.accessToken;
        this.map = new mapboxgl.Map({
            container: this.$refs.map,
            style: this.mapStyle,
            maxZoom: 12,
            attributionControl: false,
            scrollZoom: false,
        });
        this.map.addControl(new mapboxgl.NavigationControl(), "top-right");
        this.map.addControl(new mapboxgl.GeolocateControl(), "top-right");
        this.map.on("load", () => this.onMapLoaded());
    },
    beforeDestroy() {
        if (this.map) {
            this.map.remove();
        }
    },
    methods: {
        onMapLoaded() {
            const map = this.map;
            const geojson = this.geojson;
            const defaultAvatar = this.defaultAvatar;
            map.addSource("usersGeojson", {
                type: "geojson",
                data: this.geojson,
                cluster: true,
                clusterRadius: 25,
            });
            map.addLayer({
                id: "users",
                type: "circle",
                source: "usersGeojson",
                filter: ["!=", "cluster", true],
                paint: {
                    "circle-opacity": 0.0,
                },
            });

            let markers = {};
            let markersOnScreen = {};

            function avatarOrDefault(avatar) {
                return avatar && avatar !== "null" ? avatar : defaultAvatar;
            }

            function projectAllFeatures() {
                var projected = [];
                for (var i = 0; i < geojson.features.length; i++) {
                    var avatar = geojson.features[i].properties.avatar;
                    if (avatar && avatar !== "null") {
                        projected.push({
                            avatar: avatar,
                            pixels: map.project(geojson.features[i].geometry.coordinates),
                        });
                    }
                }
                return projected;
            }

            var CLUSTER_AVATAR_RADIUS = 20;
            var CLUSTER_AVATAR_RADIUS_SQ = CLUSTER_AVATAR_RADIUS * CLUSTER_AVATAR_RADIUS;

            function getClusterAvatar(projectedFeatures, coordinates) {
                var pointPixels = map.project(coordinates);
                for (var i = 0; i < projectedFeatures.length; i++) {
                    var dx = projectedFeatures[i].pixels.x - pointPixels.x;
                    var dy = projectedFeatures[i].pixels.y - pointPixels.y;
                    if (dx * dx + dy * dy <= CLUSTER_AVATAR_RADIUS_SQ) {
                        return projectedFeatures[i].avatar;
                    }
                }
                return defaultAvatar;
            }

            function updateMarkers() {
                var projectedFeatures = projectAllFeatures();
                let newMarkers = {};
                let features = map.querySourceFeatures("usersGeojson");

                for (let i = 0; i < features.length; i++) {
                    const coords = features[i].geometry.coordinates;
                    const props = features[i].properties;
                    const id = props.cluster_id || props.id;

                    let marker = markers[id];
                    if (!marker) {
                        if (props.cluster) {
                            let clusterElement = document.createElement("div");
                            clusterElement.classList.add("people-map-user-cluster");
                            clusterElement.innerText = props.point_count;
                            const clusterAvatar = getClusterAvatar(projectedFeatures, coords);
                            clusterElement.style.backgroundImage = "url('" + avatarOrDefault(clusterAvatar) + "')";
                            marker = new mapboxgl.Marker({ element: clusterElement }).setLngLat(coords);
                            clusterElement.addEventListener("click", function () {
                                map.flyTo({ center: coords, zoom: map.getZoom() + 2, offset: [200, 0] });
                            });
                        } else {
                            let markerElement = document.createElement("a");
                            markerElement.href = props.url;
                            markerElement.target = "_blank";
                            markerElement.classList.add("people-map-user-marker");
                            markerElement.style.backgroundImage = "url('" + avatarOrDefault(props.avatar) + "')";
                            marker = new mapboxgl.Marker({ element: markerElement }).setLngLat(coords);
                        }
                    }
                    newMarkers[id] = marker;
                    markers[id] = marker;

                    if (!markersOnScreen[id]) marker.addTo(map);
                }

                for (let id in markersOnScreen) {
                    if (!newMarkers[id]) markersOnScreen[id].remove();
                }
                markersOnScreen = newMarkers;
            }

            // Register move/moveend handlers once (not inside "data" to avoid accumulation)
            map.on("move", updateMarkers);
            map.on("moveend", updateMarkers);

            map.on("data", function (e) {
                if (e.sourceId !== "usersGeojson" || !e.isSourceLoaded) return;
                updateMarkers();
            });
        },
    },
};
</script>
