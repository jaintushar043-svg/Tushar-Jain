from uuid import UUID

from fastapi import Depends, FastAPI, Header, HTTPException
from sqlalchemy import text

from . import schemas
from .audit import verify_chain, write_audit_log
from .db import admin_connection, tenant_connection
from .recommender import recommend

app = FastAPI(
    title="Aegis Compliance OS — KYC API (MVP)",
    version="0.1.0",
    description=(
        "MVP slice of the KYC service per docs/architecture/06-api-design.md. "
        "Auth here is a placeholder (X-Tenant-Id/X-User-Id headers) standing in "
        "for the OIDC/JWT flow described in the design docs — every write is "
        "still tenant-isolated via Postgres RLS and hash-chained audit logging."
    ),
)


def current_tenant(x_tenant_id: str = Header(...)) -> str:
    return x_tenant_id


def current_user(x_user_id: str | None = Header(default=None)) -> str | None:
    return x_user_id


# ── Tenant provisioning (dev/admin only — not part of the tenant-scoped API surface) ──
@app.post("/v1/tenants", response_model=schemas.TenantOut, status_code=201)
def create_tenant(body: schemas.TenantCreate):
    with admin_connection() as conn:
        row = conn.execute(
            text(
                "INSERT INTO tenants (name, industry) VALUES (:name, :industry) "
                "RETURNING id, name, industry"
            ),
            body.model_dump(),
        ).mappings().one()
        return schemas.TenantOut(**row)


# ── Users ────────────────────────────────────────────────────────────────
@app.post("/v1/users", response_model=schemas.UserOut, status_code=201)
def create_user(body: schemas.UserCreate, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "INSERT INTO users (tenant_id, email, full_name) "
                "VALUES (:tenant_id, :email, :full_name) RETURNING id, email, full_name"
            ),
            {**body.model_dump(), "tenant_id": tenant_id},
        ).mappings().one()
        return schemas.UserOut(**row)


# ── Customers ──────────────────────────────────────────────────────────
@app.post("/v1/customers", response_model=schemas.CustomerOut, status_code=201)
def create_customer(body: schemas.CustomerCreate, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO customers (tenant_id, display_name, customer_type, country, external_ref)
                VALUES (:tenant_id, :display_name, :customer_type, :country, :external_ref)
                RETURNING id, display_name, customer_type, country, onboarding_status
                """
            ),
            {**body.model_dump(), "tenant_id": tenant_id},
        ).mappings().one()
        write_audit_log(
            conn,
            tenant_id=tenant_id,
            actor_id=None,
            actor_type="human",
            action="customer.created",
            resource_type="customer",
            resource_id=str(row["id"]),
            after_state=dict(row),
        )
        return schemas.CustomerOut(**row)


@app.get("/v1/customers/{customer_id}", response_model=schemas.CustomerOut)
def get_customer(customer_id: UUID, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT id, display_name, customer_type, country, onboarding_status "
                "FROM customers WHERE id = :id"
            ),
            {"id": str(customer_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "customer not found")
        return schemas.CustomerOut(**row)


# ── KYC cases ──────────────────────────────────────────────────────────
@app.post("/v1/kyc/cases", response_model=schemas.KycCaseOut, status_code=201)
def create_kyc_case(body: schemas.KycCaseCreate, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                """
                INSERT INTO kyc_cases (tenant_id, customer_id, case_type)
                VALUES (:tenant_id, :customer_id, :case_type)
                RETURNING id, customer_id, case_type, status, risk_tier,
                          ai_recommendation, decision, decision_rationale
                """
            ),
            {**body.model_dump(mode="json"), "tenant_id": tenant_id},
        ).mappings().one()
        write_audit_log(
            conn,
            tenant_id=tenant_id,
            actor_id=None,
            actor_type="human",
            action="kyc_case.created",
            resource_type="kyc_case",
            resource_id=str(row["id"]),
            after_state={"status": row["status"], "case_type": row["case_type"]},
        )
        return schemas.KycCaseOut(**row)


@app.get("/v1/kyc/cases/{case_id}", response_model=schemas.KycCaseOut)
def get_kyc_case(case_id: UUID, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        row = conn.execute(
            text(
                "SELECT id, customer_id, case_type, status, risk_tier, "
                "ai_recommendation, decision, decision_rationale FROM kyc_cases WHERE id = :id"
            ),
            {"id": str(case_id)},
        ).mappings().first()
        if not row:
            raise HTTPException(404, "kyc case not found")
        return schemas.KycCaseOut(**row)


@app.get("/v1/kyc/cases/{case_id}/ai-recommendation", response_model=schemas.AiRecommendationOut)
def get_ai_recommendation(case_id: UUID, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        case = conn.execute(
            text("SELECT id, customer_id FROM kyc_cases WHERE id = :id"),
            {"id": str(case_id)},
        ).mappings().first()
        if not case:
            raise HTTPException(404, "kyc case not found")

        customer = conn.execute(
            text("SELECT country, customer_type FROM customers WHERE id = :id"),
            {"id": str(case["customer_id"])},
        ).mappings().one()

        recommendation = recommend(customer["country"], customer["customer_type"])

        conn.execute(
            text(
                "UPDATE kyc_cases SET ai_recommendation = CAST(:rec AS JSONB), "
                "risk_tier = :risk_tier WHERE id = :id"
            ),
            {
                "rec": __import__("json").dumps(recommendation),
                "risk_tier": recommendation["risk_tier"],
                "id": str(case_id),
            },
        )
        write_audit_log(
            conn,
            tenant_id=tenant_id,
            actor_id=None,
            actor_type="ai",
            action="kyc_case.ai_recommendation_generated",
            resource_type="kyc_case",
            resource_id=str(case_id),
            after_state=recommendation,
        )
        return schemas.AiRecommendationOut(case_id=case_id, recommendation=recommendation)


@app.post("/v1/kyc/cases/{case_id}/decision", response_model=schemas.KycCaseOut)
def decide_kyc_case(case_id: UUID, body: schemas.DecisionCreate, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        before = conn.execute(
            text("SELECT id, ai_recommendation FROM kyc_cases WHERE id = :id"),
            {"id": str(case_id)},
        ).mappings().first()
        if not before:
            raise HTTPException(404, "kyc case not found")
        if before["ai_recommendation"] is None:
            raise HTTPException(
                409, "cannot decide a case with no AI recommendation on record — "
                "GET /ai-recommendation first so there is something to concur with or override"
            )

        new_status = "closed" if body.decision == "approved" else body.decision
        row = conn.execute(
            text(
                """
                UPDATE kyc_cases
                SET decision = :decision, decision_rationale = :rationale,
                    decided_by = :approver_id, decided_at = now(), status = :status
                WHERE id = :id
                RETURNING id, customer_id, case_type, status, risk_tier,
                          ai_recommendation, decision, decision_rationale
                """
            ),
            {
                "decision": body.decision,
                "rationale": body.rationale,
                "approver_id": str(body.approver_id),
                "status": new_status,
                "id": str(case_id),
            },
        ).mappings().one()
        write_audit_log(
            conn,
            tenant_id=tenant_id,
            actor_id=str(body.approver_id),
            actor_type="human",
            action="kyc_case.decided",
            resource_type="kyc_case",
            resource_id=str(case_id),
            before_state={"ai_recommendation": before["ai_recommendation"]},
            after_state={"decision": body.decision, "rationale": body.rationale},
        )
        return schemas.KycCaseOut(**row)


# ── Audit ──────────────────────────────────────────────────────────────
@app.get("/v1/audit-logs")
def list_audit_logs(resource_type: str, resource_id: UUID, tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        rows = conn.execute(
            text(
                "SELECT id, actor_id, actor_type, action, resource_type, resource_id, "
                "before_state, after_state, prev_hash, record_hash, created_at "
                "FROM audit_logs WHERE resource_type = :rt AND resource_id = :rid ORDER BY id"
            ),
            {"rt": resource_type, "rid": str(resource_id)},
        ).mappings().all()
        return [dict(r) for r in rows]


@app.post("/v1/audit-logs/verify")
def verify_audit_logs(tenant_id: str = Depends(current_tenant)):
    with tenant_connection(tenant_id) as conn:
        return {"tenant_id": tenant_id, "chain_intact": verify_chain(conn, tenant_id)}
