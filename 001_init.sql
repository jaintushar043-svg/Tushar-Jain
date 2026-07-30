-- Aegis Compliance OS — initial MVP schema
-- Scope: tenancy, identity/RBAC, KYC case management, document/RAG substrate, audit log.
-- Full schema (AML, policy gap analysis, workflow engine) is in docs/architecture/02-database-schema.md
-- and lands in later phases per docs/architecture/09-development-roadmap.md.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
CREATE EXTENSION IF NOT EXISTS citext;
CREATE EXTENSION IF NOT EXISTS vector;

-- ── Tenancy & Identity ─────────────────────────────────────────────
CREATE TABLE tenants (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                TEXT NOT NULL,
    tier                TEXT NOT NULL DEFAULT 'pool' CHECK (tier IN ('pool','bridge','silo')),
    region              TEXT NOT NULL DEFAULT 'local',
    industry            TEXT NOT NULL CHECK (industry IN ('bank','nbfc','insurance','fintech')),
    status              TEXT NOT NULL DEFAULT 'active',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    email           CITEXT NOT NULL,
    full_name       TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, email)
);

CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID REFERENCES tenants(id),
    name        TEXT NOT NULL,
    UNIQUE (tenant_id, name)
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(id),
    role_id UUID NOT NULL REFERENCES roles(id),
    PRIMARY KEY (user_id, role_id)
);

-- ── KYC ────────────────────────────────────────────────────────────
CREATE TABLE customers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    external_ref        TEXT,
    customer_type       TEXT NOT NULL CHECK (customer_type IN ('individual','entity')),
    display_name        TEXT NOT NULL,
    country             TEXT NOT NULL,
    onboarding_status   TEXT NOT NULL DEFAULT 'pending',
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE kyc_cases (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           UUID NOT NULL REFERENCES tenants(id),
    customer_id         UUID NOT NULL REFERENCES customers(id),
    case_type           TEXT NOT NULL CHECK (case_type IN ('onboarding','periodic_review','edd','remediation')),
    status              TEXT NOT NULL DEFAULT 'in_progress',
    risk_tier           TEXT CHECK (risk_tier IN ('low','medium','high','prohibited')),
    ai_recommendation   JSONB,
    decided_by          UUID REFERENCES users(id),
    decision            TEXT CHECK (decision IN ('approved','rejected','escalated')),
    decision_rationale  TEXT,
    decided_at          TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE kyc_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    kyc_case_id     UUID NOT NULL REFERENCES kyc_cases(id),
    doc_type        TEXT NOT NULL,
    storage_uri     TEXT NOT NULL,
    classification  TEXT,
    uploaded_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Document / RAG substrate ───────────────────────────────────────
CREATE TABLE documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    source_type     TEXT NOT NULL CHECK (source_type IN ('policy','regulation','kyc_doc')),
    storage_uri     TEXT NOT NULL,
    classification  TEXT,
    summary         TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE document_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES tenants(id),
    document_id     UUID NOT NULL REFERENCES documents(id),
    chunk_index     INT NOT NULL,
    text            TEXT NOT NULL,
    embedding       VECTOR(384)
);
CREATE INDEX document_chunks_embedding_idx ON document_chunks USING hnsw (embedding vector_cosine_ops);

-- ── Audit (append-only, hash-chained) ──────────────────────────────
CREATE TABLE audit_logs (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    actor_id        UUID,
    actor_type      TEXT NOT NULL CHECK (actor_type IN ('human','ai','system')),
    action          TEXT NOT NULL,
    resource_type   TEXT NOT NULL,
    resource_id     UUID,
    before_state    JSONB,
    after_state     JSONB,
    prev_hash       TEXT NOT NULL,
    record_hash     TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Row-Level Security: every tenant-scoped table is isolated by app.current_tenant ─
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE kyc_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE kyc_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON users USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON customers USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON kyc_cases USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON kyc_documents USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON documents USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON document_chunks USING (tenant_id = current_setting('app.current_tenant', true)::uuid);
CREATE POLICY tenant_isolation ON audit_logs USING (tenant_id = current_setting('app.current_tenant', true)::uuid);

-- audit_logs is insert-only for the application role: no UPDATE/DELETE grants issued to app_user below.
CREATE ROLE app_user NOLOGIN;
GRANT SELECT, INSERT, UPDATE ON tenants, users, roles, user_roles, customers, kyc_cases, kyc_documents, documents, document_chunks TO app_user;
GRANT SELECT, INSERT ON audit_logs TO app_user;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_user;
