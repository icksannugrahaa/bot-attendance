import math
import random

# Base configurations
MB_CENTER = (-6.240723226162096, 106.8365991740012)
KANPUS_CENTER = (-6.216556144511367, 106.81407082204778)

# 1 degree of latitude is ~111km (111139 meters)
LAT_METER_DEG = 1.0 / 111139.0


def _meters_to_lng_deg(latitude: float) -> float:
    """Lng distance changes depending on latitude due to Earth's curvature."""
    return 1.0 / (111139.0 * math.cos(math.radians(latitude)))


def get_random_location(pool_type: str) -> dict:
    """
    Returns a random {lat, lng} within a 50m radius of the requested pool center.
    Default fallback is 'mb'.
    """
    pool_type = pool_type.lower()
    
    if pool_type == "kanpus":
        center_lat, center_lng = KANPUS_CENTER
    else:
        # Default fallback to "mb"
        center_lat, center_lng = MB_CENTER

    # Generate random distance up to 50m
    max_radius_m = 50.0
    r = max_radius_m * math.sqrt(random.random())
    theta = random.random() * 2 * math.pi

    # Offset in meters
    dx = r * math.cos(theta)
    dy = r * math.sin(theta)

    # Offset in degrees
    d_lat = dy * LAT_METER_DEG
    d_lng = dx * _meters_to_lng_deg(center_lat)

    return {
        "lat": center_lat + d_lat,
        "lng": center_lng + d_lng
    }
