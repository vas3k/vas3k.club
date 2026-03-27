const mockMarkerInstance = {
    setLngLat: jest.fn().mockReturnThis(),
    addTo: jest.fn().mockReturnThis(),
    remove: jest.fn(),
};

const mockMap = {
    addSource: jest.fn(),
    addLayer: jest.fn(),
    addControl: jest.fn(),
    querySourceFeatures: jest.fn().mockReturnValue([]),
    project: jest.fn((coords) => ({ x: coords[0], y: coords[1] })),
    getZoom: jest.fn().mockReturnValue(5),
    flyTo: jest.fn(),
    on: jest.fn(),
    remove: jest.fn(),
};

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
});
