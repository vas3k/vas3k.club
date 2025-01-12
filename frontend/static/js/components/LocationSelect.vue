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
        <input type="text" v-model="latitude" :name="latitudeFieldName" readonly>
        <input type="text" v-model="longitude" :name="longitudeFieldName" readonly>
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
            mapStyle: "mapbox://styles/mapbox/outdoors-v11?optimize=true",
            latitude: this.defaultLatitude,
            longitude: this.defaultLongitude,
            map: null,
            zoom: 1,
            userInteracted: false,
        };
    },
    methods: {
        onMapLoaded(event) {
            this.map = event.map;
            this.map.setCenter([this.defaultLongitude, this.defaultLatitude]);
            this.updateCoordinates(this.defaultLatitude, this.defaultLongitude);
            this.map.on('movestart', this.onUserInteraction);

            if (this.defaultLatitude && this.defaultLongitude) {
                this.map.setZoom(4);
            }
        },
        onMapMove() {
            if (this.map && this.userInteracted) {
                const center = this.map.getCenter();
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
