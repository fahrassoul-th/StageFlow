from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC datetime - matches the models' `created_at` columns
    (plain TIMESTAMP, no timezone), which follow the course's own
    `datetime.datetime.utcnow` convention. A timezone-aware value here
    would work fine against SQLite (used in the test suite) but Postgres
    rejects mixing aware/naive datetimes in the same column outright."""
    return datetime.now(timezone.utc).replace(tzinfo=None)
