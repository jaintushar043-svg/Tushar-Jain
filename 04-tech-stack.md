# 4. Tech Stack

## 4.1 Overview by layer

| Layer | Technology | Rationale |
|---|---|---|
| **Frontend** | React + TypeScript, Vite, TanStack Query, shadcn/ui + Tailwind | Fast iteration, strong typing for a compliance UI where field correctness matters; component library keeps a dense data-grid-heavy UI consistent |
| **Mobile** | React Native | Shared logic/design system with web; single team can own both |
| **API Gateway** | Kong / AWS API Gateway | Multi-tenant routing, rate limiting, plugin ecosystem for auth |
| **Backend services** | Go (high-throughput services: AML, transaction ingest) + Python/FastAPI (AI-adjacent services: NLP pipeline, RAG orchestrator) | Go for low-latency, high-QPS transaction paths; Python where deep ML/NLP library ecosystem (HF Transformers, spaCy) is decisive |
| **Workflow engine** | Temporal | Durable execution for long-running, multi-step approval workflows that must survive service restarts and support human-in-the-loop waits |
| **Message bus** | Apache Kafka (MSK) or SQS/SNS for smaller tenants | Kafka for high-volume transaction streams and replayability (needed for AML backtesting); SQS as a lower-ops option for the pool tier |
| **Primary database** | PostgreSQL 16 (RDS/Aurora) with `pgvector`, `pgcrypto`, `citext` | Mature RLS support for multi-tenancy; pgvector avoids a second datastore at moderate scale |
| **Vector store (scale-out)** | Qdrant (self-hosted or Cloud) | For silo/tier-1 tenants exceeding pgvector's comfortable scale, or requiring dedicated resource isolation |
| **Search (BM25 / hybrid)** | OpenSearch | Hybrid retrieval alongside vector search; also powers general case/document search in the UI |
| **Object storage** | S3 (or GCS/Azure Blob) with SSE-KMS, Object Lock for WORM audit copies | Industry standard, native encryption + compliance-mode retention |
| **Cache** | Redis (ElastiCache) | Session state, rate limiting, workflow read-models |
| **Data warehouse** | Snowflake | Regulator reporting extracts, BI, model training data marts, isolated from OLTP load |
| **AI inference serving** | vLLM (proprietary SLM), Triton Inference Server for embedding/NER models | High-throughput, low-latency open-source serving with continuous batching; avoids per-token API cost/latency of hosted LLMs for the bulk of inference |
| **Fine-tuning** | Hugging Face `transformers` + `peft` (LoRA/QLoRA) + `trl` (DPO) on managed GPU clusters | Standard, well-supported tooling for parameter-efficient fine-tuning of 3–8B models |
| **Experiment tracking / eval** | MLflow + RAGAS + custom regulatory QA benchmark | Track fine-tune runs, gate promotion on retrieval/generation quality metrics |
| **LLM Gateway (fallback/general)** | LiteLLM proxy in front of Anthropic Claude / OpenAI (opt-in, non-PII tasks only) | Unified interface if a tenant opts into using a frontier model for e.g. general drafting; strictly gated by the PII redaction layer |
| **IAM / Auth** | Keycloak or Auth0 (OIDC/SAML), custom RBAC/ABAC service | SSO is table stakes for enterprise bank procurement; Keycloak for self-hosted/silo deployments |
| **Secrets & keys** | AWS KMS + HashiCorp Vault | Per-tenant envelope encryption keys, dynamic DB credentials |
| **Container orchestration** | Kubernetes (EKS), Karpenter for autoscaling (incl. GPU node pools) | Standard for multi-service, multi-tenant workload isolation and cost-aware autoscaling |
| **IaC** | Terraform + Helm | Reproducible, reviewable infra across tenant environments |
| **CI/CD** | GitHub Actions + Argo CD (GitOps) | Automated test/build/deploy with progressive delivery (canary) for model and service updates |
| **Observability** | OpenTelemetry, Prometheus + Grafana, Loki, Sentry | Unified tracing across sync API and async AI pipeline; critical for debugging RAG latency/quality issues |
| **Audit/immutable log** | S3 Object Lock (compliance mode) + hash-chained Postgres ledger table | Tamper-evident by construction, verifiable independently of the running application |

## 4.2 Why a polyglot backend (Go + Python), not one language

- **Go** handles the transaction ingestion and AML rule-evaluation hot path, where p99 latency and throughput under bursty core-banking load matter more than ML ecosystem access.
- **Python/FastAPI** owns everything touching the AI pipeline — OCR, NLP, embeddings, RAG orchestration, fine-tuning triggers — where the HF/PyTorch ecosystem is a 10x productivity multiplier over reimplementing in Go.
- Both communicate exclusively via the event bus and well-typed internal gRPC/REST contracts, so the language boundary never leaks into a shared library or shared database write path.

## 4.3 Build vs. buy calls

| Component | Decision | Why |
|---|---|---|
| ID verification / liveness | Buy (Onfido/Trulioo) | Regulated identity-proofing accreditation and biometric liveness are not core differentiators worth rebuilding |
| Sanctions/PEP/adverse-media lists | Buy (Refinitiv/Dow Jones) | List curation and coverage breadth is a data-licensing business, not an ML problem |
| SLM base model | Build on open weights (fine-tune) | Domain specialization and data-residency control are core differentiators; frontier-model APIs can't guarantee in-VPC PII isolation |
| Workflow engine | Buy (Temporal, self-hosted) | Durable execution is a solved, hard distributed-systems problem |
| Frontend design system | Build (on shadcn primitives) | Compliance UX (dense tables, side-by-side citation view, redline diffs) is differentiated enough to own |
