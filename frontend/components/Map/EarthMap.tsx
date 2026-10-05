"use client";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

interface Props {
  selected: { lat: number; lon: number } | null;
  onSelect: (lat: number, lon: number) => void;
  zones?: GeoJSON.FeatureCollection | null;
}

export default function EarthMap({ selected, onSelect, zones }: Props) {
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const marker = useRef<maplibregl.Marker | null>(null);
  const cb = useRef(onSelect);
  cb.current = onSelect;

  useEffect(() => {
    if (!el.current || map.current) return;
    const m = new maplibregl.Map({
      container: el.current,
      center: [20, 20],
      zoom: 1.6,
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster", tileSize: 256, maxzoom: 19,
            tiles: ["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
    });
    m.addControl(new maplibregl.NavigationControl(), "bottom-right");
    m.addControl(new maplibregl.ScaleControl(), "bottom-left");
    m.on("click", (e) => cb.current(e.lngLat.lat, e.lngLat.lng));
    map.current = m;
    return () => { m.remove(); map.current = null; };
  }, []);

  useEffect(() => {
    if (!map.current || !selected) return;
    marker.current?.remove();
    marker.current = new maplibregl.Marker({ color: "#f2b134" }).setLngLat([selected.lon, selected.lat]).addTo(map.current);
    map.current.flyTo({ center: [selected.lon, selected.lat], zoom: Math.max(map.current.getZoom(), 8) });
  }, [selected]);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const source = m.getSource("change-zones") as maplibregl.GeoJSONSource | undefined;
    if (source) source.setData(zones ?? { type: "FeatureCollection", features: [] });
    else if (zones) {
      m.addSource("change-zones", { type: "geojson", data: zones });
      m.addLayer({ id: "change-zones-fill", type: "fill", source: "change-zones",
        paint: { "fill-color": "#e8765f", "fill-opacity": 0.35 } });
      m.addLayer({ id: "change-zones-line", type: "line", source: "change-zones",
        paint: { "line-color": "#f2b134", "line-width": 2 } });
    }
  }, [zones]);

  return <div ref={el} className="map" aria-label="Interactive world map" />;
}
