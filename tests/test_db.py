from parking_subscriptions import db


def test_connect_sets_a_busy_timeout(tmp_path, monkeypatch):
    monkeypatch.setenv("PARKING_SUBSCRIPTIONS_DB_PATH", str(tmp_path / "test.db"))
    conn = db.connect()
    try:
        assert conn.execute("PRAGMA busy_timeout").fetchone()[0] == 5000
    finally:
        conn.close()
