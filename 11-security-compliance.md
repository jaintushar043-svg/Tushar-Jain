# 11. Security & Compliance

Security is not a feature of Aegis — it is the sales pitch. A compliance platform that itself fails a security audit is disqualifying, not merely embarrassing.

## 11.1 RBAC / ABAC

- **Roles** are tenant-scoped (`roles` table) with system-defined defaults (`admin`, `compliance_officer`, `mlro`, `risk_analyst`, `auditor`, `read_only`) and tenant-custom roles for larger customers.
- **Permissions** are resource+action pairs (`kyc_case:approve`, `policy:publish`, `audit_log:export`) — fine enough that "can view KYC cases" and "can approve KYC cases" are separable, which regulators expect (maker-checker segregation of duties).
- **ABAC layer on top of RBAC**: attribute checks beyond role — e.g., a `compliance_officer` cannot approve a case they themselves were the AI-recommendation reviewer flagged as "related party" on, and cannot approve their own workflow step (maker-checker enforced in code, not just policy).
- **Enforcement point**: a policy-as-code engine (OPA/Rego) evaluated at the API gateway and re-checked at the service layer (defense in depth — never trust the gateway decision alone inside a service).
- **Least privilege for AI**: the AI service accounts that write `ai_inferences` have **no** grant to write directly to `kyc_cases.risk_tier`, `aml_alerts.status`, or any field that constitutes a final compliance decision — only a human-attributed `approvals` write can flip those fields. This is enforced at the database grant level, not just application logic, so a bug or prompt-injection in the AI path cannot silently become an unreviewed compliance decision.

## 11.2 Encryption

| Layer | Mechanism |
|---|---|
| At rest — database | AWS RDS/Aurora encryption (AES-256) via KMS, plus application-level envelope encryption for PII fields (`customers.pii_encrypted`) so even a DB snapshot leak doesn't expose plaintext PII without the tenant's KMS key |
| At rest — object storage | S3 SSE-KMS, per-tenant CMK |
| At rest — audit archive | S3 Object Lock (compliance mode, non-deletable for the retention period) + KMS |
| In transit | TLS 1.2+ everywhere (mTLS between internal services), HSTS enforced at the edge |
| Key management | Per-tenant KMS Customer Master Keys; silo tenants may bring their own key (BYOK) or manage keys entirely in their own KMS/HSM via cross-account grants |
| Secrets | HashiCorp Vault / AWS Secrets Manager, dynamic short-lived DB credentials, no long-lived secrets in config or environment files |
| Field-level | Tokenization for search-required PII (e.g., name matching for sanctions screening uses a hashed/tokenized lookup, not plaintext indexing) |

## 11.3 Audit logging

- **Append-only, hash-chained** (`audit_logs.prev_hash`/`record_hash`) — each record's hash includes the previous record's hash, so any retroactive tampering breaks the chain and is detectable via `POST /v1/audit-logs/verify`.
- **Mirrored to WORM storage** (S3 Object Lock, compliance mode) on a short delay — even a compromised database admin credential cannot rewrite history that's already landed in the immutable archive.
- **Every AI inference is logged**, including inputs (by reference, not full PII payload), outputs, citations, model version, and confidence — this is what lets Aegis answer "why did the system recommend X" for any historical case, a hard requirement for regulator examination.
- **Every human decision is logged** with actor identity, timestamp, and rationale — satisfies maker-checker evidentiary requirements across every regulator covered (RBI, FCA, FinCEN, IRDAI all require this in some form).
- **Retention**: tenant-configurable, defaulting to 7 years (typical AML record-keeping requirement), up to 10 years for jurisdictions that require it; retention period is enforced at the Object Lock policy level, not just application logic.

## 11.4 SOC 2 (Type I → Type II)

Trust Service Criteria coverage:

| Criterion | Representative controls |
|---|---|
| Security | MFA enforced org-wide, RBAC/ABAC, encryption at rest/in transit, vulnerability scanning (SAST/DAST/dependency scanning in CI), quarterly pen tests, incident response runbook with defined SLAs |
| Availability | Multi-AZ deployment, documented RTO/RPO ([§8.4](08-deployment-architecture.md)), DR game-days, status page + SLA monitoring |
| Processing integrity | Idempotent APIs, hash-chained audit log, AI-eval regression gates on every model promotion, change-management approval workflow for production deploys |
| Confidentiality | Per-tenant encryption keys, tenant data isolation (RLS/schema/silo per tier), NDA + least-privilege access for employees, data classification policy |
| Privacy | See GDPR section below |

Path: **Type I** (point-in-time control design assessment) targeted end of Phase 2, **Type II** (6-month operating-effectiveness observation) targeted through Phase 3, report issued early Phase 4. `docs/compliance/` in the repo holds the live control-to-evidence mapping reviewed each audit cycle.

## 11.5 ISO 27001

Annex A control mapping highlights (illustrative, not exhaustive):

- **A.5 (Organizational)**: information security policy, supplier (sub-processor) security review process — critical given reliance on ID-verification/screening vendors.
- **A.8 (Asset management / access control)**: asset inventory including model checkpoints and training datasets (an AI-specific asset class most ISO programs miss), classified by sensitivity.
- **A.8.24 (Cryptography)**: key management policy covering both data encryption keys and, distinctly, model weight/adapter storage (proprietary SLM weights are a protected asset — exfiltration risk, not just a data-privacy risk).
- **A.5.23 / A.8.28 (Secure development)**: secure SDLC, code review gates, dependency/SAST scanning as CI-blocking checks.
- **A.5.30 (ICT readiness for business continuity)**: DR plan, tested per [§8.4](08-deployment-architecture.md).

Certification targeted Phase 4, run in parallel with SOC 2 Type II using a shared control-evidence base to avoid duplicated audit effort.

## 11.6 GDPR (and equivalent regimes — DPDP Act in India, etc.)

- **Lawful basis & DPAs**: standard Data Processing Agreements with every tenant; sub-processor list (ID verification, screening vendors, cloud provider) published and change-notified per GDPR Art. 28.
- **Data subject rights**: right of access and rectification supported directly (customer PII is queryable/correctable via the KYC service); **right to erasure is deliberately constrained** — AML/KYC record-keeping law in every covered jurisdiction *overrides* GDPR erasure for records within the statutory retention window (this is GDPR Art. 17(3)(b) working as intended, not a gap). Aegis's data model handles this by supporting **crypto-shredding**: erasure requests outside the retention-protected path destroy the tenant's per-subject encryption sub-key, rendering the PII permanently unrecoverable while the (now-unreadable) audit shell record remains for statistical/regulatory count purposes.
- **Data residency**: enforced structurally via the per-tenant `region` pinning described in [§8.3](08-deployment-architecture.md) — not a policy promise, a routing-layer guarantee.
- **Data minimization in the AI pipeline**: PII redaction before embedding/generation ([AI Pipeline §3.3](03-ai-pipeline.md)) means the vector index and any external LLM Gateway path structurally never hold raw PII.
- **DPIA**: a Data Protection Impact Assessment is a required deliverable before any tenant onboards AI-driven risk scoring or automated decision-support that affects a data subject — templated and repeated per tenant given GDPR Art. 22 concerns around automated decision-making; mitigated because Aegis's design mandates human-in-the-loop for every decision with legal/financial effect (satisfies the Art. 22(1) "solely automated" carve-out by construction).

## 11.7 AI-specific governance

- **Model cards** published per jurisdiction adapter: training data provenance, eval benchmark scores, known limitations, last-updated date.
- **Bias/fairness audits**: periodic disparate-impact testing on AI risk-scoring outputs across protected characteristics available in the (jurisdiction-appropriate) evaluation dataset, reviewed by an independent function, not the model's own training team.
- **Human-in-the-loop as a control, not a UX choice**: enforced at the database-grant level ([§11.1](11-security-compliance.md)) so it is auditable as an actual security control, satisfying emerging AI-specific regulatory expectations (EU AI Act high-risk system requirements for human oversight map directly onto this).
- **Incident response**: AI-specific runbook entries for model-output incidents (e.g., a hallucinated citation reaching a user) distinct from traditional security incidents, with its own severity taxonomy and postmortem process feeding back into the eval benchmark.

## 11.8 Application security

- SAST (Semgrep), dependency/SCA scanning (Snyk/Dependabot), container image scanning (Trivy) — all CI-blocking.
- Quarterly third-party penetration testing, annual red-team exercise once at Enterprise scale.
- Responsible disclosure program / bug bounty from Phase 2 onward.
- Prompt-injection–specific testing as part of the AI-eval regression suite (adversarial documents designed to manipulate the SLM's output via embedded instructions), given documents are an untrusted-input surface feeding directly into generation.
