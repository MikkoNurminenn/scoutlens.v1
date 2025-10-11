from app import calendar_ui


def test_maps_search_url_combines_parts():
    url = calendar_ui._maps_search_url("Estadio Uno", "La Plata")
    assert url is not None
    assert url.startswith("https://www.google.com/maps/search/?api=1&query=")
    assert "Estadio+Uno%2C+La+Plata" in url


def test_maps_search_url_handles_empty_values():
    assert calendar_ui._maps_search_url(" ", None) is None
    assert calendar_ui._maps_search_url() is None
