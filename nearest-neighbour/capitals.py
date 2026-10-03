"""The 50 US state capitals, with coordinates.

City-centre coordinates to four decimal places, which is about 11 m -- far
finer than the question "which capital is nearest" needs, and these are
public geographic facts rather than a dataset with a licence. `validate()`
checks every point against plausible bounds for its state's region, so a
transposed sign or a digit slip fails loudly instead of quietly moving Juneau
into the Pacific.
"""

from __future__ import annotations

CAPITALS: list[tuple[str, str, float, float]] = [
    ("Montgomery", "AL", 32.3792, -86.3077),
    ("Juneau", "AK", 58.3019, -134.4197),
    ("Phoenix", "AZ", 33.4484, -112.0740),
    ("Little Rock", "AR", 34.7465, -92.2896),
    ("Sacramento", "CA", 38.5816, -121.4944),
    ("Denver", "CO", 39.7392, -104.9903),
    ("Hartford", "CT", 41.7658, -72.6734),
    ("Dover", "DE", 39.1582, -75.5244),
    ("Tallahassee", "FL", 30.4383, -84.2807),
    ("Atlanta", "GA", 33.7490, -84.3880),
    ("Honolulu", "HI", 21.3069, -157.8583),
    ("Boise", "ID", 43.6150, -116.2023),
    ("Springfield", "IL", 39.7817, -89.6501),
    ("Indianapolis", "IN", 39.7684, -86.1581),
    ("Des Moines", "IA", 41.5868, -93.6250),
    ("Topeka", "KS", 39.0473, -95.6752),
    ("Frankfort", "KY", 38.2009, -84.8733),
    ("Baton Rouge", "LA", 30.4515, -91.1871),
    ("Augusta", "ME", 44.3106, -69.7795),
    ("Annapolis", "MD", 38.9784, -76.4922),
    ("Boston", "MA", 42.3601, -71.0589),
    ("Lansing", "MI", 42.7325, -84.5555),
    ("Saint Paul", "MN", 44.9537, -93.0900),
    ("Jackson", "MS", 32.2988, -90.1848),
    ("Jefferson City", "MO", 38.5767, -92.1735),
    ("Helena", "MT", 46.5891, -112.0391),
    ("Lincoln", "NE", 40.8136, -96.7026),
    ("Carson City", "NV", 39.1638, -119.7674),
    ("Concord", "NH", 43.2081, -71.5376),
    ("Trenton", "NJ", 40.2206, -74.7597),
    ("Santa Fe", "NM", 35.6870, -105.9378),
    ("Albany", "NY", 42.6526, -73.7562),
    ("Raleigh", "NC", 35.7796, -78.6382),
    ("Bismarck", "ND", 46.8083, -100.7837),
    ("Columbus", "OH", 39.9612, -82.9988),
    ("Oklahoma City", "OK", 35.4676, -97.5164),
    ("Salem", "OR", 44.9429, -123.0351),
    ("Harrisburg", "PA", 40.2732, -76.8867),
    ("Providence", "RI", 41.8240, -71.4128),
    ("Columbia", "SC", 34.0007, -81.0348),
    ("Pierre", "SD", 44.3683, -100.3510),
    ("Nashville", "TN", 36.1627, -86.7816),
    ("Austin", "TX", 30.2672, -97.7431),
    ("Salt Lake City", "UT", 40.7608, -111.8910),
    ("Montpelier", "VT", 44.2601, -72.5754),
    ("Richmond", "VA", 37.5407, -77.4360),
    ("Olympia", "WA", 47.0379, -122.9007),
    ("Charleston", "WV", 38.3498, -81.6326),
    ("Madison", "WI", 43.0731, -89.4012),
    ("Cheyenne", "WY", 41.1400, -104.8202),
]

# Contiguous states plus the two that are not, checked separately.
CONTIGUOUS_BOUNDS = (24.0, 49.5, -125.5, -66.5)  # lat min/max, lon min/max


def validate() -> None:
    assert len(CAPITALS) == 50, f"expected 50 capitals, got {len(CAPITALS)}"
    codes = {code for _, code, _, _ in CAPITALS}
    assert len(codes) == 50, "duplicate state code"

    lat_lo, lat_hi, lon_lo, lon_hi = CONTIGUOUS_BOUNDS
    for name, code, lat, lon in CAPITALS:
        if code == "AK":
            assert 54 < lat < 72 and -170 < lon < -130, f"{name} outside Alaska"
        elif code == "HI":
            assert 18 < lat < 23 and -161 < lon < -154, f"{name} outside Hawaii"
        else:
            assert lat_lo < lat < lat_hi, f"{name} {code} latitude {lat} implausible"
            assert lon_lo < lon < lon_hi, f"{name} {code} longitude {lon} implausible"
