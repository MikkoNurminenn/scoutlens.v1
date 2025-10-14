from datetime import date

from app.report_payload import build_report_payload


def test_build_report_payload_includes_player_name_and_sanitizes_text():
    payload = build_report_payload(
        player_id="pid-123",
        player_name="  Ada Hegerberg  ",
        report_date=date(2024, 7, 4),
        competition="  UEFA  ",
        opponent="  PSG  ",
        location="  Lyon  ",
        attrs={"position": "CF"},
        match_id="mid-1",
    )

    assert payload["player_id"] == "pid-123"
    assert payload["player_name"] == "Ada Hegerberg"
    assert payload["competition"] == "UEFA"
    assert payload["opponent"] == "PSG"
    assert payload["location"] == "Lyon"
    assert payload["match_id"] == "mid-1"
    assert payload["attributes"]["position"] == "CF"


def test_build_report_payload_handles_missing_optional_fields():
    payload = build_report_payload(
        player_id="pid-456",
        player_name="",
        report_date=date(2024, 7, 5),
        competition=None,
        opponent="",
        location="  ",
        attrs={},
        match_id=None,
        include_player_name=False,
    )

    assert "player_name" not in payload
    assert payload["competition"] is None
    assert payload["opponent"] is None
    assert payload["location"] is None
    assert "match_id" not in payload
