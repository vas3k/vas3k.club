import { useEffect, useRef, useState } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";
import "../../static/css/components/location-select.css";

export default function LocationSelect({
    defaultLatitude = 0,
    defaultLongitude = 0,
    latitudeFieldName = "latitude",
    longitudeFieldName = "longitude",
}) {
    const container = useRef(null);
    const [coordinates, setCoordinates] = useState([
        Number(defaultLongitude).toFixed(6),
        Number(defaultLatitude).toFixed(6),
    ]);
    const [error, setError] = useState("");
    useEffect(() => {
        let map;
        try {
            map = new mapboxgl.Map({
                container: container.current,
                accessToken: "pk.eyJ1IjoidmFzM2siLCJhIjoiY2thZ254NXVwMDhkbjJ5dDk5eGh5Y21wbyJ9.wYXG58PrErQfRHTflvdSfA",
                style: "mapbox://styles/mapbox/outdoors-v12",
                center: [Number(defaultLongitude), Number(defaultLatitude)],
                zoom: defaultLatitude || defaultLongitude ? 8 : 1,
                maxZoom: 14,
                attributionControl: false,
                scrollZoom: true,
            });
            map.addControl(new mapboxgl.NavigationControl(), "top-right");
            map.addControl(new mapboxgl.GeolocateControl(), "top-right");
            map.on("moveend", () => {
                const { lng, lat } = map.getCenter();
                setCoordinates([lng.toFixed(6), lat.toFixed(6)]);
            });
        } catch (failure) {
            setError(failure.message);
        }
        return () => map?.remove();
    }, []);
    return (
        <div className="location-select">
            <div ref={container} className="location-select-map" />
            <div className="location-select-target">📍</div>
            {error && <div role="alert">Не удалось загрузить карту: {error}</div>}
            <input type="hidden" name={latitudeFieldName} value={coordinates[1]} />
            <input type="hidden" name={longitudeFieldName} value={coordinates[0]} />
        </div>
    );
}
