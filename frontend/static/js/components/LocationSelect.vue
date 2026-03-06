<template>
    <div class="location-select">
        <div ref="map" class="location-select-map"></div>
        <div class="location-select-target">📍</div>
        <slot></slot>
        <input type="hidden" v-model="latitude" :name="latitudeFieldName" readonly />
        <input type="hidden" v-model="longitude" :name="longitudeFieldName" readonly />
    </div>
</template>

<script>
import mapboxgl from "mapbox-gl";

export default {
    name: "LocationSelect",
    props: {
        defaultLatitude: {
            type: Number,
            default: 0,
        },
        defaultLongitude: {
            type: Number,
            default: 0,
        },
        latitudeFieldName: {
            type: String,
            default: "latitude",
        },
        longitudeFieldName: {
            type: String,
            default: "longitude",
        },
    },
    data() {
        return {
            accessToken: "pk.eyJ1IjoidmFzM2siLCJhIjoiY2thZ254NXVwMDhkbjJ5dDk5eGh5Y21wbyJ9.wYXG58PrErQfRHTflvdSfA",
            mapStyle: "mapbox://styles/mapbox/outdoors-v12",
            latitude: this.defaultLatitude,
            longitude: this.defaultLongitude,
            zoom: 1,
            userInteracted: false,
        };
    },
    mounted() {
        mapboxgl.accessToken = this.accessToken;
        this.map = new mapboxgl.Map({
            container: this.$refs.map,
            style: this.mapStyle,
            maxZoom: 14,
            zoom: this.zoom,
            attributionControl: false,
            scrollZoom: true,
        });
        this.map.addControl(new mapboxgl.NavigationControl(), "top-right");
        this.map.addControl(new mapboxgl.GeolocateControl(), "top-right");
        this.map.on("load", () => this.onMapLoaded());
        this.map.on("move", () => this.onMapMove());
    },
    beforeUnmount() {
        if (this.map) {
            this.map.remove();
        }
    },
    methods: {
        onMapLoaded() {
            this.map.setCenter([this.defaultLongitude, this.defaultLatitude]);
            this.updateCoordinates(this.defaultLatitude, this.defaultLongitude);
            this.map.on("movestart", this.onUserInteraction);

            if (this.defaultLatitude && this.defaultLongitude) {
                this.map.setZoom(8);
            }
        },
        onMapMove() {
            if (this.userInteracted) {
                const center = this.map.getCenter();
                this.updateCoordinates(center.lat, center.lng);
            }
        },
        onUserInteraction() {
            this.userInteracted = true;
            this.map.off("movestart", this.onUserInteraction);
        },
        updateCoordinates(lat, lng) {
            this.latitude = lat.toFixed(6);
            this.longitude = lng.toFixed(6);
        },
    },
};
</script>

<style>
.location-select {
    position: relative;
    margin: 0 auto;
    max-width: 550px;
}

.location-select .mapboxgl-map,
.location-select .location-select-map {
    position: relative;
    width: 100%;
    height: 300px;
    max-width: 550px;
}

.location-select-target {
    position: absolute;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -95%);
    font-size: 40px;
    line-height: 1em;
    width: 40px;
    height: 40px;
}
</style>
