import hashlib
import json

from sqlalchemy import text
from sqlalchemy.engine import Connection

GENESIS_HASH = "0" * 64


def _hash(payload: dict) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def write_audit_log(
    conn: Connection,
    *,
    tenant_id: str,
    actor_id: str | None,
    actor_type: str,
    action: str,
    resource_type: str,
    resource_id: str | None,
    before_state: dict | None = None,
    after_state: dict | None = None,
) -> None:
    """Append one hash-chained audit record.

    Each record's hash covers the previous record's hash, so tampering
    with any historical row breaks the chain for every row after it —
    this is what POST /v1/audit-logs/verify (see docs/architecture/06)
    would check in a full implementation.
    """
    prev = conn.execute(
        text(
            "SELECT record_hash FROM audit_logs WHERE tenant_id = :tenant_id "
            "ORDER BY id DESC LIMIT 1"
        ),
        {"tenant_id": tenant_id},
    ).scalar()
    prev_hash = prev or GENESIS_HASH

    payload = {
        "tenant_id": tenant_id,
        "actor_id": actor_id,
        "actor_type": actor_type,
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "before_state": before_state,
        "after_state": after_state,
        "prev_hash": prev_hash,
    }
    record_hash = _hash(payload)

    conn.execute(
        text(
            """
            INSERT INTO audit_logs
                (tenant_id, actor_id, actor_type, action, resource_type, resource_id,
                 before_state, after_state, prev_hash, record_hash)
            VALUES
                (:tenant_id, :actor_id, :actor_type, :action, :resource_type, :resource_id,
                 CAST(:before_state AS JSONB), CAST(:after_state AS JSONB), :prev_hash, :record_hash)
            """
        ),
        {
            **payload,
            "before_state": json.dumps(before_state, default=str) if before_state is not None else None,
            "after_state": json.dumps(after_state, default=str) if after_state is not None else None,
            "record_hash": record_hash,
        },
    )


def verify_chain(conn: Connection, tenant_id: str) -> bool:
    rows = conn.execute(
        text(
            "SELECT actor_id, actor_type, action, resource_type, resource_id, "
            "before_state, after_state, prev_hash, record_hash "
            "FROM audit_logs WHERE tenant_id = :tenant_id ORDER BY id ASC"
        ),
        {"tenant_id": tenant_id},
    ).mappings().all()

    expected_prev = GENESIS_HASH
    for row in rows:
        if row["prev_hash"] != expected_prev:
            return False
        payload = {
            "tenant_id": tenant_id,
            "actor_id": str(row["actor_id"]) if row["actor_id"] else None,
            "actor_type": row["actor_type"],
            "action": row["action"],
            "resource_type": row["resource_type"],
            "resource_id": str(row["resource_id"]) if row["resource_id"] else None,
            "before_state": row["before_state"],
            "after_state": row["after_state"],
            "prev_hash": row["prev_hash"],
        }
        if _hash(payload) != row["record_hash"]:
            return False
        expected_prev = row["record_hash"]
    return True
