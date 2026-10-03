"""Great-circle distance, and the coordinate change that makes a k-d tree correct.

A k-d tree splits space with axis-aligned planes and prunes using a distance
metric. That only works if the coordinates it indexes form a metric space in
which "close in the index" means "close in reality".

Latitude and longitude do not. Longitude wraps at 180, so (lat 0, lon 179.9)
and (lat 0, lon -179.9) are 0.2 degrees apart on the globe and 359.8 apart in
the index. Latitude does not wrap, but a degree of longitude is 111 km at the
equator and 0 km at the pole, so even away from the seam the axes are not
commensurable.

The fix is to leave the lat/lon plane entirely: map each point to a unit
vector in 3-space. Euclidean distance between unit vectors (the chord) is a
strictly increasing function of the great-circle distance,

    chord = 2 * sin(theta / 2)

so whichever neighbour is nearest by chord is nearest by great circle, and a
k-d tree over x, y, z prunes correctly with no wrap-around anywhere.
"""

from __future__ import annotations

import math

EARTH_RADIUS_KM = 6371.0088  # IUGG mean radius


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(min(1.0, a)))


def to_unit_vector(lat: float, lon: float) -> tuple[float, float, float]:
    """Lat/lon in degrees to a point on the unit sphere."""
    phi, lam = math.radians(lat), math.radians(lon)
    cos_phi = math.cos(phi)
    return (cos_phi * math.cos(lam), cos_phi * math.sin(lam), math.sin(phi))


def chord_to_km(chord: float) -> float:
    """Invert chord = 2 sin(theta/2) to recover the arc length."""
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, chord / 2))


def squared_chord(a: tuple[float, float, float],
                  b: tuple[float, float, float]) -> float:
    """Squared Euclidean distance between unit vectors.

    Squared, because the k-d tree never needs the square root: comparisons and
    pruning are both monotone in it, and skipping ~n sqrt calls is most of the
    constant factor in a brute-force scan.
    """
    return (a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2


def lonlat_plane_distance(lat1: float, lon1: float,
                          lat2: float, lon2: float) -> float:
    """The wrong metric, kept so its failure can be demonstrated rather than
    asserted: plain Euclidean distance in the lat/lon plane."""
    return math.hypot(lat2 - lat1, lon2 - lon1)
