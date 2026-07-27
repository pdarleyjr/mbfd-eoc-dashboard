from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

MIAMI_BEACH_DEFAULT_CENTER = {"lat": 25.7907, "lng": -80.1300}

# These centerlines define the explicit operational access corridors. They are
# deliberately wider than the roadway footprint so an incident on an approach
# is retained. The authoritative municipal polygon is also ingested from the
# Miami-Dade publisher service and exposed as a map layer.
CAUSEWAY_FOCUS: dict[str, list[tuple[float, float]]] = {
    "macarthur": [(-80.1889, 25.7839), (-80.1696, 25.7831), (-80.1387, 25.7774)],
    "julia_tuttle": [(-80.1874, 25.8134), (-80.1645, 25.8119), (-80.1385, 25.8097)],
    "venetian": [(-80.1912, 25.7913), (-80.1660, 25.7906), (-80.1422, 25.7902)],
}

# Conservative local pre-filter covering the barrier islands from South Pointe
# through the northern city limit. It is unioned with buffered causeway
# centerlines. PostGIS applies authoritative ingested geometry where available.
_island_scope = Polygon(
    [
        (-80.1545, 25.7570),
        (-80.1240, 25.7570),
        (-80.1120, 25.8785),
        (-80.1405, 25.8785),
        (-80.1545, 25.7570),
    ]
)
_corridors = [LineString(points).buffer(0.006) for points in CAUSEWAY_FOCUS.values()]
OPERATIONAL_SCOPE = unary_union([_island_scope.buffer(0.004), *_corridors])


def is_miami_beach_relevant(longitude: float, latitude: float) -> bool:
    return bool(OPERATIONAL_SCOPE.covers(Point(longitude, latitude)))
