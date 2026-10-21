import { Component, createRef } from "react";
import { createPortal } from "react-dom";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import ClubApi from "../lib/api.service";
import { pluralize } from "../lib/utils";

const MESSAGES_SOURCE = "messagesGeojson";
const MESSAGES_CLUSTER_RADIUS = 40;
const MESSAGE_TEXT_MIN_ZOOM = 10;
const ROOM_MARKER_LARGE_ZOOM = 4;
const CAMERA_ANIMATION_MS = 200;

export default class PeopleMap extends Component {
    mapContainer = createRef();
    composeInput = createRef();
    state = {
        postingAllowed: this.props.canPostMessage !== false,
        composeMode: false,
        draft: null,
        draftText: "",
        draftError: null,
        isSaving: false,
        mapError: null,
    };
    defaultAvatar = "https://i.vas3k.club/v.png";
    messageMarkers = {};
    messageMarkersOnScreen = {};

    componentDidMount() {
        this.disposed = false;
        this.usersGeojson = this.parseFeatureCollection(this.props.geojson);
        this.messagesGeojson = this.parseFeatureCollection(this.props.messages);
        this.roomsGeojson = this.parseFeatureCollection(this.props.rooms);
        this.composeElement = document.createElement("div");
        this.composeElement.className = "people-map-message people-map-message-compose";
        try {
            this.map = new mapboxgl.Map({
                container: this.mapContainer.current,
                accessToken: "pk.eyJ1IjoidmFzM2siLCJhIjoiY2thZ254NXVwMDhkbjJ5dDk5eGh5Y21wbyJ9.wYXG58PrErQfRHTflvdSfA",
                style: "mapbox://styles/vas3k/ckagmhzm90tkd1inu8pg76p9s/draft",
                maxZoom: 16,
                attributionControl: false,
                scrollZoom: true,
                dragPan: true,
                touchZoomRotate: true,
            });
            this.map.addControl(new mapboxgl.NavigationControl(), "top-right");
            this.map.addControl(new mapboxgl.GeolocateControl(), "top-right");
            this.map.on("load", this.onMapLoaded);
            this.map.on("error", (event) => console.error("Mapbox:", event.error));
        } catch (error) {
            this.setState({ mapError: error.message });
        }
    }

    componentWillUnmount() {
        this.disposed = true;
        clearTimeout(this.closeDraftTimer);
        document.removeEventListener("click", this.onDocumentClick);
        this.composeMarker?.remove();
        this.map?.remove();
    }

    render() {
        const { editProfileUrl, createMessageUrl, maxMessageLength = 128 } = this.props;
        const { postingAllowed, composeMode, draft, draftText, draftError, isSaving, mapError } = this.state;
        return (
            <div className="people-map-root people-map-container">
                <div ref={this.mapContainer} className="people-map-gl" />
                {mapError && <div role="alert">Не удалось загрузить карту: {mapError}</div>}
                <div className="people-map-buttons">
                    {editProfileUrl && (
                        <a href={editProfileUrl} className="button">
                            📍 Передвинуть себя
                        </a>
                    )}
                    {createMessageUrl && (
                        <button
                            type="button"
                            className={`button people-map-compose-button ${
                                composeMode ? "people-map-compose-button-active" : ""
                            }`}
                            disabled={!postingAllowed || Boolean(mapError)}
                            onClick={this.toggleComposeMode}
                        >
                            {!postingAllowed
                                ? "⏳ Подождите 24 часа"
                                : composeMode
                                ? "✖️ Отменить"
                                : "💬 Оставить сообщение"}
                        </button>
                    )}
                </div>
                {draft &&
                    createPortal(
                        <>
                            <textarea
                                ref={this.composeInput}
                                className="people-map-message-input"
                                maxLength={maxMessageLength}
                                placeholder="Что здесь интересного?"
                                value={draftText}
                                onChange={(event) => this.setState({ draftText: event.target.value })}
                            />
                            {draftError && (
                                <div role="alert" className="people-map-message-error">
                                    {draftError}
                                </div>
                            )}
                            <div className="people-map-message-footer">
                                <button
                                    type="button"
                                    className="button people-map-message-save"
                                    disabled={!draftText.trim() || isSaving}
                                    onClick={this.saveDraft}
                                >
                                    {isSaving ? "..." : "Написать тут"}
                                </button>
                            </div>
                        </>,
                        this.composeElement
                    )}
            </div>
        );
    }

    onMapLoaded = () => {
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
                const id = props.cluster ? `cluster-${props.cluster_id}` : props.id;

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
                            map.flyTo({
                                center: coords,
                                zoom: map.getZoom() + 2,
                                offset: map.getContainer().offsetWidth > 700 ? [200, 0] : [0, 0],
                                duration: CAMERA_ANIMATION_MS,
                            });
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

        if (this.props.messages || this.props.createMessageUrl) {
            this.setupMessages();
        }
        this.setupRooms();
    };

    parseFeatureCollection = (value) => {
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
    };

    setupRooms = () => {
        const markers = this.roomsGeojson;
        if (!markers.features.length) return;

        this.roomMarkerElements = markers.features.map((feature) => {
            const element = this.createRoomMarker(feature.properties);
            new mapboxgl.Marker({ element: element }).setLngLat(feature.geometry.coordinates).addTo(this.map);
            return element;
        });
        this.applyRoomMarkerSize();
        this.map.on("zoom", () => this.applyRoomMarkerSize());
    };

    applyRoomMarkerSize = () => {
        if (!this.roomMarkerElements) return;

        const compact = this.map.getZoom() < ROOM_MARKER_LARGE_ZOOM;
        this.roomMarkerElements.forEach((element) => {
            element.classList.toggle("people-map-room-marker-compact", compact);
        });
    };

    createRoomMarker = (props) => {
        const element = document.createElement(props.url ? "a" : "div");
        element.classList.add("people-map-room-marker");
        if (props.url) {
            element.href = props.url;
            element.target = "_blank";
            element.rel = "noreferrer";
        }
        element.title = props.title || "";
        element.style.color = props.color || "#333333";

        if (props.image) {
            element.style.backgroundImage = "url(" + JSON.stringify(props.image) + ")";
        } else if (props.icon) {
            element.classList.add("people-map-room-marker-icon");
            element.innerText = props.icon;
        }

        const label = document.createElement("span");
        label.classList.add("people-map-room-label");
        const name = props.title || "";
        const count = parseInt(props.member_count, 10) || 0;
        label.innerText =
            count > 0
                ? "Чат " + name + " ・ " + count + " " + pluralize(count, ["человек", "человека", "человек"])
                : "Чат " + name;
        element.appendChild(label);

        return element;
    };

    setupMessages = () => {
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
    };

    updateMessageMarkers = () => {
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
    };

    createMessageClusterElement = (props, coords) => {
        const element = document.createElement("div");
        element.classList.add("people-map-message", "people-map-message-cluster");
        element.innerText = "💬 " + props.point_count;
        element.addEventListener("click", () => {
            this.map.flyTo({
                center: coords,
                zoom: this.map.getZoom() + 2,
                duration: CAMERA_ANIMATION_MS,
            });
        });
        return element;
    };

    createMessageElement = (props, coords, withText) => {
        const element = document.createElement("div");
        element.classList.add("people-map-message");

        if (!withText) {
            element.classList.add("people-map-message-icon");
            element.innerText = "💬";
            element.title = props.author_name || "";
            element.addEventListener("click", () => {
                this.map.flyTo({
                    center: coords,
                    zoom: MESSAGE_TEXT_MIN_ZOOM,
                    duration: CAMERA_ANIMATION_MS,
                });
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
    };

    createUpvoteElement = (props) => {
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
    };

    upvoteMessage = async (props, button, counter) => {
        if (button.disabled) return;
        button.disabled = true;
        try {
            const data = await ClubApi.post(props.upvote_url);
            if (this.disposed) return;
            counter.innerText = data.upvotes;
            button.classList.add("people-map-message-upvote-counted");
            button.title = "Вы уже проголосовали";
            this.rememberUpvote(props.id, data.upvotes);
        } catch (error) {
            if (this.disposed) return;
            button.disabled = false;
            button.title = error.message;
        }
    };

    // markers are rebuilt from the source on every zoom change, so the vote has to
    // land in the geojson too, otherwise the button comes back active
    rememberUpvote = (id, upvotes) => {
        const feature = this.messagesGeojson.features.find((f) => f.properties.id === id);
        if (!feature) return;

        feature.properties.upvotes = upvotes;
        feature.properties.is_voted = true;
        for (const key of Object.keys(this.messageMarkers)) {
            if (key.startsWith(`${id}:`)) {
                this.messageMarkers[key].remove();
                delete this.messageMarkers[key];
                delete this.messageMarkersOnScreen[key];
            }
        }

        const source = this.map.getSource(MESSAGES_SOURCE);
        if (source) {
            source.setData(this.messagesGeojson);
        }
    };

    toggleComposeMode = () => {
        if (!this.state.postingAllowed) return;
        this.cancelDraft();
        this.setState(({ composeMode }) => ({ composeMode: !composeMode }), this.applyComposeCursor);
    };

    applyComposeCursor = () => {
        this.map.getCanvas().style.cursor = this.state.composeMode ? "crosshair" : "";
    };

    onMapClick = (event) => {
        if (!this.state.composeMode) return;
        const { lat, lng } = event.lngLat;
        this.setState(
            { composeMode: false, draft: { latitude: lat, longitude: lng }, draftText: "", draftError: null },
            () => {
                this.applyComposeCursor();
                if (!this.composeMarker)
                    this.composeMarker = new mapboxgl.Marker({ element: this.composeElement, anchor: "bottom" });
                this.composeMarker.setLngLat([lng, lat]).addTo(this.map);
                this.map.easeTo({
                    center: [lng, lat],
                    offset: this.map.getContainer().offsetWidth > 700 ? [160, 140] : [0, 120],
                    duration: CAMERA_ANIMATION_MS,
                });
                this.composeInput.current?.focus();
                this.closeDraftTimer = setTimeout(() => document.addEventListener("click", this.onDocumentClick), 0);
            }
        );
    };

    onDocumentClick = (event) => {
        if (!this.composeElement.contains(event.target)) this.cancelDraft();
    };

    cancelDraft = () => {
        clearTimeout(this.closeDraftTimer);
        document.removeEventListener("click", this.onDocumentClick);
        this.composeMarker?.remove();
        this.setState({ draft: null, draftText: "", draftError: null });
    };

    saveDraft = async () => {
        const { draft, draftText, isSaving } = this.state;
        if (!draft || !draftText.trim() || isSaving) return;
        this.setState({ isSaving: true, draftError: null });
        try {
            const data = await ClubApi.postForm(this.props.createMessageUrl, { ...draft, text: draftText.trim() });
            if (this.disposed) return;
            this.appendMessage(data.feature);
            if (data.can_post === false) this.setState({ postingAllowed: false });
            this.cancelDraft();
        } catch (error) {
            if (!this.disposed) this.setState({ draftError: error.message });
        } finally {
            if (!this.disposed) this.setState({ isSaving: false });
        }
    };

    appendMessage = (feature) => {
        if (!feature) return;

        this.messagesGeojson.features.push(feature);

        const source = this.map.getSource(MESSAGES_SOURCE);
        if (source) {
            source.setData(this.messagesGeojson);
        }
    };
}
