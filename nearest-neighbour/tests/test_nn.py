"""Tests. Brute force is the oracle for the tree; published distances are the
oracle for haversine; the lat/lon tree's failures are pinned as results.
"""

from __future__ import annotations

import math
import random
import unittest

from benchmark import clustered, uniform_sphere
from capitals import CAPITALS, validate
from geo import (EARTH_RADIUS_KM, chord_to_km, haversine_km,
                 lonlat_plane_distance, squared_chord, to_unit_vector)
from kdtree import (SearchStats, brute_force, build, naive_lonlat_tree_nearest,
                    nearest)


class TestHaversine(unittest.TestCase):
    def test_zero_distance(self):
        self.assertEqual(haversine_km(33.7, -84.4, 33.7, -84.4), 0.0)

    def test_symmetric(self):
        a = haversine_km(10, 20, -30, 40)
        b = haversine_km(-30, 40, 10, 20)
        self.assertAlmostEqual(a, b, places=9)

    def test_pole_to_pole_is_half_the_circumference(self):
        self.assertAlmostEqual(haversine_km(90, 0, -90, 0),
                               math.pi * EARTH_RADIUS_KM, places=6)

    def test_quarter_turn_on_the_equator(self):
        self.assertAlmostEqual(haversine_km(0, 0, 0, 90),
                               math.pi * EARTH_RADIUS_KM / 2, places=6)

    def test_longitude_is_irrelevant_at_the_pole(self):
        self.assertAlmostEqual(haversine_km(90, 0, 90, 150), 0.0, places=6)

    def test_published_distances(self):
        """Reference values are standard figures; 1% tolerance because the
        published numbers depend on which city-centre point is used."""
        for lat1, lon1, lat2, lon2, km in [
            (40.7128, -74.0060, 51.5074, -0.1278, 5570),   # New York - London
            (33.7490, -84.3880, 39.7392, -104.9903, 1949),  # Atlanta - Denver
        ]:
            got = haversine_km(lat1, lon1, lat2, lon2)
            self.assertLess(abs(got - km) / km, 0.01)


class TestUnitVectors(unittest.TestCase):
    def test_vectors_are_unit_length(self):
        rng = random.Random(0)
        for _ in range(200):
            lat = math.degrees(math.asin(rng.uniform(-1, 1)))
            v = to_unit_vector(lat, rng.uniform(-180, 180))
            self.assertAlmostEqual(math.sqrt(sum(c * c for c in v)), 1.0, places=12)

    def test_chord_recovers_the_great_circle_distance(self):
        rng = random.Random(1)
        for _ in range(300):
            a = (math.degrees(math.asin(rng.uniform(-1, 1))), rng.uniform(-180, 180))
            b = (math.degrees(math.asin(rng.uniform(-1, 1))), rng.uniform(-180, 180))
            chord = math.sqrt(squared_chord(to_unit_vector(*a), to_unit_vector(*b)))
            self.assertAlmostEqual(chord_to_km(chord), haversine_km(*a, *b), places=6)

    def test_chord_is_monotone_in_arc_length(self):
        """The property the whole approach rests on: ranking by chord is the
        same as ranking by great circle."""
        previous = -1.0
        for degrees in range(0, 181, 5):
            chord = math.sqrt(squared_chord(to_unit_vector(0, 0),
                                            to_unit_vector(0, degrees)))
            self.assertGreater(chord, previous)
            previous = chord

    def test_the_antimeridian_is_near_in_reality_and_far_in_latlon(self):
        self.assertLess(haversine_km(0, 179.9, 0, -179.9), 25)
        self.assertGreater(lonlat_plane_distance(0, 179.9, 0, -179.9), 350)


class TestCapitals(unittest.TestCase):
    def test_validate_passes(self):
        validate()

    def test_there_are_fifty_with_unique_codes(self):
        self.assertEqual(len({code for _, code, _, _ in CAPITALS}), 50)

    def test_validate_catches_a_transposed_sign(self):
        import capitals
        original = capitals.CAPITALS
        try:
            capitals.CAPITALS = [("Atlanta", "GA", 33.7490, 84.3880)] + original[1:]
            with self.assertRaises(AssertionError):
                capitals.validate()
        finally:
            capitals.CAPITALS = original


class TestTreeAgreesWithBruteForce(unittest.TestCase):
    def test_every_capital_gets_the_same_answer(self):
        items = [(to_unit_vector(lat, lon), (n, c)) for n, c, lat, lon in CAPITALS]
        for name, code, lat, lon in CAPITALS:
            with self.subTest(name):
                target = to_unit_vector(lat, lon)
                rest = [(p, q) for p, q in items if q != (name, code)]
                self.assertEqual(nearest(build(rest), target)[0],
                                 brute_force(rest, target)[0])

    def test_agreement_on_random_point_sets(self):
        for seed in range(12):
            rng = random.Random(seed)
            items = uniform_sphere(rng.randrange(1, 120), rng)
            root = build(items)
            for _ in range(20):
                target = to_unit_vector(
                    math.degrees(math.asin(rng.uniform(-1, 1))),
                    rng.uniform(-180, 180))
                kd, kd_d = nearest(root, target)
                bf, bf_d = brute_force(items, target)
                self.assertAlmostEqual(kd_d, bf_d, places=12)

    def test_agreement_on_clustered_point_sets(self):
        """Clustering is where a mis-written pruning test shows up."""
        for seed in range(8):
            rng = random.Random(100 + seed)
            items = clustered(200, rng)
            root = build(items)
            for _ in range(20):
                target = to_unit_vector(rng.uniform(-60, 60), rng.uniform(-180, 180))
                self.assertAlmostEqual(nearest(root, target)[1],
                                       brute_force(items, target)[1], places=12)

    def test_a_single_point_tree(self):
        items = [(to_unit_vector(0, 0), "only")]
        self.assertEqual(nearest(build(items), to_unit_vector(45, 45))[0], "only")

    def test_an_empty_tree_returns_nothing(self):
        payload, d = nearest(build([]), to_unit_vector(0, 0))
        self.assertIsNone(payload)
        self.assertEqual(d, float("inf"))

    def test_duplicate_points_do_not_break_the_build(self):
        items = [(to_unit_vector(10, 10), i) for i in range(9)]
        self.assertIsNotNone(nearest(build(items), to_unit_vector(10, 10))[0])


class TestPruning(unittest.TestCase):
    def test_the_tree_does_far_less_work_than_the_scan(self):
        rng = random.Random(5)
        items = uniform_sphere(5000, rng)
        root = build(items)
        kd, bf = SearchStats(), SearchStats()
        for _ in range(40):
            target = to_unit_vector(math.degrees(math.asin(rng.uniform(-1, 1))),
                                    rng.uniform(-180, 180))
            nearest(root, target, kd)
            brute_force(items, target, bf)
        self.assertLess(kd.distance_calls, bf.distance_calls / 100)

    def test_clustering_destroys_the_pruning(self):
        """The headline result. On uniform points the tree touches a
        logarithmic number of nodes; clumped together, it touches a sizeable
        fraction of the whole set."""
        n = 5000
        uni_stats, clu_stats = SearchStats(), SearchStats()
        uni = build(uniform_sphere(n, random.Random(1)))
        clu_items = clustered(n, random.Random(2))
        clu = build(clu_items)
        rng = random.Random(3)
        for _ in range(40):
            target = to_unit_vector(rng.uniform(-60, 60), rng.uniform(-180, 180))
            nearest(uni, target, uni_stats)
            nearest(clu, target, clu_stats)
        self.assertGreater(clu_stats.distance_calls, 10 * uni_stats.distance_calls)


class TestTheLatLonMistake(unittest.TestCase):
    """A 2-d tree on raw lat/lon returns wrong neighbours. Pinned as a result
    so it cannot quietly start passing."""

    PACIFIC = [
        ("Suva, Fiji", -18.1416, 178.4415),
        ("Funafuti, Tuvalu", -8.5211, 179.1962),
        ("Nuku'alofa, Tonga", -21.1393, -175.2026),
        ("Apia, Samoa", -13.8333, -171.7667),
        ("Mata-Utu, Wallis", -13.2825, -176.1744),
        ("Auckland, NZ", -36.8485, 174.7633),
    ]

    def truth(self, qlat, qlon):
        return min(self.PACIFIC, key=lambda p: haversine_km(qlat, qlon, p[1], p[2]))[0]

    def test_the_three_d_tree_is_right_on_all_of_them(self):
        items = [(to_unit_vector(lat, lon), name) for name, lat, lon in self.PACIFIC]
        root = build(items)
        for qlat, qlon in [(-14.0, 179.5), (-16.0, -179.0), (-20.0, 179.9)]:
            with self.subTest(q=(qlat, qlon)):
                self.assertEqual(nearest(root, to_unit_vector(qlat, qlon))[0],
                                 self.truth(qlat, qlon))

    def test_the_latlon_tree_is_wrong_across_the_seam(self):
        pairs = [((lat, lon), name) for name, lat, lon in self.PACIFIC]
        wrong = 0
        for qlat, qlon in [(-14.0, 179.5), (-16.0, -179.0), (-20.0, 179.9)]:
            if naive_lonlat_tree_nearest(pairs, (qlat, qlon)) != self.truth(qlat, qlon):
                wrong += 1
        self.assertEqual(wrong, 2)


if __name__ == "__main__":
    unittest.main()
