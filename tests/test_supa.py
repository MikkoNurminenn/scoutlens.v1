import httpx
import pytest

from app.utils import supa
from app.utils.supa import SupabaseConfigError, first_row


def test_first_row_basic():
    class Resp:
        def __init__(self, data):
            self.data = data
    assert first_row(Resp([{"a": 1}])) == {"a": 1}
    assert first_row(Resp([])) is None
    assert first_row(None) is None


def test_create_supabase_client_http_status_error(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_ANON_KEY", "anon-key")

    request = httpx.Request("GET", "https://example.supabase.co")
    response = httpx.Response(404, request=request, text="Not Found")

    def _raise_http_status(*args, **kwargs):  # pragma: no cover - helper for test
        raise httpx.HTTPStatusError("not found", request=request, response=response)

    monkeypatch.setattr(supa, "create_client", _raise_http_status)

    with pytest.raises(SupabaseConfigError) as excinfo:
        supa._create_supabase_client()  # pylint: disable=protected-access

    assert "HTTP 404" in str(excinfo.value)
