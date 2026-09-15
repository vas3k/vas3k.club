<template>
    <div class="people-map-root">
        <div ref="map" class="people-map-gl"></div>

        <div class="people-map-buttons">
            <a v-if="editProfileUrl" :href="editProfileUrl" class="button">📍 Передвинуть себя</a>

            <button
                v-if="createMessageUrl"
                type="button"
                class="button people-map-compose-button"
                :class="{ 'people-map-compose-button-active': composeMode }"
                :disabled="!postingAllowed"
                @click="toggleComposeMode"
            >
                <span v-if="!postingAllowed">⏳ Подождите 24 часа</span>
                <span v-else-if="composeMode">✖️ Отменить</span>
                <span v-else>💬 Оставить сообщение</span>
            </button>
        </div>

        <div v-show="draft" ref="composeBubble" class="people-map-message people-map-message-compose">
            <textarea
                ref="composeInput"
                v-model="draftText"
                class="people-map-message-input"
                :maxlength="maxMessageLength"
                placeholder="Что здесь интересного?"
            ></textarea>
            <div v-if="draftError" class="people-map-message-error">{{ draftError }}</div>
            <div class="people-map-message-footer">
                <button
                    type="button"
                    class="button people-map-message-save"
                    :disabled="!canSaveDraft"
                    @click="saveDraft"
                >
                    {{ isSaving ? "..." : "Написать тут" }}
                </button>
            </div>
        </div>

        <slot></slot>
    </div>
</template>

<script>
import mapboxgl from "mapbox-gl";

import ClubApi from "../common/api.service";

const MESSAGES_SOURCE = "messagesGeojson";
const MESSAGES_CLUSTER_RADIUS = 40;
const MESSAGE_TEXT_MIN_ZOOM = 10;

export default {
    name: "PeopleMap",
    props: {
        geojson: {
            type: [Object, String],
            required: true,
        },
        messages: {
            type: [Object, String],
            default: "",
        },
        createMessageUrl: {
            type: String,
            default: null,
        },
        canPostMessage: {
            type: Boolean,
            default: true,
        },
        editProfileUrl: {
            type: String,
            default: null,
        },
        maxMessageLength: {
            type: Number,
            default: 128,
        },
    },
    data() {
        return {
            accessToken: "pk.eyJ1IjoidmFzM2siLCJhIjoiY2thZ254NXVwMDhkbjJ5dDk5eGh5Y21wbyJ9.wYXG58PrErQfRHTflvdSfA",
            mapStyle: "mapbox://styles/vas3k/ckagmhzm90tkd1inu8pg76p9s/draft",
            coordinates: [18.3, 51.06],
            defaultAvatar: "https://i.vas3k.club/v.png",
            postingAllowed: this.canPostMessage,
            composeMode: false,
            draft: null,
            draftText: "",
            draftError: null,
            isSaving: false,
        };
    },
    computed: {
        messagesEnabled() {
            return Boolean(this.messages || this.createMessageUrl);
        },
        canSaveDraft() {
            return Boolean(this.draft) && this.draftText.trim().length > 0 && !this.isSaving;
        },
    },
    created() {
        // kept out of "data" on purpose: geojson is only read by imperative marker code,
        // making it reactive would cost a lot and buy nothing
        this.usersGeojson = this.parseFeatureCollection(this.geojson);
        this.messagesGeojson = this.parseFeatureCollection(this.messages);
        this.messageMarkers = {};
        this.messageMarkersOnScreen = {};
        this.messagesSourceAdded = false;
    },
    mounted() {
        mapboxgl.accessToken = this.accessToken;
        this.map = new mapboxgl.Map({
            container: this.$refs.map,
            style: this.mapStyle,
            maxZoom: 16,
            attributionControl: false,
            scrollZoom: true,
            dragPan: true,
            touchZoomRotate: true,
        });
        this.map.addControl(new mapboxgl.NavigationControl(), "top-right");
        this.map.addControl(new mapboxgl.GeolocateControl(), "top-right");
        this.map.on("load", () => this.onMapLoaded());
    },
    beforeDestroy() {
        clearTimeout(this.closeDraftTimer);
        document.removeEventListener("click", this.onDocumentClick);

        if (this.map) {
            this.map.remove();
        }
    },
    methods: {
        onMapLoaded() {
            const map = this.map;
            const geojson = this.usersGeojson;
            const defaultAvatar = this.defaultAvatar;

            map.addSource("usersGeojson", {
                type: "geojson",
                data: this.usersGeojson,
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

            function cssBackgroundImage(url) {
                return "url(" + JSON.stringify(avatarOrDefault(url)) + ")";
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
                            clusterElement.style.backgroundImage = cssBackgroundImage(clusterAvatar);
                            marker = new mapboxgl.Marker({ element: clusterElement }).setLngLat(coords);
                            clusterElement.addEventListener("click", function () {
                                map.flyTo({ center: coords, zoom: map.getZoom() + 2, offset: [200, 0] });
                            });
                        } else {
                            let markerElement = document.createElement("a");
                            markerElement.href = props.url;
                            markerElement.target = "_blank";
                            markerElement.classList.add("people-map-user-marker");
                            markerElement.style.backgroundImage = cssBackgroundImage(props.avatar);
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
            map.on("move", () => {
                updateMarkers();
                this.updateMessageMarkers();
            });
            map.on("moveend", () => {
                updateMarkers();
                this.updateMessageMarkers();
            });

            map.on("data", (e) => {
                if (!e.isSourceLoaded) return;
                if (e.sourceId === "usersGeojson") {
                    updateMarkers();
                } else if (e.sourceId === MESSAGES_SOURCE) {
                    this.updateMessageMarkers();
                }
            });

            if (this.messagesEnabled) {
                this.setupMessages();
            }
        },

        parseFeatureCollection(value) {
            const empty = { type: "FeatureCollection", features: [] };
            if (!value) return empty;
            if (typeof value === "object") {
                return value.features ? value : empty;
            }

            try {
                const parsed = JSON.parse(value);
                return parsed && parsed.features ? parsed : empty;
            } catch (e) {
                return empty;
            }
        },

        setupMessages() {
            this.map.addSource(MESSAGES_SOURCE, {
                type: "geojson",
                data: this.messagesGeojson,
                cluster: true,
                clusterRadius: MESSAGES_CLUSTER_RADIUS,
            });
            this.map.addLayer({
                id: "messages",
                type: "circle",
                source: MESSAGES_SOURCE,
                filter: ["!=", "cluster", true],
                paint: {
                    "circle-opacity": 0.0,
                },
            });
            this.messagesSourceAdded = true;

            this.map.on("click", this.onMapClick);
            this.updateMessageMarkers();
        },

        updateMessageMarkers() {
            if (!this.messagesSourceAdded) return;

            const map = this.map;
            const withText = map.getZoom() >= MESSAGE_TEXT_MIN_ZOOM;
            const features = map.querySourceFeatures(MESSAGES_SOURCE);
            const newMarkers = {};

            for (let i = 0; i < features.length; i++) {
                const coords = features[i].geometry.coordinates;
                const props = features[i].properties;
                // the display mode is part of the key, so markers are rebuilt when zoom crosses the text threshold
                const id = (props.cluster ? "cluster-" + props.cluster_id : props.id) + (withText ? ":text" : ":icon");

                let marker = this.messageMarkers[id];
                if (!marker) {
                    const element = props.cluster
                        ? this.createMessageClusterElement(props, coords)
                        : this.createMessageElement(props, coords, withText);
                    marker = new mapboxgl.Marker({ element: element, anchor: "bottom" }).setLngLat(coords);
                    this.messageMarkers[id] = marker;
                }
                newMarkers[id] = marker;

                if (!this.messageMarkersOnScreen[id]) marker.addTo(map);
            }

            for (let id in this.messageMarkersOnScreen) {
                if (!newMarkers[id]) this.messageMarkersOnScreen[id].remove();
            }
            this.messageMarkersOnScreen = newMarkers;
        },

        createMessageClusterElement(props, coords) {
            const element = document.createElement("div");
            element.classList.add("people-map-message", "people-map-message-cluster");
            element.innerText = "💬 " + props.point_count;
            element.addEventListener("click", () => {
                this.map.flyTo({ center: coords, zoom: this.map.getZoom() + 2 });
            });
            return element;
        },

        createMessageElement(props, coords, withText) {
            const element = document.createElement("div");
            element.classList.add("people-map-message");

            if (!withText) {
                element.classList.add("people-map-message-icon");
                element.innerText = "💬";
                element.title = props.author_name || "";
                element.addEventListener("click", () => {
                    this.map.flyTo({ center: coords, zoom: MESSAGE_TEXT_MIN_ZOOM });
                });
                return element;
            }

            element.classList.add("people-map-message-full");

            // only the avatar is shown, the name would eat too much space in the bubble
            const author = document.createElement("a");
            author.classList.add("people-map-message-author");
            author.href = props.author_url;
            author.target = "_blank";
            author.title = props.author_name || "";

            const avatar = document.createElement("span");
            avatar.classList.add("people-map-message-avatar");
            avatar.style.backgroundImage = "url(" + JSON.stringify(props.author_avatar || this.defaultAvatar) + ")";
            author.appendChild(avatar);

            const body = document.createElement("span");
            body.classList.add("people-map-message-body");
            body.innerText = props.text || ""; // innerText, so message text can never become markup

            element.appendChild(author);
            element.appendChild(body);

            const upvote = this.createUpvoteElement(props);
            if (upvote) element.appendChild(upvote);

            return element;
        },

        createUpvoteElement(props) {
            const upvotes = parseInt(props.upvotes) || 0;
            const isMine = props.is_mine === true || props.is_mine === "true";

            // a dead button on your own message is just noise until somebody votes for it
            if (isMine && upvotes === 0) return null;

            const counter = document.createElement("span");
            counter.classList.add("people-map-message-upvotes");
            counter.innerText = upvotes > 0 ? upvotes : "";

            const button = document.createElement("button");
            button.type = "button";
            button.classList.add("button", "people-map-message-upvote");

            // drawn with css, no font puts a "+" glyph in the optical center of a circle
            const plus = document.createElement("span");
            plus.classList.add("people-map-message-plus");
            button.appendChild(plus);
            button.appendChild(counter);

            if (upvotes > 0) {
                button.classList.add("people-map-message-upvote-counted");
            }

            // votes are final, so the button is only ever active once per message
            const isVoted = props.is_voted === true || props.is_voted === "true";
            if (isMine) {
                button.disabled = true;
                button.title = "За свои сообщения голосовать нельзя";
            } else if (isVoted) {
                button.disabled = true;
                button.title = "Вы уже проголосовали";
            } else {
                button.title = "Хорошее сообщение!";
                button.addEventListener("click", () => this.upvoteMessage(props, button, counter));
            }

            return button;
        },

        upvoteMessage(props, button, counter) {
            if (button.disabled) return;
            button.disabled = true;

            ClubApi.postForm(props.upvote_url, {}, (data) => {
                if (data.error) {
                    button.disabled = false;
                    button.title = data.error;
                    return;
                }

                counter.innerText = data.upvotes;
                button.classList.add("people-map-message-upvote-counted");
                button.title = "Вы уже проголосовали";
                this.rememberUpvote(props.id, data.upvotes);
            });
        },

        // markers are rebuilt from the source on every zoom change, so the vote has to
        // land in the geojson too, otherwise the button comes back active
        rememberUpvote(id, upvotes) {
            const feature = this.messagesGeojson.features.find((f) => f.properties.id === id);
            if (!feature) return;

            feature.properties.upvotes = upvotes;
            feature.properties.is_voted = true;

            const source = this.map.getSource(MESSAGES_SOURCE);
            if (source) {
                source.setData(this.messagesGeojson);
            }
        },

        toggleComposeMode() {
            if (!this.postingAllowed) return;

            this.composeMode = !this.composeMode;
            this.applyComposeCursor();

            if (!this.composeMode) {
                this.cancelDraft();
            }
        },

        applyComposeCursor() {
            const canvas = this.map && this.map.getCanvas && this.map.getCanvas();
            if (canvas) {
                canvas.style.cursor = this.composeMode ? "crosshair" : "";
            }
        },

        onMapClick(e) {
            if (!this.composeMode) return;

            this.composeMode = false;
            this.applyComposeCursor();
            this.openDraft(e.lngLat);
        },

        openDraft(lngLat) {
            this.draft = { latitude: lngLat.lat, longitude: lngLat.lng };
            this.draftText = "";
            this.draftError = null;

            if (!this.composeMarker) {
                this.composeMarker = new mapboxgl.Marker({ element: this.$refs.composeBubble, anchor: "bottom" });
            }
            this.composeMarker.setLngLat([lngLat.lng, lngLat.lat]).addTo(this.map);
            this.panDraftIntoView(lngLat);

            this.$nextTick(() => {
                if (this.$refs.composeInput) this.$refs.composeInput.focus();
            });

            // the click that opened the bubble is still propagating towards the document,
            // so the listener has to wait for the next task to not close it right away
            this.closeDraftTimer = setTimeout(() => {
                document.addEventListener("click", this.onDocumentClick);
            }, 0);
        },

        onDocumentClick(e) {
            const bubble = this.$refs.composeBubble;
            if (bubble && bubble.contains(e.target)) return;

            this.cancelDraft();
        },

        // the filter sidebar and the search row are laid out on top of the map, so a bubble
        // opened under them would be unreachable. move the point into the free area instead
        panDraftIntoView(lngLat) {
            const container = this.map.getContainer && this.map.getContainer();
            const isWide = container && container.offsetWidth > 700;

            this.map.easeTo({
                center: [lngLat.lng, lngLat.lat],
                offset: isWide ? [160, 140] : [0, 120],
                duration: 400,
            });
        },

        cancelDraft() {
            this.draft = null;
            this.draftText = "";
            this.draftError = null;

            clearTimeout(this.closeDraftTimer);
            document.removeEventListener("click", this.onDocumentClick);

            if (this.composeMarker) {
                this.composeMarker.remove();
            }
        },

        saveDraft() {
            if (!this.canSaveDraft) return;

            this.isSaving = true;
            this.draftError = null;

            const payload = {
                text: this.draftText.trim(),
                latitude: this.draft.latitude,
                longitude: this.draft.longitude,
            };

            ClubApi.postForm(this.createMessageUrl, payload, (data) => {
                this.isSaving = false;

                if (data.error) {
                    this.draftError = data.error;
                    return;
                }

                this.appendMessage(data.feature);
                if (data.can_post === false) {
                    this.postingAllowed = false;
                }
                this.cancelDraft();
            });
        },

        appendMessage(feature) {
            if (!feature) return;

            this.messagesGeojson.features.push(feature);

            const source = this.map.getSource(MESSAGES_SOURCE);
            if (source) {
                source.setData(this.messagesGeojson);
            }
        },
    },
};
</script>
