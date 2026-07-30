# Tushar-Jain
# Aegis Compliance OS

**An AI-native Compliance Operating System for regulated financial institutions** — Banks, NBFCs, Insurance carriers, and FinTechs.

Aegis unifies KYC/AML, risk monitoring, regulatory intelligence, policy governance, and audit into a single AI-first platform. It is built around a **proprietary Small Language Model (SLM)** fine-tuned on financial regulation (RBI, SEBI, IRDAI, FATF, FinCEN, FCA, MAS, Basel, GDPR), backed by a **Retrieval-Augmented Generation (RAG)** layer over each tenant's own policies and regulatory corpus, with a **human-in-the-loop approval layer** on every AI decision that carries regulatory or financial consequence.

## Why this exists

Compliance teams at regulated institutions drown in three problems: (1) regulation changes faster than policy can be rewritten, (2) KYC/AML/risk decisions require evidence trails that most tools bolt on as an afterthought, and (3) generic LLMs hallucinate on jurisdiction-specific rules and can't be trusted unsupervised in a regulated environment. Aegis is designed around **AI proposes, human disposes** — every AI output is generated with citations back to source regulation, routed through a configurable approval workflow, and permanently logged for audit.

## Documentation

| # | Document | Contents |
|---|----------|----------|
| 1 | [System Architecture](01-system-architecture.md) | Full system diagram, layer-by-layer breakdown, data flow |
| 2 | [Database Schema](02-database-schema.md) | ERD, multi-tenant strategy, core table DDL |
| 3 | [AI Pipeline](03-ai-pipeline.md) | Ingestion → NLP → classification → RAG → generation → review loop |
| 4 | [Tech Stack](04-tech-stack.md) | Full stack by layer, with rationale |
| 5 | [Folder Structure](05-folder-structure.md) | Monorepo layout for services, AI, infra, frontend |
| 6 | [API Design](06-api-design.md) | REST conventions, auth, endpoint catalog, samples |
| 7 | [SLM + RAG Architecture](07-slm-rag-architecture.md) | Fine-tuning strategy, retrieval pipeline, grounding, evals |
| 8 | [Deployment Architecture](08-deployment-architecture.md) | AWS-primary reference deployment, GCP/Azure notes, DR |
| 9 | [Development Roadmap](09-development-roadmap.md) | MVP → Growth → Enterprise, phased over 24 months |
| 10 | [Cost Estimation](10-cost-estimation.md) | Infra, inference, and team cost by phase; unit economics |
| 11 | [Security & Compliance](11-security-compliance.md) | RBAC, encryption, audit logging, SOC 2 / ISO 27001 / GDPR mapping |
| 12 | [Open-Source SLM Candidates](12-open-source-slm-models.md) | Base model shortlist, embedding models, OCR/NER stack |

## Core design principles

1. **AI-first, human-final** — AI drafts, classifies, scores, and drafts remediation; a licensed compliance officer approves anything that changes a customer's status or a filed obligation.
2. **Every AI answer is a citation** — no ungrounded generation reaches a user. If the RAG layer can't retrieve supporting source text, the system says so instead of guessing.
3. **Multi-tenant by construction, single-tenant by option** — shared infrastructure with strict row-level isolation for mid-market; dedicated VPC/silo deployment for tier-1 banks with data-residency mandates.
4. **Immutable audit trail** — every AI inference, human decision, and data mutation is append-only and independently verifiable, because in compliance software the audit log *is* the product.
5. **Small models, not big bills** — a fine-tuned 7–8B parameter proprietary SLM handles >90% of domain-specific inference in-VPC; larger frontier models are used selectively, never on raw customer PII.
