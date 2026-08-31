"""Production wiring helpers for the E.Y.T Order Center.

The deployment must provide the existing ERP PostgreSQL connection factory.
No credentials are stored here.
"""
from __future__ import annotations

from .atomic_confirm import AtomicOrderConfirmation
from .fastapi_router import configure_order_center


def configure_atomic_order_confirmation(connection_factory):
    """Register the production atomic confirmation service.

    `connection_factory` must return the ERP's existing PostgreSQL connection.
    """
    service = AtomicOrderConfirmation(connection_factory)
    return service
