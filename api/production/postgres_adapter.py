"""Shared PostgreSQL connection adapter for E.Y.T runtime APIs."""
from __future__ import annotations

import os
from typing import Any

import psycopg


def get_connection() -> Any:
    """Open a PostgreSQL connection using the repository's DATABASE_URL contract."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not configured")
    return psycopg.connect(url)
