from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)


@contextmanager
def tenant_connection(tenant_id: str):
    """Open a transaction scoped to one tenant.

    Every query issued through this connection is subject to the
    tenant_isolation RLS policies defined in data/migrations/001_init.sql —
    SET LOCAL only lasts for the current transaction, so a bug can never
    leak app.current_tenant across requests or tenants.
    """
    with engine.connect() as conn:  # type: Connection
        with conn.begin():
            conn.execute(text("SET LOCAL app.current_tenant = :tenant_id"), {"tenant_id": tenant_id})
            yield conn


@contextmanager
def admin_connection():
    """Unscoped connection for cross-tenant operations (tenant provisioning only)."""
    with engine.connect() as conn:
        with conn.begin():
            yield conn
