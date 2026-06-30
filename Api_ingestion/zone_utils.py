from typing import Optional

# Centre approximatif de Paris (utilisé comme référence pour quadrants)
PARIS_CENTER_LAT = 48.8566
PARIS_CENTER_LON = 2.3522


def get_paris_zone(lat: float, lon: float) -> str:
    lat_diff = lat - PARIS_CENTER_LAT
    lon_diff = lon - PARIS_CENTER_LON

    if abs(lat_diff) >= abs(lon_diff):
        return "Paris Nord" if lat_diff >= 0 else "Paris Sud"
    return "Paris Est" if lon_diff >= 0 else "Paris Ouest"


def normalize_zone(zone: Optional[str]) -> Optional[str]:
    if zone is None:
        return None

    z = zone.strip().lower()
    mapping = {
        "nord": "Paris Nord",
        "sud": "Paris Sud",
        "est": "Paris Est",
        "ouest": "Paris Ouest",
        "paris nord": "Paris Nord",
        "paris sud": "Paris Sud",
        "paris est": "Paris Est",
        "paris ouest": "Paris Ouest",
    }
    return mapping.get(z, zone.strip())