const mockMarkerInstance = {
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
};

const mockCanvas = { style: {} };
const mockContainer = { offsetWidth: 1200 };
const mockSource = { setData: jest.fn() };

const mockMap = {
    addSource: jest.fn(),
    addLayer: jest.fn(),
    addControl: jest.fn(),
    querySourceFeatures: jest.fn().mockReturnValue([]),
    project: jest.fn((coords) => ({ x: coords[0], y: coords[1] })),
    getZoom: jest.fn().mockReturnValue(5),
    getCanvas: jest.fn(() => mockCanvas),
    getContainer: jest.fn(() => mockContainer),
    getSource: jest.fn(() => mockSource),
    flyTo: jest.fn(),
    easeTo: jest.fn(),
    on: jest.fn(),
    remove: jest.fn(),
};

jest.mock("../common/api.service", () => ({
    __esModule: true,
    default: { get: jest.fn(), post: jest.fn(), postForm: jest.fn() },
}));

jest.mock("mapbox-gl", () => ({
    __esModule: true,
    default: {
        Map: jest.fn(() => mockMap),
        Marker: jest.fn(() => mockMarkerInstance),
        NavigationControl: jest.fn(),
        GeolocateControl: jest.fn(),
        accessToken: null,
    },
}));

import { shallowMount } from "@vue/test-utils";
import PeopleMap from "../components/PeopleMap.vue";

function makeGeojson(features) {
    return {
        type: "FeatureCollection",
        features: features.map((f, i) => ({
            type: "Feature",
            geometry: { type: "Point", coordinates: f.coords },
            properties: { id: f.id || `user-${i}`, avatar: f.avatar || null, url: f.url || "/u/test" },
        })),
    };
}

function getHandler(eventName) {
    var call = mockMap.on.mock.calls.find(([e]) => e === eventName);
    return call ? call[1] : null;
}

function fireDataEvent(sourceId, isSourceLoaded) {
    var handler = getHandler("data");
    handler({ sourceId: sourceId || "usersGeojson", isSourceLoaded: isSourceLoaded !== false });
}

describe("PeopleMap.vue", () => {
    let wrapper;

    beforeEach(() => {
        jest.clearAllMocks();
        mockMarkerInstance.setLngLat.mockReturnThis();
        mockMarkerInstance.addTo.mockReturnThis();
    });

    afterEach(() => {
        if (wrapper) wrapper.destroy();
    });

    function mountMap(geojson) {
        wrapper = shallowMount(PeopleMap, {
            propsData: { geojson },
            stubs: { default: true },
        });
        // Simulate map load: the "load" callback is registered via map.on("load", ...)
        var loadCall = mockMap.on.mock.calls.find(([e]) => e === "load");
        if (loadCall) loadCall[1]();
    }

    describe("map initialization", () => {
        it("creates a mapbox-gl Map and adds controls", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            var mapboxgl = require("mapbox-gl").default;
            expect(mapboxgl.Map).toHaveBeenCalledTimes(1);
            expect(mockMap.addControl).toHaveBeenCalledTimes(2);
        });

        it("adds clustered geojson source and transparent circle layer", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            expect(mockMap.addSource).toHaveBeenCalledWith("usersGeojson", expect.objectContaining({
                type: "geojson",
                cluster: true,
                clusterRadius: 25,
            }));
            expect(mockMap.addLayer).toHaveBeenCalledWith(expect.objectContaining({
                id: "users",
                source: "usersGeojson",
            }));
        });

        it("accepts geojson as a json string", () => {
            mountMap(JSON.stringify(makeGeojson([{ coords: [10, 20] }])));

            expect(mockMap.addSource).toHaveBeenCalledWith("usersGeojson", expect.objectContaining({
                type: "geojson",
            }));
        });
    });

    describe("event handling", () => {
        it("registers move, moveend and data event handlers", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            var onCalls = mockMap.on.mock.calls;
            expect(onCalls.filter(([e]) => e === "move")).toHaveLength(1);
            expect(onCalls.filter(([e]) => e === "moveend")).toHaveLength(1);
            expect(onCalls.filter(([e]) => e === "data")).toHaveLength(1);
        });

        it("handler count stays constant regardless of how many data events fire", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            var initialCount = mockMap.on.mock.calls.length;

            fireDataEvent();
            fireDataEvent();
            fireDataEvent();

            expect(mockMap.on.mock.calls.length).toBe(initialCount);
        });

        it("ignores data events from other sources", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            mockMap.querySourceFeatures.mockClear();

            fireDataEvent("otherSource", true);

            expect(mockMap.querySourceFeatures).not.toHaveBeenCalled();
        });

        it("ignores data events when source is not yet loaded", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            mockMap.querySourceFeatures.mockClear();

            fireDataEvent("usersGeojson", false);

            expect(mockMap.querySourceFeatures).not.toHaveBeenCalled();
        });
    });

    describe("individual markers", () => {
        it("creates a link element with user avatar and url", () => {
            var geojson = makeGeojson([{ coords: [10, 20], avatar: "https://example.com/a.jpg", url: "/u/alice" }]);
            var feature = {
                geometry: { coordinates: [10, 20] },
                properties: { id: "u1", avatar: "https://example.com/a.jpg", url: "/u/alice" },
            };
            mockMap.querySourceFeatures.mockReturnValue([feature]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.tagName).toBe("A");
            expect(el.href).toContain("/u/alice");
            expect(el.classList.contains("people-map-user-marker")).toBe(true);
            expect(el.style.backgroundImage).toContain("a.jpg");
        });

        it("uses default avatar for users without avatar", () => {
            var feature = {
                geometry: { coordinates: [10, 20] },
                properties: { id: "u1", avatar: null, url: "/u/bob" },
            };
            mockMap.querySourceFeatures.mockReturnValue([feature]);
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.style.backgroundImage).toContain("v.png");
        });
    });

    describe("cluster markers", () => {
        it("creates a div with point count and nearby user avatar", () => {
            var geojson = makeGeojson([
                { coords: [10, 20], avatar: "https://example.com/nearby.jpg", id: "u1" },
            ]);
            var cluster = {
                geometry: { coordinates: [10.5, 20.5] },
                properties: { cluster: true, cluster_id: "c1", point_count: 3 },
            };
            mockMap.querySourceFeatures.mockReturnValue([cluster]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.tagName).toBe("DIV");
            expect(el.classList.contains("people-map-user-cluster")).toBe(true);
            expect(el.innerText).toBe(3);
            expect(el.style.backgroundImage).toContain("nearby.jpg");
        });

        it("selects avatar of the nearest feature within pixel threshold", () => {
            var geojson = makeGeojson([
                { coords: [10, 20], avatar: "https://example.com/nearby.jpg", id: "u1" },
                { coords: [100, 200], avatar: "https://example.com/far.jpg", id: "u2" },
            ]);
            var cluster = {
                geometry: { coordinates: [10.5, 20.5] },
                properties: { cluster: true, cluster_id: "c1", point_count: 2 },
            };
            mockMap.querySourceFeatures.mockReturnValue([cluster]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.style.backgroundImage).toContain("nearby.jpg");
        });

        it("falls back to default avatar when no feature is within pixel threshold", () => {
            var geojson = makeGeojson([
                { coords: [100, 200], avatar: "https://example.com/far.jpg", id: "u1" },
            ]);
            var cluster = {
                geometry: { coordinates: [10, 20] },
                properties: { cluster: true, cluster_id: "c1", point_count: 1 },
            };
            mockMap.querySourceFeatures.mockReturnValue([cluster]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.style.backgroundImage).toContain("v.png");
        });

        it("ignores features with null or 'null' avatars when selecting cluster avatar", () => {
            var geojson = makeGeojson([
                { coords: [10, 20], avatar: null, id: "u1" },
                { coords: [10.1, 20.1], avatar: "null", id: "u2" },
                { coords: [100, 200], avatar: "https://example.com/real.jpg", id: "u3" },
            ]);
            var cluster = {
                geometry: { coordinates: [10, 20] },
                properties: { cluster: true, cluster_id: "c1", point_count: 3 },
            };
            mockMap.querySourceFeatures.mockReturnValue([cluster]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.style.backgroundImage).toContain("v.png");
        });

        it("uses map.project() linearly — once per feature + once per cluster", () => {
            var features = [
                { coords: [10, 20], avatar: "https://example.com/a.jpg", id: "u1" },
                { coords: [11, 21], avatar: "https://example.com/b.jpg", id: "u2" },
                { coords: [12, 22], avatar: "https://example.com/c.jpg", id: "u3" },
                { coords: [30, 40], avatar: "https://example.com/d.jpg", id: "u4" },
                { coords: [31, 41], avatar: "https://example.com/e.jpg", id: "u5" },
            ];
            var clusters = [
                {
                    geometry: { coordinates: [10.5, 20.5] },
                    properties: { cluster: true, cluster_id: "c1", point_count: 3 },
                },
                {
                    geometry: { coordinates: [30.5, 40.5] },
                    properties: { cluster: true, cluster_id: "c2", point_count: 2 },
                },
            ];
            mockMap.querySourceFeatures.mockReturnValue(clusters);
            mountMap(makeGeojson(features));
            mockMap.project.mockClear();

            fireDataEvent();

            var expected = features.filter((f) => f.avatar).length + clusters.length;
            expect(mockMap.project).toHaveBeenCalledTimes(expected);
        });

        it("flies to cluster location on click", () => {
            var geojson = makeGeojson([{ coords: [10, 20], avatar: "https://example.com/a.jpg" }]);
            var cluster = {
                geometry: { coordinates: [15, 25] },
                properties: { cluster: true, cluster_id: "c1", point_count: 2 },
            };
            mockMap.querySourceFeatures.mockReturnValue([cluster]);
            mountMap(geojson);
            fireDataEvent();

            var MarkerCtor = require("mapbox-gl").default.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            el.click();

            expect(mockMap.flyTo).toHaveBeenCalledWith(expect.objectContaining({
                center: [15, 25],
            }));
        });
    });

    describe("marker lifecycle", () => {
        it("adds new markers to the map", () => {
            var feature = {
                geometry: { coordinates: [10, 20] },
                properties: { id: "u1", url: "/u/test" },
            };
            mockMap.querySourceFeatures.mockReturnValue([feature]);
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            fireDataEvent();

            expect(mockMarkerInstance.addTo).toHaveBeenCalledWith(mockMap);
        });

        it("removes markers that are no longer visible", () => {
            var feature1 = {
                geometry: { coordinates: [10, 20] },
                properties: { id: "u1", url: "/u/test" },
            };
            mockMap.querySourceFeatures.mockReturnValue([feature1]);
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            fireDataEvent();

            mockMap.querySourceFeatures.mockReturnValue([]);
            fireDataEvent();

            expect(mockMarkerInstance.remove).toHaveBeenCalled();
        });

        it("reuses existing markers instead of creating duplicates", () => {
            var feature = {
                geometry: { coordinates: [10, 20] },
                properties: { id: "u1", url: "/u/test" },
            };
            mockMap.querySourceFeatures.mockReturnValue([feature]);
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            var MarkerCtor = require("mapbox-gl").default.Marker;
            fireDataEvent();
            var countAfterFirst = MarkerCtor.mock.calls.length;

            fireDataEvent();
            expect(MarkerCtor.mock.calls.length).toBe(countAfterFirst);
        });
    });

    describe("cleanup", () => {
        it("calls map.remove() on destroy", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            wrapper.destroy();

            expect(mockMap.remove).toHaveBeenCalled();
            wrapper = null; // prevent double destroy in afterEach
        });
    });

    describe("map messages", () => {
        var ClubApi = require("../common/api.service").default;

        function makeMessages(messages) {
            return JSON.stringify({
                type: "FeatureCollection",
                features: messages.map((m, i) => ({
                    type: "Feature",
                    geometry: { type: "Point", coordinates: m.coords || [10, 20] },
                    properties: {
                        id: m.id || `message-${i}`,
                        text: m.text || "hello",
                        author_name: m.authorName || "Alice",
                        author_url: m.authorUrl || "/user/alice/",
                        author_avatar: m.authorAvatar || "https://example.com/alice.jpg",
                        upvotes: m.upvotes || 0,
                        upvote_url: m.upvoteUrl || `/map/messages/message-${i}/upvote.json`,
                        is_voted: m.isVoted || false,
                        is_mine: m.isMine || false,
                    },
                })),
            });
        }

        function zoomedInMessage(properties) {
            mockMap.getZoom.mockReturnValue(10);
            mockMap.querySourceFeatures.mockReturnValue([{
                geometry: { coordinates: [10, 20] },
                properties: Object.assign({
                    id: "m1",
                    text: "hi",
                    author_url: "/user/alice/",
                    upvotes: 0,
                    upvote_url: "/map/messages/m1/upvote.json",
                }, properties),
            }]);
            mountMapWithMessages(makeMessages([{ id: "m1", text: "hi" }]));
            fireDataEvent("messagesGeojson");
            return lastMarkerElement();
        }

        function mountMapWithMessages(messages) {
            wrapper = shallowMount(PeopleMap, {
                propsData: {
                    geojson: makeGeojson([]),
                    messages: messages,
                    createMessageUrl: "/map/messages/create.json",
                    editProfileUrl: "/user/me/edit/profile/#map-location",
                    maxMessageLength: 128,
                },
                stubs: { default: true },
            });
            var loadCall = mockMap.on.mock.calls.find(([e]) => e === "load");
            if (loadCall) loadCall[1]();
        }

        function lastMarkerElement() {
            var MarkerCtor = require("mapbox-gl").default.Marker;
            var calls = MarkerCtor.mock.calls;
            return calls[calls.length - 1][0].element;
        }

        beforeEach(() => {
            mockMap.getZoom.mockReturnValue(5);
            mockMap.querySourceFeatures.mockReturnValue([]);
            mockCanvas.style = {};
        });

        it("adds a clustered messages source when the feature is enabled", () => {
            mountMapWithMessages(makeMessages([{ text: "hi" }]));

            expect(mockMap.addSource).toHaveBeenCalledWith("messagesGeojson", expect.objectContaining({
                type: "geojson",
                cluster: true,
            }));
        });

        it("does not touch the messages source when the feature is disabled", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            expect(mockMap.addSource).not.toHaveBeenCalledWith("messagesGeojson", expect.anything());

            // the shared move handler must stay harmless without a messages source
            getHandler("move")();
            expect(mockMap.querySourceFeatures).not.toHaveBeenCalledWith("messagesGeojson");
        });

        it("shows only an icon when zoomed out further than the city level", () => {
            mockMap.querySourceFeatures.mockReturnValue([{
                geometry: { coordinates: [10, 20] },
                properties: { id: "m1", text: "secret plans", author_name: "Alice" },
            }]);
            mountMapWithMessages(makeMessages([{ text: "secret plans" }]));

            fireDataEvent("messagesGeojson");

            var el = lastMarkerElement();
            expect(el.classList.contains("people-map-message-icon")).toBe(true);
            expect(el.innerText).not.toContain("secret plans");
        });

        it("shows the full bubble with the avatar and text when zoomed in", () => {
            mockMap.getZoom.mockReturnValue(10);
            mockMap.querySourceFeatures.mockReturnValue([{
                geometry: { coordinates: [10, 20] },
                properties: {
                    id: "m1",
                    text: "secret plans",
                    author_name: "Alice",
                    author_url: "/user/alice/",
                    author_avatar: "https://example.com/alice.jpg",
                },
            }]);
            mountMapWithMessages(makeMessages([{ text: "secret plans" }]));

            fireDataEvent("messagesGeojson");

            var el = lastMarkerElement();
            expect(el.classList.contains("people-map-message-full")).toBe(true);
            expect(el.querySelector(".people-map-message-body").innerText).toBe("secret plans");

            // the name is not rendered, the avatar alone links to the profile
            var author = el.querySelector(".people-map-message-author");
            expect(author.href).toContain("/user/alice/");
            expect(author.title).toBe("Alice");
            expect(author.textContent).toBe("");
            expect(author.querySelectorAll(".people-map-message-avatar")).toHaveLength(1);
        });

        it("rebuilds markers when zoom crosses the text threshold", () => {
            mockMap.querySourceFeatures.mockReturnValue([{
                geometry: { coordinates: [10, 20] },
                properties: { id: "m1", text: "hi", author_name: "Alice", author_url: "/user/alice/" },
            }]);
            mountMapWithMessages(makeMessages([{ text: "hi" }]));
            fireDataEvent("messagesGeojson");
            expect(lastMarkerElement().classList.contains("people-map-message-icon")).toBe(true);

            mockMap.getZoom.mockReturnValue(10);
            fireDataEvent("messagesGeojson");

            expect(lastMarkerElement().classList.contains("people-map-message-full")).toBe(true);
        });

        it("renders message clusters with a counter and zooms in on click", () => {
            mockMap.querySourceFeatures.mockReturnValue([{
                geometry: { coordinates: [15, 25] },
                properties: { cluster: true, cluster_id: "c1", point_count: 7 },
            }]);
            mountMapWithMessages(makeMessages([{ text: "hi" }]));

            fireDataEvent("messagesGeojson");

            var el = lastMarkerElement();
            expect(el.classList.contains("people-map-message-cluster")).toBe(true);
            expect(el.innerText).toContain("7");

            el.click();
            expect(mockMap.flyTo).toHaveBeenCalledWith(expect.objectContaining({ center: [15, 25] }));
        });

        it("upvotes a message once and shows the count returned by the server", () => {
            var el = zoomedInMessage({ upvotes: 3 });
            var button = el.querySelector(".people-map-message-upvote");
            var counter = el.querySelector(".people-map-message-upvotes");

            expect(button.disabled).toBe(false);
            expect(counter.innerText).toBe(3);

            ClubApi.postForm.mockImplementation((url, payload, callback) => callback({ upvotes: 4 }));
            button.click();

            expect(ClubApi.postForm).toHaveBeenCalledWith(
                "/map/messages/m1/upvote.json", {}, expect.any(Function)
            );
            expect(counter.innerText).toBe(4);
            expect(button.disabled).toBe(true);
            expect(button.classList.contains("people-map-message-upvote-counted")).toBe(true);

            // a second click can not happen, the vote is final
            button.click();
            expect(ClubApi.postForm).toHaveBeenCalledTimes(1);
        });

        it("keeps the vote in the geojson so rebuilt markers stay voted", () => {
            var el = zoomedInMessage({ upvotes: 1 });
            ClubApi.postForm.mockImplementation((url, payload, callback) => callback({ upvotes: 2 }));

            el.querySelector(".people-map-message-upvote").click();

            expect(mockSource.setData).toHaveBeenCalledWith(expect.objectContaining({
                features: [expect.objectContaining({
                    properties: expect.objectContaining({ id: "m1", upvotes: 2, is_voted: true }),
                })],
            }));
        });

        it("re-enables the button when the vote fails", () => {
            var el = zoomedInMessage({ upvotes: 0 });
            var button = el.querySelector(".people-map-message-upvote");
            ClubApi.postForm.mockImplementation((url, payload, callback) => callback({ error: "Нельзя" }));

            button.click();

            expect(button.disabled).toBe(false);
            expect(button.title).toBe("Нельзя");
        });

        it("does not let a user vote for the same message twice", () => {
            var el = zoomedInMessage({ is_voted: true, upvotes: 2 });
            var button = el.querySelector(".people-map-message-upvote");

            expect(button.disabled).toBe(true);
            expect(el.querySelector(".people-map-message-upvotes").innerText).toBe(2);

            button.click();
            expect(ClubApi.postForm).not.toHaveBeenCalled();
        });

        it("does not let a user vote for their own message", () => {
            var el = zoomedInMessage({ is_mine: true, upvotes: 2 });
            var button = el.querySelector(".people-map-message-upvote");

            expect(button.disabled).toBe(true);
            expect(button.title).toContain("свои сообщения");
            expect(el.querySelector(".people-map-message-upvotes").innerText).toBe(2);

            button.click();
            expect(ClubApi.postForm).not.toHaveBeenCalled();
        });

        it("hides the button on own messages nobody voted for yet", () => {
            var el = zoomedInMessage({ is_mine: true, upvotes: 0 });

            expect(el.querySelector(".people-map-message-upvote")).toBe(null);
        });

        it("links to the profile settings anchor only when the url is given", () => {
            mountMapWithMessages(makeMessages([]));
            var link = wrapper.find(".people-map-buttons a");
            expect(link.attributes("href")).toBe("/user/me/edit/profile/#map-location");
            expect(link.text()).toContain("Передвинуть себя");

            wrapper.destroy();
            wrapper = shallowMount(PeopleMap, {
                propsData: { geojson: makeGeojson([]) },
                stubs: { default: true },
            });
            expect(wrapper.find(".people-map-buttons a").exists()).toBe(false);
        });

        it("disables the compose button while the author is on the daily cooldown", () => {
            mountMapWithMessages(makeMessages([]));
            expect(wrapper.find(".people-map-compose-button").attributes("disabled")).toBeFalsy();

            wrapper.destroy();
            wrapper = shallowMount(PeopleMap, {
                propsData: {
                    geojson: makeGeojson([]),
                    createMessageUrl: "/map/messages/create.json",
                    canPostMessage: false,
                },
                stubs: { default: true },
            });

            var button = wrapper.find(".people-map-compose-button");
            expect(button.attributes("disabled")).toBeTruthy();
            expect(button.text()).toContain("Подождите 24 часа");
            expect(button.text()).not.toContain("Оставить сообщение");

            wrapper.vm.toggleComposeMode();
            expect(wrapper.vm.composeMode).toBe(false);
        });

        it("switches the map cursor to a crosshair while composing", () => {
            mountMapWithMessages(makeMessages([]));

            wrapper.vm.toggleComposeMode();
            expect(mockCanvas.style.cursor).toBe("crosshair");

            wrapper.vm.toggleComposeMode();
            expect(mockCanvas.style.cursor).toBe("");
        });

        it("ignores map clicks until compose mode is activated", () => {
            mountMapWithMessages(makeMessages([]));

            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });
            expect(wrapper.vm.draft).toBe(null);

            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });

            expect(wrapper.vm.draft).toEqual({ latitude: 1, longitude: 2 });
            expect(wrapper.vm.composeMode).toBe(false);
            expect(mockCanvas.style.cursor).toBe("");
        });

        it("pans the clicked point out from under the overlaying sidebar", () => {
            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();

            wrapper.vm.onMapClick({ lngLat: { lat: 52.5, lng: 13.4 } });

            expect(mockMap.easeTo).toHaveBeenCalledWith(expect.objectContaining({
                center: [13.4, 52.5],
                offset: [160, 140],
            }));
        });

        it("closes the draft on a click outside of the bubble and keeps it on a click inside", () => {
            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });

            wrapper.vm.onDocumentClick({ target: wrapper.vm.$refs.composeBubble });
            expect(wrapper.vm.draft).not.toBe(null);

            wrapper.vm.onDocumentClick({ target: document.body });
            expect(wrapper.vm.draft).toBe(null);
        });

        it("listens for outside clicks only while a draft is open", () => {
            jest.useFakeTimers();
            var add = jest.spyOn(document, "addEventListener");
            var remove = jest.spyOn(document, "removeEventListener");

            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });

            // the opening click must not reach the listener that closes the bubble
            expect(add).not.toHaveBeenCalledWith("click", wrapper.vm.onDocumentClick);
            jest.runAllTimers();
            expect(add).toHaveBeenCalledWith("click", wrapper.vm.onDocumentClick);

            wrapper.vm.cancelDraft();
            expect(remove).toHaveBeenCalledWith("click", wrapper.vm.onDocumentClick);

            add.mockRestore();
            remove.mockRestore();
            jest.useRealTimers();
        });

        it("posts the draft and adds the created message to the source", () => {
            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 52.5, lng: 13.4 } });
            wrapper.vm.draftText = "  hello map  ";

            var newFeature = {
                type: "Feature",
                geometry: { coordinates: [13.4, 52.5] },
                properties: { id: "new", text: "hello map" },
            };
            ClubApi.postForm.mockImplementation((url, payload, callback) => callback({
                feature: newFeature,
                can_post: false,
            }));

            wrapper.vm.saveDraft();

            expect(ClubApi.postForm).toHaveBeenCalledWith(
                "/map/messages/create.json",
                { text: "hello map", latitude: 52.5, longitude: 13.4 },
                expect.any(Function)
            );
            expect(mockSource.setData).toHaveBeenCalledWith(
                expect.objectContaining({ features: [newFeature] })
            );
            expect(wrapper.vm.draft).toBe(null);
            expect(wrapper.vm.postingAllowed).toBe(false);
        });

        it("keeps the draft and shows the error when saving fails", () => {
            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });
            wrapper.vm.draftText = "hello";

            ClubApi.postForm.mockImplementation((url, payload, callback) => callback({ error: "Слишком длинное" }));

            wrapper.vm.saveDraft();

            expect(wrapper.vm.draftError).toBe("Слишком длинное");
            expect(wrapper.vm.draft).not.toBe(null);
            expect(wrapper.vm.isSaving).toBe(false);
        });

        it("does not post empty drafts", () => {
            mountMapWithMessages(makeMessages([]));
            wrapper.vm.toggleComposeMode();
            wrapper.vm.onMapClick({ lngLat: { lat: 1, lng: 2 } });
            wrapper.vm.draftText = "   ";

            wrapper.vm.saveDraft();

            expect(ClubApi.postForm).not.toHaveBeenCalled();
        });

        it("survives malformed messages json", () => {
            mountMapWithMessages("{not json");

            expect(mockMap.addSource).toHaveBeenCalledWith("messagesGeojson", expect.objectContaining({
                data: { type: "FeatureCollection", features: [] },
            }));
        });
    });
});
