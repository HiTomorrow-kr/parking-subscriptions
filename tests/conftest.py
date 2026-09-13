import sqlite3

import pytest

from parking_subscriptions import db


@pytest.fixture
def conn():
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    connection.executescript(db.SCHEMA)
    yield connection
    connection.close()
