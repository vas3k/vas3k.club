import mapboxgl from "mapbox-gl";
import ClubApi from "../lib/api.service";
const { mockMarkerInstance, mockCanvas, mockContainer, mockSource, mockMap } = vi.hoisted(() => {
const mockMarkerInstance = {
    setLngLat: vi.fn().mockReturnThis(),
    addTo: vi.fn().mockReturnThis(),
    remove: vi.fn(),
};

const mockCanvas = { style: {} };
const mockContainer = { offsetWidth: 1200 };
const mockSource = { setData: vi.fn() };

const mockMap = {
    addSource: vi.fn(),
    addLayer: vi.fn(),
    addControl: vi.fn(),
    querySourceFeatures: vi.fn().mockReturnValue([]),
    project: vi.fn((coords) => ({ x: coords[0], y: coords[1] })),
    getZoom: vi.fn().mockReturnValue(5),
    getCanvas: vi.fn(() => mockCanvas),
    getContainer: vi.fn(() => mockContainer),
    getSource: vi.fn(() => mockSource),
    flyTo: vi.fn(),
    easeTo: vi.fn(),
    on: vi.fn(),
    remove: vi.fn(),
};

return { mockMarkerInstance, mockCanvas, mockContainer, mockSource, mockMap };
});

vi.mock("../lib/api.service", () => ({
    __esModule: true,
    default: { get: vi.fn(), post: vi.fn(), postForm: vi.fn() },
}));

vi.mock("mapbox-gl", () => ({
    __esModule: true,
    default: {
        Map: vi.fn(function () { return mockMap; }),
        Marker: vi.fn(function () { return mockMarkerInstance; }),
        NavigationControl: vi.fn(),
        GeolocateControl: vi.fn(),
        accessToken: null,
    },
}));

import { act } from "react";
import { render } from "../../test/render";
import PeopleMap from "../components/PeopleMap";

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

describe("PeopleMap", () => {
    let wrapper;

    beforeEach(() => {
        vi.clearAllMocks();
        mockMarkerInstance.setLngLat.mockReturnThis();
        mockMarkerInstance.addTo.mockReturnThis();
    });

    afterEach(() => {
        if (wrapper) wrapper.unmount();
    });

    function mountMap(geojson) {
        wrapper = render(PeopleMap, { geojson });
        // Simulate map load: the "load" callback is registered via map.on("load", ...)
        var loadCall = mockMap.on.mock.calls.find(([e]) => e === "load");
        if (loadCall) loadCall[1]();
    }

    describe("map initialization", () => {
        it("creates a mapbox-gl Map and adds controls", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
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

            var MarkerCtor = mapboxgl.Marker;
            fireDataEvent();
            var countAfterFirst = MarkerCtor.mock.calls.length;

            fireDataEvent();
            expect(MarkerCtor.mock.calls.length).toBe(countAfterFirst);
        });
    });

    describe("cleanup", () => {
        it("calls map.remove() on destroy", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));
            wrapper.unmount();

            expect(mockMap.remove).toHaveBeenCalled();
            wrapper = null; // prevent double destroy in afterEach
        });
    });

    describe("map messages", () => {

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
                        upvote_url: m.upvoteUrl || `/map/messages/message-${i}/votes.json`,
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
                    upvote_url: "/map/messages/m1/votes.json",
                }, properties),
            }]);
            mountMapWithMessages(makeMessages([{ id: "m1", text: "hi" }]));
            fireDataEvent("messagesGeojson");
            return lastMarkerElement();
        }

        function mountMapWithMessages(messages) {
            wrapper = render(PeopleMap, {
                    geojson: makeGeojson([]),
                    messages: messages,
                    createMessageUrl: "/map/messages.json",
                    editProfileUrl: "/user/me/edit/profile/#map-location",
                    maxMessageLength: 128,
                });
            var loadCall = mockMap.on.mock.calls.find(([e]) => e === "load");
            if (loadCall) loadCall[1]();
        }

        function lastMarkerElement() {
            var MarkerCtor = mapboxgl.Marker;
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

        it("upvotes a message once and shows the count returned by the server", async () => {
            var el = zoomedInMessage({ upvotes: 3 });
            var button = el.querySelector(".people-map-message-upvote");
            var counter = el.querySelector(".people-map-message-upvotes");

            expect(button.disabled).toBe(false);
            expect(counter.innerText).toBe(3);

            ClubApi.post.mockResolvedValue({ upvotes: 4 });
            button.click();
            await act(async () => {});

            expect(ClubApi.post).toHaveBeenCalledWith(
                "/map/messages/m1/votes.json"
            );
            expect(counter.innerText).toBe(4);
            expect(button.disabled).toBe(true);
            expect(button.classList.contains("people-map-message-upvote-counted")).toBe(true);

            // a second click can not happen, the vote is final
            button.click();
            await act(async () => {});
            expect(ClubApi.post).toHaveBeenCalledTimes(1);
        });

        it("keeps the vote in the geojson so rebuilt markers stay voted", async () => {
            var el = zoomedInMessage({ upvotes: 1 });
            ClubApi.post.mockResolvedValue({ upvotes: 2 });

            el.querySelector(".people-map-message-upvote").click();
            await act(async () => {});

            expect(mockSource.setData).toHaveBeenCalledWith(expect.objectContaining({
                features: [expect.objectContaining({
                    properties: expect.objectContaining({ id: "m1", upvotes: 2, is_voted: true }),
                })],
            }));
        });

        it("re-enables the button when the vote fails", async () => {
            var el = zoomedInMessage({ upvotes: 0 });
            var button = el.querySelector(".people-map-message-upvote");
            ClubApi.post.mockRejectedValue(new Error("Нельзя"));

            button.click();
            await act(async () => {});

            expect(button.disabled).toBe(false);
            expect(button.title).toBe("Нельзя");
        });

        it("does not let a user vote for the same message twice", async () => {
            var el = zoomedInMessage({ is_voted: true, upvotes: 2 });
            var button = el.querySelector(".people-map-message-upvote");

            expect(button.disabled).toBe(true);
            expect(el.querySelector(".people-map-message-upvotes").innerText).toBe(2);

            button.click();
            await act(async () => {});
            expect(ClubApi.post).not.toHaveBeenCalled();
        });

        it("does not let a user vote for their own message", async () => {
            var el = zoomedInMessage({ is_mine: true, upvotes: 2 });
            var button = el.querySelector(".people-map-message-upvote");

            expect(button.disabled).toBe(true);
            expect(button.title).toContain("свои сообщения");
            expect(el.querySelector(".people-map-message-upvotes").innerText).toBe(2);

            button.click();
            await act(async () => {});
            expect(ClubApi.post).not.toHaveBeenCalled();
        });

        it("hides the button on own messages nobody voted for yet", () => {
            var el = zoomedInMessage({ is_mine: true, upvotes: 0 });

            expect(el.querySelector(".people-map-message-upvote")).toBe(null);
        });

        it("links to the profile settings anchor only when the url is given", () => {
            mountMapWithMessages(makeMessages([]));
            var link = wrapper.container.querySelector(".people-map-buttons a");
            expect(link.getAttribute("href")).toBe("/user/me/edit/profile/#map-location");
            expect(link.textContent).toContain("Передвинуть себя");

            wrapper.unmount();
            wrapper = render(PeopleMap, { geojson: makeGeojson([]) });
            expect(Boolean(wrapper.container.querySelector(".people-map-buttons a"))).toBe(false);
        });

        it("disables the compose button while the author is on the daily cooldown", () => {
            mountMapWithMessages(makeMessages([]));
            expect(wrapper.container.querySelector(".people-map-compose-button").disabled).toBeFalsy();

            wrapper.unmount();
            wrapper = render(PeopleMap, {
                    geojson: makeGeojson([]),
                    createMessageUrl: "/map/messages.json",
                    canPostMessage: false,
                });

            var button = wrapper.container.querySelector(".people-map-compose-button");
            expect(button.disabled).toBeTruthy();
            expect(button.textContent).toContain("Подождите 24 часа");
            expect(button.textContent).not.toContain("Оставить сообщение");

            act(() => wrapper.instance.toggleComposeMode());
            expect(wrapper.instance.state.composeMode).toBe(false);
        });

        it("switches the map cursor to a crosshair while composing", () => {
            mountMapWithMessages(makeMessages([]));

            act(() => wrapper.instance.toggleComposeMode());
            expect(mockCanvas.style.cursor).toBe("crosshair");

            act(() => wrapper.instance.toggleComposeMode());
            expect(mockCanvas.style.cursor).toBe("");
        });

        it("ignores map clicks until compose mode is activated", () => {
            mountMapWithMessages(makeMessages([]));

            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));
            expect(wrapper.instance.state.draft).toBe(null);

            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));

            expect(wrapper.instance.state.draft).toEqual({ latitude: 1, longitude: 2 });
            expect(wrapper.instance.state.composeMode).toBe(false);
            expect(mockCanvas.style.cursor).toBe("");
        });

        it("pans the clicked point out from under the overlaying sidebar", () => {
            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());

            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 52.5, lng: 13.4 } }));

            expect(mockMap.easeTo).toHaveBeenCalledWith(expect.objectContaining({
                center: [13.4, 52.5],
                offset: [160, 140],
            }));
        });

        it("closes the draft on a click outside of the bubble and keeps it on a click inside", () => {
            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));

            act(() => wrapper.instance.onDocumentClick({ target: wrapper.instance.composeElement }));
            expect(wrapper.instance.state.draft).not.toBe(null);

            act(() => wrapper.instance.onDocumentClick({ target: document.body }));
            expect(wrapper.instance.state.draft).toBe(null);
        });

        it("listens for outside clicks only while a draft is open", () => {
            vi.useFakeTimers();
            var add = vi.spyOn(document, "addEventListener");
            var remove = vi.spyOn(document, "removeEventListener");

            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));

            // the opening click must not reach the listener that closes the bubble
            expect(add).not.toHaveBeenCalledWith("click", wrapper.instance.onDocumentClick);
            vi.runAllTimers();
            expect(add).toHaveBeenCalledWith("click", wrapper.instance.onDocumentClick);

            act(() => wrapper.instance.cancelDraft());
            expect(remove).toHaveBeenCalledWith("click", wrapper.instance.onDocumentClick);

            add.mockRestore();
            remove.mockRestore();
            vi.useRealTimers();
        });

        it("posts the draft and adds the created message to the source", async () => {
            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 52.5, lng: 13.4 } }));
            act(() => wrapper.instance.setState({ draftText: "  hello map  " }));

            var newFeature = {
                type: "Feature",
                geometry: { coordinates: [13.4, 52.5] },
                properties: { id: "new", text: "hello map" },
            };
            ClubApi.postForm.mockResolvedValue({ feature: newFeature, can_post: false });

            await act(async () => wrapper.instance.saveDraft());

            expect(ClubApi.postForm).toHaveBeenCalledWith(
                "/map/messages.json",
                { text: "hello map", latitude: 52.5, longitude: 13.4 }
            );
            expect(mockSource.setData).toHaveBeenCalledWith(
                expect.objectContaining({ features: [newFeature] })
            );
            expect(wrapper.instance.state.draft).toBe(null);
            expect(wrapper.instance.state.postingAllowed).toBe(false);
        });

        it("keeps the draft and shows the error when saving fails", async () => {
            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));
            act(() => wrapper.instance.setState({ draftText: "hello" }));

            ClubApi.postForm.mockRejectedValue(new Error("Слишком длинное"));

            await act(async () => wrapper.instance.saveDraft());

            expect(wrapper.instance.state.draftError).toBe("Слишком длинное");
            expect(wrapper.instance.state.draft).not.toBe(null);
            expect(wrapper.instance.state.isSaving).toBe(false);
        });

        it("does not post empty drafts", async () => {
            mountMapWithMessages(makeMessages([]));
            act(() => wrapper.instance.toggleComposeMode());
            act(() => wrapper.instance.onMapClick({ lngLat: { lat: 1, lng: 2 } }));
            act(() => wrapper.instance.setState({ draftText: "   " }));

            await act(async () => wrapper.instance.saveDraft());

            expect(ClubApi.postForm).not.toHaveBeenCalled();
        });

        it("survives malformed messages json", () => {
            mountMapWithMessages("{not json");

            expect(mockMap.addSource).toHaveBeenCalledWith("messagesGeojson", expect.objectContaining({
                data: { type: "FeatureCollection", features: [] },
            }));
        });
    });

    describe("geo chat rooms", () => {
        function makeRooms(rooms) {
            return JSON.stringify({
                type: "FeatureCollection",
                features: rooms.map((room, i) => ({
                    type: "Feature",
                    geometry: { type: "Point", coordinates: room.coords || [13.4, 52.52] },
                    properties: {
                        id: room.id || `room-${i}`,
                        title: room.title || "Берлин",
                        image: room.image || "https://example.com/berlin.jpg",
                        color: room.color || "#FFCC00",
                        url: room.url === undefined ? "/room/berlin/chat/" : room.url,
                        member_count: room.memberCount || 12,
                        icon: room.icon || "",
                    },
                })),
            });
        }

        function mountMapWithRooms(rooms) {
            wrapper = render(PeopleMap, {
                    geojson: makeGeojson([]),
                    rooms: rooms,
                });
            var loadCall = mockMap.on.mock.calls.find(([e]) => e === "load");
            if (loadCall) loadCall[1]();
        }

        it("does not add polygon layers for geo chats", () => {
            mountMapWithRooms(makeRooms([{ title: "Берлин" }]));

            expect(mockMap.addSource).not.toHaveBeenCalledWith("roomsAreas", expect.anything());
            expect(mockMap.addLayer).not.toHaveBeenCalledWith(expect.objectContaining({
                id: "rooms-areas-fill",
            }));
        });

        it("renders a non-clickable marker when the room has no chat url", () => {
            mountMapWithRooms(makeRooms([{ url: null }]));

            var MarkerCtor = mapboxgl.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.tagName).toBe("DIV");
            expect(el.getAttribute("href")).toBe(null);
        });

        it("creates a room marker that links to the chat", () => {
            mountMapWithRooms(makeRooms([{
                title: "Берлин",
                url: "/room/berlin/chat/",
                memberCount: 2085,
            }]));

            var MarkerCtor = mapboxgl.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.tagName).toBe("A");
            expect(el.href).toContain("/room/berlin/chat/");
            expect(el.classList.contains("people-map-room-marker")).toBe(true);
            expect(el.style.backgroundImage).toContain("berlin.jpg");
            expect(el.querySelector(".people-map-room-label").innerText).toBe("Чат Берлин ・ 2085 человек");
        });

        it("toggles the compact class when the map zoom changes", () => {
            mockMap.getZoom.mockReturnValue(0);
            mountMapWithRooms(makeRooms([{ title: "Берлин" }]));

            var MarkerCtor = mapboxgl.Marker;
            var el = MarkerCtor.mock.calls[0][0].element;
            expect(el.classList.contains("people-map-room-marker-compact")).toBe(true);

            mockMap.getZoom.mockReturnValue(16);
            getHandler("zoom")();
            expect(el.classList.contains("people-map-room-marker-compact")).toBe(false);
        });

        it("does not add a rooms source when there are no geo chats", () => {
            mountMap(makeGeojson([{ coords: [10, 20] }]));

            expect(mockMap.addSource).not.toHaveBeenCalledWith("roomsAreas", expect.anything());
        });

        it("survives malformed rooms json", () => {
            mountMapWithRooms("{not json");

            expect(mockMap.addSource).not.toHaveBeenCalledWith("roomsAreas", expect.anything());
        });
    });
});
