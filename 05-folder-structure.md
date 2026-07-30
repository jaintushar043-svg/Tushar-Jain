# 5. Folder Structure

Monorepo, organized by deployable unit. Rationale: compliance/audit requirements benefit from a single reviewable history and shared CI security gates across all services, while each `services/*` and `ai/*` directory still builds/deploys independently.

```
aegis-compliance-os/
├── apps/
│   ├── web/                        # React compliance web app
│   │   ├── src/
│   │   │   ├── features/           # kyc, aml, policy, audit, workflows (feature-sliced)
│   │   │   ├── components/         # shared design-system components
│   │   │   ├── api/                # typed API client (generated from OpenAPI)
│   │   │   └── routes/
│   │   └── package.json
│   └── mobile/                     # React Native field-KYC app
│
├── services/                       # Go + Python backend microservices
│   ├── api-gateway/                # Kong config, gateway plugins
│   ├── identity/                   # auth, RBAC/ABAC, SSO
│   ├── tenant/                     # tenant provisioning & config
│   ├── kyc/
│   ├── aml/
│   ├── risk-scoring/
│   ├── policy/
│   ├── workflow/                   # Temporal workers + workflow definitions
│   ├── audit/                      # immutable audit writer
│   ├── regulatory-monitor/
│   └── notification/
│
├── ai/
│   ├── ingestion/                  # OCR, layout parsing, ingestion workers
│   ├── nlp-pipeline/                # classification, NER, summarization
│   ├── embeddings/                  # embedding service
│   ├── rag/                         # retrieval orchestrator, reranker, prompt templates
│   ├── slm/
│   │   ├── training/                 # LoRA/QLoRA/DPO fine-tuning scripts
│   │   ├── eval/                     # RAGAS + regulatory QA benchmark harness
│   │   ├── serving/                  # vLLM serving configs
│   │   └── model-registry/           # versioned checkpoints, promotion gates
│   ├── guardrails/                   # grounding checks, PII leak checks, policy filters
│   └── agents/                       # audit assistant, gap-analysis agent orchestration
│
├── data/
│   ├── migrations/                   # SQL migrations (per-service, tenant-RLS aware)
│   ├── seed/                         # regulation corpus seed data, demo tenants
│   └── warehouse/                    # dbt models for Snowflake marts
│
├── infra/
│   ├── terraform/
│   │   ├── modules/                  # vpc, eks, rds, kms, s3-worm, msk
│   │   └── environments/             # dev, staging, prod, tenant-silo templates
│   ├── helm/                         # per-service Helm charts
│   └── argocd/                       # GitOps app-of-apps definitions
│
├── libs/                             # shared internal libraries
│   ├── go/                           # shared Go packages (auth middleware, tracing)
│   ├── python/                       # shared Python packages (pii-redaction, prompt-lib)
│   └── proto/                        # gRPC/protobuf contracts between services
│
├── docs/
│   ├── architecture/                 # this design system
│   ├── runbooks/                     # on-call runbooks
│   ├── compliance/                   # SOC2/ISO27001 control evidence docs
│   └── api/                          # generated OpenAPI specs
│
├── tests/
│   ├── e2e/                          # Playwright end-to-end
│   ├── load/                         # k6 load tests
│   └── ai-eval/                      # golden-set regression tests for AI pipeline
│
├── .github/workflows/                 # CI: lint, test, build, security scan, deploy
└── Makefile
```

## 5.1 Conventions

- Every `services/*` and `ai/*` directory is independently buildable/testable (`make test` at that directory root) and independently deployable via its own Helm chart in `infra/helm/<name>`.
- `libs/proto` is the single source of truth for inter-service contracts; breaking changes require a version bump and are caught in CI via buf breaking-change detection.
- `docs/compliance/` holds live evidence mappings (which control, which code/config satisfies it, last review date) — treated as a first-class artifact reviewed every audit cycle, not an afterthought.
