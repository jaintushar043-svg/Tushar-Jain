# 6. API Design

## 6.1 Conventions

- **Style**: REST over HTTPS, JSON bodies, resource-oriented URLs. Internal service-to-service calls use gRPC; everything client-facing is REST for ecosystem/partner-integration friendliness.
- **Base URL**: `https://api.aegis-compliance.io/v1/{resource}` — tenant is derived from the authenticated principal, **never** from the URL, to make cross-tenant path-tampering structurally impossible.
- **Versioning**: URL major version (`/v1`); breaking changes ship as `/v2` with a minimum 12-month deprecation window on the prior version for enterprise tenants.
- **Auth**: OAuth 2.0 / OIDC (Authorization Code + PKCE for the web app, Client Credentials for partner/M2M integrations) — access token is a short-lived JWT (15 min), refresh token rotated on use. Partner integrations may alternatively use scoped, revocable API keys with HMAC request signing.
- **Idempotency**: all `POST` endpoints that create a resource accept an `Idempotency-Key` header; replays with the same key return the original result rather than duplicating.
- **Pagination**: cursor-based (`?cursor=...&limit=50`), never offset-based, to stay stable under concurrent writes on large tables like `transactions`.
- **Errors**: RFC 7807 `application/problem+json` — `{type, title, status, detail, instance, trace_id}`.
- **Rate limiting**: per-tenant + per-API-key token bucket at the gateway; `429` with `Retry-After`.
- **Webhooks**: outbound event delivery (`kyc.case.decided`, `aml.alert.raised`, `policy.gap.detected`) signed with HMAC-SHA256, at-least-once delivery with consumer-side idempotency expected.

## 6.2 Endpoint catalog (representative)

### Auth & Identity
```
POST   /v1/auth/token                 # OAuth2 token exchange
POST   /v1/auth/token/refresh
GET    /v1/users/me
GET    /v1/users
POST   /v1/users
PATCH  /v1/users/{userId}/roles
```

### Tenant management
```
GET    /v1/tenant
PATCH  /v1/tenant                     # feature flags, data-residency config
GET    /v1/tenant/usage
```

### KYC
```
POST   /v1/customers
GET    /v1/customers/{customerId}
POST   /v1/kyc/cases                                  # opens a case, kicks off async pipeline
GET    /v1/kyc/cases/{caseId}
POST   /v1/kyc/cases/{caseId}/documents                # multipart upload
GET    /v1/kyc/cases/{caseId}/documents/{docId}
GET    /v1/kyc/cases/{caseId}/ai-recommendation         # SLM output + citations
POST   /v1/kyc/cases/{caseId}/decision                  # human approve/reject/escalate
GET    /v1/kyc/cases/{caseId}/screening-results
```

### AML / transaction monitoring
```
POST   /v1/transactions                                 # or Kafka topic for bulk streaming ingest
GET    /v1/aml/alerts?status=open&severity=high
GET    /v1/aml/alerts/{alertId}
POST   /v1/aml/alerts/{alertId}/disposition
POST   /v1/aml/alerts/{alertId}/sar                     # file/flag SAR (human-gated)
```

### Risk
```
GET    /v1/customers/{customerId}/risk-score
GET    /v1/customers/{customerId}/risk-score/history
```

### Policy & gap analysis
```
POST   /v1/policies
POST   /v1/policies/{policyId}/versions                  # upload new version, triggers ingestion
GET    /v1/policies/{policyId}/versions/{versionId}
POST   /v1/gap-analysis/runs                              # {policyVersionId, regulationId}
GET    /v1/gap-analysis/runs/{runId}
GET    /v1/gap-analysis/runs/{runId}/results
POST   /v1/gap-analysis/results/{resultId}/review          # human sign-off
```

### Regulatory change monitoring
```
GET    /v1/regulations?jurisdiction=IN-RBI
GET    /v1/regulations/{regulationId}/changes
POST   /v1/regulations/{regulationId}/changes/{changeId}/acknowledge
```

### AI Assistant (RAG chat / audit assistant)
```
POST   /v1/assistant/query                                # {question, scope: policyId|regulationId|caseId}
POST   /v1/assistant/sessions                              # multi-turn audit interview session
POST   /v1/assistant/sessions/{sessionId}/messages
GET    /v1/assistant/sessions/{sessionId}
```

### Workflow & approvals
```
GET    /v1/workflows/{workflowId}
GET    /v1/approvals?assignee=me&status=pending
POST   /v1/approvals/{approvalId}/decision
```

### Audit
```
GET    /v1/audit-logs?resourceType=kyc_case&resourceId=...
GET    /v1/audit-logs/export                              # signed, time-bounded export for regulator requests
POST   /v1/audit-logs/verify                              # verifies hash-chain integrity over a range
```

## 6.3 Sample request/response — AI-assisted KYC recommendation

```http
GET /v1/kyc/cases/8f14e.../ai-recommendation
Authorization: Bearer <jwt>
```

```json
{
  "caseId": "8f14e...",
  "model": "aegis-slm-7b-v3.2",
  "recommendation": {
    "decision": "escalate_edd",
    "riskTier": "high",
    "confidence": 0.78,
    "rationale": "Customer's declared occupation (import/export trading) combined with incorporation in a jurisdiction flagged on the tenant's high-risk country list (FATF grey list, updated 2026-06) meets the criteria in Policy §4.2 for mandatory Enhanced Due Diligence.",
    "citations": [
      {
        "sourceType": "policy_clause",
        "documentId": "d1a2...",
        "clauseRef": "AML-Policy v7 §4.2",
        "snippet": "Customers incorporated in a jurisdiction on the current FATF grey/black list require EDD prior to onboarding approval."
      },
      {
        "sourceType": "regulation_clause",
        "documentId": "r9c3...",
        "clauseRef": "RBI Master Direction on KYC, Sec 38",
        "snippet": "..."
      }
    ]
  },
  "requiresHumanApproval": true,
  "status": "pending_review"
}
```

```json
POST /v1/kyc/cases/8f14e.../decision
{
  "decision": "approved",
  "matchesAiRecommendation": true,
  "rationale": "Concur with EDD escalation per cited policy clause.",
  "approverId": "u_772..."
}
```

## 6.4 Partner / SDK support

Server SDKs (TypeScript, Python, Go, Java) generated from the OpenAPI 3.1 spec published at `/v1/openapi.json`, versioned in lockstep with the API. Postman/Insomnia collections auto-published per release for integration teams at bank/NBFC partners.
