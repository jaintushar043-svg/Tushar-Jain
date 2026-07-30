def _create_customer(client, tenant, country="IR"):
    resp = client.post(
        "/v1/customers",
        headers={"X-Tenant-Id": tenant},
        json={"display_name": "Jane Doe", "customer_type": "individual", "country": country},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def _create_case(client, tenant, customer_id, case_type="onboarding"):
    resp = client.post(
        "/v1/kyc/cases",
        headers={"X-Tenant-Id": tenant},
        json={"customer_id": customer_id, "case_type": case_type},
    )
    assert resp.status_code == 201
    return resp.json()["id"]


def test_full_kyc_flow_produces_grounded_recommendation_and_gated_decision(client, tenant, approver):
    customer_id = _create_customer(client, tenant, country="IR")
    case_id = _create_case(client, tenant, customer_id)

    rec_resp = client.get(f"/v1/kyc/cases/{case_id}/ai-recommendation", headers={"X-Tenant-Id": tenant})
    assert rec_resp.status_code == 200
    rec = rec_resp.json()["recommendation"]
    assert rec["decision"] == "escalate_edd"
    assert rec["risk_tier"] == "high"
    # every AI recommendation must ship at least one citation — no ungrounded output
    assert len(rec["citations"]) >= 1

    decision_resp = client.post(
        f"/v1/kyc/cases/{case_id}/decision",
        headers={"X-Tenant-Id": tenant},
        json={"approver_id": approver, "decision": "escalated", "rationale": "Concur with EDD escalation"},
    )
    assert decision_resp.status_code == 200
    body = decision_resp.json()
    assert body["decision"] == "escalated"
    assert body["status"] == "escalated"


def test_low_risk_customer_gets_approve_recommendation(client, tenant, approver):
    customer_id = _create_customer(client, tenant, country="US")
    case_id = _create_case(client, tenant, customer_id)

    rec = client.get(f"/v1/kyc/cases/{case_id}/ai-recommendation", headers={"X-Tenant-Id": tenant}).json()
    assert rec["recommendation"]["decision"] == "approve"
    assert rec["recommendation"]["risk_tier"] == "low"


def test_decision_is_blocked_until_ai_recommendation_exists(client, tenant, approver):
    """The human-approval gate is a hard business rule, not a UI nicety —
    the API must refuse a decision on a case with no AI recommendation on record."""
    customer_id = _create_customer(client, tenant)
    case_id = _create_case(client, tenant, customer_id)

    resp = client.post(
        f"/v1/kyc/cases/{case_id}/decision",
        headers={"X-Tenant-Id": tenant},
        json={"approver_id": approver, "decision": "approved", "rationale": "n/a"},
    )
    assert resp.status_code == 409


def test_tenant_cannot_read_another_tenants_kyc_case(client, tenant, approver):
    customer_id = _create_customer(client, tenant)
    case_id = _create_case(client, tenant, customer_id)

    other_tenant = client.post("/v1/tenants", json={"name": "Other Bank", "industry": "nbfc"}).json()["id"]

    same_tenant_resp = client.get(f"/v1/kyc/cases/{case_id}", headers={"X-Tenant-Id": tenant})
    assert same_tenant_resp.status_code == 200

    cross_tenant_resp = client.get(f"/v1/kyc/cases/{case_id}", headers={"X-Tenant-Id": other_tenant})
    assert cross_tenant_resp.status_code == 404, "RLS must make another tenant's case invisible, not just forbidden"


def test_audit_log_is_recorded_and_hash_chain_verifies(client, tenant, approver):
    customer_id = _create_customer(client, tenant)
    case_id = _create_case(client, tenant, customer_id)
    client.get(f"/v1/kyc/cases/{case_id}/ai-recommendation", headers={"X-Tenant-Id": tenant})
    client.post(
        f"/v1/kyc/cases/{case_id}/decision",
        headers={"X-Tenant-Id": tenant},
        json={"approver_id": approver, "decision": "approved", "rationale": "ok"},
    )

    logs = client.get(
        "/v1/audit-logs",
        params={"resource_type": "kyc_case", "resource_id": case_id},
        headers={"X-Tenant-Id": tenant},
    ).json()
    actions = [log["action"] for log in logs]
    assert "kyc_case.created" in actions
    assert "kyc_case.ai_recommendation_generated" in actions
    assert "kyc_case.decided" in actions

    verify = client.post("/v1/audit-logs/verify", headers={"X-Tenant-Id": tenant}).json()
    assert verify["chain_intact"] is True
