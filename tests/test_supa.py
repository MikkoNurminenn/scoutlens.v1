from app.utils.supa import first_row


def test_first_row_basic():
    class Resp:
        def __init__(self, data):
            self.data = data
    assert first_row(Resp([{"a": 1}])) == {"a": 1}
    assert first_row(Resp([])) is None
    assert first_row(None) is None
