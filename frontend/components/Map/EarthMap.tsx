"use client";
import maplibregl from "maplibre-gl";
import { useEffect, useRef } from "react";

interface Props {
  selected: { lat: number; lon: number } | null;
  onSelect: (lat: number, lon: number) => void;
}

export default function EarthMap({ selected, onSelect }: Props) {
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

  return <div ref={el} className="map" aria-label="Interactive world map" />;
}
