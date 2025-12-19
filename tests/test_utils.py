from tyousa.utils import haversine_distance_m


def test_haversine_distance_matches_known_value():
    # Distance between two nearby Osaka points ~1.36km
    dist = haversine_distance_m(34.702485, 135.495951, 34.692285, 135.502165)
    assert 1200 <= dist <= 1400
