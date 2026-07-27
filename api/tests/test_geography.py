from app.geography import (
    CAUSEWAY_FOCUS,
    MIAMI_BEACH_DEFAULT_CENTER,
    is_miami_beach_relevant,
)


def test_miami_beach_point_is_relevant() -> None:
    assert is_miami_beach_relevant(-80.1300, 25.7907)


def test_unrelated_western_county_point_is_rejected() -> None:
    assert not is_miami_beach_relevant(-80.50, 25.79)


def test_all_required_causeways_have_focus_geometry() -> None:
    assert set(CAUSEWAY_FOCUS) == {"macarthur", "julia_tuttle", "venetian"}
    assert MIAMI_BEACH_DEFAULT_CENTER == {"lat": 25.7907, "lng": -80.1300}
