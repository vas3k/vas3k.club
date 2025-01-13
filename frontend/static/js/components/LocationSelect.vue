<template>
    <div class="location-select">
        <MglMap
            :accessToken="accessToken"
            :mapStyle="mapStyle"
            :maxZoom="14"
            :zoom="zoom"
            :attributionControl="false"
            :scrollZoom="true"
            @load="onMapLoaded"
            @move="onMapMove"
        >
            <MglNavigationControl position="top-right" />
            <MglGeolocateControl position="top-right" />
            <div class="location-select-target">📍</div>
            <slot></slot>
        </MglMap>
        <input type="hidden" v-model="latitude" :name="latitudeFieldName" readonly>
        <input type="hidden" v-model="longitude" :name="longitudeFieldName" readonly>
    </div>
</template>

<script>
import Mapbox from "mapbox-gl";
import { MglMap, MglNavigationControl, MglGeolocateControl, MglMarker } from "vue-mapbox-ho";

export default {
    name: "LocationSelect",
    components: {
        MglMap,
        MglNavigationControl,
        MglGeolocateControl,
        MglMarker,
    },
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
    methods: {
        onMapLoaded(event) {
            event.map.setCenter([this.defaultLongitude, this.defaultLatitude]);
            this.updateCoordinates(this.defaultLatitude, this.defaultLongitude);
            event.map.on('movestart', this.onUserInteraction);

            if (this.defaultLatitude && this.defaultLongitude) {
                event.map.setZoom(8);
            }
        },
        onMapMove(event) {
            if (event.map && this.userInteracted) {
                const center = event.map.getCenter();
                this.updateCoordinates(center.lat, center.lng);
            }
        },
        onUserInteraction() {
            this.userInteracted = true;
            this.map.off('movestart', this.onUserInteraction); // Remove listener after first interaction
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
    .location-select .mgl-map-wrapper {
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
