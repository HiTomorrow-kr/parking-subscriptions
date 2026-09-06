import os

# --- Section: Configuration ---
# parking_subscriptions owns its own data location. Orchestrators (Telegram
# bot, Discord bot, ...) don't need to know or configure where the SQLite
# file lives — they get it for free just by pointing PYTHONPATH at this repo.
# PARKING_SUBSCRIPTIONS_DB_PATH still overrides it, for tests or a deployment
# that genuinely needs multiple independent databases.
_ENV_VAR = "PARKING_SUBSCRIPTIONS_DB_PATH"
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEFAULT_DB_PATH = os.path.join(_REPO_ROOT, "data", "parking.db")


def get_db_path() -> str:
    """Resolves the SQLite database path.

    Returns:
        str: PARKING_SUBSCRIPTIONS_DB_PATH if set, otherwise this repo's
            own data/parking.db.
    """
    return os.environ.get(_ENV_VAR) or _DEFAULT_DB_PATH
