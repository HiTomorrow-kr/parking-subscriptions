import os

# --- Section: Configuration ---
# No hardcoded path and no fallback default: every orchestrator (Telegram
# bot, Discord bot, ...) must explicitly say which SQLite file to use.
# Orchestrators sharing the same server point this at the same path to share data.
_ENV_VAR = "PARKING_SUBSCRIPTIONS_DB_PATH"


def get_db_path() -> str:
    """Resolves the SQLite database path from the environment.

    Returns:
        str: Absolute or relative path to the SQLite database file.

    Raises:
        RuntimeError: If PARKING_SUBSCRIPTIONS_DB_PATH is not set by the caller.
    """
    db_path = os.environ.get(_ENV_VAR)
    if not db_path:
        raise RuntimeError(
            f"{_ENV_VAR} is not set. Orchestrators must point this at the SQLite "
            "file they want parking_subscriptions to read/write."
        )
    return db_path
