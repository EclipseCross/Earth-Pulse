"""Coordinate / AOI validation. Bounding box order is (west, south, east, north)."""
MAX_AOI_DEG2 = 4.0  # hackathon guard: keep AOI processing small


class InvalidAOI(ValueError):
    pass


def validate_point(lat: float, lon: float) -> tuple[float, float]:
    if not (-90 <= lat <= 90):
        raise InvalidAOI(f"Latitude {lat} is outside -90..90.")
    if not (-180 <= lon <= 180):
        raise InvalidAOI(f"Longitude {lon} is outside -180..180.")
    return lat, lon


def validate_bbox(w: float, s: float, e: float, n: float) -> tuple[float, float, float, float]:
    validate_point(s, w)
    validate_point(n, e)
    if w >= e or s >= n:
        raise InvalidAOI("Bounding box must satisfy west < east and south < north.")
    if (e - w) * (n - s) > MAX_AOI_DEG2:
        raise InvalidAOI(f"AOI is too large (max {MAX_AOI_DEG2} square degrees). Select a smaller area.")
    return w, s, e, n


def point_to_bbox(lat: float, lon: float, half_deg: float = 0.05) -> tuple[float, float, float, float]:
    validate_point(lat, lon)
    return (max(-180, lon - half_deg), max(-90, lat - half_deg),
            min(180, lon + half_deg), min(90, lat + half_deg))
